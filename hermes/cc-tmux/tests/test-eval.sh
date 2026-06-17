#!/usr/bin/env bash
# test-eval.sh — TDD for eval-compliance.sh §Phase-3 passive-model rescore.
#
# The "reporting" dimension USED to score cc-monitor poll DENSITY (runs / duration).
# In the passive model the watcher owns cadence, so density is the WRONG metric — it
# would penalise Hermes for NOT polling, the exact behaviour we now want. The rescore
# instead checks: was completion SIGNALLED (turn-done marker / transcript evidence) and
# was every freeze HANDLED (no lingering cc-freeze marker unacknowledged).

set -uo pipefail

EVAL="$(cd "$(dirname "$0")/../scripts" && pwd)/eval-compliance.sh"
SESS="cctmux-test-eval-$$"
TGT="evaltgt-$$"
T="/tmp/cc-eval-transcript-$$.txt"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){ rm -f "$T" "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log" \
                 "/tmp/cc-turn-done-${SESS}" "/tmp/cc-freeze-${SESS}"; }
trap cleanup EXIT
cleanup

# SPARSE monitoring fixture: RUNCOUNT=1 over a 600s span → the OLD density metric FAILS.
# The §Phase-3 passive model must NOT care about poll count at all.
sparse_fixture(){
  local now; now=$(date +%s)
  printf '%s|1|IDLE|?|%s|1\n' "$now" "$now" > "/tmp/cc-heartbeat-${SESS}"
  printf '{"epoch":%s,"state":"STARTING"}\n{"epoch":%s,"state":"IDLE"}\n' "$((now-600))" "$now" > "/tmp/cc-state-${SESS}.log"
  printf 'hermes-cc-default-%s-0617 launched\ncc-start.sh mkdir cc-lock-%s\ncc-finish.sh --verify ls -la /tmp/cc-output\n%s\n' \
    "$TGT" "$TGT" "$1" > "$T"
}
rep(){ bash "$EVAL" --mode test --transcript "$T" --target "$TGT" --session "$SESS" 2>/dev/null | jq -r '.checks.reporting.status'; }

echo "=== eval-compliance TDD: §Phase-3 passive rescore (turn-done, not poll density) ==="
echo ""

# Test 1: sparse monitoring + turn-done marker present → PASS (density no longer penalised)
sparse_fixture "work done"
printf '{"event":"turn_done"}\n' > "/tmp/cc-turn-done-${SESS}"
[[ "$(rep)" == "pass" ]] && ok "sparse poll + turn-done marker → pass (poll density no longer scored)" || bad "should pass on turn-done despite sparse polling"

# Test 2: sparse + NO turn-done anywhere → FAIL (completion never signalled)
rm -f "/tmp/cc-turn-done-${SESS}"; sparse_fixture "nothing relevant here"
[[ "$(rep)" == "fail" ]] && ok "no turn-done evidence → fail (completion never signalled)" || bad "should fail without turn-done"

# Test 3: no marker, but transcript shows Hermes read the turn-done flow → PASS
sparse_fixture "read /tmp/cc-turn-done-x and relayed the results"
[[ "$(rep)" == "pass" ]] && ok "transcript references turn-done flow → pass" || bad "should pass on transcript turn-done evidence"

# Test 4: turn-done present BUT a freeze marker lingers unacknowledged → FAIL (missed alert)
sparse_fixture "work done"; printf '{"event":"turn_done"}\n' > "/tmp/cc-turn-done-${SESS}"
printf '{"event":"freeze","freeze_s":240}\n' > "/tmp/cc-freeze-${SESS}"
[[ "$(rep)" == "fail" ]] && ok "lingering freeze unacknowledged → fail (missed alert)" || bad "should fail on unhandled freeze"

# Test 5: freeze present AND transcript acknowledges it → PASS (handled)
sparse_fixture "saw the cc-freeze marker, Ctrl-C'd and re-asked"; printf '{"event":"turn_done"}\n' > "/tmp/cc-turn-done-${SESS}"
printf '{"event":"freeze"}\n' > "/tmp/cc-freeze-${SESS}"
[[ "$(rep)" == "pass" ]] && ok "freeze acknowledged in transcript → pass (handled)" || bad "should pass when freeze handled"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
