#!/usr/bin/env bash
# test-hooks.sh — TDD for the cc-tmux driven-CC hooks (§3.3/§3.4/§3.5/§3.7)
#
# Hooks are command-type, so each is tested by feeding the hook JSON on stdin
# (or setting the env it reads) and asserting side effects / stdout / exit code.

set -uo pipefail

HOOKS="$(cd "$(dirname "$0")/../hooks" && pwd)"
GATE="$(cd "$(dirname "$0")/../scripts/gate" && pwd)"
TMPD="/tmp/cc-hooks-test-$$"
SESS="hooktest-$$"
PASS=0 FAIL=0

cleanup() {
  rm -rf "$TMPD" "/tmp/cc-counter-stop-precheck-${SESS}.json" \
         "/tmp/cc-expect-${SESS}" "/tmp/cc-state-${SESS}.log" "/tmp/cc-heartbeat-${SESS}"
}
trap cleanup EXIT
cleanup; mkdir -p "$TMPD"

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "=== cc-tmux hooks TDD (§3.3/§3.4/§3.5/§3.7) ==="
echo ""

# ─────────────────────────────────────────────────────────────
# §3.3  cc-posttool.sh — Write|Edit archival
# ─────────────────────────────────────────────────────────────
echo "§3.3 cc-posttool.sh"

# Test 1: big file (>8192) → archived under CC_OUTPUT_ROOT/<sess>/
BIG="$TMPD/big.txt"; head -c 9000 /dev/zero | tr '\0' 'x' > "$BIG"
out=$(printf '{"tool_input":{"file_path":"%s"}}' "$BIG" \
      | CLAUDE_SESSION_ID="$SESS" CC_OUTPUT_ROOT="$TMPD/out" bash "$HOOKS/cc-posttool.sh"; echo "rc=$?")
if [[ "$out" == *"rc=0"* ]] && ls "$TMPD/out/$SESS/"big.txt.* >/dev/null 2>&1; then
  ok "big file archived (rc 0)"
else
  bad "big file not archived: $out / $(ls -R "$TMPD/out" 2>&1)"
fi

# Test 2: small file → NOT archived, rc 0
SMALL="$TMPD/small.txt"; echo "tiny" > "$SMALL"
printf '{"tool_input":{"file_path":"%s"}}' "$SMALL" \
  | CLAUDE_SESSION_ID="$SESS" CC_OUTPUT_ROOT="$TMPD/out2" bash "$HOOKS/cc-posttool.sh"; rc=$?
if [[ "$rc" -eq 0 ]] && ! ls "$TMPD/out2/$SESS/"small.txt.* >/dev/null 2>&1; then
  ok "small file not archived (rc 0)"
else
  bad "small file unexpectedly archived (rc=$rc)"
fi

# Test 3: missing file → no-op, rc 0
printf '{"tool_input":{"file_path":"%s"}}' "$TMPD/does-not-exist" \
  | CLAUDE_SESSION_ID="$SESS" bash "$HOOKS/cc-posttool.sh"; rc=$?
[[ "$rc" -eq 0 ]] && ok "missing file → rc 0 no-op" || bad "missing file rc=$rc"

# Test 4: empty file_path (MultiEdit edits[] shape) → no-op, rc 0
printf '{"tool_input":{"edits":[{"old":"a","new":"b"}]}}' \
  | CLAUDE_SESSION_ID="$SESS" bash "$HOOKS/cc-posttool.sh"; rc=$?
[[ "$rc" -eq 0 ]] && ok "no file_path → rc 0 no-op" || bad "no file_path rc=$rc"

# Test 5: big .md still archived (formatting excluded, archival is not)
BIGMD="$TMPD/doc.md"; head -c 9000 /dev/zero | tr '\0' 'x' > "$BIGMD"
printf '{"tool_input":{"file_path":"%s"}}' "$BIGMD" \
  | CLAUDE_SESSION_ID="$SESS" CC_OUTPUT_ROOT="$TMPD/out3" bash "$HOOKS/cc-posttool.sh" >/dev/null 2>&1
if ls "$TMPD/out3/$SESS/"doc.md.* >/dev/null 2>&1; then ok "big .md archived (format-excluded, archive applies)"; else bad "big .md not archived"; fi

echo ""
echo "§3.3 Bash big-tool_response inline command (extracted from settings.template.json)"
TPL="$HOOKS/settings.template.json"
BASH_CMD=$(jq -r '.hooks.PostToolUse[0].hooks[0].command' "$TPL")
# Test 6: big tool_response (>4096) → appended to responses log
RESP=$(head -c 5000 /dev/zero | tr '\0' 'y')
printf '{"tool_response":"%s"}' "$RESP" \
  | CLAUDE_SESSION_ID="$SESS" CC_OUTPUT_ROOT="$TMPD/bashout" bash -c "$BASH_CMD"
if ls "$TMPD/bashout/$SESS/"responses-*.log >/dev/null 2>&1; then ok "big tool_response archived"; else bad "big tool_response not archived"; fi

# Test 7: small tool_response (<4096) → NOT archived
printf '{"tool_response":"%s"}' "short" \
  | CLAUDE_SESSION_ID="$SESS" CC_OUTPUT_ROOT="$TMPD/bashout2" bash -c "$BASH_CMD"
ls "$TMPD/bashout2/$SESS/"responses-*.log >/dev/null 2>&1 \
  && bad "small tool_response wrongly archived" || ok "small tool_response not archived"

echo ""
echo "§3.4 Notification inline command (extracted from template)"
NOTIF_CMD=$(jq -r '.hooks.Notification[0].hooks[0].command' "$TPL")
# Test 8: appends single-line JSONL + touches heartbeat
CLAUDE_SESSION_ID="$SESS" bash -c "$NOTIF_CMD"
lines=$(wc -l < "/tmp/cc-state-${SESS}.log" | tr -d ' ')
if [[ -f "/tmp/cc-heartbeat-${SESS}" && "$lines" -eq 1 ]] && grep -q '"event":"notification"' "/tmp/cc-state-${SESS}.log"; then
  ok "notification → 1-line JSONL + heartbeat touched"
else
  bad "notification side effects wrong (lines=$lines)"
fi
# Test 9: JSONL line stays < 4KB (PIPE_BUF atomicity)
linelen=$(tail -1 "/tmp/cc-state-${SESS}.log" | wc -c | tr -d ' ')
[[ "$linelen" -lt 4096 ]] && ok "notification line <4KB ($linelen)" || bad "notification line too long ($linelen)"

echo ""
echo "§3.5 SessionStart inline command (extracted from template)"
SS_CMD=$(jq -r '.hooks.SessionStart[0].hooks[0].command' "$TPL")
# Test 10: injects cc-tmux context banner + recent state tail
out=$(CLAUDE_SESSION_ID="$SESS" bash -c "$SS_CMD")
if printf '%s' "$out" | grep -q 'cc-tmux 驱动' && printf '%s' "$out" | grep -q "$SESS"; then
  ok "SessionStart injects banner + session id"
else
  bad "SessionStart injection wrong: $out"
fi

echo ""
echo "§3.7 cc-stop-check.sh — early-warning soft gate"
EXPECT="/tmp/cc-expect-${SESS}"
run_stop() { CLAUDE_SESSION_ID="$SESS" CC_EXPECT_FILE="$EXPECT" \
             CC_TMUX_GATE_DIR="$GATE" CC_STOP_SEARCH_ROOT="$TMPD/artifacts" \
             bash "$HOOKS/cc-stop-check.sh"; }

# Test 11: no expect file → exit 0, no block
rm -f "$EXPECT"; out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "no expect file → silent exit 0" || bad "no-expect: rc=$rc out=$out"

# Test 12: artifact present → exit 0, no block
mkdir -p "$TMPD/artifacts"; echo "done" > "$TMPD/artifacts/result-final.md"
echo 'result-*.md' > "$EXPECT"
out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "artifact present → no block" || bad "present: rc=$rc out=$out"

# Test 13: artifact missing → bounded rewake (gate-counter --limit 2, reject default).
# gate-counter exits 20 when count>=limit AFTER inc, so with limit 2: call#1 (count 1)
# blocks, call#2 (count 2) is capped → 1 effective re-block then defer to cc-finish.
# (Plan prose says "block 2 次"; its code artifact is --limit 2, which yields this.
#  The safety property under test is: bounded, never blocks forever.)
rm -f "$TMPD/artifacts/result-final.md"
rm -f "/tmp/cc-counter-stop-precheck-${SESS}.json"
o1=$(run_stop); o2=$(run_stop); o3=$(run_stop)
if printf '%s' "$o1" | grep -q '"decision":"block"' \
   && [[ -z "$o2" && -z "$o3" ]]; then
  ok "missing artifact → block then capped silent (bounded rewake, no wedge)"
else
  bad "rewake cap wrong: o1=[$o1] o2=[$o2] o3=[$o3]"
fi

# Test 14: empty pattern in expect file → no block (conservative)
: > "$EXPECT"; out=$(run_stop); rc=$?
[[ "$rc" -eq 0 && -z "$out" ]] && ok "empty pattern → no block" || bad "empty pattern: rc=$rc out=$out"

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
