#!/usr/bin/env bash
# cc-stop-check.sh — Stop hook early-warning SOFT gate (§3.7)
#
# Before a turn ends, deterministically check that the expected artifact (the
# glob cc-send.sh recorded in /tmp/cc-expect-<session> via --expect) exists and
# is non-empty. If missing, emit a Stop `block` to push CC back to finish it —
# bounded by a DETERMINISTIC rewake cap (gate-counter, independent key) so an
# over-blocking Stop hook can never wedge the turn.
#
# NOT authoritative: cc-finish.sh remains the independent witness that always
# runs. A passing Stop check ≠ completion ("被审计者不能是自己的终审").
#
# Stop semantics: there is NO `approve`. Artifacts present → exit 0 silently.
# Always exit 0 even when emitting block JSON (the JSON, not the rc, blocks).
set -uo pipefail

S="${CLAUDE_SESSION_ID:-unknown}"
EXPECT="${CC_EXPECT_FILE:-/tmp/cc-expect-${S}}"
GATE_DIR="${CC_TMUX_GATE_DIR:-/Users/$(id -un)/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/gate}"
SEARCH_ROOT="${CC_STOP_SEARCH_ROOT:-/tmp}"

# No declared expectation → never block (conservative).
[ -f "$EXPECT" ] || exit 0
PATTERN=$(cat "$EXPECT" 2>/dev/null)
[ -z "$PATTERN" ] && exit 0

# Artifact present and non-empty → normal end of turn (no block).
HIT=$(find -L "$SEARCH_ROOT" -maxdepth 3 -name "$PATTERN" -type f -size +0c 2>/dev/null | head -1)
[ -n "$HIT" ] && exit 0

# Missing: deterministic rewake cap via INDEPENDENT key so we do not consume the
# human-review reject budget (/tmp/cc-counter-<sid>.json). exit 20 = cap reached.
if ! bash "$GATE_DIR/gate-counter.sh" --key "stop-precheck-$S" --kind reject --inc --limit 2 >/dev/null 2>&1; then
  exit 0   # already blocked twice → let the turn end; cc-finish is the backstop.
fi

# Emit Stop block (non-deny path: blocks turn-end + feeds reason back to CC).
printf '{"decision":"block","reason":"期望产物 %s 缺失或为空,请在结束前生成它(写到 /tmp/cc-output/%s/)"}\n' \
  "$PATTERN" "$S"
exit 0
