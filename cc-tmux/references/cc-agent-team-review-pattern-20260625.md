# CC Agent Team Review Pattern — 2026-06-25

Use this when Alex asks to “拉 CC 审核/优化”, especially for Obsidian architecture/design documents.

## Durable lessons

1. Prefer **Agent Team + high effort** for review/optimization work.
   - Do not default to `max`: max can overthink, burn huge tokens, and amplify API-failure recovery cost.
   - Avoid over-constraining the context into a mechanical 3-point patch when the user wants review + optimization. Give scope and boundaries, but let CC independently audit and improve.

2. AskUserQuestion is fragile in tmux.
   - Context should say `Do not AskUserQuestion` unless interactive choice is truly required.
   - If CC opens AskUserQuestion anyway and the UI gets stuck, use Escape and a plain-text decision; verify the prompt actually consumes the queued message.

3. After API error or suspicious “Edit success”, trust only disk.
   - Check file mtimes, grep for key phrases, read the report file, and rerun wikilink/validation.
   - If CC self-reports edits but mtimes/content did not change, stop that session and restart fresh rather than continuing to burn tokens.

4. For doc optimization, the context should contain:
   - project directory and relevant files;
   - background design decisions;
   - required focus areas but not overly narrow patch instructions;
   - boundaries: no skill edits, no deletes, no commit/push, no unrelated directories;
   - required output report path;
   - explicit verification command/criterion.

## Context skeleton

```md
Use Agent Team mode with high effort, not max. Do not AskUserQuestion.

Project: <absolute project dir>
Relevant files: <list>

Background:
- <recent decisions>

Task:
Use agent team to audit and optimize the docs. Focus on but do not limit yourself to:
1. <focus A>
2. <focus B>
3. <focus C>

Agent Team suggestion:
- Agent A: <concern 1>
- Agent B: <concern 2>
Leader synthesizes and applies focused patches.

Boundaries:
- May edit related md files in project dir.
- Do not edit skills.
- Do not delete files.
- Do not commit/push.
- Avoid whole-document rewrites unless clearly necessary.
- Verify wikilinks.

Output:
Save report to /tmp/<task-report>.md with changed files, design judgments, verification result, unresolved questions.
End with DONE_<TASK>.
```

## Verification checklist

- [ ] Report file exists and is non-empty.
- [ ] Project file mtimes changed as expected.
- [ ] Key content grep confirms actual edits.
- [ ] Wikilink check passes.
- [ ] cc-finish releases lock.
