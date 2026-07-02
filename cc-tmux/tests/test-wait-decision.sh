#!/usr/bin/env bash
# test-wait-decision.sh — TDD for cc-wait-decision.sh
# Covers: wait-marker passthrough, exit-4 evidence classification, artifacts, freeze, timeout.

set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../scripts" && pwd)/cc-wait-decision.sh"
TMPROOT=$(mktemp -d /tmp/cc-wait-decision-test.XXXXXX)
SESSION="cc-wait-decision-test"
PASS=0 FAIL=0

cleanup() { rm -rf "$TMPROOT"; }
trap cleanup EXIT

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
bad() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

make_wait_stub() {
  local rc="$1" out="${2:-}" err="${3:-}"
  local p="$TMPROOT/wait-$rc.sh"
  cat > "$p" <<EOF
#!/usr/bin/env bash
printf '%s' '$out'
printf '%s' '$err' >&2
exit $rc
EOF
  chmod +x "$p"
  echo "$p"
}

make_monitor_stub() {
  local rc="${1:-0}"
  local p="$TMPROOT/monitor-$rc.sh"
  cat > "$p" <<'EOF'
#!/usr/bin/env bash
echo '===📡 BEGIN (relay verbatim)==='
echo 'stub monitor'
echo '===📡 END==='
if [[ -n "${CC_DECISION_MONITOR_STATE:-}" ]]; then
  echo "META session=cc-wait-decision-test state=${CC_DECISION_MONITOR_STATE} changed=false" >&2
else
  echo 'META session=cc-wait-decision-test changed=false' >&2
fi
exit 0
EOF
  chmod +x "$p"
  echo "$p"
}

make_tmux_stub() {
  local mode="$1"
  local p="$TMPROOT/tmux-$mode.sh"
  cat > "$p" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "capture-pane" ]]; then
  case "${CC_DECISION_PANE_MODE:-idle}" in
    tool) printf '● Running tool\nesc to interrupt\n' ;;
    thinking) printf '✻ Thinking 3s\nesc to interrupt\n' ;;
    queue) printf 'Press up to edit queued messages\n❯ 按 /tmp/task.md 执行\n' ;;
    residual) printf '────────────────\n❯ 按 /tmp/task.md 执行\n' ;;
    path_anchor) printf '────────────────\n❯ Please read /tmp/cc-friction-task.md\nand follow it. If this context references a skill\n' ;;
    prediction) printf '────────────────\n❯ read the task file\n' ;;
    stale_text) printf '────────────────\n❯ some old echo text\n' ;;
    idle) printf '────────────────\n❯ \n' ;;
    oldtool_idle) printf '● Old tool output\n────────────────\n❯ \n' ;;
    empty) printf '' ;;
  esac
  exit 0
fi
exit 0
EOF
  chmod +x "$p"
  echo "$p"
}

write_status() {
  local state="$1"
  printf '{"state":"%s"}\n' "$state" > "$TMPROOT/cc-status-$SESSION.json"
}

run_decision() {
  local wait="$1" pane="$2" expect_rc="$3" name="$4" state_expect="$5"
  shift 5
  local out rc mon tmux_stub
  mon=$(make_monitor_stub 0)
  tmux_stub=$(make_tmux_stub "$pane")
  set +e
  out=$(CC_WAIT_DECISION_WAIT_MARKER="$wait" \
        CC_WAIT_DECISION_MONITOR="$mon" \
        CC_WAIT_DECISION_TMUX="$tmux_stub" \
        CC_WAIT_DECISION_TMPDIR="$TMPROOT" \
        CC_WAIT_DECISION_NOW=2000 \
        CC_DECISION_PANE_MODE="$pane" \
        CC_DECISION_MONITOR_STATE="${MONITOR_STATE:-}" \
        bash "$SCRIPT" --session "$SESSION" --after 1000 --timeout 1 "$@" 2>"$TMPROOT/err")
  rc=$?
  set -e
  if [[ "$rc" -ne "$expect_rc" ]]; then
    bad "$name rc=$rc expected=$expect_rc out=${out:0:120} err=$(cat "$TMPROOT/err")"
    return
  fi
  if ! printf '%s' "$out" | python3 -m json.tool >/dev/null 2>&1; then
    bad "$name output is not JSON: ${out:0:120}"
    return
  fi
  got=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["decision"]["state"])')
  if [[ "$got" != "$state_expect" ]]; then
    bad "$name state=$got expected=$state_expect"
    return
  fi
  ok "$name"
}

# 加强版 run_decision：同时校验 prompt.kind
run_decision_pk() {
  local wait="$1" pane="$2" expect_rc="$3" name="$4" state_expect="$5" prompt_kind_expect="$6"
  shift 6
  local out rc mon tmux_stub
  mon=$(make_monitor_stub 0)
  tmux_stub=$(make_tmux_stub "$pane")
  set +e
  MONITOR_STATE=IDLE out=$(CC_WAIT_DECISION_WAIT_MARKER="$wait" \
        CC_WAIT_DECISION_MONITOR="$mon" \
        CC_WAIT_DECISION_TMUX="$tmux_stub" \
        CC_WAIT_DECISION_TMPDIR="$TMPROOT" \
        CC_WAIT_DECISION_NOW=2000 \
        CC_DECISION_PANE_MODE="$pane" \
        CC_DECISION_MONITOR_STATE="IDLE" \
        bash "$SCRIPT" --session "$SESSION" --after 1000 --timeout 1 "$@" 2>"$TMPROOT/err")
  rc=$?
  set -e
  if [[ "$rc" -ne "$expect_rc" ]]; then
    bad "$name rc=$rc expected=$expect_rc out=${out:0:120} err=$(cat "$TMPROOT/err")"
    return
  fi
  got_state=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["decision"]["state"])')
  if [[ "$got_state" != "$state_expect" ]]; then
    bad "$name state=$got_state expected=$state_expect"
    return
  fi
  got_kind=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("pane",{}).get("prompt",{}).get("kind",""))')
  if [[ "$got_kind" != "$prompt_kind_expect" ]]; then
    bad "$name prompt_kind=$got_kind expected=$prompt_kind_expect"
    return
  fi
  ok "$name"
}

echo "=== cc-wait-decision TDD ==="

# Test 1: rc0 marker passthrough
run_decision "$(make_wait_stub 0 'DONE')" idle 0 "rc0 marker → marker_done" marker_done

# Test 2: rc4 + fresh monitor TOOL => active_no_resend exit5
MONITOR_STATE=TOOL run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 5 "rc4 + monitor TOOL → active_no_resend" active_no_resend

# Test 3: rc4 + fresh monitor THINKING => active_no_resend exit5
MONITOR_STATE=THINKING run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 5 "rc4 + monitor THINKING → active_no_resend" active_no_resend

# Test 4: rc4 + active pane signal => active_no_resend exit5
run_decision "$(make_wait_stub 4 '' 'startup gate')" tool 5 "rc4 + pane tool signal → active_no_resend" active_no_resend

# Test 5: rc4 + queue banner => not_started_retryable exit4
run_decision "$(make_wait_stub 4 '' 'startup gate')" queue 4 "rc4 + queue → not_started_retryable" not_started_retryable

# Test 6: rc4 + residual with matching --sent-line => not_started_retryable exit4
run_decision "$(make_wait_stub 4 '' 'startup gate')" residual 4 "rc4 + residual + sent-line match → not_started_retryable" not_started_retryable --sent-line "按 /tmp/task.md 执行"

# Test 6a: rc4 + wrapped/path-anchor residual with orchestration-hint sent line
# classifies as fresh_sent_line and safe to submit/resend, despite pane wrapping.
run_decision_pk "$(make_wait_stub 4 '' 'startup gate')" path_anchor 4 "rc4 + path-anchor orchestration hint → fresh_sent_line" not_started_retryable fresh_sent_line --sent-line "Please read /tmp/cc-friction-task.md and follow it. If this context references a skill with its own multi-agent, agent-team, workflow, or multi-stage process, load and follow that complete skill process yourself. Do not wait for Hermes to split it into workers; Hermes is the messenger, CC is the factory."

# Test 6b: rc4 + residual without --sent-line => prompt_text_needs_clear exit6
run_decision "$(make_wait_stub 4 '' 'startup gate')" residual 6 "rc4 + residual no sent-line → prompt_text_needs_clear" prompt_text_needs_clear

# Test 7: rc4 + clean IDLE => not_started_retryable exit4
run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 4 "rc4 + clean IDLE → not_started_retryable" not_started_retryable

# Test 8: rc4 + expected artifact newer => artifact_satisfied_no_marker exit0
art="$TMPROOT/report.md"; echo ok > "$art"
touch -t "$(date -v-1S +%Y%m%d%H%M.%S 2>/dev/null || date -d '1 seconds ago' +%Y%m%d%H%M.%S)" "$art" 2>/dev/null || true
run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 0 "rc4 + artifact newer → artifact_satisfied" artifact_satisfied_no_marker --expect "$art"

# Test 9: rc1 timeout + fresh monitor ACTIVE => active_no_resend exit5
MONITOR_STATE=ACTIVE run_decision "$(make_wait_stub 1 '' 'timeout')" idle 5 "rc1 + active status → active_no_resend" active_no_resend

# Test 10: rc1 timeout + no evidence => wait_timeout_unresolved exit1
run_decision "$(make_wait_stub 1 '' 'timeout')" idle 1 "rc1 + no active evidence → wait_timeout_unresolved" wait_timeout_unresolved

# Test 11: GONE/SHELL/ERROR => session_dead exit3
MONITOR_STATE=GONE run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 3 "rc4 + GONE → session_dead" session_dead

# Test 12: freeze marker => frozen_needs_confirm exit6
touch "$TMPROOT/cc-freeze-$SESSION"
run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 6 "rc4 + freeze → frozen_needs_confirm" frozen_needs_confirm
rm -f "$TMPROOT/cc-freeze-$SESSION"

# Test 13: stale/contradicting cc-status must not override fresh monitor IDLE
write_status TOOL
MONITOR_STATE=IDLE run_decision "$(make_wait_stub 4 '' 'startup gate')" idle 4 "fresh monitor IDLE beats stale TOOL status" not_started_retryable
rm -f "$TMPROOT/cc-status-$SESSION.json"

# Test 14: old tool scrollback + bottom idle prompt must not count as active pane
MONITOR_STATE=IDLE run_decision "$(make_wait_stub 4 '' 'startup gate')" oldtool_idle 4 "old tool scrollback + idle prompt → not_started" not_started_retryable

# Test 16: rc4 + prediction text (matches heuristic: /command or English verb) → prompt_text_needs_clear rc=6
run_decision_pk "$(make_wait_stub 4 '' 'startup gate')" prediction 6 "rc4 + prediction text → prompt_text_needs_clear" prompt_text_needs_clear prediction_candidate

# Test 17: rc4 + stale/unknown text (no match) → prompt_text_needs_clear rc=6
run_decision_pk "$(make_wait_stub 4 '' 'startup gate')" stale_text 6 "rc4 + stale unknown text → prompt_text_needs_clear" prompt_text_needs_clear stale_or_unknown

# Test 15: invalid args => usage_error exit2 (script-level)
set +e
out=$(bash "$SCRIPT" --after nope 2>/dev/null); rc=$?
set -e
if [[ "$rc" -eq 2 ]]; then ok "invalid args → exit2"; else bad "invalid args rc=$rc"; fi

echo ""
echo "=== Results: $PASS/$((PASS+FAIL)) passed ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
