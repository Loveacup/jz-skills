#!/usr/bin/env bash
# cc-watcher.sh — two modes:
#  (A) DEFAULT audit (cron/launchd): scan ALL CC sessions for orphans/stale-locks/
#      longruns. Findings → stdout. `--quiet` = output only on findings.
#  (B) §Phase-2 resident per-session daemon: `--watch <session>` — the ONE deterministic
#      poller. It probes (cc-monitor --force-capture) ONLY when the hook-driven heartbeat
#      goes stale, disambiguating a long think from a freeze (the one thing no hook can
#      see). This moves the monitoring CADENCE off the LLM onto a守时 shell loop.
#      cc-start launches it (nohup) per session; cc-finish --kill-session kills it; it
#      also self-retires when the session dies. `--once` = single check (unit-testable).
# Usage: cc-watcher.sh [--quiet]
#        cc-watcher.sh --watch <session> [--once] [--stale <s>] [--interval <s>]

set -euo pipefail

QUIET=false
WATCH_SESSION="" ONCE=false
STALE="${CC_WATCH_STALE:-45}"        # heartbeat older than this (s) → probe
INTERVAL="${CC_WATCH_INTERVAL:-15}"  # daemon loop sleep (s)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet)    QUIET=true; shift ;;
    --watch)    WATCH_SESSION="$2"; shift 2 ;;
    --once)     ONCE=true; shift ;;
    --stale)    STALE="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ── Mode B: resident per-session freeze-probe daemon ──────────
if [[ -n "$WATCH_SESSION" ]]; then
  MONITOR="$(cd "$(dirname "$0")" && pwd)/cc-monitor.sh"
  RETIRE=0
  # One check: retire if the session is gone; else probe only when the heartbeat is
  # stale (hooks stopped touching it → a pure-think gap or a real freeze).
  watch_once() {
    RETIRE=0
    local s="$1"
    if ! tmux has-session -t "$s" 2>/dev/null; then RETIRE=1; return 0; fi
    local hb="/tmp/cc-heartbeat-${s}" age=999999 m
    if [[ -f "$hb" ]]; then
      m=$(stat -f %m "$hb" 2>/dev/null || echo 0)
      age=$(( $(date +%s) - m ))
    fi
    if [[ "$age" -ge "$STALE" ]]; then
      # §P1-1: hook 现在直接写状态权威 /tmp/cc-status-<s>.json。watcher 缩职责——
      # 心跳陈旧时，若 hook 说状态是「静默本属预期」(IDLE 等待输入 / COMPLETED 已完成 /
      # BLOCKED 等权限 / GONE / ERROR)→ 直接信 hook，不抓屏。只有「在途状态却沉默」
      # (RECEIVED/TOOL/ACTIVE/未知/无 status 文件) 才兜底抓屏——这正是 hook 看不见的
      # 纯思考-或-冻结歧义区。注：hook 不会写 THINKING（纯思考无事件），故按状态语义而非
      # 字面 THINKING 判定；skip-list 设计让未知/未来状态默认仍探（保守）。
      local sf="/tmp/cc-status-${s}.json" hstate=""
      if [[ -f "$sf" ]] && command -v jq >/dev/null 2>&1; then
        hstate=$(jq -r '.state // ""' "$sf" 2>/dev/null || echo "")
      fi
      case "$hstate" in
        IDLE|COMPLETED|GONE|BLOCKED|ERROR|COMPACTING) : ;;  # 信 hook，不探
        *) bash "$MONITOR" --session "$s" --force-capture >/dev/null 2>&1 || true ;;
      esac
    fi
    return 0
  }
  if $ONCE; then
    watch_once "$WATCH_SESSION"
    exit 0
  fi
  while true; do
    watch_once "$WATCH_SESSION"
    [[ "$RETIRE" -eq 1 ]] && exit 0
    sleep "$INTERVAL"
  done
fi

# ── Mode A: default global audit (unchanged) ─────────────────
FINDINGS=0
NOW=$(date -u +%Y-%m-%dT%H:%M:%S)

TMUX_CC=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^hermes-cc-' || true)
LOCK_DIRS=$(ls -d /tmp/cc-lock-*/ 2>/dev/null || true)

# ── 1. Sessions without locks ─────────────────────────────────
if [[ -n "$TMUX_CC" && -z "$LOCK_DIRS" ]]; then
  while IFS= read -r sess; do
    [[ -z "$sess" ]] && continue
    FINDINGS=$((FINDINGS + 1))
    echo "⚠️  [ORPHAN-SESSION] '$sess' has NO lock dir (bypassed cc-start.sh?)"
  done <<< "$TMUX_CC"
fi

# ── 2. Stale locks (PID dead) ─────────────────────────────────
if [[ -n "$LOCK_DIRS" ]]; then
  for lock in $LOCK_DIRS; do
    [[ -z "$lock" ]] && continue
    LOCK_PID=$(cat "$lock/tmux_pid" 2>/dev/null || cat "$lock/script_pid" 2>/dev/null || echo "?")
    LOCK_SESSION=$(cat "$lock/session" 2>/dev/null || echo "?")
    LOCK_CREATED=$(cat "$lock/created" 2>/dev/null || echo "?")
    if [[ "$LOCK_PID" != "?" ]]; then
      # v1.3: use tmux has-session for STALE detection
      if [[ "$LOCK_SESSION" != "?" ]] && ! tmux has-session -t "$LOCK_SESSION" 2>/dev/null; then
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [STALE-LOCK] '$(basename "$lock")' session '$LOCK_SESSION' gone (created $LOCK_CREATED)"
      elif ! kill -0 "$LOCK_PID" 2>/dev/null; then
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [STALE-LOCK] '$(basename "$lock")' PID $LOCK_PID dead (created $LOCK_CREATED)"
      fi
    fi
  done
fi

# ── 3. Long-running sessions (>6 hours) ───────────────────────
if [[ -n "$TMUX_CC" ]]; then
  while IFS= read -r sess; do
    [[ -z "$sess" ]] && continue
    CREATED_TS=$(tmux display-message -t "$sess" -p '#{session_created}' 2>/dev/null || echo 0)
    if [[ "$CREATED_TS" != "0" ]]; then
      AGE=$(( $(date +%s) - CREATED_TS ))
      if [[ $AGE -gt 21600 ]]; then
        HOURS=$((AGE / 3600))
        FINDINGS=$((FINDINGS + 1))
        echo "⚠️  [LONGRUN] '$sess' running ${HOURS}h (abandoned?)"
      fi
    fi
  done <<< "$TMUX_CC"
fi

# ── Output ────────────────────────────────────────────────────
if $QUIET; then
  [[ $FINDINGS -gt 0 ]] && echo "[cc-watcher] $FINDINGS finding(s) at $NOW"
else
  SESS_COUNT=$(echo "$TMUX_CC" | grep -c 'hermes-cc-' 2>/dev/null || echo 0)
  LOCK_COUNT=$(echo "$LOCK_DIRS" | grep -c 'cc-lock-' 2>/dev/null || echo 0)
  echo "cc-watcher @ $NOW | sessions=$SESS_COUNT locks=$LOCK_COUNT findings=$FINDINGS"
  [[ $FINDINGS -eq 0 ]] && echo "✅ All clear"
fi

exit 0
