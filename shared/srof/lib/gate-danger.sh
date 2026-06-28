#!/usr/bin/env bash
# gate-danger.sh — safety sensor
# PURE: CLASSIFIES an intended action; never runs it.
# The ONLY family that emits `block`; `block` ⇒ authority:human (only a human may clear, §6.2).
# Skill-specific danger patterns live LOCAL and shadow any central namesake (§6.6).
# Usage:  gate-danger.sh <namespace:arg[:arg]>
# Stdout: one JSON line (§6.4). Exit 0 = classified; exit 1 = could-not-classify ("unknown").
# Location: $SKILL_DIR/scripts/gate-danger.sh (skill-local override)
# Matrix-independent: zero tmux/iii/Hermes coupling.
set -uo pipefail
TARGET="${1:-}"

emit() { local ev="${4:-}"; [ -n "$ev" ] || ev='{}'
  printf '{"gate":"danger","target":"%s","verdict":"%s","authority":"%s","reason":"%s","evidence":%s}\n' \
    "$TARGET" "$1" "$2" "$3" "$ev"; }

case "$TARGET" in
  remote_delete:*)
    what="${TARGET#remote_delete:}"
    emit block human "irreversible remote delete of '$what'" "{\"resource\":\"$what\"}" ;;

  rm_rf:*)
    path="${TARGET#rm_rf:}"
    emit block human "recursive delete of '$path'" "{\"path\":\"$path\"}" ;;

  force_push:*)
    br="${TARGET#force_push:}"
    emit block human "force-push to '$br' rewrites history" "{\"branch\":\"$br\"}" ;;

  kill_pane:*)                           # skill-specific: never kill self / the orchestrator pane
    tgt="${TARGET#kill_pane:}"
    if [ "$tgt" = "self" ] || [ "$tgt" = "orchestrator" ] || [ "$tgt" = "${SROF_ORCHESTRATOR_PANE:-}" ]; then
      emit block human "refusing to kill the orchestrator pane" "{\"pane\":\"$tgt\"}"
    else
      emit pass none "killing pane '$tgt' is permitted" "{\"pane\":\"$tgt\"}"
    fi ;;

  *)
    emit unknown none "unknown danger target — cannot classify"; exit 1 ;;
esac
