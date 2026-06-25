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
  "cat /tmp/cc-start-fake-fixture.txt; sleep 999" </dev/null >/dev/null 2>&1
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

# Test 5: §D-4 — the claude launch line must inject CC_TMUX_SESSION=<tmux name> so the
# in-CC hooks key per-session state by the tmux name (aligning with cc-monitor/-send/
# -finish). `VAR=val claude …` sets the launched process env by shell semantics; the
# claude→hook propagation itself is a deployment smoke item, not unit-testable here.
if grep 'claude --model' "$START" | grep -Eq 'CC_TMUX_SESSION=.*SESSION'; then
  ok "#D4 cc-start launch injects CC_TMUX_SESSION=\$SESSION"
else
  bad "#D4 cc-start launch does NOT inject CC_TMUX_SESSION"
fi

# Test 6: §Phase1 — launch line must export CC_TMUX_HOOK_DIR so the in-CC hooks
# self-locate their scripts in the SKILL dir (R2-verified env propagation), making
# the skill the single source — no global ~/.claude/hooks copy needed.
if grep 'claude --model' "$START" | grep -q 'CC_TMUX_HOOK_DIR='; then
  ok "#P1 cc-start launch exports CC_TMUX_HOOK_DIR"
else
  bad "#P1 cc-start launch does NOT export CC_TMUX_HOOK_DIR"
fi

# Test 7: §Phase1 — launch line must inject --settings <runtime template> so each
# launch auto-syncs the latest hook config from the skill (no cp/jq/restart).
if grep 'claude --model' "$START" | grep -q -- '--settings'; then
  ok "#P1 cc-start launch injects --settings"
else
  bad "#P1 cc-start launch does NOT inject --settings"
fi

# Test 8: §Phase1 — runtime settings template exists and its script-path hooks
# self-locate via $CC_TMUX_HOOK_DIR (NOT a hardcoded ~/.claude/hooks global copy).
RUNTIME_TPL="$REAL_ROOT/templates/settings.runtime.json"
if [[ -f "$RUNTIME_TPL" ]] \
   && grep -q 'CC_TMUX_HOOK_DIR' "$RUNTIME_TPL" \
   && ! grep -q '\.claude/hooks' "$RUNTIME_TPL"; then
  ok "#P1 settings.runtime.json self-locates hooks via \$CC_TMUX_HOOK_DIR"
else
  bad "#P1 settings.runtime.json missing or still uses ~/.claude/hooks"
fi

# Test 9: §Phase2 — cc-start spawns the resident watcher daemon in the background and
# records its PID in the lock dir so cc-finish can kill it (the ONE deterministic poller,
# moving monitoring cadence off the LLM).
if grep -Eq 'cc-watcher\.sh.*--watch' "$START" && grep -q 'watcher_pid' "$START"; then
  ok "#P2 cc-start spawns cc-watcher --watch + records watcher_pid in lock"
else
  bad "#P2 cc-start does NOT spawn watcher daemon / record watcher_pid"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
