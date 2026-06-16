#!/usr/bin/env bash
# cc-finish.sh — Close out a CC session: residual-input safety gate,
#                monitoring-gap audit (heartbeat + state log), artifact verify,
#                lock release, optional kill.
#
# Usage:
#   cc-finish.sh --session <name> --target <lock-target> [--release-lock]
#                [--kill-session] [--verify <glob>] [--force]
#
# --force  : override the monitoring-gap rejection ONLY (never the residual gate).
#
# Mechanical gate (v1.3): if cc-monitor.sh was not run within the last 120s
# (heartbeat stale) OR never ran (no heartbeat), finish REJECTS completion
# (exit 2, lock kept, session kept) unless --force. This is the teeth behind
# "report on cadence" — silence has a script-level consequence.

set -euo pipefail

SESSION="" TARGET="" RELEASE_LOCK=false KILL=false VERIFY_PATTERN="" FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)  SESSION="$2"; shift 2 ;;
    --target)   TARGET="$2"; shift 2 ;;
    --release-lock) RELEASE_LOCK=true; shift ;;
    --kill-session) KILL=true; shift ;;
    --verify)   VERIFY_PATTERN="$2"; shift 2 ;;
    --force)    FORCE=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "Usage: cc-finish.sh --session <name> --target <t> [--release-lock] [--kill-session] [--verify <glob>] [--force]" >&2
  exit 1
fi

NOW=$(date +%s)
HB="/tmp/cc-heartbeat-${SESSION}"
STATELOG="/tmp/cc-state-${SESSION}.log"
EXIT_CODE=0
GAP_BLOCK=false

echo "===📋 BEGIN cc-finish (relay verbatim)==="

# ── 1. Residual-input safety gate (border-aware ❯ extraction) ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
  INPUT_LINE=$(tmux capture-pane -t "$SESSION" -p -S -8 2>/dev/null | grep '❯' | tail -1 || true)
  # strip box borders + ❯ + surrounding space; whatever remains is typed residual
  RESIDUAL=$(printf '%s' "$INPUT_LINE" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
  if [[ -n "$RESIDUAL" ]]; then
    DANGER=$(printf '%s' "$RESIDUAL" | grep -ioE 'rm -rf|rm -fr|git push|git reset --hard|git clean|sudo |mkfs|dd if=|killall|kill -9|>[[:space:]]*/[A-Za-z]' | paste -sd',' - | sed 's/,/, /g' || true)
    echo "⚠️  ❯ 残留输入: ${RESIDUAL:0:90}"
    if [[ -n "$DANGER" ]]; then
      echo "  ⛔ 危险模式命中: $DANGER"
      echo "  → CC 建议/预填的危险操作 ≠ 你的授权。绝不要回车。"
    fi
    echo "  → 先 C-u 清行（tmux send-keys -t $SESSION C-u）再收尾，勿按 Enter。"
    EXIT_CODE=1
  else
    echo "✓ ❯ 无残留输入（输入框干净）"
  fi
else
  echo "ℹ️  Session '$SESSION' 不存在（可能已退出）"
fi

# ── 2. Monitoring-gap audit (heartbeat freshness) ─────────────
if [[ -f "$HB" ]]; then
  HB_EPOCH=0; HB_RUNS=0; HB_STATE="?"; HB_SEQ=0
  # heartbeat schema: EPOCH|RUNCOUNT|STATE|TOKENS|TOKCHG_EPOCH|SEQ|THINK_TIME
  # (trailing _ absorbs THINK_TIME so HB_SEQ stays clean)
  IFS='|' read -r HB_EPOCH HB_RUNS HB_STATE _ _ HB_SEQ _ < "$HB" 2>/dev/null || true
  [[ -z "${HB_EPOCH:-}" || ! "${HB_EPOCH}" =~ ^[0-9]+$ ]] && HB_EPOCH=0
  AGE=$((NOW - HB_EPOCH))
  if [[ "$AGE" -gt 120 ]]; then
    echo "⚠️  监控间隙: 距最后一次 cc-monitor ${AGE}s（>120s），最后状态=${HB_STATE}"
    $FORCE || GAP_BLOCK=true
  else
    echo "✓ 监控新鲜: 距最后一次 cc-monitor ${AGE}s（最后状态=${HB_STATE}, 共 ${HB_RUNS} 次）"
  fi
else
  echo "⚠️  监控缺失: 从未跑过 cc-monitor（无心跳文件）"
  $FORCE || GAP_BLOCK=true
fi

# ── 3. State-transition summary (from JSONL log) ──────────────
if [[ -f "$STATELOG" ]]; then
  RUNS=$(grep -c '' "$STATELOG" 2>/dev/null || echo 0)
  TRANSITIONS=$(grep -c '"changed":true' "$STATELOG" 2>/dev/null || echo 0)
  SEQ_STATES=$(grep '"changed":true' "$STATELOG" 2>/dev/null | grep -oE '"state":"[^"]+"' | sed -E 's/"state":"([^"]+)"/\1/' | paste -sd'→' - 2>/dev/null || true)
  # max gap between consecutive monitor runs
  MAXGAP=0; PREV=0
  while IFS= read -r e; do
    [[ -z "$e" ]] && continue
    if [[ "$PREV" -ne 0 ]]; then
      d=$((e - PREV)); [[ "$d" -gt "$MAXGAP" ]] && MAXGAP=$d
    fi
    PREV=$e
  done < <(grep -oE '"epoch":[0-9]+' "$STATELOG" | sed 's/"epoch"://')
  echo "📊 监控记录: ${RUNS} 次抓屏 · ${TRANSITIONS} 次状态转移 · 最大间隙 ${MAXGAP}s"
  [[ -n "$SEQ_STATES" ]] && echo "   状态序列: ${SEQ_STATES}"
  [[ "$MAXGAP" -gt 120 ]] && echo "   ⚠️ 存在 >120s 的监控间隙"
else
  echo "📊 监控记录: 无状态日志"
fi

# ── 4. Hard gate: reject completion on monitoring gap ─────────
if $GAP_BLOCK; then
  echo "⛔ 拒绝收尾：监控未达标。补跑一次 cc-monitor 再收尾，或加 --force 覆盖。"
  echo "   (lock 未释放、session 未杀——收尾未完成)"
  echo "===📋 END cc-finish==="
  exit 2
fi

# ── 5. Verify artifacts (fixed: was `-newer /tmp`, near-useless) ──
if [[ -n "$VERIFY_PATTERN" ]]; then
  # -L: /tmp is a symlink to /private/tmp on macOS; without -L find won't descend.
  FILES=$(find -L /tmp -maxdepth 2 -name "$VERIFY_PATTERN" -type f 2>/dev/null | head -50 || true)
  if [[ -n "$FILES" ]]; then
    echo "✓ 产物命中 '$VERIFY_PATTERN':"
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      SIZE=$(wc -c < "$f" 2>/dev/null | tr -d ' ' || echo 0)
      FLAG=""; [[ "$SIZE" -eq 0 ]] && FLAG="  ⚠️ 0 字节（空文件！）"
      echo "  $f (${SIZE} bytes)${FLAG}"
    done <<< "$FILES"
  else
    echo "⚠️  未找到匹配 '$VERIFY_PATTERN' 的产物 → 回 MONITOR，告诉 CC『文件未落盘』"
    EXIT_CODE=1
  fi
fi

# ── 6. Release lock ───────────────────────────────────────────
if $RELEASE_LOCK && [[ -n "$TARGET" ]]; then
  LOCKDIR="/tmp/cc-lock-${TARGET}"
  if [[ -d "$LOCKDIR" ]]; then
    rm -rf "$LOCKDIR"
    echo "✓ Lock 已释放: $LOCKDIR"
  else
    echo "ℹ️  无 lock 目录: $LOCKDIR"
  fi
fi

# ── 7. Kill session (+ clean state files post-mortem) ─────────
if $KILL; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
    echo "✓ Session 已杀: $SESSION"
  else
    echo "ℹ️  Session 已不存在: $SESSION"
  fi
  # §3.7 + D-4 cleanup: all per-session state now shares ONE key — the tmux session
  # name. cc-start injects CC_TMUX_SESSION=<tmux name>, so the in-CC hooks key their
  # output (cc-output/, cc-state log, rewake counter) by the SAME name cc-finish knows.
  # So cc-finish can finally drop the hook-written artifacts alongside its own state,
  # solving the /tmp leak. (If CC_TMUX_SESSION did not propagate, those files were
  # keyed by the CC UUID instead and simply won't match here — harmless miss, no error.)
  rm -f  "$HB" "$STATELOG" "/tmp/cc-expect-${SESSION}" \
         "/tmp/cc-counter-stop-precheck-${SESSION}.json"
  rm -rf "/tmp/cc-output/${SESSION}"
fi

echo "===📋 END cc-finish==="
exit $EXIT_CODE
