#!/usr/bin/env bash
# test-hooks.sh — TDD for the cc-tmux driven-CC hooks (§3.3/§3.4/§3.5/§3.7)
#
# Hooks are command-type. They receive the hook JSON on stdin and learn their
# session_id from it (CLAUDE_SESSION_ID is EMPTY in the hook env — Pitfall #15).
#
# D-4 key unification (2026-06-17): the canonical per-session key is
#   ${CC_TMUX_SESSION:-<stdin .session_id>}
# cc-start.sh injects CC_TMUX_SESSION=<tmux session name> when launching claude,
# so hook-written state aligns with the tmux-name-keyed files the OUTSIDE scripts
# (cc-monitor / cc-send / cc-finish) use. When CC_TMUX_SESSION is absent (a CC not
# launched by cc-tmux) the key safely degrades to the CC UUID.
#
# Each hook is therefore tested by feeding stdin JSON with a session_id AND
# exercising the CC_TMUX_SESSION precedence path (which is what production uses).

set -uo pipefail

HOOKS="$(cd "$(dirname "$0")/../hooks" && pwd)"
TPL="$(cd "$(dirname "$0")/../templates" && pwd)/settings.runtime.json"   # §Phase-1: the --settings-injected runtime template (single source); inline cmds unchanged from the old template
GATE="$(cd "$(dirname "$0")/../scripts/gate" && pwd)"
TMPD="/tmp/cc-hooks-test-$$"
SESS="hooktest-$$"               # stands in for the tmux session name (CC_TMUX_SESSION)
UUID="uuid-$$-deadbeef"          # stands in for the CC-internal session_id
PASS=0 FAIL=0

cleanup() {
  rm -rf "$TMPD" \
         "/tmp/cc-counter-stop-precheck-${SESS}.json" \
         "/tmp/cc-counter-stop-precheck-${UUID}.json" \
         "/tmp/cc-counter-stop-precheck-unknown.json" \
         "/tmp/cc-expect-${SESS}" "/tmp/cc-expect-${UUID}" \
         "/tmp/cc-state-${SESS}.log" "/tmp/cc-state-${UUID}.log" \
         "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-heartbeat-${UUID}" \
         "/tmp/cc-turn-done-${SESS}" "/tmp/cc-turn-done-${UUID}"
}
trap cleanup EXIT
cleanup; mkdir -p "$TMPD"

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# JSON helpers (always carry session_id so hooks can resolve the UUID-fallback key)
j_file() { printf '{"session_id":"%s","tool_input":{"file_path":"%s"}}' "$UUID" "$1"; }
j_resp() { printf '{"session_id":"%s","tool_response":"%s"}' "$UUID" "$1"; }
j_bare() { printf '{"session_id":"%s"}' "$UUID"; }

echo "=== cc-tmux hooks TDD (§3.3/§3.4/§3.5/§3.7) — D-4 key-unified ==="
echo ""

# ─────────────────────────────────────────────────────────────
# §3.3  cc-posttool.sh — Write|Edit archival, keyed by CC_TMUX_SESSION
# ─────────────────────────────────────────────────────────────
echo "§3.3 cc-posttool.sh"

# Test 1: big file (>8192) → archived under CC_TMUX_SESSION key
BIG="$TMPD/big.txt"; head -c 9000 /dev/zero | tr '\0' 'x' > "$BIG"
out=$(j_file "$BIG" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/out" bash "$HOOKS/cc-posttool.sh"; echo "rc=$?")
if [[ "$out" == *"rc=0"* ]] && ls "$TMPD/out/$SESS/"big.txt.* >/dev/null 2>&1; then
  ok "big file archived under tmux-session key (rc 0)"
else
  bad "big file not archived: $out / $(ls -R "$TMPD/out" 2>&1)"
fi

# Test 2: small file → NOT archived, rc 0
SMALL="$TMPD/small.txt"; echo "tiny" > "$SMALL"
j_file "$SMALL" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/out2" bash "$HOOKS/cc-posttool.sh"; rc=$?
if [[ "$rc" -eq 0 ]] && ! ls "$TMPD/out2/$SESS/"small.txt.* >/dev/null 2>&1; then
  ok "small file not archived (rc 0)"
else
  bad "small file unexpectedly archived (rc=$rc)"
fi

# Test 3: missing file → no-op, rc 0
j_file "$TMPD/does-not-exist" | CC_TMUX_SESSION="$SESS" bash "$HOOKS/cc-posttool.sh"; rc=$?
[[ "$rc" -eq 0 ]] && ok "missing file → rc 0 no-op" || bad "missing file rc=$rc"

# Test 4: empty file_path (MultiEdit edits[] shape) → no-op, rc 0
printf '{"session_id":"%s","tool_input":{"edits":[{"old":"a","new":"b"}]}}' "$UUID" \
  | CC_TMUX_SESSION="$SESS" bash "$HOOKS/cc-posttool.sh"; rc=$?
[[ "$rc" -eq 0 ]] && ok "no file_path → rc 0 no-op" || bad "no file_path rc=$rc"

# Test 5: big .md still archived (formatting excluded, archival is not)
BIGMD="$TMPD/doc.md"; head -c 9000 /dev/zero | tr '\0' 'x' > "$BIGMD"
j_file "$BIGMD" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/out3" bash "$HOOKS/cc-posttool.sh" >/dev/null 2>&1
if ls "$TMPD/out3/$SESS/"doc.md.* >/dev/null 2>&1; then ok "big .md archived (format-excluded, archive applies)"; else bad "big .md not archived"; fi

# Test 6: D-4 precedence — CC_TMUX_SESSION wins over stdin session_id (UUID)
j_file "$BIG" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/out6" bash "$HOOKS/cc-posttool.sh" >/dev/null 2>&1
if ls "$TMPD/out6/$SESS/"big.txt.* >/dev/null 2>&1 && ! ls "$TMPD/out6/$UUID/" >/dev/null 2>&1; then
  ok "CC_TMUX_SESSION key wins over stdin UUID (D-4)"
else
  bad "D-4 precedence wrong: $(ls -R "$TMPD/out6" 2>&1)"
fi

# Test 7: UUID fallback — no CC_TMUX_SESSION → archives under stdin session_id
j_file "$BIG" | env -u CC_TMUX_SESSION CC_OUTPUT_ROOT="$TMPD/out7" bash "$HOOKS/cc-posttool.sh" >/dev/null 2>&1
if ls "$TMPD/out7/$UUID/"big.txt.* >/dev/null 2>&1; then
  ok "UUID fallback when CC_TMUX_SESSION unset (safe degrade)"
else
  bad "UUID fallback wrong: $(ls -R "$TMPD/out7" 2>&1)"
fi

echo ""
echo "§3.3 Bash big-tool_response inline command (from templates/settings.runtime.json)"
BASH_CMD=$(jq -r '.hooks.PostToolUse[0].hooks[0].command' "$TPL")
# Test 8: big tool_response (>4096) → appended to responses log under tmux key
RESP=$(head -c 5000 /dev/zero | tr '\0' 'y')
j_resp "$RESP" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/bashout" bash -c "$BASH_CMD"
if ls "$TMPD/bashout/$SESS/"responses-*.log >/dev/null 2>&1; then ok "big tool_response archived (tmux key)"; else bad "big tool_response not archived"; fi

# Test 9: small tool_response (<4096) → NOT archived
j_resp "short" | CC_TMUX_SESSION="$SESS" CC_OUTPUT_ROOT="$TMPD/bashout2" bash -c "$BASH_CMD"
ls "$TMPD/bashout2/$SESS/"responses-*.log >/dev/null 2>&1 \
  && bad "small tool_response wrongly archived" || ok "small tool_response not archived"

echo ""
echo "§3.4 Notification inline command (from templates/) — writes the SHARED bus"
NOTIF_CMD=$(jq -r '.hooks.Notification[0].hooks[0].command' "$TPL")
# Test 10: appends single-line JSONL to the tmux-keyed state log + touches heartbeat
j_bare | CC_TMUX_SESSION="$SESS" bash -c "$NOTIF_CMD"
lines=$(wc -l < "/tmp/cc-state-${SESS}.log" 2>/dev/null | tr -d ' ' || echo 0)
if [[ -f "/tmp/cc-heartbeat-${SESS}" && "$lines" -eq 1 ]] && grep -q '"event":"notification"' "/tmp/cc-state-${SESS}.log"; then
  ok "notification → 1-line JSONL on tmux-keyed bus + heartbeat (§3.4 bus unified)"
else
  bad "notification side effects wrong (lines=$lines, log=/tmp/cc-state-${SESS}.log)"
fi
# Test 11: JSONL line stays < 4KB (PIPE_BUF atomicity)
linelen=$(tail -1 "/tmp/cc-state-${SESS}.log" | wc -c | tr -d ' ')
[[ "$linelen" -lt 4096 ]] && ok "notification line <4KB ($linelen)" || bad "notification line too long ($linelen)"

echo ""
echo "§3.5 SessionStart inline command (from templates/) — reads the SHARED bus"
SS_CMD=$(jq -r '.hooks.SessionStart[0].hooks[0].command' "$TPL")
# Test 12: injects banner + the tmux-keyed recent-state tail (proves bus is shared
# with cc-monitor, which writes /tmp/cc-state-<tmux-name>.log).
echo '{"ts":"2026-06-17T00:00:00Z","state":"THINKING","marker":"MONITOR_WROTE_THIS"}' > "/tmp/cc-state-${SESS}.log"
out=$(j_bare | CC_TMUX_SESSION="$SESS" bash -c "$SS_CMD")
if printf '%s' "$out" | grep -q 'cc-tmux 驱动' \
   && printf '%s' "$out" | grep -q "$SESS" \
   && printf '%s' "$out" | grep -q 'MONITOR_WROTE_THIS'; then
  ok "SessionStart injects banner + reads tmux-keyed recent state (§3.5 not empty)"
else
  bad "SessionStart injection wrong: $out"
fi

echo ""
echo "§3.7 cc-stop-check.sh — early-warning soft gate (now wired end-to-end)"
EXPECT="/tmp/cc-expect-${SESS}"
# run_stop feeds stdin JSON (session_id) AND sets CC_TMUX_SESSION so the gate-counter
# key is deterministic (stop-precheck-$SESS), mirroring production where cc-send wrote
# /tmp/cc-expect-<tmux-name> and the Stop hook resolves the SAME tmux key.
run_stop() { j_bare | CC_TMUX_SESSION="$SESS" CC_TMUX_GATE_DIR="$GATE" \
             CC_STOP_SEARCH_ROOT="$TMPD/artifacts" \
             bash "$HOOKS/cc-stop-check.sh"; }

# Test 13: no expect file → exit 0, no block
rm -f "$EXPECT"; out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "no expect file → silent exit 0" || bad "no-expect: rc=$rc out=$out"

# Test 14: D-4 wired — expect file keyed by tmux name (what cc-send --expect writes),
# artifact present → exit 0, no block. Proves the Stop hook reads the SAME key.
mkdir -p "$TMPD/artifacts"; echo "done" > "$TMPD/artifacts/result-final.md"
echo 'result-*.md' > "$EXPECT"
out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "expect(tmux-key) + artifact present → no block (D-4 wired)" || bad "present: rc=$rc out=$out"

# Test 15: artifact missing → bounded rewake. gate-counter --limit 2: call#1 blocks,
# call#2 capped (exit 20 → silent), call#3 silent. Safety property: bounded, never wedges.
rm -f "$TMPD/artifacts/result-final.md"
rm -f "/tmp/cc-counter-stop-precheck-${SESS}.json"
o1=$(run_stop); o2=$(run_stop); o3=$(run_stop)
if printf '%s' "$o1" | grep -q '"decision":"block"' && [[ -z "$o2" && -z "$o3" ]]; then
  ok "missing artifact → block then capped silent (bounded rewake, no wedge)"
else
  bad "rewake cap wrong: o1=[$o1] o2=[$o2] o3=[$o3]"
fi

# Test 16: empty pattern in expect file → no block (conservative)
: > "$EXPECT"; out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "empty pattern → no block" || bad "empty pattern: rc=$rc out=$out"

# ═════════════════════════════════════════════════════════════
# §Phase-2 event-driven monitoring: hooks own the freshness bus
# ═════════════════════════════════════════════════════════════
echo ""
echo "§Phase2 PreToolUse inline — high-freq heartbeat touch (async, no log bloat)"
PRE_CMD=$(jq -r '.hooks.PreToolUse[0].hooks[0].command' "$TPL")
# Test 17: PreToolUse touches the heartbeat (freshness beat) under the D-4 key
rm -f "/tmp/cc-heartbeat-${SESS}"
j_bare | CC_TMUX_SESSION="$SESS" bash -c "$PRE_CMD"
[[ -f "/tmp/cc-heartbeat-${SESS}" ]] && ok "PreToolUse touches heartbeat (tmux key)" || bad "PreToolUse did not touch heartbeat"

echo ""
echo "§Phase2 UserPromptSubmit inline — new turn: touch hb + log + clear stale turn-done"
UPS_CMD=$(jq -r '.hooks.UserPromptSubmit[0].hooks[0].command' "$TPL")
# Test 18: hb touched, state logged, AND a stale turn-done marker is cleared (new turn)
rm -f "/tmp/cc-heartbeat-${SESS}" "/tmp/cc-state-${SESS}.log"
echo "stale" > "/tmp/cc-turn-done-${SESS}"
j_bare | CC_TMUX_SESSION="$SESS" bash -c "$UPS_CMD"
if [[ -f "/tmp/cc-heartbeat-${SESS}" ]] \
   && grep -qiE 'received|prompt' "/tmp/cc-state-${SESS}.log" 2>/dev/null \
   && [[ ! -f "/tmp/cc-turn-done-${SESS}" ]]; then
  ok "UserPromptSubmit: hb touched + state logged + stale turn-done cleared"
else
  bad "UserPromptSubmit side effects wrong (hb=$([ -f "/tmp/cc-heartbeat-${SESS}" ] && echo y || echo n) turndone=$([ -f "/tmp/cc-turn-done-${SESS}" ] && echo present || echo gone))"
fi

echo ""
echo "§Phase2 SessionEnd inline — lifecycle GONE marker on the state bus"
SE_CMD=$(jq -r '.hooks.SessionEnd[0].hooks[0].command' "$TPL")
# Test 19: SessionEnd appends a GONE entry (lets cc-finish distinguish exit vs crash)
rm -f "/tmp/cc-state-${SESS}.log"
printf '{"session_id":"%s","reason":"prompt_input_exit"}' "$UUID" | CC_TMUX_SESSION="$SESS" bash -c "$SE_CMD"
grep -qiE 'gone|sessionend|"event":"end"' "/tmp/cc-state-${SESS}.log" 2>/dev/null \
  && ok "SessionEnd logs GONE to state bus" || bad "SessionEnd did not log GONE: $(cat "/tmp/cc-state-${SESS}.log" 2>/dev/null)"

echo ""
echo "§Phase2 Stop — writes cc-turn-done marker on NON-block paths only"
# Test 20: no expect file → turn ends normally → marker written (Hermes's 'go look' signal)
rm -f "$EXPECT" "/tmp/cc-turn-done-${SESS}"
run_stop >/dev/null 2>&1
[[ -f "/tmp/cc-turn-done-${SESS}" ]] && ok "Stop (no expect) writes turn-done marker" || bad "Stop did not write turn-done"

# Test 21: blocking path (artifact missing, not capped) → marker NOT written (turn not done)
rm -f "$TMPD/artifacts/result-final.md" "/tmp/cc-turn-done-${SESS}" "/tmp/cc-counter-stop-precheck-${SESS}.json"
mkdir -p "$TMPD/artifacts"; echo 'result-*.md' > "$EXPECT"
out=$(run_stop)   # call#1 → blocks
if printf '%s' "$out" | grep -q '"decision":"block"' && [[ ! -f "/tmp/cc-turn-done-${SESS}" ]]; then
  ok "Stop (blocking) does NOT write turn-done (turn not done)"
else
  bad "Stop turn-done/block logic wrong: out=[$out] marker=$([ -f "/tmp/cc-turn-done-${SESS}" ] && echo present || echo gone)"
fi

echo ""
echo "§P1-1 cc-status-writer — 状态权威：7 事件全接线 + 端到端写 cc-status-<key>.json"
# Test 22: every fired event wires cc-status-writer.sh, AND it writes the authoritative
# status file (state from the event arg). Proves the L2 layer became the state authority.
WIRED=$(grep -c 'cc-status-writer.sh' "$TPL")
SW="$HOOKS/cc-status-writer.sh"
SWTMP="$TMPD/status"; mkdir -p "$SWTMP"
printf '%s' '{"session_id":"'"$UUID"'","tool_name":"Write"}' | CC_TMUX_SESSION="$SESS" CC_STATUS_TMPDIR="$SWTMP" bash "$SW" PreToolUse >/dev/null 2>&1
SWSTATE=$(jq -r '.state' "$SWTMP/cc-status-${SESS}.json" 2>/dev/null || echo "")
if [[ "$WIRED" -ge 7 ]] && [[ "$SWSTATE" == "TOOL" ]]; then
  ok "cc-status-writer 接线 ${WIRED} 处(≥7 事件) + 端到端写 state=TOOL"
else
  bad "status-writer wiring/write 失败 (wired=$WIRED state=$SWSTATE)"
fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
