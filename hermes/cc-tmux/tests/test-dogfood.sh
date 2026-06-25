#!/usr/bin/env bash
# test-dogfood.sh — TDD for the dogfood instrumentation contract.
#
# Two units under test:
#   1. cc-finish.sh appends ONE dogfood JSON record per finish (all 3 exit paths),
#      keyed by env-overridable CC_DOGFOOD_LOG (default /tmp/cc-dogfood.jsonl).
#   2. cc-dogfood-report.sh emits a summary only when unreported records >= threshold
#      (default 5), is silent below it (exit 0, no output), --force overrides, --reset
#      marks all reported.
#
# report tests use FIXTURE jsonl (CC_DOGFOOD_LOG/STATE point at temp files), so they
# never touch the real dogfood history.

set -uo pipefail

SCRIPTS="$(cd "$(dirname "$0")/../scripts" && pwd)"
FINISH="$SCRIPTS/cc-finish.sh"
REPORT="$SCRIPTS/cc-dogfood-report.sh"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

TMP=$(mktemp -d "/tmp/cc-dogfood-test-$$.XXXXXX")
LOG="$TMP/dogfood.jsonl"
STATE="$TMP/state.json"

SESS="cctmux-dogfood-$$"
cleanup() {
  tmux kill-session -t "$SESS" 2>/dev/null || true
  tmux kill-session -t "${SESS}-danger" 2>/dev/null || true
  rm -rf "$TMP" \
         "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log" \
         "/tmp/cc-turn-done-${SESS}"
}
trap cleanup EXIT
cleanup; mkdir -p "$TMP"

# Fixture record emitter (mimics one cc-finish dogfood line).
emit() {
  # emit <ts> <residue_danger> <residue_benign> <gap_s> <gap_blocked> <turn_done_missing> <states> <exit_code>
  printf '{"ts":"%s","session":"s","target":"t","residue_danger":%s,"residue_benign":%s,"monitor_gap_s":%s,"gap_blocked":%s,"turn_done_missing":%s,"states":"%s","exit_code":%s}\n' \
    "$1" "$2" "$3" "$4" "$5" "$6" "$7" "$8" >> "$LOG"
}

echo "=== dogfood TDD ==="
echo ""
echo "--- cc-finish emits records (live) ---"

# Fixture: clean ❯ pane + fresh turn-done/heartbeat → finish exits 0 (normal path).
tmux new-session -d -s "$SESS" -x 100 -y 20 "printf '❯ '; sleep 999" </dev/null >/dev/null 2>&1
sleep 0.3
NOW=$(date +%s)
printf '%s|1|IDLE|?|%s|1\n' "$NOW" "$NOW" > "/tmp/cc-heartbeat-${SESS}"
date +%s > "/tmp/cc-turn-done-${SESS}"
printf '{"epoch":%s,"changed":true,"state":"IDLE"}\n' "$NOW" > "/tmp/cc-state-${SESS}.log"

CC_DOGFOOD_LOG="$LOG" bash "$FINISH" --session "$SESS" --target "tgt-$$" >/dev/null 2>&1
rc=$?

# TC1: normal path appended a record
LINES=$(grep -c '.' "$LOG" 2>/dev/null || true)
if [[ "${LINES:-0}" -ge 1 ]]; then ok "TC1 normal finish appended a dogfood record"; else bad "TC1 no record written (lines=${LINES:-0})"; fi

# TC2: record is valid JSON (jq parses) with the session field
if jq -e --arg s "$SESS" 'select(.session==$s) | .exit_code != null' "$LOG" >/dev/null 2>&1; then
  ok "TC2 record is valid JSON, parseable by jq, carries session"
else
  bad "TC2 record not valid JSON / missing session"
fi

# TC3: dangerous residue path → record exit_code=10, residue_danger=true (written before exit 10)
DLOG="$TMP/danger.jsonl"
tmux new-session -d -s "${SESS}-danger" -x 100 -y 20 "printf '❯ rm -rf /tmp/x'; sleep 999" </dev/null >/dev/null 2>&1
sleep 0.3
CC_DOGFOOD_LOG="$DLOG" bash "$FINISH" --session "${SESS}-danger" >/dev/null 2>&1
drc=$?
if [[ "$drc" -eq 10 ]] && jq -e 'select(.exit_code==10 and .residue_danger==true)' "$DLOG" >/dev/null 2>&1; then
  ok "TC3 danger residue → record exit_code=10, residue_danger=true (finish rc=$drc)"
else
  bad "TC3 danger record wrong: finish rc=$drc, $(cat "$DLOG" 2>/dev/null)"
fi
tmux kill-session -t "${SESS}-danger" 2>/dev/null || true

echo ""
echo "--- cc-dogfood-report (fixture) ---"

# TC4: < threshold → silent exit 0, no output
rm -f "$LOG" "$STATE"
for i in 1 2 3; do emit "2026-06-2${i}T10:00:00Z" false false 0 false false "STARTING→IDLE" 0; done
out=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc4=$?
if [[ "$rc4" -eq 0 && -z "$out" ]]; then ok "TC4 <5 records → silent exit 0"; else bad "TC4 expected silence, rc=$rc4 out='$out'"; fi

# TC5: >= threshold → summary printed
rm -f "$LOG" "$STATE"
emit "2026-06-20T10:00:00Z" false true  0   false false "STARTING→THINKING→TOOL" 1
emit "2026-06-21T10:00:00Z" false false 130 false false "STARTING→THINKING→TOOL" 0
emit "2026-06-22T10:00:00Z" false false 0   false false "STARTING→THINKING→TOOL" 0
emit "2026-06-23T10:00:00Z" false false 0   false false "STARTING→IDLE→THINKING" 0
emit "2026-06-24T10:00:00Z" false false 0   false false "STARTING→IDLE→THINKING" 0
out5=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc5=$?
if [[ "$rc5" -eq 0 ]] && printf '%s' "$out5" | grep -q 'Dogfood 摘要'; then
  ok "TC5 >=5 records → summary printed"
else
  bad "TC5 no summary: rc=$rc5 out='$out5'"
fi
# state updated to total
if [[ -f "$STATE" ]] && jq -e '.last_reported_count==5' "$STATE" >/dev/null 2>&1; then
  ok "TC5b state last_reported_count==5 after report"
else
  bad "TC5b state not updated: $(cat "$STATE" 2>/dev/null)"
fi
# second run with no new records → silent
out5c=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc5c=$?
if [[ "$rc5c" -eq 0 && -z "$out5c" ]]; then ok "TC5c re-run with 0 new → silent"; else bad "TC5c expected silence, out='$out5c'"; fi

# TC6: --force below threshold → still prints
rm -f "$LOG" "$STATE"
emit "2026-06-24T10:00:00Z" false false 0 false false "STARTING→IDLE" 0
out6=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" --force 2>&1); rc6=$?
if [[ "$rc6" -eq 0 ]] && printf '%s' "$out6" | grep -q 'Dogfood 摘要'; then
  ok "TC6 --force prints summary below threshold"
else
  bad "TC6 --force did not print: rc=$rc6 out='$out6'"
fi

# TC7: --reset marks all reported (count goes to zero → next run silent)
rm -f "$LOG" "$STATE"
for i in 1 2 3 4 5 6; do emit "2026-06-2${i}T10:00:00Z" false false 0 false false "STARTING→IDLE" 0; done
CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" --reset >/dev/null 2>&1
rc7=$?
out7=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc7b=$?
if [[ "$rc7" -eq 0 ]] && jq -e '.last_reported_count==6' "$STATE" >/dev/null 2>&1 && [[ -z "$out7" ]]; then
  ok "TC7 --reset marks all reported (count→0, next run silent)"
else
  bad "TC7 reset failed: rc=$rc7 state=$(cat "$STATE" 2>/dev/null) nextOut='$out7'"
fi

# TC8: missing jsonl → exit 0 silently
rm -f "$LOG" "$STATE"
out8=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc8=$?
if [[ "$rc8" -eq 0 && -z "$out8" ]]; then ok "TC8 missing jsonl → silent exit 0"; else bad "TC8 expected silence, rc=$rc8 out='$out8'"; fi

# TC9: blank lines in jsonl are skipped (not counted)
rm -f "$LOG" "$STATE"
for i in 1 2 3; do emit "2026-06-2${i}T10:00:00Z" false false 0 false false "STARTING→IDLE" 0; done
printf '\n\n' >> "$LOG"   # two blank lines — must NOT push count to 5
out9=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc9=$?
if [[ "$rc9" -eq 0 && -z "$out9" ]]; then ok "TC9 blank lines skipped (3 real records → still silent)"; else bad "TC9 blank lines miscounted: out='$out9'"; fi

# TC10: exit 10 danger residue happens before completion audit; its default
# turn_done_missing=true is a code-ordering artifact, not a Stop-hook signal.
rm -f "$LOG" "$STATE"
emit "2026-06-20T10:00:00Z" true  false 0 false true  "STARTING" 10
emit "2026-06-21T10:00:00Z" false false 0 false false "STARTING→IDLE" 0
emit "2026-06-22T10:00:00Z" false false 0 false false "STARTING→IDLE" 0
emit "2026-06-23T10:00:00Z" false false 0 false false "STARTING→IDLE" 0
emit "2026-06-24T10:00:00Z" false false 0 false false "STARTING→IDLE" 0
out10=$(CC_DOGFOOD_LOG="$LOG" CC_DOGFOOD_STATE="$STATE" bash "$REPORT" 2>&1); rc10=$?
if [[ "$rc10" -eq 0 ]] && printf '%s' "$out10" | grep -q '危险残留: 1 次' && printf '%s' "$out10" | grep -q 'turn-done 缺失: 0 次'; then
  ok "TC10 exit 10 danger residue does not inflate turn-done-missing"
else
  bad "TC10 expected tdm=0 for exit10 artifact, rc=$rc10 out='$out10'"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
