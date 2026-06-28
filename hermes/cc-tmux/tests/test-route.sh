#!/usr/bin/env bash
# test-route.sh — TDD for cc-route.sh (消息路由层：Hermes↔CC 中断转发)
#
# HERMETIC: no real tmux, no real CC. Inject CC_ROUTE_TMPDIR to point all signal
# files at a throwaway sandbox. cc-route.sh reads only from that sandbox.
#
# Machine assertion lines on stderr: ROUTEMETA … / ROUTEITEM …
#
# Covers: 10 routing scenarios across CC states × user intents

set -euo pipefail

ROUTE="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-route.sh"
PASS=0 FAIL=0
D=""

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

new_sandbox() {
  D=$(mktemp -d "/tmp/cc-route-test.XXXXXX")
}
cleanup() { [[ -n "$D" && -d "$D" ]] && rm -rf "$D"; return 0; }
trap cleanup EXIT

# ── Fixture helpers ──
write_status() { # <session> <state> <age_s_ago> [last_tool]
  local s="$1" st="$2" age="$3" tool="${4:-}" now ts since seq heartbeat
  now=$(date +%s)
  ts=$(date -u -v "-${age}S" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "${age} seconds ago" +%Y-%m-%dT%H:%M:%SZ)
  since="$ts"
  heartbeat=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  seq=$(( RANDOM % 100 + 1 ))
  cat > "$D/cc-status-$s.json" <<JSON
{"state":"$st","state_since":"$since","last_event":"UserPromptSubmit","last_tool":"$tool","last_tool_since":"$since","seq":$seq,"heartbeat":"$heartbeat"}
JSON
}

write_heartbeat() { # <session> <age_s_ago>
  local s="$1" age="$2"
  echo "$(date +%s)|1|ACTIVE_HOOK|?|0|1|?" > "$D/cc-heartbeat-$s"
  touch -t "$(date -v "-${age}S" +%Y%m%d%H%M 2>/dev/null || date -d "${age} seconds ago" +%Y%m%d%H%M)" "$D/cc-heartbeat-$s" 2>/dev/null || true
}

write_freeze() { # <session>
  echo '{"ts":"2026-01-01T00:00:00Z","event":"freeze","state":"THINKING","freeze_s":200}' > "$D/cc-freeze-$1"
}

write_turn_done() { # <session>
  echo '{"status":"completed","task":"test"}' > "$D/cc-turn-done-$1"
}

# ── Run cc-route with sandbox wired in ──
run_route() {
  CC_ROUTE_TMPDIR="$D" bash "$ROUTE" "$@" 2>/dev/null
}

# ── Assertion helpers ──
assert_action() { # <json_output> <expected_action>
  local out="$1" expected="$2"
  local actual
  actual=$(echo "$out" | jq -r '.recommendation.action // "?"' 2>/dev/null || echo "?")
  [[ "$actual" == "$expected" ]]
}

assert_risk() { # <json_output> <expected_risk>
  local out="$1" expected="$2"
  local actual
  actual=$(echo "$out" | jq -r '.recommendation.risk // "?"' 2>/dev/null || echo "?")
  [[ "$actual" == "$expected" ]]
}

echo "=== cc-route TDD: 消息路由层 ==="
echo ""

# ═══════════════════════════════════════════════════════════════
# TC1: CC IDLE + user new_task → handle_directly
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc1"; write_status "$S" "IDLE" 5; write_heartbeat "$S" 5
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC1 IDLE + new_task → handle_directly"
else no "TC1 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC2: CC TOOL + user continuation → forward_now
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc2"; write_status "$S" "TOOL" 3 "Bash"; write_heartbeat "$S" 3
out=$(run_route --session "$S" --intent continuation)
if assert_action "$out" "forward_now" && assert_risk "$out" "low"; then
  ok "TC2 TOOL + continuation → forward_now"
else no "TC2 预期 forward_now/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC3: CC THINKING + user new_task → queue
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc3"; write_status "$S" "THINKING" 10; write_heartbeat "$S" 10
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "queue" && assert_risk "$out" "low"; then
  ok "TC3 THINKING + new_task → queue (不打断思考)"
else no "TC3 预期 queue/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC4: CC THINKING + freeze + user redirect → interrupt
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc4"; write_status "$S" "THINKING" 200; write_heartbeat "$S" 200; write_freeze "$S"
out=$(run_route --session "$S" --intent redirect)
if assert_action "$out" "interrupt" && assert_risk "$out" "medium"; then
  ok "TC4 THINKING + freeze + redirect → interrupt"
else no "TC4 预期 interrupt/medium，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC5: CC COMPLETED + user anything → handle_directly
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc5"; write_status "$S" "COMPLETED" 30; write_heartbeat "$S" 30; write_turn_done "$S"
out=$(run_route --session "$S" --intent continuation)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC5 COMPLETED + continuation → handle_directly"
else no "TC5 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC6: CC BLOCKED + user redirect → forward_now (帮 CC 脱困)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc6"; write_status "$S" "BLOCKED" 15; write_heartbeat "$S" 15
out=$(run_route --session "$S" --intent redirect)
if assert_action "$out" "forward_now" && assert_risk "$out" "low"; then
  ok "TC6 BLOCKED + redirect → forward_now"
else no "TC6 预期 forward_now/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC7: No status file → fallback to heartbeat → infer ACTIVE
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc7"; write_heartbeat "$S" 5
out=$(run_route --session "$S" --intent status_query)
action=$(echo "$out" | jq -r '.recommendation.action' 2>/dev/null)
if [[ "$action" == "report_status" ]]; then
  ok "TC7 无 status 文件 + 有心跳 → report_status"
else no "TC7 预期 report_status，实际 action=$action"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC8: No files at all → no CC session → handle_directly
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc8"
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC8 无任何文件 → handle_directly (CC 不在)"
else no "TC8 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC9: CC WAITING_AGENTS + user continuation → queue
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc9"; write_status "$S" "WAITING_AGENTS" 8; write_heartbeat "$S" 8
out=$(run_route --session "$S" --intent continuation)
if assert_action "$out" "queue" && assert_risk "$out" "low"; then
  ok "TC9 WAITING_AGENTS + continuation → queue"
else no "TC9 预期 queue/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC10: CC GONE + user redirect → handle_directly (CC 已死)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc10"; write_status "$S" "GONE" 60; write_heartbeat "$S" 60
out=$(run_route --session "$S" --intent redirect)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC10 GONE + redirect → handle_directly"
else no "TC10 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC11: CC TOOL + user new_task → queue (不打断工具调用)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc11"; write_status "$S" "TOOL" 2 "Write"; write_heartbeat "$S" 2
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "queue" && assert_risk "$out" "low"; then
  ok "TC11 TOOL + new_task → queue"
else no "TC11 预期 queue/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC12: CC SHELL + user anything → handle_directly (疑似崩溃)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc12"; write_status "$S" "ERROR" 5; write_heartbeat "$S" 5
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC12 ERROR + new_task → handle_directly"
else no "TC12 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC13: stale status (age>120s) + heartbeat fresh → use heartbeat
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc13"; write_status "$S" "TOOL" 0; write_heartbeat "$S" 5
# Make status file OLD (180s ago) so heartbeat fallback kicks in
touch -t "$(date -v-180S +%Y%m%d%H%M 2>/dev/null || date -d '180 seconds ago' +%Y%m%d%H%M)" "$D/cc-status-$S.json" 2>/dev/null || true
out=$(run_route --session "$S" --intent status_query)
source=$(echo "$out" | jq -r '.cc_state_source' 2>/dev/null)
if [[ "$source" == "heartbeat" ]]; then
  ok "TC13 status 陈旧 + heartbeat 新鲜 → source=heartbeat"
else no "TC13 预期 source=heartbeat，实际 $source"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC14: CC SHELL + new_task → handle_directly (P0-A: 崩溃等价 ERROR)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc14"; write_status "$S" "SHELL" 5; write_heartbeat "$S" 5
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "handle_directly" && assert_risk "$out" "low"; then
  ok "TC14 SHELL + new_task → handle_directly (崩溃 CC 不排队)"
else no "TC14 预期 handle_directly/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC15: CC THINKING (fresh, no freeze) + redirect → queue (不打断正常思考)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc15"; write_status "$S" "THINKING" 10; write_heartbeat "$S" 10
# 无 freeze 文件
out=$(run_route --session "$S" --intent redirect)
if assert_action "$out" "queue" && assert_risk "$out" "low"; then
  ok "TC15 THINKING (no freeze) + redirect → queue"
else no "TC15 预期 queue/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC16: unknown intent + CC IDLE → report_status
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc16"; write_status "$S" "IDLE" 5
out=$(run_route --session "$S" --intent unknown)
if assert_action "$out" "report_status"; then
  ok "TC16 unknown intent + IDLE → report_status (先汇报等指令)"
else no "TC16 预期 report_status，实际 $(echo "$out" | jq -r '.recommendation.action' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC17: CC COMPACTING + new_task → queue (context 压缩中，排队)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc17"; write_status "$S" "COMPACTING" 5; write_heartbeat "$S" 5
out=$(run_route --session "$S" --intent new_task)
if assert_action "$out" "queue" && assert_risk "$out" "low"; then
  ok "TC17 COMPACTING + new_task → queue"
else no "TC17 预期 queue/low，实际 $(echo "$out" | jq -c '.recommendation' 2>/dev/null)"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC18: jq 不可用 (CC_ROUTE_JQ=/nonexistent) → error JSON + handle_directly
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc18"; write_status "$S" "TOOL" 5
out=$(CC_ROUTE_JQ="/nonexistent_jq_stub_$$" CC_ROUTE_TMPDIR="$D" bash "$ROUTE" --session "$S" --intent redirect 2>/dev/null)
err_field=$(echo "$out" | jq -r '.error // ""' 2>/dev/null || echo "")
action_field=$(echo "$out" | jq -r '.recommendation.action // ""' 2>/dev/null || echo "")
if [[ "$err_field" == "jq_unavailable" && "$action_field" == "handle_directly" ]]; then
  ok "TC18 jq 不可用 → error=jq_unavailable + action=handle_directly"
else no "TC18 预期 error=jq_unavailable+handle_directly，实际 err=$err_field action=$action_field out=$out"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC19: THINKING + turn_done=true → queue (保守) + turn_done 字段正确
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc19"; write_status "$S" "THINKING" 5; write_heartbeat "$S" 5; write_turn_done "$S"
out=$(run_route --session "$S" --intent continuation)
td=$(echo "$out" | jq -r '.turn_done' 2>/dev/null)
action=$(echo "$out" | jq -r '.recommendation.action' 2>/dev/null)
if [[ "$td" == "true" && "$action" == "queue" ]]; then
  ok "TC19 THINKING + turn_done → queue + turn_done=true 正确暴露"
else no "TC19 预期 queue + turn_done=true，实际 action=$action td=$td"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC20: interrupt 场景 → confirm_required=true (P1-B)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc20"; write_status "$S" "THINKING" 200; write_heartbeat "$S" 200; write_freeze "$S"
out=$(run_route --session "$S" --intent redirect)
cr=$(echo "$out" | jq -r '.recommendation.confirm_required // "missing"' 2>/dev/null)
if assert_action "$out" "interrupt" && [[ "$cr" == "true" ]]; then
  ok "TC20 interrupt → confirm_required=true"
else no "TC20 预期 interrupt + confirm_required=true，实际 action=$(echo "$out" | jq -r '.recommendation.action' 2>/dev/null) cr=$cr"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
# TC21: hook_status 来源 → status_age_s 为非负整数 (P1-A)
# ═══════════════════════════════════════════════════════════════
new_sandbox
S="hermes-cc-route-tc21"; write_status "$S" "IDLE" 0
out=$(run_route --session "$S" --intent status_query)
sa=$(echo "$out" | jq -r '.status_age_s // "missing"' 2>/dev/null)
if [[ "$sa" =~ ^[0-9]+$ ]]; then
  ok "TC21 hook_status → status_age_s 有值且为整数（${sa}s）"
else no "TC21 预期 status_age_s 为整数，实际 $sa"; fi
cleanup

# ═══════════════════════════════════════════════════════════════
echo ""
echo "=== 结果: $PASS 通过 / $FAIL 失败 ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
