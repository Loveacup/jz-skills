# omp-ops Automation

This directory is the maintenance control plane for the `omp-ops` skill.

It documents Codex-side daily maintenance of the skill itself. It is separate
from:

- normal `omp-ops` user workflows
- OMP runtime/profile management
- Agent Skills hub governance patrols

## Documents

- `01-codex-daily-maintenance.md` - Codex daily maintenance contract,
  automation scope, helper-script roadmap, verification, and release rules.
- `02-cross-platform-script-audit.md` - audit of current helper scripts against
  macOS/Windows portability requirements.

## Non-Daily Setup

- `scripts/install-skill.sh` is an optional setup/linking helper. It is not part
  of the daily maintenance pipeline.

## Operating Rule

Automation may maintain files under `/Users/alexcai/code/jz-skills/omp/omp-ops/`
only. It must not read or write sensitive OMP runtime content such as databases,
sessions, logs, auth files, env files, real API keys, tokens, or passwords.



## Debug Instrumentation Rule

Temporary instrumentation (e.g. `console.error` trace lines added to
external plugin repos like `omp-supermemory/src/index.js`) is a manual /
runtime debugging activity. It is NOT within the maintenance scope of
omp-ops automation, and automation MUST NOT modify external repos under
this rule.

When such debugging occurs, apply these hygiene rules:

- Instrumentation MUST be reverted before the debugging session is
  considered closed. Stale trace lines produce noise for the user
  (e.g. red `[RECALL-TRACE]` output on every prompt).
- Restart OMP after reverting — the old module stays loaded in the
  running process and continues emitting noise.
- NEVER commit temporary instrumentation to any repo, and NEVER
  backfill runtime trace output, session logs, or live debug artifacts
  into the skill repository. This extends the Operating Rule above.