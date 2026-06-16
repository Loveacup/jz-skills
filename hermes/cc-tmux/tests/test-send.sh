#!/usr/bin/env bash
# test-send.sh — TDD test for cc-send.sh post-send verification (§3.2)
#
# Tests (now exercise the verify logic against REAL ❯-prompt fixtures,
# not bare `sleep 999` sessions where no prompt ever renders):
#  1. Basic send to a busy session (no ❯) → treated as consumed → rc 0
#  2. Send --message to a busy session → rc 0
#  3. Missing session → rc 1
#  4. --dry-run never escalates → rc 0
#  5. --expect writes expected-artifacts file → rc 0
#  6. Empty ❯ prompt fixture → verified success → rc 0
#  7. Stuck residual ❯ (Enter never registers) → escalation → rc 2   [§3.2 core]
#  8. Stuck queue mode ("Press up to edit") → escalation → rc 2       [§3.2 core]
#  9. --dry-run over a stuck residual fixture → simulated, rc 0 (no escalation)

set -euo pipefail

SEND="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-send.sh"
SESSION="cctmux-test-send"
PASS=0 FAIL=0

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -f "/tmp/cc-send-test-ctx.md" "/tmp/cc-send-fixture-${SESSION}.txt" "/tmp/cc-expect-${SESSION}"
}
trap cleanup EXIT

echo "# test context" > "/tmp/cc-send-test-ctx.md"

# run_test [--fixture <content>] [--redraw <line>] <name> <expected_rc> -- <send args...>
#   --fixture : static one-shot content (cat then sleep)
#   --redraw  : self-redrawing loop that re-clears + reprints <line> every 0.3s,
#               so tty echo of injected keystrokes cannot mask a "stuck" banner.
run_test() {
  local launch="sleep 999"
  case "${1:-}" in
    --fixture)
      printf '%s\n' "$2" > "/tmp/cc-send-fixture-${SESSION}.txt"
      launch="cat /tmp/cc-send-fixture-${SESSION}.txt; sleep 999"; shift 2 ;;
    --redraw)
      launch="while true; do printf '\\033[2J\\033[H%s\\n' '$2'; sleep 0.3; done"; shift 2 ;;
  esac
  local name="$1" expected_rc="$2"; shift 2
  local output rc

  cleanup
  tmux new-session -d -s "$SESSION" -x 120 -y 20 "$launch" 2>/dev/null
  sleep 0.6

  output=$(bash "$SEND" "$@" 2>&1) || rc=$?
  rc=${rc:-0}

  if [[ "$rc" -eq "$expected_rc" ]]; then
    echo "  ✅ $name (rc=$rc)"
    PASS=$((PASS+1))
  else
    echo "  ❌ $name → expected rc=$expected_rc, got rc=$rc"
    printf '%s\n' "$output" | sed 's/^/      | /'
    FAIL=$((FAIL+1))
  fi

  cleanup
}

echo "=== cc-send TDD: Post-send Verification (§3.2) ==="
echo ""

# Test 1: Basic send to busy session (no ❯ visible) → consumed → rc 0
run_test "Basic send (--context, busy)" 0 \
  --session "$SESSION" --context "/tmp/cc-send-test-ctx.md"

# Test 2: send --message to busy session → rc 0
run_test "Send message (busy)" 0 \
  --session "$SESSION" --message "hello"

# Test 3: Missing session → exit 1
run_test "Missing session" 1 \
  --session "nonexistent-session-99999"

# Test 4: --dry-run never escalates → rc 0
run_test "Dry-run mode accepted" 0 \
  --session "$SESSION" --context "/tmp/cc-send-test-ctx.md" --dry-run

# Test 5: --expect writes expected-artifacts file → rc 0
run_test "--expect writes artifact file" 0 \
  --session "$SESSION" --context "/tmp/cc-send-test-ctx.md" --expect "output-*.md"
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" 2>/dev/null
bash "$SEND" --session "$SESSION" --context "/tmp/cc-send-test-ctx.md" --expect "output-*.md" >/dev/null 2>&1 || true
if [[ -f "/tmp/cc-expect-${SESSION}" ]]; then
  echo "     ↳ expect file verified: $(cat /tmp/cc-expect-${SESSION})"
else
  echo "     ⚠️ expect file NOT written"; FAIL=$((FAIL+1))
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true
rm -f "/tmp/cc-expect-${SESSION}"

# Test 6: empty ❯ prompt fixture → verified success → rc 0
run_test --fixture '❯ ' "Empty ❯ → verified success" 0 \
  --session "$SESSION" --message "go"

# Test 7: stuck residual ❯ (text never clears) → escalation → rc 2
run_test --redraw '❯ leftover unsent text' "Stuck residual ❯ → escalation rc 2" 2 \
  --session "$SESSION" --message "go"

# Test 8: stuck queue mode → escalation → rc 2
run_test --redraw 'Press up to edit queued messages' "Stuck queue → escalation rc 2" 2 \
  --session "$SESSION" --message "go"

# Test 9: dry-run over a stuck residual fixture → simulated, no escalation → rc 0
run_test --redraw '❯ leftover unsent text' "Dry-run over stuck residual → rc 0" 0 \
  --session "$SESSION" --message "go" --dry-run

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
