#!/usr/bin/env bash
# test-wait-marker.sh — TDD for cc-wait-marker.sh (§3 In-Turn Wait)
#
# cc-wait-marker.sh blocks until a turn-done marker NEWER than --after appears,
# so Hermes can `process(action=wait)` on it inside a single turn and loop
# send → wait → read → send. Contract under test:
#   --session <name>   build marker path /private/tmp/cc-turn-done-<name>
#   --after <epoch>    block until mtime(marker) > after  (strict >)
#   --timeout <secs>   default 21600; on expiry exit 1
#   exit 0 + cat marker → a marker strictly newer than --after appeared
#   exit 1             → timeout, no newer marker
#   exit 2 + stderr    → bad/missing args (e.g. no --session)
#   poll interval 2s, paths under /private/tmp (macOS symlink)
#
# NOTE on Test 3: the task spec's literal "--after N+100" contradicts the
# core contract ("block until mtime > after") and Test 6. The spec's own
# parenthetical "(marker 存在且更新)" reveals the intent: a marker ALREADY
# NEWER than --after → immediate exit 0. We therefore encode Test 3 as
# marker mtime=N with --after = N-100 (after is OLDER than the marker).
# Flagged for confirmation at the RED review gate.

set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-wait-marker.sh"
SESS="cctmux-test-waitmarker-$$"
MARKER="/private/tmp/cc-turn-done-${SESS}"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){ rm -f "$MARKER" "/tmp/cc-turn-done-${SESS}"; }
trap cleanup EXIT
cleanup

# Wait up to $1 seconds for pid $2 to exit; returns when dead or on deadline.
wait_pid_exit(){
  local secs="$1" pid="$2" i=0
  while [[ "$i" -lt "$secs" ]]; do
    kill -0 "$pid" 2>/dev/null || return 0
    sleep 1; i=$((i+1))
  done
  return 1
}

echo "=== cc-wait-marker TDD: in-turn wait on turn-done marker (§3) ==="
echo ""

# ── Test 1: a NEWER marker appears after start → exit 0, stdout = marker content ──
printf 'OLD\n' > "$MARKER"
touch -t 202601010000.00 "$MARKER" 2>/dev/null || true   # old mtime (2026-01-01)
AFTER=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
outf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after "$AFTER" --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-1\n' > "$MARKER"        # fresh mtime (now) > AFTER
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-1' "$outf"; then
    ok "newer marker after start → exit 0 + emits marker content"
  else
    bad "newer marker: rc=$rc out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "newer marker: script never exited"
fi
rm -f "$outf"

# ── Test 2: no marker at start, --after 0, marker appears → exit 0 + content ──
rm -f "$MARKER"
outf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout 30 >"$outf" 2>/dev/null &
pid=$!
sleep 1
printf 'DONE-2\n' > "$MARKER"
if wait_pid_exit 10 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 0 ]] && grep -q 'DONE-2' "$outf"; then
    ok "no prior marker, --after 0 → waits then exit 0 + content"
  else
    bad "no-prior-marker: rc=$rc out='$(tr -d '\n' <"$outf")'"
  fi
else
  kill "$pid" 2>/dev/null; bad "no-prior-marker: script never exited"
fi
rm -f "$outf"

# ── Test 3: marker already NEWER than --after → immediate exit 0 + content ──
# (See header NOTE: spec's "--after N+100" reinterpreted as marker newer than after.)
printf 'DONE-3\n' > "$MARKER"
N=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
AFTER=$((N - 100))
outf=$(mktemp)
start=$(date +%s)
bash "$SCRIPT" --session "$SESS" --after "$AFTER" --timeout 30 >"$outf" 2>/dev/null
rc=$?
elapsed=$(( $(date +%s) - start ))
if [[ "$rc" -eq 0 ]] && grep -q 'DONE-3' "$outf" && [[ "$elapsed" -lt 3 ]]; then
  ok "marker already newer than --after → immediate exit 0 (${elapsed}s) + content"
else
  bad "already-newer: rc=$rc elapsed=${elapsed}s out='$(tr -d '\n' <"$outf")'"
fi
rm -f "$outf"

# ── Test 4: no marker, --timeout 3 → exit 1 after ~timeout ──
rm -f "$MARKER"
start=$(date +%s)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout 3 >/dev/null 2>&1
rc=$?
elapsed=$(( $(date +%s) - start ))
if [[ "$rc" -eq 1 ]] && [[ "$elapsed" -ge 3 ]] && [[ "$elapsed" -lt 12 ]]; then
  ok "no marker, --timeout 3 → exit 1 (after ${elapsed}s)"
else
  bad "timeout: rc=$rc elapsed=${elapsed}s (want rc=1, 3<=t<12)"
fi

# ── Test 5: missing --session → exit 2 + stderr message ──
err=$(bash "$SCRIPT" --after 0 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "missing --session → exit 2 + stderr"
else
  bad "arg-validation: rc=$rc (want 2) stderr='$(printf '%s' "$err" | tr -d '\n')'"
fi

# ── Test 6: marker NOT newer than --after → blocks (does not exit) ──
printf 'STALE\n' > "$MARKER"
N=$(stat -f %m "$MARKER" 2>/dev/null || echo 0)
bash "$SCRIPT" --session "$SESS" --after "$N" --timeout 30 >/dev/null 2>&1 &
pid=$!
sleep 3
if kill -0 "$pid" 2>/dev/null; then
  ok "marker not newer than --after → still blocking after 3s"
  kill "$pid" 2>/dev/null
else
  bad "marker not newer → exited early (should block)"
fi
wait "$pid" 2>/dev/null || true

# ── Test 7: unknown arg → exit 2 + stderr ──
err=$(bash "$SCRIPT" --session "$SESS" --bogus 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "unknown arg → exit 2 + stderr"
else
  bad "unknown-arg: rc=$rc (want 2) stderr='$(printf '%s' "$err" | tr -d '\n')'"
fi

# ── Test 8: -h/--help → exit 0 + usage on stderr ──
out=$(bash "$SCRIPT" --help 2>&1); rc=$?
if [[ "$rc" -eq 0 ]] && printf '%s' "$out" | grep -qi 'usage'; then
  ok "--help → exit 0 + usage"
else
  bad "help: rc=$rc (want 0) out='$(printf '%s' "$out" | tr -d '\n' | cut -c1-40)'"
fi

# ── Test 9: --after as trailing arg with no value → exit 2 (not unbound crash) ──
err=$(bash "$SCRIPT" --session "$SESS" --after 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "--after missing value → exit 2 + stderr"
else
  bad "after-missing-value: rc=$rc (want 2; rc=1 = set -u unbound crash)"
fi

# ── Test 10: --timeout as trailing arg with no value → exit 2 (not unbound crash) ──
err=$(bash "$SCRIPT" --session "$SESS" --timeout 2>&1 >/dev/null); rc=$?
if [[ "$rc" -eq 2 ]] && [[ -n "$err" ]]; then
  ok "--timeout missing value → exit 2 + stderr"
else
  bad "timeout-missing-value: rc=$rc (want 2; rc=1 = set -u unbound crash)"
fi

# ── Test 11: non-numeric --after → exit 2 (input validation, no hang/late timeout) ──
errf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after notanum --timeout 5 >/dev/null 2>"$errf" &
pid=$!
if wait_pid_exit 6 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 2 ]] && [[ -s "$errf" ]]; then
    ok "non-numeric --after → exit 2 + stderr"
  else
    bad "non-numeric-after: rc=$rc (want 2; rc=1 = blocked to timeout, no validation)"
  fi
else
  kill "$pid" 2>/dev/null; bad "non-numeric-after: never exited (no validation, would hang)"
fi
rm -f "$errf"

# ── Test 12: non-numeric --timeout → exit 2 (must not infinite-loop on bad arith) ──
errf=$(mktemp)
bash "$SCRIPT" --session "$SESS" --after 0 --timeout notanum >/dev/null 2>"$errf" &
pid=$!
if wait_pid_exit 6 "$pid"; then
  wait "$pid" 2>/dev/null; rc=$?
  if [[ "$rc" -eq 2 ]] && [[ -s "$errf" ]]; then
    ok "non-numeric --timeout → exit 2 + stderr"
  else
    bad "non-numeric-timeout: rc=$rc (want 2)"
  fi
else
  kill "$pid" 2>/dev/null; bad "non-numeric-timeout: never exited (infinite loop on bad arith)"
fi
rm -f "$errf"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
