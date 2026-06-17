#!/usr/bin/env bash
# cc-wait-marker.sh — Block until CC writes a turn-done marker NEWER than --after
# §3 In-Turn Wait: lets Hermes `process(action=wait)` on this inside ONE turn and
# loop send → wait → read → send, instead of ending the turn and re-injecting.
#
# Usage:
#   cc-wait-marker.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
#
# Contract:
#   · marker path = /private/tmp/cc-turn-done-<session>   (/private/tmp, not /tmp:
#     macOS /tmp is a symlink and FSEvents/mtime resolve through /private/tmp)
#   · blocks until mtime(marker) > --after  (STRICT >, so a marker equal to the
#     baseline you already saw does NOT trigger — you must record --after as the
#     mtime/epoch BEFORE sending the next instruction; see Pitfall: mtime 比较)
#   · on a strictly-newer marker → print its contents (cat, no jq) and exit 0
#   · on --timeout expiry        → exit 1
#   · on bad/missing args        → exit 2 (+ stderr usage)
#   · poll interval 2s
#
# Defaults: --after 0 (any marker newer than the epoch), --timeout 21600 (6h).

set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: cc-wait-marker.sh --session <tmux-session-name> [--after <unix_ts>] [--timeout <secs>]
  Blocks until /private/tmp/cc-turn-done-<session> has mtime strictly greater than
  --after, then prints the marker contents and exits 0.
    --after    baseline unix timestamp (default 0); wait for mtime > this value
    --timeout  max seconds to block (default 21600 = 6h); on expiry exit 1
  Exit codes: 0 newer marker found · 1 timeout · 2 bad/missing args
EOF
}

SESSION="" AFTER=0 TIMEOUT=21600

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --session requires a value" >&2; usage; exit 2; }; SESSION="$2"; shift 2 ;;
    --after)   [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --after requires a value"   >&2; usage; exit 2; }; AFTER="$2";   shift 2 ;;
    --timeout) [[ $# -ge 2 ]] || { echo "❌ cc-wait-marker: --timeout requires a value" >&2; usage; exit 2; }; TIMEOUT="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "❌ cc-wait-marker: unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "❌ cc-wait-marker: --session is required" >&2
  usage
  exit 2
fi

if ! [[ "$AFTER" =~ ^[0-9]+$ ]]; then
  echo "❌ cc-wait-marker: --after must be a non-negative integer (got: '$AFTER')" >&2
  usage
  exit 2
fi

if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
  echo "❌ cc-wait-marker: --timeout must be a non-negative integer (got: '$TIMEOUT')" >&2
  usage
  exit 2
fi

MARKER="/private/tmp/cc-turn-done-${SESSION}"
POLL=2
start=$(date +%s)

while true; do
  if [[ -f "$MARKER" ]]; then
    m=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
    if [[ "$m" -gt "$AFTER" ]]; then
      cat "$MARKER" 2>/dev/null || true
      exit 0
    fi
  fi

  now=$(date +%s)
  if [[ $((now - start)) -ge "$TIMEOUT" ]]; then
    echo "⏱  cc-wait-marker: timeout after ${TIMEOUT}s — no marker newer than ${AFTER} (session=${SESSION})" >&2
    exit 1
  fi

  sleep "$POLL"
done
