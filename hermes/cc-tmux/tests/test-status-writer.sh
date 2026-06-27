#!/usr/bin/env bash
# test-status-writer.sh — TDD test for hooks/cc-status-writer.sh (P1-1 Hook 成状态权威)
#
# cc-status-writer.sh <EVENT> reads a hook JSON on stdin and writes the authoritative
# /tmp/cc-status-<key>.json (event→state mapping) + refreshes the heartbeat (compat).
# HERMETIC: CC_STATUS_TMPDIR points all files at a throwaway dir; mock stdin JSON.
#   key = ${CC_TMUX_SESSION:-<stdin .session_id>}   (D-4)
#   schema: {state, state_since, last_event, last_tool, last_tool_since, seq, heartbeat}

set -euo pipefail

WRITER="$(cd "$(dirname "$0")/../hooks" && pwd)/cc-status-writer.sh"
PASS=0 FAIL=0
D=""

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

new_sandbox() { D=$(mktemp -d "/tmp/cc-sw-test.XXXXXX"); }
cleanup() { [[ -n "$D" && -d "$D" ]] && rm -rf "$D"; return 0; }
trap cleanup EXIT

# fire <EVENT> <stdin-json> [extra env assignments via CC_TMUX_SESSION already set by caller]
fire() { # uses $D as CC_STATUS_TMPDIR; KEY env via CC_TMUX_SESSION
  local ev="$1" json="$2"
  printf '%s' "$json" | CC_STATUS_TMPDIR="$D" bash "$WRITER" "$ev" >/dev/null 2>&1 || true
}
jqf() { jq -r "$2" "$D/cc-status-$1.json" 2>/dev/null; }   # jqf <key> <filter>

echo "=== cc-status-writer TDD: Hook 成状态权威 (P1-1) ==="
echo ""

# ── TC1: PreToolUse + tool=Write → state=TOOL, last_tool=Write, valid JSON ──
new_sandbox
CC_TMUX_SESSION="s1" fire PreToolUse '{"session_id":"uuid-x","tool_name":"Write"}'
if jq -e . "$D/cc-status-s1.json" >/dev/null 2>&1 \
   && [[ "$(jqf s1 .state)" == "TOOL" ]] && [[ "$(jqf s1 .last_tool)" == "Write" ]]; then
  ok "TC1 PreToolUse → state=TOOL · last_tool=Write · 合法 JSON"
else no "TC1 ($(cat "$D/cc-status-s1.json" 2>/dev/null | head -c 100))"; fi
cleanup

# ── TC2: Stop → COMPLETED ──
new_sandbox; CC_TMUX_SESSION="s1" fire Stop '{"session_id":"uuid-x"}'
[[ "$(jqf s1 .state)" == "COMPLETED" ]] && ok "TC2 Stop → COMPLETED" || no "TC2 got $(jqf s1 .state)"; cleanup

# ── TC3: Notification(idle) → IDLE ──
new_sandbox; CC_TMUX_SESSION="s1" fire Notification '{"session_id":"uuid-x","message":"idle"}'
[[ "$(jqf s1 .state)" == "IDLE" ]] && ok "TC3 Notification(idle) → IDLE" || no "TC3 got $(jqf s1 .state)"; cleanup

# ── TC4: Notification(permission) → BLOCKED ──
new_sandbox; CC_TMUX_SESSION="s1" fire Notification '{"session_id":"uuid-x","message":"permission required"}'
[[ "$(jqf s1 .state)" == "BLOCKED" ]] && ok "TC4 Notification(permission) → BLOCKED" || no "TC4 got $(jqf s1 .state)"; cleanup

# ── TC5: UserPromptSubmit → RECEIVED ──
new_sandbox; CC_TMUX_SESSION="s1" fire UserPromptSubmit '{"session_id":"uuid-x"}'
[[ "$(jqf s1 .state)" == "RECEIVED" ]] && ok "TC5 UserPromptSubmit → RECEIVED" || no "TC5 got $(jqf s1 .state)"; cleanup

# ── TC6: SessionEnd → GONE ──
new_sandbox; CC_TMUX_SESSION="s1" fire SessionEnd '{"session_id":"uuid-x","reason":"clear"}'
[[ "$(jqf s1 .state)" == "GONE" ]] && ok "TC6 SessionEnd → GONE" || no "TC6 got $(jqf s1 .state)"; cleanup

# ── TC7: SessionStart → ACTIVE ──
new_sandbox; CC_TMUX_SESSION="s1" fire SessionStart '{"session_id":"uuid-x"}'
[[ "$(jqf s1 .state)" == "ACTIVE" ]] && ok "TC7 SessionStart → ACTIVE" || no "TC7 got $(jqf s1 .state)"; cleanup

# ── TC7b: PreCompact → COMPACTING（压缩前，避免 watcher 误判 freeze）──
new_sandbox; CC_TMUX_SESSION="s1" fire PreCompact '{"session_id":"uuid-x"}'
[[ "$(jqf s1 .state)" == "COMPACTING" ]] && ok "TC7b PreCompact → COMPACTING" || no "TC7b got $(jqf s1 .state)"; cleanup

# ── TC7c: SessionStart(source=compact) → ACTIVE 且 last_event=SessionStart:compact ──
new_sandbox; CC_TMUX_SESSION="s1" fire SessionStart '{"session_id":"uuid-x","source":"compact"}'
if [[ "$(jqf s1 .state)" == "ACTIVE" ]] && [[ "$(jqf s1 .last_event)" == "SessionStart:compact" ]]; then
  ok "TC7c SessionStart(compact) → ACTIVE · last_event=SessionStart:compact"
else no "TC7c state=$(jqf s1 .state) last_event=$(jqf s1 .last_event)"; fi
cleanup

# ── TC8: state_since continuity + seq increment (same state) ──
new_sandbox
# pre-seed a TOOL status with an OLD state_since
printf '{"state":"TOOL","state_since":"2020-01-01T00:00:00Z","last_event":"PreToolUse","last_tool":"Write","last_tool_since":"2020-01-01T00:00:00Z","seq":5,"heartbeat":"2020-01-01T00:00:00Z"}\n' > "$D/cc-status-s1.json"
CC_TMUX_SESSION="s1" fire PreToolUse '{"session_id":"uuid-x","tool_name":"Write"}'
if [[ "$(jqf s1 .state_since)" == "2020-01-01T00:00:00Z" ]] && [[ "$(jqf s1 .seq)" == "6" ]]; then
  ok "TC8 同态续接：state 不变 → state_since 不变 · seq 5→6"
else no "TC8 since=$(jqf s1 .state_since) seq=$(jqf s1 .seq)"; fi
cleanup

# ── TC9: state change resets state_since ──
new_sandbox
printf '{"state":"TOOL","state_since":"2020-01-01T00:00:00Z","last_event":"PreToolUse","last_tool":"Write","last_tool_since":"2020-01-01T00:00:00Z","seq":5,"heartbeat":"2020-01-01T00:00:00Z"}\n' > "$D/cc-status-s1.json"
CC_TMUX_SESSION="s1" fire Stop '{"session_id":"uuid-x"}'
if [[ "$(jqf s1 .state)" == "COMPLETED" ]] && [[ "$(jqf s1 .state_since)" != "2020-01-01T00:00:00Z" ]]; then
  ok "TC9 状态切换 → state_since 重置（≠旧值）"
else no "TC9 state=$(jqf s1 .state) since=$(jqf s1 .state_since)"; fi
cleanup

# ── TC10: heartbeat compat file written ──
new_sandbox; CC_TMUX_SESSION="s1" fire PreToolUse '{"session_id":"uuid-x","tool_name":"Bash"}'
[[ -f "$D/cc-heartbeat-s1" ]] && ok "TC10 兼容：同时刷心跳文件" || no "TC10 心跳文件未写"; cleanup

# ── TC11: D-4 key — CC_TMUX_SESSION overrides stdin session_id ──
new_sandbox; CC_TMUX_SESSION="override-key" fire PreToolUse '{"session_id":"uuid-x","tool_name":"Read"}'
if [[ -f "$D/cc-status-override-key.json" ]] && [[ ! -f "$D/cc-status-uuid-x.json" ]]; then
  ok "TC11 D-4：CC_TMUX_SESSION 覆盖 stdin session_id"
else no "TC11 key 解析错"; fi
cleanup

# ── TC12: fallback — no CC_TMUX_SESSION → stdin session_id ──
new_sandbox
printf '%s' '{"session_id":"uuid-fallback","tool_name":"Read"}' | env -u CC_TMUX_SESSION CC_STATUS_TMPDIR="$D" bash "$WRITER" PreToolUse >/dev/null 2>&1 || true
[[ -f "$D/cc-status-uuid-fallback.json" ]] && ok "TC12 兜底：无 CC_TMUX_SESSION → 用 stdin session_id" || no "TC12 兜底失败"; cleanup

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
