#!/usr/bin/env bash
# test-hook-check.sh — cc-hook-check.sh hook 冒烟自检的 TDD
# 注入 CC_HOOK_CHECK_TMUX(stub 列 session + capture-pane) + CC_HOOK_CHECK_TMPDIR(fixture 产物)
# 做 hermetic 测试：零真实 CC session、零 tmux、零网络。

set -uo pipefail

HC="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-hook-check.sh"
TD="/tmp/cc-hctest-$$"
PASS=0 FAIL=0
ok(){  echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
cleanup(){ rm -rf "$TD"; }
trap cleanup EXIT
cleanup; mkdir -p "$TD"

echo "=== cc-hook-check TDD: 被动检视 hook 产物 ==="
echo ""

# tmux stub：list-sessions 输出由 $TD/sessions 控制；capture-pane 对 healthy 给注入痕迹
cat > "$TD/tmux.sh" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "list-sessions" ]]; then cat "$TD/sessions" 2>/dev/null || true; exit 0; fi
if [[ "\$1" == "capture-pane" ]]; then
  case "\$*" in
    *hermes-cc-healthy*) echo '[cc-tmux] 你是被 cc-tmux 驱动的 CC ...' ;;
    *) echo 'unrelated pane' ;;
  esac
  exit 0
fi
exit 0
EOF
chmod +x "$TD/tmux.sh"
RUN(){ CC_HOOK_CHECK_TMUX="bash $TD/tmux.sh" CC_HOOK_CHECK_TMPDIR="$TD" bash "$HC" "$@"; }

mk_healthy(){
  printf '{"state":"TOOL","seq":7,"heartbeat":"x"}' > "$TD/cc-status-$1.json"
  touch "$TD/cc-heartbeat-$1"
  printf '{"event":"received"}\n' > "$TD/cc-state-$1.log"
}

# Test 1: 无活跃 session → "(no active CC sessions)" 且 exit 0
: > "$TD/sessions"
out=$(RUN 2>/dev/null); rc=$?
if [[ "$rc" -eq 0 ]] && printf '%s' "$out" | grep -q 'no active CC sessions'; then
  ok "无活跃 session → (no active CC sessions) exit 0"
else
  bad "no-session 处理错误 rc=$rc"
fi

# Test 2: 脚本自身不依赖活 CC session（上一条已证 exit 0，不崩）
[[ "$rc" -eq 0 ]] && ok "脚本不依赖活 session（无 session 不崩）" || bad "无 session 时崩了 rc=$rc"

# Test 3: 单 healthy session → exit 0
printf 'hermes-cc-healthy\n' > "$TD/sessions"
mk_healthy hermes-cc-healthy
RUN >/dev/null 2>&1; rc=$?
[[ "$rc" -eq 0 ]] && ok "healthy session → exit 0" || bad "healthy 误判 rc=$rc"

# Test 4: 非 hermes-cc-* session 被过滤（只剩 other → 视为无活跃 CC）
printf 'other-session\nsome-shell\n' > "$TD/sessions"
out=$(RUN 2>/dev/null); rc=$?
if [[ "$rc" -eq 0 ]] && printf '%s' "$out" | grep -q 'no active CC sessions'; then
  ok "非 hermes-cc-* session 被过滤"
else
  bad "session 前缀过滤失效 rc=$rc"
fi

# Test 5: 缺 cc-status-<s>.json → degraded exit 1
printf 'hermes-cc-broken\n' > "$TD/sessions"
touch "$TD/cc-heartbeat-hermes-cc-broken"   # 有心跳但无 status
RUN >/dev/null 2>&1; rc=$?
[[ "$rc" -eq 1 ]] && ok "缺 status.json → degraded exit 1" || bad "缺 status 应 1，得 rc=$rc"

# Test 6: 缺 heartbeat → degraded exit 1
rm -f "$TD/cc-heartbeat-hermes-cc-broken"
printf '{"state":"IDLE","seq":2}' > "$TD/cc-status-hermes-cc-broken.json"
RUN >/dev/null 2>&1; rc=$?
[[ "$rc" -eq 1 ]] && ok "缺 heartbeat → degraded exit 1" || bad "缺 heartbeat 应 1，得 rc=$rc"

# Test 7: status.json seq=0（无效）→ degraded
touch "$TD/cc-heartbeat-hermes-cc-broken"
printf '{"state":"IDLE","seq":0}' > "$TD/cc-status-hermes-cc-broken.json"
RUN >/dev/null 2>&1; rc=$?
[[ "$rc" -eq 1 ]] && ok "status seq=0（无效）→ degraded exit 1" || bad "无效 status 应 1，得 rc=$rc"

# Test 8: 一 healthy + 一 broken → 报告区分、exit 1
printf 'hermes-cc-healthy\nhermes-cc-broken\n' > "$TD/sessions"
mk_healthy hermes-cc-healthy
printf '{"state":"IDLE","seq":0}' > "$TD/cc-status-hermes-cc-broken.json"
out=$(RUN 2>/dev/null); rc=$?
if [[ "$rc" -eq 1 ]] \
  && printf '%s' "$out" | grep -q '✅ hermes-cc-healthy' \
  && printf '%s' "$out" | grep -q '❌ hermes-cc-broken'; then
  ok "混合健康度 → 报告区分 + exit 1"
else
  bad "混合场景报告/退出码错误 rc=$rc"
fi

# Test 9: 机器断言行 HOOKCHECK 走 stderr
err=$(RUN 2>&1 >/dev/null)
printf '%s' "$err" | grep -q 'HOOKCHECK total=2' && ok "HOOKCHECK 断言行走 stderr" || bad "缺 HOOKCHECK stderr 断言行"

# Test 10: --help 不崩、含用法
bash "$HC" --help 2>&1 | grep -q 'cc-hook-check' && ok "--help 输出用法" || bad "--help 异常"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
