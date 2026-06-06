# Max-Effort Thinking Loop Recovery

## Symptom

CC at max effort (`--effort max`) shows "almost done thinking with max effort" for >3min with **frozen token count**. The thinking indicator rotates (✻→✽→✳→✶) but no action happens.

## Root Cause

Max effort on complex/long prompts causes CC to plan exhaustively without reaching a termination condition. The longer the prompt, the more likely this is.

## Recovery Recipe (tested 2× on 2026-06-05)

1. **Ctrl+C** to interrupt
2. **Narrow the scope**: replace the original broad task with a single atomic action
3. **Use a short prompt**: ≤200 chars, single sentence
4. **File-pass when possible**: write the narrowed task to `/tmp/cc-task-<name>.md`, then `Read /tmp/cc-task-<name>.md` as the command

## Examples

❌ "Read context file. Do cross-module consistency review on 4 modules, find all semantic mismatches, then write decision recommendations for 3 open questions. Use agent team."
✅ "Read /tmp/cc-task-narrow.md" (file contains: "Search and read SkillX and RKC papers. Reply with 5-10 bullet points. No architecture design.")

## Prevention

- Keep prompts under 500 chars for max effort
- Break complex tasks: first do research, then do architecture, then do review
- Use `--effort high` instead of `max` when the task doesn't need deep architectural reasoning
- Pre-write context to `/tmp/` files, have CC read them, don't inline long prompts
