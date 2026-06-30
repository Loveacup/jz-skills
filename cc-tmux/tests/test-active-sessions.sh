#!/usr/bin/env bash
# test-active-sessions.sh — TDD for cc-active-sessions.sh
#
# HERMETIC: CC_ACTIVE_TMPDIR + CC_ACTIVE_TMUX stub injection.
# Covers: empty / single / multi / --topic filter / --json / state resolution

set -euo pipefail

ACTIVE="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-active-sessions.sh"
PASS=0 FAIL=0
D=""

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

new_sandbox() {
  D=$(mktemp -d "/tmp/cc-active-test.XXXXXX")
  # tmux stub that reads sessions.txt
  cat > "$D/stub-tmux.sh" <<'STUB'
#!/usr/bin/env bash
D="$CC_ACTIVE_STUB_DIR"
case "${1:-}" in
  list-sessions) cat "$D/sessions.txt" 2>/dev/null ;;
  *) exit 0 ;;
esac
STUB
  chmod +x "$D/stub-tmux.sh"
}
cleanup() { [[ -n "$D" && -d "$D" ]] && rm -rf "$D"; return 0; }
trap cleanup EXIT

# helpers
add_session() { echo "$1" >> "$D/sessions.txt"; }
write_status() { # <session> <state> [last_tool]
  local s="$1" st="$2" tool="${3:-}"
  cat > "$D/cc-status-$s.json" <<JSON
{"state":"$st","state_since":"2026-01-01T00:00:00Z","last_event":"PostToolUse","last_tool":"$tool","last_tool_since":"2026-01-01T00:00:00Z","seq":5,"heartbeat":"2026-01-01T00:00:00Z"}
JSON
}
write_heartbeat() { : > "$D/cc-heartbeat-$1"; }
write_freeze()    { : > "$D/cc-freeze-$1"; }
write_turndone()  { : > "$D/cc-turn-done-$1"; }

run_active() {
  CC_ACTIVE_TMPDIR="$D" CC_ACTIVE_TMUX="bash $D/stub-tmux.sh" CC_ACTIVE_STUB_DIR="$D" \
    bash "$ACTIVE" "$@"
}

echo "=== cc-active-sessions TDD ==="
echo ""

# TC1: 无 session → 空输出
new_sandbox
out=$(run_active 2>/dev/null)
if echo "$out" | grep -q "📭"; then
  ok "TC1 无 session → 空输出"
else no "TC1 预期空输出，实际: $out"; fi
cleanup

# TC2: 单 session + 状态
new_sandbox
S="hermes-cc-default-test-0101-0000"
add_session "$S"; write_status "$S" "TOOL" "Bash"; write_heartbeat "$S"
out=$(run_active 2>/dev/null)
if echo "$out" | grep -q "TOOL" && echo "$out" | grep -q "$S"; then
  ok "TC2 单 session → 含状态+session名"
else no "TC2 未找到状态/session: $out"; fi
cleanup

# TC3: --json 输出合法 JSON 数组
new_sandbox
S="hermes-cc-default-test-0101-0000"
add_session "$S"; write_status "$S" "IDLE"; write_heartbeat "$S"
out=$(run_active --json 2>/dev/null)
if echo "$out" | python3 -c "import sys,json; json.loads(sys.stdin.read())" 2>/dev/null; then
  ok "TC3 --json 输出合法 JSON 数组"
else no "TC3 JSON 非法: ${out:0:80}..."; fi
cleanup

# TC4: --json 多 session
new_sandbox
S1="hermes-cc-default-a-0101-0000"; S2="hermes-cc-default-b-0101-0000"
add_session "$S1"; write_status "$S1" "TOOL" "Bash"; write_heartbeat "$S1"
add_session "$S2"; write_status "$S2" "THINKING"; write_heartbeat "$S2"
out=$(run_active --json 2>/dev/null)
count=$(echo "$out" | jq 'length')
if [[ "$count" -eq 2 ]]; then
  ok "TC4 --json 多 session → 2 条"
else no "TC4 预期 2 条，实际 $count"; fi
cleanup

# TC5: --topic 过滤
new_sandbox
S="hermes-cc-default-jz-skills-0101-0000"
add_session "$S"; write_status "$S" "TOOL"; write_heartbeat "$S"
# topic map
echo '{"jz-skills":"hermes-cc-default-jz-skills-0101-0000"}' > "$D/cc-topic-map.json"
out=$(run_active --topic jz-skills 2>/dev/null)
if echo "$out" | grep -q "$S"; then
  ok "TC5 --topic jz-skills → 匹配成功"
else no "TC5 topic 未匹配: $out"; fi
cleanup

# TC6: --topic 无匹配
new_sandbox
S="hermes-cc-default-other-0101-0000"
add_session "$S"; write_status "$S" "IDLE"; write_heartbeat "$S"
echo '{"jz-skills":"hermes-cc-default-jz-skills-0101-0000"}' > "$D/cc-topic-map.json"
out=$(run_active --topic nonexistent 2>/dev/null)
if echo "$out" | grep -q "📭"; then
  ok "TC6 --topic nonexistent → 空输出"
else no "TC6 预期空，实际: $out"; fi
cleanup

# TC7: freeze 标记可见
new_sandbox
S="hermes-cc-default-test-0101-0000"
add_session "$S"; write_status "$S" "THINKING"; write_heartbeat "$S"; write_freeze "$S"
out=$(run_active 2>/dev/null)
if echo "$out" | grep -q "冻结"; then
  ok "TC7 freeze → 包含冻结标记"
else no "TC7 无冻结标记: $out"; fi
cleanup

# TC8: turn_done 标记可见
new_sandbox
S="hermes-cc-default-test-0101-0000"
add_session "$S"; write_status "$S" "COMPLETED"; write_heartbeat "$S"; write_turndone "$S"
out=$(run_active 2>/dev/null)
if echo "$out" | grep -q "完成"; then
  ok "TC8 turn_done → 包含完成标记"
else no "TC8 无完成标记: $out"; fi
cleanup

# TC9: 非 CC session 被过滤（不以 hermes-cc- 开头）
new_sandbox
add_session "hermes-claude-longterm"
add_session "random-tmux-session"
S="hermes-cc-default-test-0101-0000"
add_session "$S"; write_status "$S" "IDLE"; write_heartbeat "$S"
out=$(run_active --json 2>/dev/null)
count=$(echo "$out" | jq 'length')
if [[ "$count" -eq 1 ]]; then
  ok "TC9 非 CC session 被过滤 → 仅 1 条"
else no "TC9 预期 1 条，实际 $count"; fi
cleanup

# TC10: 无 status 文件 → state=unknown 不崩溃
new_sandbox
S="hermes-cc-default-test-0101-0000"
add_session "$S"
out=$(run_active --json 2>/dev/null)
state=$(echo "$out" | jq -r '.[0].state')
if [[ "$state" == "unknown" ]]; then
  ok "TC10 无 status 文件 → state=unknown"
else no "TC10 预期 unknown，实际 $state"; fi
cleanup

echo ""
echo "=== 结果: $PASS 通过 / $FAIL 失败 ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
