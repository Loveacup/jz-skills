# Agent-hub real bounded smoke pattern

Use this when validating a Hermes/iii/cc-tmux runtime orchestrator path with a real bridge and possible real CC session.

## Pattern

1. Fake-first proof remains mandatory before real smoke:
   - run manifest creation
   - fake `cc::bridge_status`
   - fake `cc::execute`
   - fake watcher JSONL
   - collector convergence
   - approved intervention archive through fake `cc::intervene`
2. Real bounded smoke should be one tiny read-only task:
   - read a small known file
   - write a short report under `/tmp`
   - no repo writes, no git, no destructive action
3. Start by checking:
   - repo clean
   - bridge port not already listening
   - no leftover `cc-host-bridge.mjs` / `cc-watch-session.mjs`
   - relevant CC sessions state
4. Start real bridge and provision token, then run the orchestrator with tight bounds:
   - low `watch-max-ticks`
   - short interval
   - explicit stale threshold
5. Treat active-session gates as a safety pass-through, not a failure:
   - `lifecycle_state: active_sessions_require_ack`
   - or `status: refused, error: active_sessions_require_ack`
   should become `blocked` / human-gate state, not `failed`.
6. Do **not** add `--ack-active` automatically. Only rerun with ack after explicit user authorization to parallelize with active CC sessions.
7. If blocked by the active-session gate, stop the real smoke, kill the bridge you started, verify no watcher/session/report side effects, and record Partial/blocked evidence.
8. If real CC starts, collect evidence after bounded watcher ticks. Run approved intervention only if a suggestion exists **and** the user explicitly confirms.
9. Always clean up bridge/watchers and verify repo diff before reporting pass/partial/fail.

## Durable lesson from 2026-06-26

A real smoke of agent-hub Phase 5 hit `cc::execute` returning `status=refused,error=active_sessions_require_ack` because another CC session was TOOL. The orchestrator originally collapsed this into `failed`; the correct semantics are `blocked` with exit 3 and no watcher. Regression tests should cover both the lifecycle_state and refused/error response variants.