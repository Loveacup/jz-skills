#!/usr/bin/env bash
# test-send-robust.sh — TDD for scripts/cc-send-robust.sh (轨1 P0-1)
#
# 成功判据按 CC 现实（非 primeline 的"看到 message=成功"）：
#   consumed(空 ❯ / 无 ❯ = CC 已吃下输入) = 成功；
#   residual(❯ 后有残留文本 = Enter 未生效) / queue("Press up to edit") = 重试；
#   重试耗尽 = 非 0（不静默假成功，与 cc-send.sh §3.2 同哲学）。
#
# 用例：
#  1. 单行发送 → consumed → rc 0
#  2. Enter 未生效(residual) → 重试补 Enter → 恢复 consumed → rc 0   [核心: 按键驱动]
#  3. 持续 residual → 耗尽重试 → rc 1                                  [不静默假成功]
#  4. 多行发送(load/paste-buffer) → consumed → rc 0
#  5. C-u 清行 → pane 由脏变净 → 后续发送 consumed → rc 0
#  6. 不存在的 target → 非 0

set -uo pipefail

ROBUST="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-send-robust.sh"
SESSION="cctmux-test-robust"
FIXDIR="/tmp/cc-robust-fix.$$"
PASS=0 FAIL=0

# 加速时序：按键/C-u 驱动的 fixture 不依赖墙钟，缩短安全；留足 tmux 渲染余量
export CC_SEND_T_LITERAL=0.15 CC_SEND_T_VERIFY=0.4 CC_SEND_T_ESCAPE=0.15 CC_SEND_T_PASTE=0.2

mkdir -p "$FIXDIR"

cleanup() {
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  rm -rf "$FIXDIR"
}
trap cleanup EXIT

# ── fixtures（各自模拟一种 CC pane 状态）──

# 静态 consumed：空 ❯（CC 已吃下输入，正常态）
cat > "$FIXDIR/consumed.sh" <<'EOF'
#!/usr/bin/env bash
printf '\033[2J\033[H❯ \n'
sleep 999
EOF

# 永久 residual：❯ 后始终有残留文本（Enter 永不生效），自重绘防 tty 回显遮蔽
cat > "$FIXDIR/residual.sh" <<'EOF'
#!/usr/bin/env bash
while true; do printf '\033[2J\033[H❯ leftover-unsent\n'; sleep 0.1; done
EOF

# 按键驱动恢复：收到 2 个回车后由 residual 翻成 consumed
#   send_to_pane 初次 Enter → cr=1（仍 residual）；重试补发 Enter → cr=2（consumed）
cat > "$FIXDIR/recover.sh" <<'EOF'
#!/usr/bin/env bash
cr=0
draw() { if [ "$cr" -lt 2 ]; then printf '\033[2J\033[H❯ leftover-unsent\n'; else printf '\033[2J\033[H❯ \n'; fi; }
draw
# read -rsn1 读到回车(行分隔符)时返回空 c：空 c == 收到一次 Enter
while IFS= read -rsn1 c; do
  if [ -z "$c" ]; then cr=$((cr+1)); draw; fi
done
EOF

# C-u 驱动清行：初始脏(❯ dirty)，收到 C-u(0x15) 后清成 consumed(❯ )
cat > "$FIXDIR/cu.sh" <<'EOF'
#!/usr/bin/env bash
clean=0
draw() { if [ "$clean" -eq 0 ]; then printf '\033[2J\033[H❯ dirty-residual\n'; else printf '\033[2J\033[H❯ \n'; fi; }
draw
while IFS= read -rsn1 c; do
  case "$c" in
    $'\x15') clean=1; draw ;;
  esac
done
EOF
chmod +x "$FIXDIR"/*.sh

# run_test <launch-cmd> <name> <expected_rc> -- <robust args...>
run_test() {
  local launch="$1" name="$2" expected_rc="$3"; shift 3
  local rc=0 output
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  tmux new-session -d -s "$SESSION" -x 120 -y 20 "$launch" </dev/null >/dev/null 2>&1
  sleep 0.5
  output=$(bash "$ROBUST" "$@" 2>&1) || rc=$?
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  if [[ "$rc" -eq "$expected_rc" ]]; then
    echo "  ✅ $name (rc=$rc)"; PASS=$((PASS+1))
  else
    echo "  ❌ $name → expected rc=$expected_rc, got rc=$rc"
    printf '%s\n' "$output" | sed 's/^/      | /'; FAIL=$((FAIL+1))
  fi
}

echo "=== cc-send-robust TDD (轨1 P0-1) ==="
echo ""

# 1. 单行发送 → consumed → rc 0
run_test "bash $FIXDIR/consumed.sh" \
  "单行发送 → consumed → rc 0" 0 \
  send-to-pane "$SESSION" "hello world" 3

# 2. Enter 未生效 → 重试补 Enter → 恢复 → rc 0   [核心]
run_test "bash $FIXDIR/recover.sh" \
  "Enter 未生效 → 重试 → 成功 → rc 0" 0 \
  send-to-pane "$SESSION" "go" 3

# 3. 持续 residual → 耗尽重试 → rc 1（不静默假成功）
run_test "bash $FIXDIR/residual.sh" \
  "持续 residual → 耗尽重试 → rc 1" 1 \
  send-to-pane "$SESSION" "go" 2

# 4. 多行发送 → consumed → rc 0
run_test "bash $FIXDIR/consumed.sh" \
  "多行发送(load/paste-buffer) → rc 0" 0 \
  send-multiline "$SESSION" $'line1\nline2\nline3'

# 5. C-u 清行 → 由脏变净 → rc 0
run_test "bash $FIXDIR/cu.sh" \
  "C-u 清行 → 由脏变净 → rc 0" 0 \
  send-clear-then "$SESSION" "after-clear"

# 6. 不存在的 target → 非 0（无需起 session）
rc=0; bash "$ROBUST" send-to-pane "nonexistent-session-99999" "x" 1 >/dev/null 2>&1 || rc=$?
if [[ "$rc" -ne 0 ]]; then
  echo "  ✅ 不存在 target → 非0 (rc=$rc)"; PASS=$((PASS+1))
else
  echo "  ❌ 不存在 target 应返回非0，got rc=0"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
