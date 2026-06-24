#!/usr/bin/env bash
# cc-thinking.sh — Extract recent thinking content from CC transcript JSONL
#
# Usage: cc-thinking.sh --session <tmux-name> [--tail-lines <N>]
# Output: plain-text thinking blocks, newest first, or "(no thinking)" if none
#
# Depends on SessionStart hook having stored transcript_path in
# /tmp/cc-transcript-path-<session> (see settings.runtime.json SessionStart hook).
# If that file is missing, exits 2 with a clear message.

set -euo pipefail

SESSION="" TAIL_LINES=200
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)    SESSION="$2"; shift 2 ;;
    --tail-lines) TAIL_LINES="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

[[ -z "$SESSION" ]] && { echo "Usage: cc-thinking.sh --session <tmux-name>" >&2; exit 1; }

TPATH_FILE="/tmp/cc-transcript-path-${SESSION}"
if [[ ! -f "$TPATH_FILE" ]]; then
  echo "(no transcript path stored — SessionStart hook hasn't fired yet?)"
  exit 2
fi

TPATH=$(cat "$TPATH_FILE" 2>/dev/null || echo "")
[[ -z "$TPATH" || ! -f "$TPATH" ]] && { echo "(transcript file not found: ${TPATH:-?})"; exit 2; }

# Tail the last N lines, parse JSONL for assistant thinking blocks
thinking=$(tail -n "$TAIL_LINES" "$TPATH" 2>/dev/null | while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  # Each line is a JSON object; we need type=assistant with content[].thinking
  type=$(printf '%s' "$line" | jq -r '.type // empty' 2>/dev/null || true)
  [[ "$type" != "assistant" ]] && continue
  printf '%s' "$line" | jq -r '
    .message.content[]? | select(.type == "thinking") | .thinking // empty
  ' 2>/dev/null || true
done)

if [[ -z "${thinking:-}" ]]; then
  echo "(no thinking content in last $TAIL_LINES transcript lines)"
else
  printf '%s\n' "$thinking"
fi
