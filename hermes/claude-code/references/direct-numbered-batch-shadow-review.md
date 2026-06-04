# Direct numbered batches with CC shadow-review

Use this pattern when the user selects multiple previously offered options compactly (for example `134`) and adds “directly handle it, let CC assist”.

## Trigger

- User references numbered options from the previous answer: `13`, `134`, `1/3/4`, `123`.
- User says “直接处理”, “直接做”, “让 CC 协助”, “让 cc 协助”.
- The selected items are a mixed batch: code fix + docs update + cleanup + verification.

## Pattern

1. **Decode the numbers immediately.** Restate the mapping briefly, but do not ask the user to reconfirm unless the mapping is genuinely ambiguous.
2. **Start with prerequisite checks.** Load relevant skills; check worktree / kanban / CC occupancy.
3. **Do not let stale CC sessions block deterministic progress.**
   - If existing CC sessions are busy, thinking, or have residual input, do **not** reuse them.
   - If the user said “directly handle”, Hermes may execute deterministic, reversible, or well-tested parts while preparing a clean CC shadow-review session.
   - For destructive actions, keep the destructive step behind a hard gate until CC review or explicit user authorization; see `references/destructive-cleanup-shadow-review.md`.
4. **Use CC as shadow reviewer when Hermes already made progress.**
   - Write a concise `/tmp/cc-context-<task>.md` with exact scope, files, required commands, and “do not commit / do not delete” constraints.
   - Launch an isolated tmux session, send `/clear`, send the review instruction, and verify the command actually executes (blank Enter if needed).
   - Poll and report using the normal 📡 template.
5. **Let CC verdict inform the gate.**
   - `no blockers` + tests pass → commit/push if appropriate.
   - blocker or semantic concern → fix before commit.
6. **Final cleanup and verification.**
   - Remove fresh pytest/pycache residue produced by validation.
   - Re-run the relevant tests and `git diff --check`.
   - Commit only scoped files; verify remote SHA and clean status.

## Why this exists

A too-literal reading of “CC busy” can turn “directly handle it with CC assistance” into avoidant behavior: Hermes waits for CC before doing anything, or reports that CC cannot help. The better behavior is bounded progress plus isolated CC shadow-review, with destructive steps gated.

## Minimal CC context template

```md
# CC shadow review — <task>

Workdir: `<absolute path>`

Hermes has already made changes. Your job is shadow-review and verification, not broad refactor.

## Scope
- <files / behavior to review>
- <docs / cleanup items>

## Required commands
```bash
<test command>
python3 -m py_compile <file>
git diff --check
git status --short --ignored | sed -n '1,120p'
```

## Constraints
- Do not commit.
- Do not delete files.
- Do not touch external services unless explicitly listed.

## Output
- blockers? yes/no
- tests result
- semantic concerns
- safe for Hermes to commit? yes/no
```
