#!/usr/bin/env bash
# test-monitor.sh — TDD test for cc-monitor.sh state priority fix
#
# Creates real tmux sessions with fixture pane content,
# runs cc-monitor.sh, checks detected state from META stderr line.

set -euo pipefail

MONITOR="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-monitor.sh"
SESSION="cctmux-test-fix"
PASS=0 FAIL=0

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -f "/tmp/cc-heartbeat-${SESSION}" "/tmp/cc-state-${SESSION}.log" "/tmp/cc-fixture-${SESSION}.txt"
}
trap cleanup EXIT

run_test() {
  local name="$1" fixture="$2" expected_state="$3"
  
  cleanup
  
  # Write fixture to a file, then cat it in a tmux session so capture-pane sees it
  printf '%s\n' "$fixture" > "/tmp/cc-fixture-${SESSION}.txt"
  tmux new-session -d -s "$SESSION" -x 120 -y 20 "cat /tmp/cc-fixture-${SESSION}.txt; sleep 999" 2>/dev/null
  sleep 0.8  # let cat display the content
  
  # Run monitor, capture stderr
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

echo "=== cc-monitor TDD: State Priority Fix (§3.1) ==="
echo ""

# Test 1: TOOL active (⏺) + empty ❯ at bottom → TOOL wins
run_test "TOOL > IDLE (⏺ + ❯)" \
'⏺ Writing file…
❯ ' \
"TOOL"

# Test 2: THINKING active (✻) + empty ❯ → THINKING wins
run_test "THINKING > IDLE (✻ + ❯)" \
'✻ Thinking about code…
❯ ' \
"THINKING"

# Test 3: Pure IDLE — only empty ❯
run_test "Pure IDLE (only ❯)" \
'❯ ' \
"IDLE"

# Test 4: ✢ character (previously undetected by old regex)
run_test "✢ detected (✢ Julienning)" \
'✢ Julienning…
❯ ' \
"THINKING"

# Test 5: ✳ character
run_test "✳ detected" \
'✳ Canoodling…
❯ ' \
"THINKING"

# Test 6: ✶ character
run_test "✶ detected" \
'✶ Jitterbugging…
❯ ' \
"THINKING"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
rm -f /tmp/cc-monitor-stderr-*.txt
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
