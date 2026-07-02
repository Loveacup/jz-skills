#!/usr/bin/env bash
# cc-send.sh — Send context + task to a running CC tmux session
# §3.2: + post-send verification with auto-retry, --dry-run, --expect
#
# Usage:
#   cc-send.sh --session <name> --context <file> [--message <text>]
#              [--dry-run] [--expect <glob>]
#
# Verification contract (§3.2 / Pitfall #5):
#   After send-keys, capture the bottom of the pane and classify:
#     · queue banner ("Press up to edit queued") → Escape + re-send payload (retry)
#     · ❯ with residual text                     → Enter did not register   (retry)
#     · empty ❯  OR  no ❯ at all (CC already busy)→ consumed                 (SUCCESS)
#   Only a POSITIVELY stuck state (queue / residual) is retried, max 4 times.
#   On exhaustion the script EXITS NON-ZERO (rc 2) so a human is alerted —
#   it must never silently fake success ("不静默假成功", per plan §3.2 / L1 table).

set -euo pipefail

SESSION="" CONTEXT="" MESSAGE="" DRYRUN=0 EXPECT_GLOB="" NO_PREFIX=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --context) CONTEXT="$2"; shift 2 ;;
    --message) MESSAGE="$2"; shift 2 ;;
    --dry-run) DRYRUN=1; shift ;;
    --expect)  EXPECT_GLOB="$2"; shift 2 ;;
    --no-prefix) NO_PREFIX=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$SESSION" ]]; then
  echo "Usage: cc-send.sh --session <name> [--context <file> | --message <text>] [--dry-run] [--expect <glob>] [--no-prefix]" >&2
  exit 1
fi

# Verify session exists
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "❌ Session '$SESSION' not found" >&2
  exit 1
fi

# ── §3.2 / D-4: write expected-artifacts file if --expect provided ──
if [[ -n "$EXPECT_GLOB" ]]; then
  printf '%s' "$EXPECT_GLOB" > "/tmp/cc-expect-${SESSION}"
fi

# ── Source cc-send-robust.sh for send_to_pane (P0-1: 根治 #5/#18 — 内化完整 send→classify→repair→retry 管道) ──
SKILL_DIR="${CC_TMUX_SKILL_ROOT:-$(cd "$(dirname "$0")" && pwd)}"
# shellcheck source=./cc-send-robust.sh
. "$SKILL_DIR/cc-send-robust.sh" 2>/dev/null || {
  echo "❌ cc-send: failed to source cc-send-robust.sh from $SKILL_DIR" >&2
  exit 1
}

# ── Build the message to send ──
if [[ -n "$CONTEXT" ]]; then
  if [[ "$CONTEXT" == *$'\n'* ]]; then
    echo "❌ cc-send: --context must be a single file path, not multiline content" >&2
    exit 1
  fi
  if [[ ! -f "$CONTEXT" ]]; then
    echo "❌ cc-send: context file not found: $CONTEXT" >&2
    exit 1
  fi
  if [[ ! -s "$CONTEXT" ]]; then
    echo "❌ cc-send: context file is empty: $CONTEXT" >&2
    exit 1
  fi
  if [[ "$NO_PREFIX" -eq 1 ]]; then
    # Back-compat flag: no longer injects file body. Keep accepted so old callers
    # do not break, but preserve the path-only safety contract.
    MSG="$CONTEXT"
  else
    # Path-only contract: never inject markdown body into the pane.
    # v1.41: append orchestration hint so CC knows it may use native agent teams/workflows
    # when the context references a complex skill.
    ORCHESTRATION_HINT="If this context references a skill with its own multi-agent, agent-team, workflow, or multi-stage process, load and follow that complete skill process yourself. Do not wait for Hermes to split it into workers; Hermes is the messenger, CC is the factory."
    MSG="Please read $CONTEXT and follow it. $ORCHESTRATION_HINT"
  fi
elif [[ -n "$MESSAGE" ]]; then
  if [[ "$MESSAGE" == *$'\n'* ]]; then
    echo "❌ cc-send: multiline --message is not allowed; write content to /tmp/*.md and send the file path with --context" >&2
    exit 1
  fi
  MSG="$MESSAGE"
else
  echo "⚠️  No context file or message provided." >&2
  exit 1
fi

# ── §3.2: send via send_to_pane (cc-send-robust.sh) — single call replaces send_payload + verify_delivered ──
# P0-1 (Pitfall #5/#18): send_to_pane uses -l (literal) to prevent #/! interpretation,
# has proper timing separation (literal sleep → Enter → verify), and built-in
# classify→repair→retry loop (max 3 retries by default, robust handles both
# queue-banner/Escape and residual-text/Enter stuck states).
#
# Exit codes from send_to_pane: 0=ok, 1=retry exhausted, 3=tmux error
if [[ "$DRYRUN" -eq 1 ]]; then
  echo "[dry-run] would send: $MSG"
  echo "[dry-run] via send_to_pane() with classify→repair→retry pipeline"
  exit 0
fi

send_to_pane "$SESSION" "$MSG" 4    # max 4 retries (was 3 default; bump for safety)
rc=$?

if [[ "$rc" -eq 0 ]]; then
  echo "✓ Sent to $SESSION (via send_to_pane)"
  exit 0
fi

echo "⚠️  send_to_pane 失败 (rc=$rc) — 人工 capture-pane 介入" >&2
exit 2
