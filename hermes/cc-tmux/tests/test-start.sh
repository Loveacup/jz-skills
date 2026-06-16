#!/usr/bin/env bash
# test-start.sh — TDD test for cc-start.sh §3.8 marginal hardening (#3 / #7)
#
# Tests:
#  1. #7 self-check: redirected SKILL_ROOT (missing scripts/) → exit 1 + diagnosis
#  2. #7 self-check: valid root but missing --task → still reaches usage error (exit 1)
#  3. #7 self-check: valid root passes (does NOT false-trip on the real install)
#  4. #3 exit3: an active OTHER CC session present (no --ack-active) → exit 3 + paste-ready cmd
#
# Safe: every path here exits BEFORE the mkdir lock / claude launch.

set -euo pipefail

START="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-start.sh"
REAL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAKECC="hermes-cc-faketgt-99999"
PASS=0 FAIL=0

cleanup() {
  tmux kill-session -t "$FAKECC" 2>/dev/null || true
  rm -f "/tmp/cc-start-fake-fixture.txt"
}
trap cleanup EXIT

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "=== cc-start TDD: §3.8 #3/#7 hardening ==="
echo ""

# Test 1: redirected/broken SKILL_ROOT → exit 1 with HOME-redirection diagnosis
out=$(CC_TMUX_SKILL_ROOT="/tmp/definitely-not-here-$$" bash "$START" \
        --target t1 --task "x" 2>&1) && rc=0 || rc=$?
if [[ "${rc:-0}" -eq 1 ]] && printf '%s' "$out" | grep -q '重定向'; then
  ok "#7 broken SKILL_ROOT → exit 1 + diagnosis"
else
  bad "#7 broken SKILL_ROOT → expected exit 1 + 重定向 msg, got rc=${rc:-0}: $out"
fi

# Test 2: valid root but missing --task → usage error (exit 1), self-check transparent
out=$(CC_TMUX_SKILL_ROOT="$REAL_ROOT" bash "$START" --target t2 2>&1) && rc=0 || rc=$?
if [[ "${rc:-0}" -eq 1 ]] && printf '%s' "$out" | grep -qi 'usage'; then
  ok "#7 valid root + missing --task → usage exit 1"
else
  bad "#7 valid root + missing --task → expected usage exit 1, got rc=${rc:-0}: $out"
fi

# Test 3: valid root must NOT false-trip the self-check (no '重定向' on real install)
out=$(CC_TMUX_SKILL_ROOT="$REAL_ROOT" bash "$START" 2>&1) && rc=0 || rc=$?
if printf '%s' "$out" | grep -q '重定向'; then
  bad "#7 valid root false-tripped self-check: $out"
else
  ok "#7 valid root does not false-trip self-check"
fi

# Test 4: an active OTHER CC session → exit 3 + paste-ready --ack-active command
printf '⏺ Writing file…\n' > "/tmp/cc-start-fake-fixture.txt"
tmux new-session -d -s "$FAKECC" -x 120 -y 20 \
  "cat /tmp/cc-start-fake-fixture.txt; sleep 999" 2>/dev/null
sleep 0.6
out=$(CC_TMUX_SKILL_ROOT="$REAL_ROOT" bash "$START" \
        --target uniq-test-tgt-$$ --task "demo" 2>&1) && rc=0 || rc=$?
if [[ "${rc:-0}" -eq 3 ]] \
   && printf '%s' "$out" | grep -q -- '--ack-active' \
   && printf '%s' "$out" | grep -q '可粘贴'; then
  ok "#3 active other CC → exit 3 + paste-ready cmd"
else
  bad "#3 active other CC → expected exit 3 + paste-ready, got rc=${rc:-0}: $out"
fi
# Safety: ensure no lock dir was created for the test target
rm -rf "/tmp/cc-lock-uniq-test-tgt-$$" 2>/dev/null || true

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
