#!/usr/bin/env bash
# test-watcher.sh — TDD for cc-watcher.sh --watch <session> resident-daemon mode (§Phase-2)
#
# The watcher is the ONE deterministic poller: it probes (cc-monitor --force-capture)
# ONLY when the hook-driven heartbeat goes stale — disambiguating a long think from a
# freeze, the one thing no hook can see. --once does a single check-and-maybe-probe so
# the loop logic is unit-testable. The default (no --once) is the resident loop.

set -uo pipefail

WATCHER="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-watcher.sh"
SESS="cctmux-test-watch-$$"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){
  tmux kill-session -t "$SESS" 2>/dev/null || true
  rm -f "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log" \
        "/tmp/cc-fixture-${SESS}.txt" "/tmp/cc-freeze-${SESS}" \
        "/tmp/cc-usage-alert-${SESS}"
}
trap cleanup EXIT
cleanup

echo "=== cc-watcher TDD: --watch resident daemon (§Phase-2) ==="
echo ""

# Test 1: session GONE → --once retires (exit 0), does NOT fabricate a heartbeat
out=$(bash "$WATCHER" --watch "$SESS" --once 2>&1); rc=$?
if [[ "$rc" -eq 0 && ! -f "/tmp/cc-heartbeat-${SESS}" ]]; then
  ok "session gone → --once retires (exit 0, no probe)"
else
  bad "session-gone handling wrong: rc=$rc hb=$([ -f "/tmp/cc-heartbeat-${SESS}" ] && echo present || echo none)"
fi

# Live fixture session showing a THINKING spinner
printf '✻ Thinking…（2m 0s · ?）\n❯ \n' > "/tmp/cc-fixture-${SESS}.txt"
tmux new-session -d -s "$SESS" -x 120 -y 20 \
  "while true; do cat /tmp/cc-fixture-${SESS}.txt; sleep 0.2; done" </dev/null >/dev/null 2>&1
sleep 0.6

# Test 2: FRESH heartbeat → --once does NOT probe (cc-monitor not run → content untouched)
printf 'MARKER_NOPROBE\n' > "/tmp/cc-heartbeat-${SESS}"   # fresh mtime, sentinel content
bash "$WATCHER" --watch "$SESS" --once --stale 45 >/dev/null 2>&1
if grep -q 'MARKER_NOPROBE' "/tmp/cc-heartbeat-${SESS}" 2>/dev/null; then
  ok "fresh heartbeat → no probe (cc-monitor not run, content untouched)"
else
  bad "fresh heartbeat wrongly probed (sentinel overwritten)"
fi

# Test 3: STALE heartbeat → --once probes (cc-monitor runs → heartbeat refreshed + state logged)
printf 'MARKER_STALE\n' > "/tmp/cc-heartbeat-${SESS}"
touch -t 202601010000.00 "/tmp/cc-heartbeat-${SESS}" 2>/dev/null || true
rm -f "/tmp/cc-state-${SESS}.log"
bash "$WATCHER" --watch "$SESS" --once --stale 45 >/dev/null 2>&1
if [[ -f "/tmp/cc-state-${SESS}.log" ]] && ! grep -q 'MARKER_STALE' "/tmp/cc-heartbeat-${SESS}" 2>/dev/null; then
  ok "stale heartbeat → probe (cc-monitor ran: heartbeat refreshed + state logged)"
else
  bad "stale heartbeat did NOT probe (state log=$([ -f "/tmp/cc-state-${SESS}.log" ] && echo y || echo n))"
fi

# Test 4: default audit mode (no --watch) still works (cron role preserved)
out=$(bash "$WATCHER" --quiet 2>&1); rc=$?
[[ "$rc" -eq 0 ]] && ok "default audit mode preserved (--quiet exit 0)" || bad "audit mode broke: rc=$rc"

# ── §R8c③ usage-alert tests (--usage-check single sync entrypoint, stubbed ccusage) ──
ALERT="/tmp/cc-usage-alert-${SESS}"

# Test 5: cumulative tokens ≥ ceiling → writes /tmp/cc-usage-alert-<s>
rm -f "$ALERT"
CC_USAGE_CMD="printf {\"totals\":{\"totalTokens\":2000000000,\"totalCost\":9}}" CC_USAGE_CEIL=1500000000 \
  bash "$WATCHER" --watch "$SESS" --usage-check >/dev/null 2>&1
if [[ -f "$ALERT" ]] && grep -q '天花板' "$ALERT" 2>/dev/null; then
  ok "tokens ≥ ceiling → usage-alert written"
else
  bad "ceiling breach did NOT write alert"
fi

# Test 6: cumulative below ceiling → clears stale alert
echo "stale" > "$ALERT"
CC_USAGE_CMD="printf {\"totals\":{\"totalTokens\":100,\"totalCost\":1}}" CC_USAGE_CEIL=1500000000 \
  bash "$WATCHER" --watch "$SESS" --usage-check >/dev/null 2>&1
[[ ! -f "$ALERT" ]] && ok "below ceiling → stale alert cleared" || bad "stale alert NOT cleared"

# Test 7: 'approaching limit' text in raw output → alert (best-effort grep fallback)
rm -f "$ALERT"
CC_USAGE_CMD="echo you are approaching your limit now" CC_USAGE_CEIL=1500000000 \
  bash "$WATCHER" --watch "$SESS" --usage-check >/dev/null 2>&1
[[ -f "$ALERT" ]] && ok "'approaching limit' text → alert (grep fallback)" || bad "approaching-limit text did NOT alert"

# Test 8: ccusage unavailable → silent degrade, does NOT fabricate alert, exit 0
rm -f "$ALERT"
CC_USAGE_CMD="cc-watcher-no-such-cmd-xyz" bash "$WATCHER" --watch "$SESS" --usage-check >/dev/null 2>&1; rc=$?
if [[ "$rc" -eq 0 && ! -f "$ALERT" ]]; then
  ok "ccusage failure → degrade (exit 0, no fabricated alert)"
else
  bad "ccusage-failure handling wrong: rc=$rc alert=$([ -f "$ALERT" ] && echo present || echo none)"
fi

# Test 9: ccusage failure must NOT clear a pre-existing alert (no false clear)
echo "keep" > "$ALERT"
CC_USAGE_CMD="cc-watcher-no-such-cmd-xyz" bash "$WATCHER" --watch "$SESS" --usage-check >/dev/null 2>&1
[[ -f "$ALERT" ]] && ok "ccusage failure → pre-existing alert untouched" || bad "ccusage failure wrongly cleared alert"
rm -f "$ALERT"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
