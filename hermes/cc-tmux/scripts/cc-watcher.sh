#!/usr/bin/env bash
# cc-watcher.sh — Audit-only watcher for CC tmux sessions
# Flags anomalies; does NOT auto-fix. Designed for cron/launchd.
# All findings go to stdout (cron no_agent=true delivery depends on stdout).
# Usage: cc-watcher.sh [--quiet]
#   --quiet: only output on findings (zero stdout = all clear)

set -euo pipefail

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

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
