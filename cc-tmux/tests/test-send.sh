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
  rm -f "/tmp/cc-send-fixture-${SESSION}.txt" "/tmp/cc-expect-${SESSION}"
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
      launch="while true; do printf '\\\\033[2J\\\\033[H%s\\\\n' '$2'; sleep 0.3; done"; shift 2 ;;
  esac
  local name="$1" expected_rc="$2"; shift 2
  local output rc

  cleanup
  # ensure context file exists for tests that need it
  echo "# test context" > "/tmp/cc-send-test-ctx.md"
  tmux new-session -d -s "$SESSION" -x 120 -y 20 "$launch" </dev/null >/dev/null 2>&1
  sleep 0.6

  output=$(bash "$SEND" "$@" 2>&1) || rc=$?
  rc=${rc:-0}

  # send_to_pane (P0-1) returns 1 for retry exhaustion, 4 for unsafe prompt text; both mean escalation
  if [[ "$rc" -eq "$expected_rc" ]] || { [[ "$expected_rc" -eq 2 && "$rc" -eq 1 ]]; } || { [[ "$expected_rc" -eq 2 && "$rc" -eq 4 ]]; }; then
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
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
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

# Test 10: missing --context file fails early
run_test "Missing context file → rc 1" 1 \
  --session "$SESSION" --context "/tmp/cc-send-missing-context.md" --dry-run

# Test 11: --context is path-only + includes orchestration hint; markdown body must not appear
cleanup
cat > "/tmp/cc-send-test-ctx.md" <<'EOF'
# SECRET BODY LINE SHOULD NOT BE SENT
Second markdown line should not be sent either.
EOF
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
out=$(bash "$SEND" --session "$SESSION" --context "/tmp/cc-send-test-ctx.md" --dry-run 2>&1); rc=$?
if [[ "$rc" -eq 0 && "$out" == *"Please read /tmp/cc-send-test-ctx.md and follow it."* && "$out" == *"Hermes is the messenger, CC is the factory"* && "$out" != *"SECRET BODY"* && "$out" != *"Second markdown"* ]]; then
  echo "  ✅ Context path-only + orchestration hint, no markdown body"
  PASS=$((PASS+1))
else
  echo "  ❌ Context path-only dry-run failed"
  printf '%s\n' "$out" | sed 's/^/      | /'
  FAIL=$((FAIL+1))
fi
cleanup

# Test 12: multiline --message is rejected
cleanup
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
set +e
out=$(bash "$SEND" --session "$SESSION" --message $'line1\nline2' --dry-run 2>&1); rc=$?
set -e
if [[ "$rc" -eq 1 && "$out" == *"multiline --message is not allowed"* ]]; then
  echo "  ✅ Multiline --message rejected"
  PASS=$((PASS+1))
else
  echo "  ❌ Multiline --message expected rc=1 got rc=$rc"
  printf '%s\n' "$out" | sed 's/^/      | /'
  FAIL=$((FAIL+1))
fi
cleanup

# Test 13: --context --no-prefix remains path-only (no body, no hint)
cleanup
cat > "/tmp/cc-send-test-ctx.md" <<'EOF'
# NO_PREFIX BODY SHOULD NOT BE SENT
EOF
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
out=$(bash "$SEND" --session "$SESSION" --context "/tmp/cc-send-test-ctx.md" --no-prefix --dry-run 2>&1); rc=$?
if [[ "$rc" -eq 0 && "$out" == *"/tmp/cc-send-test-ctx.md"* && "$out" != *"NO_PREFIX BODY"* && "$out" != *"Hermes is the messenger"* ]]; then
  echo "  ✅ --context --no-prefix is still path-only, no hint"
  PASS=$((PASS+1))
else
  echo "  ❌ --context --no-prefix leaked body/hint or failed"
  printf '%s\n' "$out" | sed 's/^/      | /'
  FAIL=$((FAIL+1))
fi
cleanup

# Test 14: --message does NOT include orchestration hint
cleanup
tmux new-session -d -s "$SESSION" -x 120 -y 20 "sleep 999" </dev/null >/dev/null 2>&1
out=$(bash "$SEND" --session "$SESSION" --message "do a quick thing" --dry-run 2>&1); rc=$?
if [[ "$rc" -eq 0 && "$out" == *"do a quick thing"* && "$out" != *"Hermes is the messenger"* ]]; then
  echo "  ✅ --message does not include orchestration hint"
  PASS=$((PASS+1))
else
  echo "  ❌ --message leaked orchestration hint"
  printf '%s\n' "$out" | sed 's/^/      | /'
  FAIL=$((FAIL+1))
fi
cleanup

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
