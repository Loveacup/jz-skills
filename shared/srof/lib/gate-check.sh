#!/usr/bin/env bash
# gate-check.sh — precondition + class-(a) re-query sensor
# PURE: observes the world, never mutates.
# Usage:  gate-check.sh <namespace:arg[:arg]>
# Stdout: one line of JSON (§6.4). Exit 0 = determined; exit 1 = could-not-determine ("unknown").
# Location: $SROF_LIB/gate-check.sh (central shared library)
# Matrix-independent: zero tmux/iii/Hermes coupling. On 2nd consumer → promote to independent skill.
set -uo pipefail
TARGET="${1:-}"

emit() {  # emit <verdict> <authority> <reason> [evidence-json]
  local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"check","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"
}

case "$TARGET" in
  command_exists:*)
    cmd="${TARGET#command_exists:}"
    if path="$(command -v "$cmd" 2>/dev/null)"; then emit pass none "command '$cmd' found" "{\"found\":\"$path\"}"
    else emit fail agent "command '$cmd' not found"; fi ;;

  env_exists:*)
    var="${TARGET#env_exists:}"
    if [ -n "${!var:-}" ]; then emit pass none "env '$var' set"
    else emit fail agent "env '$var' not set"; fi ;;

  file_exists:*)
    f="${TARGET#file_exists:}"
    if [ -f "$f" ]; then emit pass none "file exists" "{\"path\":\"$f\"}"
    else emit fail agent "file '$f' not found"; fi ;;

  version_gte:*)                                                    # version_gte:node:18.0.0
    rest="${TARGET#version_gte:}"; cmd="${rest%%:*}"; want="${rest#*:}"
    if ! have="$(timeout 5 "$cmd" --version 2>/dev/null | grep -oE '[0-9]+(\.[0-9]+)+' | head -1)" || [ -z "$have" ]; then
      emit unknown none "cannot read version of '$cmd'"; exit 1; fi
    lowest="$(printf '%s\n%s\n' "$want" "$have" | sort -V | head -1)"
    if [ "$lowest" = "$want" ]; then emit pass none "$cmd $have >= $want" "{\"have\":\"$have\"}"
    else emit fail agent "$cmd $have < $want" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  port_free:*)
    p="${TARGET#port_free:}"
    if command -v lsof >/dev/null 2>&1; then
      if lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then emit fail agent "port $p in use"
      else emit pass none "port $p free"; fi
    else emit unknown none "lsof unavailable; cannot determine port $p"; exit 1; fi ;;

  http_ok:*)                                                        # idempotent GET health check
    url="${TARGET#http_ok:}"
    if curl -fsS --max-time 10 -o /dev/null "$url" 2>/dev/null; then emit pass none "GET $url ok"
    else emit fail agent "GET $url not ok"; fi ;;

  status_json:*)                                                    # status_json:CMD::.path==value (CMD MUST be read-only)
    rest="${TARGET#status_json:}"; cmd="${rest%%::*}"; cond="${rest#*::}"
    path="${cond%%==*}"; want="${cond#*==}"
    if ! out="$(eval "$cmd" 2>/dev/null)"; then emit unknown none "status cmd failed: $cmd"; exit 1; fi
    if ! have="$(jq -r "$path" <<<"$out" 2>/dev/null)"; then emit unknown none "jq parse failed on status output"; exit 1; fi
    if [ "$have" = "$want" ]; then emit pass none "$path == $want" "{\"have\":\"$have\"}"
    else emit fail agent "$path is '$have', want '$want'" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  lock_free:*)
    name="${TARGET#lock_free:}"; lock="${XDG_RUNTIME_DIR:-/tmp}/srof/${name}.lock"
    if [ -d "$lock" ]; then emit block human "lock '$name' held by another session"
    else emit pass none "lock '$name' free"; fi ;;

  *)
    emit unknown none "unknown check target"; exit 1 ;;
esac
