#!/usr/bin/env bash
# gate-counter.sh — measurement sensor
# PURE: reports a number; never judges it. The engine compares evidence.count to a manifest/policy limit (§4.3).
# Counts live in the EPHEMERAL runtime.json, written by the actuator-runner/engine.
# Usage:  [SROF_RUNTIME_JSON=<path>] [SROF_SKILL=<name>] gate-counter.sh <retries:STEP|sessions_active|age_seconds:FILE>
# Location: $SROF_LIB/gate-counter.sh (central shared library)
# Matrix-independent: zero tmux/iii/Hermes coupling.
set -uo pipefail
TARGET="${1:-}"
RUNTIME="${SROF_RUNTIME_JSON:-${XDG_RUNTIME_DIR:-/tmp}/srof/${SROF_SKILL:-_}/runtime.json}"

emit()  { printf '{"gate":"counter","target":"%s","verdict":"pass","authority":"none","reason":"%s","evidence":{"count":%s}}\n' "$TARGET" "$1" "$2"; }
unkn()  { printf '{"gate":"counter","target":"%s","verdict":"unknown","authority":"none","reason":"%s","evidence":{}}\n' "$TARGET" "$1"; exit 1; }
get()   { [ -f "$RUNTIME" ] && jq -r "$1 // 0" "$RUNTIME" 2>/dev/null || echo 0; }

case "$TARGET" in
  retries:*)        step="${TARGET#retries:}"; emit "retry count for '$step'" "$(get ".retries.\"$step\"")" ;;
  sessions_active)  emit "active sessions" "$(get '.sessions_active')" ;;
  age_seconds:*)
    f="${TARGET#age_seconds:}"
    if [ -f "$f" ]; then now=$(date +%s); m=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null)
      [ -n "$m" ] && emit "age of $f" "$((now-m))" || unkn "cannot stat $f"
    else emit "file absent" "-1"; fi ;;
  *)                unkn "unknown counter target" ;;
esac
