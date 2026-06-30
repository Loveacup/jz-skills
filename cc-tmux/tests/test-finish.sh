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

SESS2="cctmux-test-finish2-$$"
cleanup() {
  tmux kill-session -t "$SESS" 2>/dev/null || true
  tmux kill-session -t "$SESS2" 2>/dev/null || true
  rm -rf "/tmp/cc-lock-${TGT}" "/tmp/cc-output/${SESS}" \
         "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log" \
         "/tmp/cc-expect-${SESS}" "/tmp/cc-counter-stop-precheck-${SESS}.json" \
         "/tmp/cc-turn-done-${SESS}" "/tmp/cc-freeze-${SESS}" \
         "/tmp/cc-heartbeat-${SESS2}" "/tmp/cc-state-${SESS2}.log" \
         "/tmp/cc-turn-done-${SESS2}" "/tmp/cc-freeze-${SESS2}"
}
trap cleanup EXIT
cleanup

echo "=== cc-finish TDD: §3.7 + D-4 cleanup contract ==="
echo ""

# Fixture: a live session + FRESH heartbeat (so the monitoring-gap gate passes) +
# the full set of per-session state the hooks/scripts create, all keyed by tmux name.
tmux new-session -d -s "$SESS" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
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

# ─── §Phase-2: turn-done marker is the completion authority ───
echo ""
echo "§Phase-2 turn-done marker overrides stale-heartbeat gap gate"
tmux new-session -d -s "$SESS2" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
sleep 0.3
# Genuinely STALE heartbeat (real Unix epoch, 300s old) → would normally gap-block...
OLD2=$(( $(date +%s) - 300 ))
printf '%s|1|THINKING|?|%s|1\n' "$OLD2" "$OLD2" > "/tmp/cc-heartbeat-${SESS2}"
# ...but a FRESH turn-done marker says the turn legitimately completed.
printf '{"ts":"now","event":"turn_done"}\n' > "/tmp/cc-turn-done-${SESS2}"

out7=$(bash "$FINISH" --session "$SESS2" --target "none-$$" 2>&1); rc7=$?
# Test 7: fresh turn-done overrides the stale-heartbeat gap block → not rejected (rc≠2)
if [[ "$rc7" -ne 2 ]] && ! printf '%s' "$out7" | grep -q '拒绝收尾'; then
  ok "fresh turn-done overrides stale-heartbeat gap block (completion authority)"
else
  bad "turn-done did not override gap block: rc=$rc7 out=$out7"
fi

# Test 8: turn-done marker cleaned on --kill-session
bash "$FINISH" --session "$SESS2" --target "none-$$" --kill-session >/dev/null 2>&1
[[ -f "/tmp/cc-turn-done-${SESS2}" ]] && bad "turn-done marker NOT cleaned on kill" || ok "turn-done marker cleaned on kill (D-4)"

# ─── §Phase-2: cc-finish --kill-session kills the resident watcher daemon ───
echo ""
echo "§Phase-2 cc-finish kills the resident watcher (PID recorded in lock dir)"
SESS3="cctmux-test-finish3-$$"; TGT3="cctmux-test-finish3-tgt-$$"
tmux new-session -d -s "$SESS3" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1; sleep 0.2
mkdir -p "/tmp/cc-lock-${TGT3}"; echo "$SESS3" > "/tmp/cc-lock-${TGT3}/session"
sleep 999 & WPID=$!; echo "$WPID" > "/tmp/cc-lock-${TGT3}/watcher_pid"
NOW3=$(date +%s); printf '%s|1|IDLE|?|%s|1\n' "$NOW3" "$NOW3" > "/tmp/cc-heartbeat-${SESS3}"
bash "$FINISH" --session "$SESS3" --target "$TGT3" --release-lock --kill-session >/dev/null 2>&1
sleep 0.3
# Test 9: the recorded watcher PID is dead after finish --kill-session
if kill -0 "$WPID" 2>/dev/null; then
  bad "watcher PID still alive after finish --kill-session"; kill "$WPID" 2>/dev/null || true
else
  ok "finish --kill-session kills resident watcher (PID from lock)"
fi
tmux kill-session -t "$SESS3" 2>/dev/null || true
rm -rf "/tmp/cc-lock-${TGT3}" "/tmp/cc-heartbeat-${SESS3}" "/tmp/cc-state-${SESS3}.log" \
       "/tmp/cc-turn-done-${SESS3}" "/tmp/cc-freeze-${SESS3}" "/tmp/cc-watch-${SESS3}.log"

# ─── §Phase-3: turn-done is the COMPLETION AUTHORITY (heartbeat demoted to auxiliary) ───
echo ""
echo "§Phase-3 turn-done acknowledged as completion authority even with a FRESH heartbeat"
SESS4="cctmux-test-finish4-$$"
tmux new-session -d -s "$SESS4" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1; sleep 0.2
NOW4=$(date +%s)
printf '%s|1|IDLE|?|%s|1\n' "$NOW4" "$NOW4" > "/tmp/cc-heartbeat-${SESS4}"   # FRESH heartbeat
printf '{"ts":"now","event":"turn_done"}\n'  > "/tmp/cc-turn-done-${SESS4}"  # FRESH turn-done
out10=$(bash "$FINISH" --session "$SESS4" --target "none4-$$" 2>&1); rc10=$?
# Test 10: with both fresh, finish must lead with turn-done as the AUTHORITY (not just
# "监控新鲜"), proving heartbeat is now auxiliary. No block.
if [[ "$rc10" -ne 2 ]] && printf '%s' "$out10" | grep -qE '完成权威|turn-done'; then
  ok "turn-done acknowledged as completion authority (heartbeat auxiliary)"
else
  bad "turn-done not acknowledged as authority: rc=$rc10 out=$out10"
fi
tmux kill-session -t "$SESS4" 2>/dev/null || true
rm -f "/tmp/cc-heartbeat-${SESS4}" "/tmp/cc-state-${SESS4}.log" "/tmp/cc-turn-done-${SESS4}"

# ── Residue gate tests (Step 1 hard gate) ──────────────────
echo ""
echo "--- residue gate ---"

# Helper: create a session with ❯ + given residual text
make_residue_session() {
  local name="$1" text="$2"
  tmux new-session -d -s "$name" -x 100 -y 20 "echo 'some output'; printf '❯ ${text}'; sleep 999" </dev/null >/dev/null 2>&1
  sleep 0.3
}

# Test R1: dangerous residue → exit 10
RSESS="cctmux-test-residue-$$"
make_residue_session "$RSESS" "rm -rf /tmp/test"
set +e; out=$(bash "$FINISH" --session "$RSESS" 2>&1); rc=$?; set -e
if [[ "$rc" -eq 10 ]] && printf '%s' "$out" | grep -q 'HARD GATE'; then
  ok "危险残留 rm -rf → exit 10 (硬门)"
else
  bad "危险残留 rm -rf: rc=$rc (expected 10)"
fi
tmux kill-session -t "$RSESS" 2>/dev/null || true

# Test R2: sudo → exit 10
RSESS2="cctmux-test-residue2-$$"
make_residue_session "$RSESS2" "sudo rm /var/log/syslog"
set +e; out=$(bash "$FINISH" --session "$RSESS2" 2>&1); rc=$?; set -e
if [[ "$rc" -eq 10 ]]; then
  ok "危险残留 sudo → exit 10"
else
  bad "危险残留 sudo: rc=$rc (expected 10)"
fi
tmux kill-session -t "$RSESS2" 2>/dev/null || true

# Test R3: harmless residue → exit 1 (not 10)
RSESS3="cctmux-test-residue3-$$"
make_residue_session "$RSESS3" "ls -la /tmp"
# Fresh turn-done + heartbeat to pass monitoring gap gate
echo "$(date +%s)|1|IDLE|0|0|0|0" > "/tmp/cc-heartbeat-${RSESS3}"
date +%s > "/tmp/cc-turn-done-${RSESS3}"
set +e; out=$(bash "$FINISH" --session "$RSESS3" 2>&1); rc=$?; set -e
if [[ "$rc" -eq 1 ]] && printf '%s' "$out" | grep -q '残留为非危险'; then
  ok "无害残留 ls → exit 1 (非硬门)"
else
  bad "无害残留 ls: rc=$rc (expected 1)"
fi
tmux kill-session -t "$RSESS3" 2>/dev/null || true
rm -f "/tmp/cc-heartbeat-${RSESS3}" "/tmp/cc-turn-done-${RSESS3}"

# Test R4: clean ❯ → no residue warning
RSESS4="cctmux-test-residue4-$$"
tmux new-session -d -s "$RSESS4" -x 100 -y 20 "echo 'output'; printf '❯ '; sleep 999" </dev/null >/dev/null 2>&1
sleep 0.3
set +e; out=$(bash "$FINISH" --session "$RSESS4" 2>&1); rc=$?; set -e
# No residue → should NOT exit 1 or 10 due to residue. It might exit non-zero for missing heartbeat.
if printf '%s' "$out" | grep -q '无残留输入'; then
  ok "干净 ❯ → 检测为无残留"
else
  bad "干净 ❯: 未检测到 '无残留输入'"
fi
tmux kill-session -t "$RSESS4" 2>/dev/null || true

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
