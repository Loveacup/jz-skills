#!/usr/bin/env bash
# gate-verify.sh — class-(b) last-result sensor
# PURE: reads the captured result file written by srof-run (§6.8); NEVER re-executes the actuator.
# Class-(a) re-query verifies are handled by gate-check, not here (§6.5).
# Usage:  SROF_RUN_RESULT=<path> gate-verify.sh <exit_code:N | result_json:.path==value>
# Stdout: one JSON line (§6.4). Exit 0 = determined; exit 1 = could-not-determine ("unknown").
# Location: $SROF_LIB/gate-verify.sh (central shared library)
# Matrix-independent: zero tmux/iii/Hermes coupling.
set -uo pipefail
TARGET="${1:-}"

emit() { local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"verify","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"; }

need_result() {                          # last-result verify requires the descriptor
  if [ -z "${SROF_RUN_RESULT:-}" ] || [ ! -f "${SROF_RUN_RESULT:-}" ]; then
    emit unknown none "last-result verify but \$SROF_RUN_RESULT missing"; exit 1; fi
}

case "$TARGET" in
  exit_code:*)
    need_result
    want="${TARGET#exit_code:}"
    have="$(jq -r '.exit_code // empty' "$SROF_RUN_RESULT" 2>/dev/null)"
    [ -n "$have" ] || { emit unknown none "no exit_code in result"; exit 1; }
    if [ "$have" = "$want" ]; then emit pass none "exit $have == $want" "{\"have\":$have}"
    else emit fail agent "exit $have != $want" "{\"have\":$have,\"want\":$want}"; fi ;;

  result_json:*)                         # result_json:.path==value (on the captured stdout)
    need_result
    expr="${TARGET#result_json:}"; path="${expr%%==*}"; want="${expr#*==}"
    out="$(jq -r '.stdout_path // empty' "$SROF_RUN_RESULT" 2>/dev/null)"
    [ -f "$out" ] || { emit unknown none "captured stdout missing"; exit 1; }
    if ! have="$(jq -r "$path" "$out" 2>/dev/null)"; then emit unknown none "jq parse failed on captured stdout"; exit 1; fi
    if [ "$have" = "$want" ]; then emit pass none "$path == $want" "{\"have\":\"$have\"}"
    else emit fail agent "$path is '$have', want '$want'" "{\"have\":\"$have\",\"want\":\"$want\"}"; fi ;;

  *)
    emit unknown none "unknown verify target (class-a re-query? route to gate-check, §6.5)"; exit 1 ;;
esac
