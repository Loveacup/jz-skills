#!/usr/bin/env bash
# srof-run.sh — the actuator-runner
# Executes one step's `run:` and writes the captured result to $SROF_RUN_RESULT
# so gate-verify can read it (the §6.8 contract). It is an ACTUATOR (it mutates the world).
# Used by BOTH interactive and headless paths — closes the P0-1 asymmetry.
# Usage:  SROF_RUN_RESULT=<path> [SROF_INPUT_FILE=<path>] srof-run.sh <step-id> -c '<run-script>'
#    or:  ... srof-run.sh <step-id>   <<<'<run-script>'
# Location: $SROF_LIB/srof-run.sh (central shared library)
# Matrix-independent: zero tmux/iii/Hermes coupling.
set -uo pipefail                       # NOT -e: we WANT to capture a non-zero exit, not die on it
STEP="${1:?step id}"; shift
if [ "${1:-}" = "-c" ]; then SCRIPT="${2:?run script}"; else SCRIPT="$(cat)"; fi

: "${SROF_RUN_RESULT:?set SROF_RUN_RESULT}"
RUNDIR="$(dirname "$SROF_RUN_RESULT")"; mkdir -p "$RUNDIR"
OUT="$RUNDIR/$STEP.out"; ERR="$RUNDIR/$STEP.err"

# Execute. $SROF_INPUT_FILE (if any) is already a PATH in the env; the secret value is never
# passed as an argument or interpolated (§3.7). stdout/stderr are captured to files — actuators
# for secret steps MUST NOT echo the secret, or it would land in $STEP.out.
bash -c "$SCRIPT" >"$OUT" 2>"$ERR"
rc=$?

# Atomic write (.tmp + mv, P2-2).
tmp="$SROF_RUN_RESULT.tmp.$$"
jq -n --argjson ec "$rc" --arg op "$OUT" --arg ep "$ERR" --arg st "$STEP" \
  '{exit_code:$ec, stdout_path:$op, stderr_path:$ep, step:$st}' > "$tmp"
mv -f "$tmp" "$SROF_RUN_RESULT"
exit "$rc"
