# Phase 0 Codex Lane Card Template

Use this template when a Hermes Kanban worker uses Codex as an input lane and a separate child card performs review.

## Implementation Card

```markdown
## Background
<Why this task exists. Include the Phase / project context and the reason Codex is useful.>

## Goal
<Exactly what Codex may help change. Define success in observable terms.>

## Allowed scope
Allowed paths only:
- `<absolute/path/one>`
- `<absolute/path/two>`

## Forbidden actions
- Do not modify files outside allowed scope.
- Do not access, print, or request secrets/tokens/credentials.
- Do not call Hermes Kanban lifecycle commands from Codex.
- Do not send external messages or mutate gateway/cron/runtime config.
- Do not perform broad rewrites or unrelated cleanup.

## Codex lane operating rules
Hermes owns task lifecycle, verification, and final board state. Codex is only an untrusted patch producer.
Run Codex in an isolated worktree/copy:
`<absolute/temp/worktree>`

Suggested command:
`codex exec --sandbox workspace-write <self-contained prompt>`

## Timeout / kill conditions
Kill Codex and record evidence if:
- no useful output or no relevant file change after `<N>` minutes;
- total runtime exceeds `<N>` minutes;
- Codex touches files outside allowed scope;
- Codex requests secrets/external permissions;
- Codex starts unrelated rewrites;
- Codex claims completion without a readable diff.

## Acceptance criteria
Hermes must verify independently:
1. `<skill/test/readback command>` succeeds.
2. Diff only touches allowed paths.
3. Structured examples / schemas parse if present.
4. No prohibited terms or sensitive markers appear in the accepted patch.
5. `metadata.codex_lane.result` is exactly one of `accepted | partial | rejected | timed_out`.

## Completion semantics
If this implementation card has a child review card, mark this card `done` only as `implementation-ready-for-review`; do not use `block(review-required)` as the review gate. The child review card makes the final `pass | request changes | reject` decision.

## Required handoff to reviewer
Include:
- changed paths;
- diff summary;
- artifact/worktree paths;
- Hermes verification output;
- `metadata.codex_lane` JSON;
- known risks or rejected partial work.
```

## Review Child Card

```markdown
Review the parent implementation card.

Decide exactly one:
- `pass`: retain the result.
- `request changes`: create a bounded follow-up for the implementer.
- `reject`: do not retain; record rollback or cleanup needed.

Checklist:
1. Did implementation stay within allowed paths?
2. Did Hermes independently verify instead of trusting Codex self-report?
3. Is `metadata.codex_lane.result` one of `accepted | partial | rejected | timed_out`?
4. Are kill/retry/timeout artifacts sufficient if failure control fired?
5. Is there any unrelated rewrite, secrets exposure, external action, or board lifecycle mutation?

Return evidence: changed paths, diff summary, verification output, and final decision.
```
