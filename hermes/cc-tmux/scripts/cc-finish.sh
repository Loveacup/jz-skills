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

SESSION="" TARGET="" RELEASE_LOCK=false KILL=false VERIFY_PATTERN="" FORCE=false CLEAN_TOPIC_MAP=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)  SESSION="$2"; shift 2 ;;
    --target)   TARGET="$2"; shift 2 ;;
    --release-lock) RELEASE_LOCK=true; shift ;;
    --kill-session) KILL=true; shift ;;
    --verify)   VERIFY_PATTERN="$2"; shift 2 ;;
    --force)    FORCE=true; shift ;;
    --clean-topic-map) CLEAN_TOPIC_MAP=true; shift ;;  # R9b: kill 时反查删 topic→session 映射
    --keep-topic-map)  CLEAN_TOPIC_MAP=false; shift ;; # R9b: 默认——保留映射（下次同 topic 发现死→自动 unset+新建）
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
# §Phase-2: read the resident watcher PID BEFORE §6 release-lock removes the lock dir,
# so §7 can still kill it. Empty if no --target or no watcher recorded (harmless).
WATCHER_PID=$(cat "/tmp/cc-lock-${TARGET}/watcher_pid" 2>/dev/null || echo "")

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

# ── 2. Completion audit: turn-done AUTHORITY, heartbeat AUXILIARY ──
# §Phase-3: the Stop hook drops /tmp/cc-turn-done-<S> on EVERY clean turn-end, so a
# fresh marker is authoritative proof the turn finished — it ALONE clears the finish.
# The heartbeat is demoted to an AUXILIARY liveness backstop, consulted only when no
# completion proof exists (Stop hook not deployed / a degraded CC). This is the teeth
# behind "Hermes stops polling": the hook proves completion, the LLM owes no cadence.
TURNDONE="/tmp/cc-turn-done-${SESSION}"
TURN_DONE_FRESH=false; TD_AGE=-1
if [[ -f "$TURNDONE" ]]; then
  TD_MTIME=$(stat -f %m "$TURNDONE" 2>/dev/null || echo 0)
  TD_AGE=$((NOW - TD_MTIME))
  [[ "$TD_AGE" -ge 0 && "$TD_AGE" -lt 300 ]] && TURN_DONE_FRESH=true
fi
# Auxiliary heartbeat liveness (read even when turn-done is fresh, for the advisory note).
# Schema: EPOCH|RUNCOUNT|STATE|TOKENS|TOKCHG_EPOCH|SEQ|THINK_TIME.
HB_PRESENT=false; AGE=-1; HB_STATE="?"; HB_RUNS=0
if [[ -f "$HB" ]]; then
  HB_PRESENT=true; HB_EPOCH=0
  IFS='|' read -r HB_EPOCH HB_RUNS HB_STATE _ _ _ _ < "$HB" 2>/dev/null || true
  [[ "${HB_EPOCH:-}" =~ ^[0-9]+$ ]] || HB_EPOCH=0
  [[ "${HB_RUNS:-}"  =~ ^[0-9]+$ ]] || HB_RUNS=0
  AGE=$((NOW - HB_EPOCH))
fi

if $TURN_DONE_FRESH; then
  echo "✓ 完成权威: turn-done 标记新鲜（${TD_AGE}s）→ 本轮已正常收尾"
  $HB_PRESENT && echo "  辅助: 心跳 ${AGE}s（最后状态=${HB_STATE}, 共 ${HB_RUNS} 次）"
  # turn-done is authoritative — never block on the auxiliary heartbeat.
elif $HB_PRESENT && [[ "$AGE" -ge 0 && "$AGE" -le 120 ]]; then
  echo "ℹ️  无 turn-done 标记，但心跳新鲜（${AGE}s，最后状态=${HB_STATE}）→ 辅助放行（正常完成应留 turn-done）"
else
  if $HB_PRESENT; then
    echo "⚠️  无 turn-done 且监控间隙 ${AGE}s（>120s），最后状态=${HB_STATE}"
  else
    echo "⚠️  无 turn-done 且无心跳（从未监控 / hook 未生效）"
  fi
  $FORCE || GAP_BLOCK=true
fi

# ── 3. State-transition summary (from JSONL log) ──────────────
if [[ -f "$STATELOG" ]]; then
  # grep -c 在空文件时仍打印 "0" 后退出码 1 → `|| echo 0` 会再追加一个 0（得到 "0\n0"，污染算术）；
  # 用 `|| true` 吞退出码、让 grep 自身的计数作唯一输出（照搬 cc-watcher.sh 兜底模式）。
  RUNS=$(grep -c '' "$STATELOG" 2>/dev/null || true)
  TRANSITIONS=$(grep -c '"changed":true' "$STATELOG" 2>/dev/null || true)
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
  # §Phase-2: stop the resident watcher daemon (it self-retires on session death anyway,
  # but kill it now for immediacy). PID was captured before the lock dir was removed.
  if [[ -n "$WATCHER_PID" ]] && kill -0 "$WATCHER_PID" 2>/dev/null; then
    kill "$WATCHER_PID" 2>/dev/null || true
    echo "✓ Watcher 已停: PID $WATCHER_PID"
  fi
  # Also reap any in-flight probe the watcher had just spawned — otherwise that child
  # cc-monitor re-creates the heartbeat AFTER we rm it below (race seen in the live
  # smoke). Matching on the session name keeps it scoped to THIS session.
  pkill -f "cc-monitor.sh --session ${SESSION}" 2>/dev/null || true
  # Settle: killing the session fires the in-CC SessionEnd hook (it appends a GONE line
  # to the state log). Give it a moment so our rm below wins the race and leaves /tmp
  # clean (D-4 no-leak). The SessionEnd hook no longer touches the heartbeat.
  sleep 0.5
  rm -f "/tmp/cc-watch-${SESSION}.log"
  # §3.7 + D-4 cleanup: all per-session state now shares ONE key — the tmux session
  # name. cc-start injects CC_TMUX_SESSION=<tmux name>, so the in-CC hooks key their
  # output (cc-output/, cc-state log, rewake counter) by the SAME name cc-finish knows.
  # So cc-finish can finally drop the hook-written artifacts alongside its own state,
  # solving the /tmp leak. (If CC_TMUX_SESSION did not propagate, those files were
  # keyed by the CC UUID instead and simply won't match here — harmless miss, no error.)
  rm -f  "$HB" "$STATELOG" "/tmp/cc-expect-${SESSION}" \
         "/tmp/cc-counter-stop-precheck-${SESSION}.json" \
         "/tmp/cc-turn-done-${SESSION}" "/tmp/cc-freeze-${SESSION}" \
         "/tmp/cc-status-${SESSION}.json"
  rm -rf "/tmp/cc-output/${SESSION}"
  # R9b: --clean-topic-map → 反查删此 session 的 topic 映射（默认保留，让下次同 topic 自动 unset+新建）
  if $CLEAN_TOPIC_MAP; then
    bash "$(cd "$(dirname "$0")" && pwd)/cc-topic-map.sh" unset-by-session "$SESSION" 2>/dev/null \
      && echo "✓ topic 映射已清理 (session=$SESSION)" || true
  fi
fi

echo "===📋 END cc-finish==="
exit $EXIT_CODE
