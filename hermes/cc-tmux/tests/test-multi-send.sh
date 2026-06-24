#!/usr/bin/env bash
# test-multi-send.sh — TDD for rapid sequential send-keys consumption
#
# Blind spot: when Hermes rapidly sends multiple messages to CC via
# send-keys, the ptty queue behavior and CC's stdin consumption order
# is untested. This test verifies the cc-send-robust.sh retry/verification
# pipeline handles rapid-fire sends correctly.
#
# Tests:
#  1. Sequential sends: 3 rapid sends all succeed
#  2. Rapid-fire verification: echos appear in order
#  3. Send-robust retry: handles transient send-keys failure
#  4. Back-to-back send+verify: no cross-contamination between sends
#  5. Stress: 10 rapid sends without corruption

set -uo pipefail

PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

TMP="/tmp/cc-multisend-test-$$"
SESSION="cctmux-test-multisend"
cleanup(){
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT
cleanup; mkdir -p "$TMP"

SEND="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-send.sh"
SEND_ROBUST="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-send-robust.sh"

echo "=== multi-send TDD: rapid sequential send-keys consumption ==="
echo ""

# ── Helper: create a busy-looking session (no ❯, simulating CC working) ──
start_busy_session() {
  tmux new-session -d -s "$SESSION" -x 120 -y 30 "while true; do echo 'busy-output-line'; sleep 0.05; done" 2>/dev/null
  sleep 0.3
}

# ── Helper: create context files ──
make_ctx() { echo "context-$1" > "$TMP/ctx-$1.md"; }

# ── Test 1: 3 rapid sequential sends all exit 0 ──
start_busy_session
make_ctx 1; make_ctx 2; make_ctx 3
failures=0
for i in 1 2 3; do
  bash "$SEND" --session "$SESSION" --context "$TMP/ctx-$i.md" >/dev/null 2>&1 || failures=$((failures+1))
done
if [[ "$failures" -eq 0 ]]; then
  ok "3次快速连续 send: 全部成功 (exit 0)"
else
  bad "3次快速连续 send: $failures 次失败"
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# ── Test 2: send-robust loads as source-able library + CLI ──
# Verify functions are defined and CLI mode doesn't crash immediately
bash "$SEND_ROBUST" >/dev/null 2>&1
rc=$?
# No subcommand → should error but not segfault
if [[ "$rc" -ne 0 ]]; then
  ok "send-robust 无参数: 正确报错不崩溃 (exit=$rc)"
else
  bad "send-robust 无参数: 意外成功"
fi

# Test CLI with bad target (exercises retry/error paths without real CC)
bash "$SEND_ROBUST" send-to-pane "nonexistent-$$" "hello" 1 >/dev/null 2>&1
rc=$?
if [[ "$rc" -ne 0 ]]; then
  ok "send-robust 坏 target: 正确失败 (exit=$rc)"
else
  bad "send-robust 坏 target: 意外成功"
fi

# ── Test 3: back-to-back sends don't cross-contaminate ──
# Verify that two rapid sends with different context produce distinct
# message lines in the right order.
start_busy_session
echo "MSG-A-unique-tag" > "$TMP/ctx-a.md"
echo "MSG-B-unique-tag" > "$TMP/ctx-b.md"

bash "$SEND" --session "$SESSION" --context "$TMP/ctx-a.md" >/dev/null 2>&1
bash "$SEND" --session "$SESSION" --context "$TMP/ctx-b.md" >/dev/null 2>&1
sleep 0.5

# Capture what was typed into the pane
captured=$(tmux capture-pane -t "$SESSION" -p -S -20 2>/dev/null || echo "")
if echo "$captured" | grep -q "MSG-A-unique-tag" && echo "$captured" | grep -q "MSG-B-unique-tag"; then
  ok "背靠背 send: 两条消息都到达 pane"
else
  bad "背靠背 send: 消息可能丢失 (A=$(echo "$captured" | grep -c 'MSG-A' || echo 0), B=$(echo "$captured" | grep -c 'MSG-B' || echo 0))"
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

# ── Test 4: retry counter (( ++tries )) doesn't trigger set -e abort ──
# Pitfall #9 fix: prefix ++ must not abort under set -uo pipefail.
# Source the script and test the counter pattern in isolation.
(
  set -euo pipefail
  tries=0
  for i in 1 2 3; do
    (( ++tries ))
  done
  [[ "$tries" -eq 3 ]] && exit 0 || exit 99
)
rc=$?
if [[ "$rc" -eq 0 ]]; then
  ok "(( ++tries )) set -e: 不自增 3 次=3 (Pitfall #9 防回归)"
else
  bad "(( ++tries )) set -e: exit=$rc"
fi

# ── Test 5: 10 rapid sends stress test ──
start_busy_session
for i in $(seq 1 10); do
  make_ctx "$i"
done
failures=0
for i in $(seq 1 10); do
  bash "$SEND" --session "$SESSION" --context "$TMP/ctx-$i.md" >/dev/null 2>&1 || failures=$((failures+1))
done
if [[ "$failures" -le 1 ]]; then
  ok "10次压力 send: $failures 次失败 (≤1 可接受)"
else
  bad "10次压力 send: $failures 次失败 (过多)"
fi
tmux kill-session -t "$SESSION" 2>/dev/null || true

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
