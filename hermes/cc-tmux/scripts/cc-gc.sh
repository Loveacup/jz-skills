#!/usr/bin/env bash
# cc-gc.sh — CC session 垃圾回收（PRD R9c 堆积检测 + R9d Session GC）
#
# 纯 bash + tmux + 文件系统，可独立运行（不依赖 cc-monitor / iii Engine）。
#
# Usage:
#   cc-gc.sh [--mode scan|gc|suggest] [--apply]
#     scan     快速全量扫描 → 表格摘要（默认）
#     gc       列出 GC 候选 + 建议动作（默认【只读·干运行】，不杀任何 session）
#     suggest  一行简洁建议
#     --apply  仅在 gc 模式生效：执行【僵尸清理】(删孤儿锁目录 + 陈旧 state/heartbeat/turn-done)。
#              注意：--apply 只清理【已死 session 的孤儿文件】，绝不 kill 任何存活 session。
#
# 3 安全规则：
#   1. 绝不自动杀存活 session——只输出建议，kill 必须 Alex 确认。--apply 仅清死 session 的孤儿文件。
#   2. 活跃不碰——TOOL/THINKING/WAITING_AGENTS → 跳过（kind=active-skip），永不入 kill 候选。
#   3. 先归档后清理——completed 候选附 cc-output 产物计数 + 提醒先确认已归档/commit 再 kill。
#
# 可移植/可测：
#   CC_GC_TMUX    tmux 调用（默认 "tmux"）——测试注入 stub
#   CC_GC_TMPDIR  状态文件基目录（默认 "/tmp"）——锁/心跳/turn-done/cc-output 都在此下
#
# 机器断言行（stderr，非给用户 relay）：
#   GCMETA mode=.. total=.. heap_warn=.. zombie=.. completed=.. idle2h=.. active=.. overflow=..
#   GCITEM kind=zombie|completed|idle2h|idle|active-skip session=.. state=.. age=.. turn_done=.. artifacts=..
#   GCAPPLY action=clean-zombie session=.. lock=..
#   GColdest session=.. age=..

set -euo pipefail

MODE="scan"; APPLY=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)  [[ $# -ge 2 ]] || { echo "❌ cc-gc: --mode requires a value" >&2; exit 2; }; MODE="$2"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    -h|--help) sed -n '2,18p' "$0" >&2; exit 0 ;;
    *) echo "❌ cc-gc: unknown arg: $1" >&2; exit 2 ;;
  esac
done
case "$MODE" in scan|gc|suggest) ;; *) echo "❌ cc-gc: --mode must be scan|gc|suggest (got '$MODE')" >&2; exit 2 ;; esac

TMUX="${CC_GC_TMUX:-tmux}"
TMP="${CC_GC_TMPDIR:-/tmp}"
NOW=$(date +%s)
IDLE_THRESHOLD="${CC_GC_IDLE_S:-7200}"   # 2h
HEAP_THRESHOLD=3                          # R9c: 残留 >3 → 告警
OVERFLOW_THRESHOLD=8                      # R9d cond4: 活跃 >8 → 告警

# shellcheck disable=SC2086  # CC_GC_TMUX 需词分割（"bash stub.sh"）
tmuxc() { $TMUX "$@"; }

# ── classify <session> — 6 状态机（移植自 cc-start.sh classify）──
classify() {
  local s="$1" pane last3 lastline prompt content
  pane=$(tmuxc capture-pane -t "$s" -p -S -20 2>/dev/null || echo "")
  [[ -z "$pane" ]] && { echo "EMPTY"; return; }
  if printf '%s' "$pane" | grep -qE 'Waiting for [0-9]+ background agent'; then echo "WAITING_AGENTS"; return; fi
  last3=$(printf '%s\n' "$pane" | grep -v '^[[:space:]]*$' | tail -3)
  prompt=$(printf '%s\n' "$last3" | grep '❯' | tail -1 || true)
  if [[ -n "$prompt" ]]; then
    content=$(printf '%s' "$prompt" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
    [[ -z "$content" ]] && { echo "IDLE"; return; }
  fi
  if printf '%s' "$pane" | grep -qE '⏺|●'; then echo "TOOL"; return; fi
  if printf '%s' "$pane" | grep -qE '[✻✳✶✢✽]'; then echo "THINKING"; return; fi
  if printf '%s' "$pane" | grep -q 'bypass permissions on'; then echo "IDLE"; return; fi
  # crash-to-shell: bare shell prompt at bottom, no bypass banner
  lastline=$(printf '%s\n' "$pane" | grep -v '^[[:space:]]*$' | tail -1 || true)
  if printf '%s' "$lastline" | grep -qE '[%$#][[:space:]]*$'; then echo "SHELL"; return; fi
  echo "UNKNOWN"
}

# ── hb_age <session> — 心跳文件 mtime 年龄(秒)，无心跳 → -1 ──
hb_age() {
  local hb="$TMP/cc-heartbeat-$1" m
  [[ -f "$hb" ]] || { echo -1; return; }
  m=$(stat -f %m "$hb" 2>/dev/null || echo 0)
  echo $(( NOW - m ))
}
# count regular files under cc-output/<session>/
artifacts_of() {
  local dir="$TMP/cc-output/$1"
  [[ -d "$dir" ]] || { echo 0; return; }
  find "$dir" -type f 2>/dev/null | wc -l | tr -d ' '
}

emit() { echo "$*" >&2; }   # machine line → stderr

ZOMBIE=0 COMPLETED=0 IDLE2H=0 IDLE_PLAIN=0 ACTIVE=0 TOTAL=0
GC_LINES=""      # human candidate lines (stdout, gc mode)
OLDEST_BUF=""    # "age<TAB>session" for active sessions (overflow oldest)

# ═══ 1) 僵尸：锁目录指向已死 session ═══════════════════════════
for lock in "$TMP"/cc-lock-*/; do
  [[ -d "$lock" ]] || continue
  sess=$(cat "$lock/session" 2>/dev/null || echo "")
  [[ -n "$sess" ]] || continue
  if tmuxc has-session -t "$sess" 2>/dev/null; then continue; fi   # 存活 → 非僵尸
  ZOMBIE=$((ZOMBIE+1))
  emit "GCITEM kind=zombie session=$sess lock=${lock%/}"
  GC_LINES="${GC_LINES}  🧟 僵尸: ${sess}（锁 ${lock%/} 指向的 session 已死）→ "$'\n'
  if [[ "$MODE" == "gc" && "$APPLY" == true ]]; then
    rm -rf "$lock" 2>/dev/null || true
    rm -f "$TMP/cc-state-$sess.log" "$TMP/cc-heartbeat-$sess" "$TMP/cc-turn-done-$sess" 2>/dev/null || true
    emit "GCAPPLY action=clean-zombie session=$sess lock=${lock%/}"
    GC_LINES="${GC_LINES}     ✅ 已清理孤儿锁 + state/heartbeat/turn-done"$'\n'
  else
    GC_LINES="${GC_LINES}     建议: cc-gc.sh --mode gc --apply 清理孤儿文件（session 已死，安全）"$'\n'
  fi
done

# ═══ 2) 存活 hermes-cc-* session ═══════════════════════════════
SESSIONS=$(tmuxc list-sessions -F '#{session_name}' 2>/dev/null || true)
if [[ -n "$SESSIONS" ]]; then
  while IFS= read -r s; do
    [[ -z "$s" ]] && continue
    [[ "$s" == hermes-cc-* ]] || continue
    TOTAL=$((TOTAL+1))
    st=$(classify "$s")
    age=$(hb_age "$s")
    td=0; [[ -f "$TMP/cc-turn-done-$s" ]] && td=1
    arts=$(artifacts_of "$s")
    case "$st" in
      TOOL|THINKING|WAITING_AGENTS)
        ACTIVE=$((ACTIVE+1))
        emit "GCITEM kind=active-skip session=$s state=$st age=$age turn_done=$td artifacts=$arts"
        OLDEST_BUF="${OLDEST_BUF}${age}	${s}"$'\n'
        ;;
      *)  # IDLE / EMPTY / UNKNOWN / SHELL → 可能可清
        if [[ "$td" -eq 1 ]]; then
          COMPLETED=$((COMPLETED+1))
          emit "GCITEM kind=completed session=$s state=$st age=$age turn_done=1 artifacts=$arts"
          GC_LINES="${GC_LINES}  ✅ 完成: ${s}（state=$st · 产物 ${arts} 个）→ 先确认已归档/commit，再 cc-finish --kill-session"$'\n'
        elif [[ "$age" -gt "$IDLE_THRESHOLD" ]]; then
          IDLE2H=$((IDLE2H+1))
          emit "GCITEM kind=idle2h session=$s state=$st age=$age turn_done=0 artifacts=$arts"
          GC_LINES="${GC_LINES}  💤 IDLE>2h: ${s}（state=$st · 心跳陈旧 ${age}s）→ 待清理，确认无用后 kill"$'\n'
        else
          IDLE_PLAIN=$((IDLE_PLAIN+1))
          emit "GCITEM kind=idle session=$s state=$st age=$age turn_done=0 artifacts=$arts"
        fi
        ;;
    esac
  done <<< "$SESSIONS"
fi

HEAP_WARN=0;  [[ "$TOTAL"  -gt "$HEAP_THRESHOLD" ]]     && HEAP_WARN=1
OVERFLOW=0;   [[ "$ACTIVE" -gt "$OVERFLOW_THRESHOLD" ]] && OVERFLOW=1

# overflow → 列出最旧 active session（按 age 降序，age 大=旧）
OLDEST_OUT=""
if [[ "$OVERFLOW" -eq 1 && -n "$OLDEST_BUF" ]]; then
  while IFS=$'\t' read -r a sn; do
    [[ -z "$sn" ]] && continue
    emit "GColdest session=$sn age=$a"
    OLDEST_OUT="${OLDEST_OUT}    · ${sn}（age=${a}s）"$'\n'
  done < <(printf '%s' "$OLDEST_BUF" | grep -v '^[[:space:]]*$' | sort -t$'\t' -k1 -rn | head -3)
fi

emit "GCMETA mode=$MODE total=$TOTAL heap_warn=$HEAP_WARN zombie=$ZOMBIE completed=$COMPLETED idle2h=$IDLE2H active=$ACTIVE overflow=$OVERFLOW"

# ═══ 输出（stdout，relay）═══════════════════════════════════════
KILLABLE=$((COMPLETED + IDLE2H))

case "$MODE" in
  suggest)
    parts=""
    [[ "$COMPLETED" -gt 0 ]] && parts="${parts}${COMPLETED} 个已完成的 session 可 kill · "
    [[ "$IDLE2H"    -gt 0 ]] && parts="${parts}${IDLE2H} 个 IDLE>2h 可清理 · "
    [[ "$ZOMBIE"    -gt 0 ]] && parts="${parts}${ZOMBIE} 个僵尸锁可清理(--apply) · "
    if [[ -z "$parts" ]]; then
      echo "💡 cc-gc: 无可清理项（total=$TOTAL · active=${ACTIVE}）"
    else
      echo "💡 cc-gc 建议: ${parts%· }"
      [[ "$HEAP_WARN" -eq 1 ]] && echo "   ⚠️ 残留 $TOTAL 个 hermes-cc session（>${HEAP_THRESHOLD}），建议收一收"
    fi
    ;;
  scan)
    echo "===📡 BEGIN (relay verbatim)==="
    echo "📋 cc-gc 扫描: total=$TOTAL · active=$ACTIVE · completed=$COMPLETED · idle>2h=$IDLE2H · zombie=$ZOMBIE"
    [[ "$HEAP_WARN" -eq 1 ]] && echo "  ⚠️ R9c 堆积: $TOTAL 个 hermes-cc session（>${HEAP_THRESHOLD}）→ 建议清理"
    if [[ "$OVERFLOW" -eq 1 ]]; then
      echo "  ⚠️ R9d 超限: $ACTIVE 个活跃 session（>${OVERFLOW_THRESHOLD}）。最旧:"
      printf '%s' "$OLDEST_OUT"
    fi
    [[ -n "$GC_LINES" ]] && { echo "  ── 候选 ──"; printf '%s' "$GC_LINES"; }
    [[ "$KILLABLE" -eq 0 && "$ZOMBIE" -eq 0 ]] && echo "  ✓ 无可清理项"
    echo "===📡 END==="
    ;;
  gc)
    echo "===📡 BEGIN (relay verbatim)==="
    if [[ "$APPLY" == true ]]; then
      echo "🧹 cc-gc GC（--apply：已清理僵尸孤儿文件；存活 session 一律只建议不杀）"
    else
      echo "🧹 cc-gc GC（干运行·只读：以下为建议，未执行任何清理/kill）"
    fi
    if [[ -n "$GC_LINES" ]]; then
      printf '%s' "$GC_LINES"
    else
      echo "  ✓ 无 GC 候选"
    fi
    [[ "$HEAP_WARN" -eq 1 ]] && echo "  ⚠️ R9c 堆积: $TOTAL 个 session（>${HEAP_THRESHOLD}）"
    [[ "$OVERFLOW"  -eq 1 ]] && { echo "  ⚠️ R9d 超限: $ACTIVE 活跃（>${OVERFLOW_THRESHOLD}）。最旧:"; printf '%s' "$OLDEST_OUT"; }
    echo "  ℹ️ 安全规则: 绝不自动杀存活 session · 活跃不碰 · 先确认归档/commit 再 kill"
    echo "===📡 END==="
    ;;
esac
exit 0
