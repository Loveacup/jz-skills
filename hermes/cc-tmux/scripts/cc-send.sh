#!/usr/bin/env bash
# cc-send.sh — Send context + task to a running CC tmux session
# §3.2: + post-send verification with auto-retry, --dry-run, --expect
#
# Usage:
#   cc-send.sh --session <name> --context <file> [--message <text>]
#              [--dry-run] [--expect <glob>]
#
# Verification contract (§3.2 / Pitfall #5):
#   After send-keys, capture the bottom of the pane and classify:
#     · queue banner ("Press up to edit queued") → Escape + re-send payload (retry)
#     · ❯ with residual text                     → Enter did not register   (retry)
#     · empty ❯  OR  no ❯ at all (CC already busy)→ consumed                 (SUCCESS)
#   Only a POSITIVELY stuck state (queue / residual) is retried, max 4 times.
#   On exhaustion the script EXITS NON-ZERO (rc 2) so a human is alerted —
#   it must never silently fake success ("不静默假成功", per plan §3.2 / L1 table).

set -euo pipefail

SESSION="" CONTEXT="" MESSAGE="" DRYRUN=0 EXPECT_GLOB=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --context) CONTEXT="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    --dry-run) DRYRUN=1; shift ;;
    --expect)  EXPECT_GLOB="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "Usage: cc-send.sh --session <name> --context <file> [--message <text>] [--dry-run] [--expect <glob>]" >&2
  exit 1
fi

# Verify session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "❌ Session '$SESSION' not found" >&2
  exit 1
fi

# ── §3.2 / D-4: write expected-artifacts file if --expect provided ──
if [[ -n "$EXPECT_GLOB" ]]; then
  printf '%s' "$EXPECT_GLOB" > "/tmp/cc-expect-${SESSION}"
fi

# ── Send payload (factored out so verify_delivered can re-send) ──
send_payload() {
  if [[ -n "$CONTEXT" && -f "$CONTEXT" ]]; then
    tmux send-keys -t "$SESSION" \
      "Please read $CONTEXT — $(head -1 "$CONTEXT" | cut -c1-80)" Enter
  elif [[ -n "$MESSAGE" ]]; then
    tmux send-keys -t "$SESSION" "$MESSAGE" Enter
  else
    echo "⚠️  No context file or message provided. Sending empty Enter to trigger." >&2
    tmux send-keys -t "$SESSION" Enter
  fi
}

# ── §3.2: verify_delivered — post-send liveness check w/ bounded retry ──
verify_delivered() {
  local tries=0 max=4
  while (( tries < max )); do
    sleep 0.6
    local tail4
    tail4=$(tmux capture-pane -t "$SESSION" -p -S -6 2>/dev/null \
            | grep -v '^[[:space:]]*$' | tail -4 || true)

    # ① queue mode (Pitfall #1) — highest priority: Escape out, re-send payload
    if printf '%s' "$tail4" | grep -q 'Press up to edit queued'; then
      if [[ "$DRYRUN" -eq 1 ]]; then
        echo "[dry-run] queue mode detected — would Escape + re-send payload" >&2
        return 0
      fi
      tmux send-keys -t "$SESSION" Escape; sleep 0.3; send_payload
      (( ++tries )); continue          # ← ++prefix: avoid set -e rc=1 abort at tries=0
    fi

    # ② ❯ prompt classification
    local pl c=""
    pl=$(printf '%s' "$tail4" | grep '❯' | tail -1 || true)
    if [[ -n "$pl" ]]; then
      c=$(printf '%s' "$pl" | sed -E 's/^[[:space:]│╎┃|]*❯[[:space:]]*//; s/[[:space:]│╎┃|]*$//')
      if [[ -n "$c" ]]; then
        # residual text after ❯ = Enter never registered → resend Enter
        if [[ "$DRYRUN" -eq 1 ]]; then
          echo "[dry-run] ❯ has residual text — would re-send Enter" >&2
          return 0
        fi
        tmux send-keys -t "$SESSION" Enter
        (( ++tries )); continue
      fi
    fi

    # ③ empty ❯, OR no ❯ at all (CC already consumed input and is working) = success
    echo "✓ Sent to $SESSION (verified, tries=$tries)"
    return 0
  done

  echo "⚠️  Enter 未生效且自动重试 ${max} 次失败 — 人工 capture-pane 介入" >&2
  return 2
}

# ── Send, then verify; verify_delivered's rc propagates as the script's rc ──
send_payload
verify_delivered
