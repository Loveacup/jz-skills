#!/usr/bin/env bash
# cc-send.sh — Send context + task to a running CC tmux session
# Usage: cc-send.sh --session <name> --context <file> [--message <text>]

set -euo pipefail

SESSION="" CONTEXT="" MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --context) CONTEXT="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "Usage: cc-send.sh --session <name> --context <file> [--message <text>]" >&2
  exit 1
fi

# Verify session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "❌ Session '$SESSION' not found" >&2
  exit 1
fi

# Send context file reference or message
if [[ -n "$CONTEXT" && -f "$CONTEXT" ]]; then
  tmux send-keys -t "$SESSION" \
    "Please read $CONTEXT — $(head -1 "$CONTEXT" | cut -c1-80)" Enter
elif [[ -n "$MESSAGE" ]]; then
  tmux send-keys -t "$SESSION" "$MESSAGE" Enter
else
  echo "⚠️  No context file or message provided. Sending empty Enter to trigger." >&2
  tmux send-keys -t "$SESSION" Enter
fi

echo "✓ Sent to $SESSION"
