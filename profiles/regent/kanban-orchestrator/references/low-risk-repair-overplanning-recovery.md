# Low-risk repair over-planning recovery

## Trigger

Use this when a governed Regent/Kanban chain for a low-risk local repair gets stuck in repeated planner/reviewer loops. Typical examples: rebuilding a local qmd index, refreshing a local cache, running deterministic CLI repair commands, or restoring local tool configuration where no secrets/core/shared resources are modified.

Signals:

- 门下 blocks a plan twice on command-flag or CLI syntax minutiae.
- A planner revision hits iteration budget exhaustion before producing new substantive value.
- The execution card is stuck in `todo` only because it is parented to a blocked review card.
- The remaining risk can be controlled by 工部 live verification (`--help`, version checks, read-back) plus 御史 downstream audit.

## Recovery pattern

1. **Inspect real parents before editing links**
   ```bash
   hermes -p regent kanban show <execution_task> --json
   ```
   Read `parents`. Do not rely on memory of the previous chain; coordinator may have rewired the child to a newer blocked review.

2. **Comment the governance decision on the execution card**
   State that the planning loop is now over-processing and the task is narrowed to deterministic local repair. Include explicit boundaries:
   - verify CLI flags with `--help` before use
   - no Hermes core changes
   - no secrets/shared-resource changes
   - BM25/search success may be accepted before vector/embed if model download is slow or not required
   - downstream auditor still verifies

3. **Unlink superseded blocked parents**
   ```bash
   hermes -p regent kanban unlink <blocked_parent> <execution_task>
   ```
   Re-run `show --json` until the execution card has no blocked parent (or only a done/approved parent).

4. **Archive superseded plan/review cards as audit trail**
   Add a comment first, then archive. Do not delete.

5. **Dispatch 工部**
   ```bash
   hermes -p regent kanban dispatch
   ```
   Confirm the execution card becomes `running` and downstream audit/final-review remain queued.

## Why this is allowed

This is not bypassing 三省六部. It is a governance downgrade from repeated plan-review to `工部实测直办 → 御史验收 → 门下终复` for a low-risk local operation. The key is that the Regent does not perform the repair; it only adjusts the task graph and acceptance boundaries.

## Anti-patterns

- Continuing to spawn planner revision v3/v4 for CLI syntax questions.
- Archiving a blocked review without checking whether it is still a parent of the execution card.
- Dropping the auditor/final-review stage after bypassing the review loop.
- Treating vector `embed` as mandatory when the task only needs keyword discoverability and BM25 `qmd search` can satisfy acceptance.
