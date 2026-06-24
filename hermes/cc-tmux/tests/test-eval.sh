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
s1stat(){ bash "$EVAL" --mode test --transcript "$T" --target "$TGT" --session "$SESS" 2>/dev/null | jq -r '.checks.reporting.s1_status'; }
s1lat(){  bash "$EVAL" --mode test --transcript "$T" --target "$TGT" --session "$SESS" 2>/dev/null | jq -r '.checks.reporting.s1_latency_s'; }

# Portable epoch→UTC-ISO and mtime setter for S1 fixtures (GNU date || BSD date)
epoch_to_iso_utc(){ date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$1" +%Y-%m-%dT%H:%M:%SZ; }
set_mtime(){ touch -d "@$2" "$1" 2>/dev/null || touch -t "$(date -r "$2" +%Y%m%d%H%M.%S)" "$1"; }

# S1 fixture: turn-done marker at mtime=$1, transcript completion mention at ISO(epoch=$2)
s1_fixture(){
  printf '{"type":"user","content":"launched hermes-cc-default-%s-0617"}\n' "$TGT" > "$T"
  printf '{"timestamp":"%s","type":"assistant","content":"CC 已完成，turn-done 已读，向用户汇报结果"}\n' "$(epoch_to_iso_utc "$2")" >> "$T"
  : > "/tmp/cc-turn-done-${SESS}"; set_mtime "/tmp/cc-turn-done-${SESS}" "$1"
}

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
rm -f "/tmp/cc-freeze-${SESS}"

# ── S1 latency auto-measurement (PRD §342): turn-done mtime → first transcript completion mention ──
# Replaces the old "测量=人工审计" with a machine-checked delta. End-signal = first
# transcript line that mentions completion AND carries an ISO8601 timestamp.
now=$(date +%s)

# Test 6: report 5s after completion → within 10s budget → pass, latency 5
s1_fixture "$now" "$((now+5))"
[[ "$(s1stat)" == "pass" && "$(s1lat)" == "5" ]] && ok "S1 完成→汇报 5s ≤10s 预算 → pass (latency=5)" || bad "S1 5s should pass latency 5 (got status=$(s1stat) lat=$(s1lat))"

# Test 7: report 15s after completion → over budget → fail, latency 15
s1_fixture "$now" "$((now+15))"
[[ "$(s1stat)" == "fail" && "$(s1lat)" == "15" ]] && ok "S1 完成→汇报 15s >10s 预算 → fail (latency=15)" || bad "S1 15s should fail latency 15 (got status=$(s1stat) lat=$(s1lat))"

# Test 8: marker present but NO timestamped completion mention → na (unmeasurable)
printf '{"type":"assistant","content":"CC 已完成但这一行没有任何时间戳"}\n' > "$T"
: > "/tmp/cc-turn-done-${SESS}"; set_mtime "/tmp/cc-turn-done-${SESS}" "$now"
[[ "$(s1stat)" == "na" ]] && ok "S1 无带时间戳的汇报行 → na (不可测)" || bad "S1 should be na without timestamped mention (got $(s1stat))"

# Test 9: no turn-done marker at all → na (completion never signalled)
rm -f "/tmp/cc-turn-done-${SESS}"
printf '{"timestamp":"%s","type":"assistant","content":"完成并汇报"}\n' "$(epoch_to_iso_utc "$now")" > "$T"
[[ "$(s1stat)" == "na" ]] && ok "S1 无 turn-done marker → na (完成从未发信号)" || bad "S1 should be na without marker (got $(s1stat))"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
