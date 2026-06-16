#!/usr/bin/env bash
# test-finish.sh — TDD for cc-finish.sh §3.7 + D-4 cleanup contract.
#
# On --kill-session, cc-finish must remove ALL per-session state keyed by the tmux
# session name: heartbeat, state log, expect file, the Stop rewake counter, AND the
# /tmp/cc-output/<session>/ archive dir. The last two became cleanable only after
# D-4 unified the key (cc-start injects CC_TMUX_SESSION so the in-CC hooks key by
# the tmux name that cc-finish already knows).

set -uo pipefail

FINISH="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-finish.sh"
SESS="cctmux-test-finish-$$"
TGT="cctmux-test-finish-tgt-$$"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

cleanup() {
  tmux kill-session -t "$SESS" 2>/dev/null || true
  rm -rf "/tmp/cc-lock-${TGT}" "/tmp/cc-output/${SESS}" \
         "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log" \
         "/tmp/cc-expect-${SESS}" "/tmp/cc-counter-stop-precheck-${SESS}.json"
}
trap cleanup EXIT
cleanup

echo "=== cc-finish TDD: §3.7 + D-4 cleanup contract ==="
echo ""

# Fixture: a live session + FRESH heartbeat (so the monitoring-gap gate passes) +
# the full set of per-session state the hooks/scripts create, all keyed by tmux name.
tmux new-session -d -s "$SESS" -x 120 -y 20 "sleep 999" 2>/dev/null
sleep 0.3
NOW=$(date +%s)
printf '%s|1|IDLE|?|%s|1\n' "$NOW" "$NOW"           > "/tmp/cc-heartbeat-${SESS}"
printf '{"state":"IDLE"}\n'                          > "/tmp/cc-state-${SESS}.log"
printf 'result-*.md'                                 > "/tmp/cc-expect-${SESS}"
printf '{"key":"stop-precheck-%s","reject":1}\n' "$SESS" > "/tmp/cc-counter-stop-precheck-${SESS}.json"
mkdir -p "/tmp/cc-output/${SESS}"; echo "archived"   > "/tmp/cc-output/${SESS}/resp.log"
mkdir -p "/tmp/cc-lock-${TGT}";    echo "$SESS"       > "/tmp/cc-lock-${TGT}/session"

out=$(bash "$FINISH" --session "$SESS" --target "$TGT" --release-lock --kill-session 2>&1); rc=$?

# Test 1: finish succeeds (clean pane + fresh heartbeat → no residual, no gap block)
[[ "$rc" -eq 0 ]] && ok "finish exit 0 (fresh heartbeat passes gap gate)" || bad "finish rc=$rc: $out"

# Test 2: session killed
tmux has-session -t "$SESS" 2>/dev/null && bad "session not killed" || ok "session killed"

# Test 3: lock released
[[ -d "/tmp/cc-lock-${TGT}" ]] && bad "lock dir not released" || ok "lock released"

# Test 4: heartbeat + state log + expect removed
if [[ ! -f "/tmp/cc-heartbeat-${SESS}" && ! -f "/tmp/cc-state-${SESS}.log" && ! -f "/tmp/cc-expect-${SESS}" ]]; then
  ok "heartbeat + state log + expect cleaned"
else
  bad "core per-session state not fully cleaned"
fi

# Test 5: D-4 — Stop rewake counter cleaned (impossible before key unification)
[[ -f "/tmp/cc-counter-stop-precheck-${SESS}.json" ]] && bad "counter file NOT cleaned (D-4)" || ok "stop-precheck counter cleaned (D-4)"

# Test 6: D-4 — cc-output archive dir cleaned
[[ -d "/tmp/cc-output/${SESS}" ]] && bad "cc-output dir NOT cleaned (D-4)" || ok "cc-output archive dir cleaned (D-4)"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
