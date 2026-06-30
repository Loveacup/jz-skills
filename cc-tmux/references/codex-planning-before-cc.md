# Codex planning before CC execution

Use this when Alex wants the development workflow to be: **Codex plans, CC executes, Hermes audits/co-ordinates**.

## Pattern

1. **Hermes gathers facts only enough to frame the task**, then stops implementing.
2. **Codex runs a read-only planning pass**:
   ```bash
   codex exec --skip-git-repo-check --sandbox read-only '只读规划任务。禁止修改文件。Read only these paths: ... Output: current facts, CC execution plan, verification checklist, Hermes audit risks. Output then exit.'
   ```
3. **Hermes turns the Codex plan into a CC execution package** with allowed files, TDD criteria, verification commands, and explicit non-goals.
4. **CC executes** via cc-tmux.
5. **Hermes audits independently**: rerun tests, inspect actual files/DOM/browser where relevant, and verify side effects (e.g. no `events.db`).

## Pitfalls

- If the project directory is not a git repo, standalone Codex may refuse unless `--skip-git-repo-check` is set.
- For planning-only use `--sandbox read-only`; otherwise Codex may treat the task as editable workspace work.
- If Codex times out after broad discovery, do not repeat the same broad prompt. Retry with explicit allowed files and forbid qmd/Obsidian/web if only local code planning is needed.
- Codex output is a plan, not proof. Hermes must still verify current files and real command/browser output.
- If Hermes has already hand-written a half-finished implementation, stop, summarize current facts, and hand the remainder to Codex/CC instead of continuing to write code directly.

## Fallback: Codex unavailable

If Codex quota is exhausted or unavailable, **skip the planning phase and let CC self-plan**:

1. Hermes prepares a detailed context file (`/tmp/cc-context-<task>.md`) with:
   - Goal and non-goals
   - Background and current state
   - Specific tasks to complete
   - Constraints and acceptance criteria
   - Output requirements
2. Send context to CC with instruction: "先规划修改方案，确认后再执行"
3. CC will read files, plan changes, and wait for confirmation before executing
4. Hermes reviews CC's plan (first capture-pane after send) before approving execution

This fallback preserves the role separation (Hermes coordinates, CC executes) while accepting that planning may happen inside CC rather than in a separate Codex pass.
