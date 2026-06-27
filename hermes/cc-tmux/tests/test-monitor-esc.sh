#!/usr/bin/env bash
# test-monitor-esc.sh — TDD test for cc-monitor.sh "esc to interrupt" gold-standard signal
#
# CC's active turn renders "esc to interrupt" at the bottom — a single, stable,
# self-rendered BUSY marker, more reliable than spinner-glyph/token heuristics.
# Contract under test:
#   1. esc in active tail (last 6 non-empty lines) → BUSY (default bucket THINKING),
#      glyph ⏺/● vs ✻ still subdivides TOOL/THINKING (existing behavior, unchanged).
#   2. no esc + empty ❯ → IDLE (positive confirmation preserved).
#   3. esc present but THINK_TIME+token both stalled → STILL a freeze (esc does NOT
#      grant a liveness exemption — Pitfall #24 anti-pattern guard).
#   4. esc lingering in scrollback (NOT active tail) + empty ❯ → IDLE, not BUSY.
#
# TC1 is RED before the fix (esc-only, no glyph → falls through to STARTING), GREEN after.

set -euo pipefail

MONITOR="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-monitor.sh"
SESSION="cctmux-test-esc"
PASS=0 FAIL=0

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -f "/tmp/cc-heartbeat-${SESSION}" "/tmp/cc-state-${SESSION}.log" \
        "/tmp/cc-fixture-${SESSION}.txt" "/tmp/cc-monitor-stderr-${SESSION}.txt" \
        "/tmp/cc-freeze-${SESSION}"
}
trap cleanup EXIT

# State assertion via META stderr line (mirrors test-monitor.sh)
run_state_test() {
  local name="$1" fixture="$2" expected_state="$3"

  cleanup

  printf '%s\n' "$fixture" > "/tmp/cc-fixture-${SESSION}.txt"
  tmux new-session -d -s "$SESSION" -x 120 -y 20 "cat /tmp/cc-fixture-${SESSION}.txt; sleep 999" </dev/null >/dev/null 2>&1
  sleep 0.8

  local stderr_file="/tmp/cc-monitor-stderr-${SESSION}.txt"
  bash "$MONITOR" --session "$SESSION" >/dev/null 2>"$stderr_file" || true
  local meta result
  meta=$(grep "^META" "$stderr_file" | head -1 || echo "")
  result=$(echo "$meta" | grep -o 'state=[A-Z_]*' | cut -d= -f2 || echo "UNKNOWN")

  if [[ "$result" == "$expected_state" ]]; then
    echo "  ✅ $name → $result"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name → expected $expected_state, got $result"
    FAIL=$((FAIL+1))
  fi

  rm -f "$stderr_file"
  cleanup
}

echo "=== cc-monitor TDD: 'esc to interrupt' gold-standard BUSY signal ==="
echo ""

# ── TC1: esc-only (no spinner glyph, no ❯) → gold standard alone gates BUSY ──
# RED before fix: no glyph/tool/idle signal → STARTING. GREEN after: esc → THINKING.
run_state_test "TC1 esc-only (no glyph) → BUSY/THINKING" \
'esc to interrupt' \
"THINKING"

# ── TC2: no esc + empty ❯ → IDLE (positive confirmation still holds) ──
run_state_test "TC2 no esc + empty ❯ → IDLE" \
'❯ ' \
"IDLE"

# ── TC4: esc lingering in scrollback (pushed out of last-6 active tail) → IDLE ──
# esc at top, >6 filler non-empty lines below it, empty ❯ at the very bottom.
# Active tail (last 6 non-empty) must NOT include the stale esc → not misjudged BUSY.
run_state_test "TC4 esc in scrollback (not active tail) → IDLE" \
'esc to interrupt
filler line 1
filler line 2
filler line 3
filler line 4
filler line 5
filler line 6
filler line 7
❯ ' \
"IDLE"

# ── TC3: esc present but THINK_TIME+token double-stall → STILL freeze ──
# esc does not exempt from freeze detection (Pitfall #24). Mirror the freeze-marker
#口径 from test-monitor-freeze.sh: establish baseline, age TOKCHG_EPOCH ~300s, re-probe.
echo ""
echo "TC3 esc + double-stall → freeze marker still written (no liveness exemption)"
cleanup
printf 'esc to interrupt\n' > "/tmp/cc-fixture-${SESSION}.txt"
tmux new-session -d -s "$SESSION" -x 120 -y 20 \
  "while true; do cat /tmp/cc-fixture-${SESSION}.txt; sleep 0.2; done" </dev/null >/dev/null 2>&1
sleep 0.8
bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
# Age TOKCHG_EPOCH ~300s into the past (preserve 7-field schema; 6th read var absorbs SEQ|THINK_TIME)
HBF="/tmp/cc-heartbeat-${SESSION}"
IFS='|' read -r e1 e2 e3 e4 _ e6 < "$HBF" 2>/dev/null || true
printf '%s|%s|%s|%s|%d|%s\n' "${e1:-0}" "${e2:-0}" "${e3:-THINKING}" "${e4:-?}" "$(( $(date +%s) - 300 ))" "${e6:-0}" > "$HBF"
bash "$MONITOR" --session "$SESSION" --force-capture >/dev/null 2>/dev/null || true
if [[ -f "/tmp/cc-freeze-${SESSION}" ]]; then
  echo "  ✅ esc + double-stall → freeze marker written (esc grants no exemption)"; PASS=$((PASS+1))
else
  echo "  ❌ esc wrongly suppressed freeze detection (no marker)"; FAIL=$((FAIL+1))
fi
cleanup

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
rm -f /tmp/cc-monitor-stderr-*.txt
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
