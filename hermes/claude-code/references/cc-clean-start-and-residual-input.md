# CC Clean Start + Residual Input Guard

Use when launching Claude Code for a high-risk cleanup/repo operation and you need a genuinely clean session, or when the bottom `❯` input line contains leftover text after CC reports completion.

## Session lesson

During a repo cleanup + Supermemory delete review, a new CC launch attempted to use an unsupported `--new-session` flag. The tmux pane exited before any useful work began. A later CC session finished its review but left a dangerous suggested command (`rm tests/unit/...`) sitting in the `❯` input line. The safe outcome came from treating both as hard guards:

1. Verify the pane is alive after launch before sending context.
2. If clean-start flags are uncertain, avoid them; use a clean workdir or `/clear` after launch instead.
3. On final capture, inspect the bottom input line for any queued text.
4. If the queued text is destructive, ambiguous, or cannot be cleared reliably, kill the session instead of reusing it.

## Clean-start launch checklist

```bash
# 1. Prefer a unique tmux session name.
tmux new-session -d -s hermes-cc-<task>-$(date +%H%M%S) -c <workdir> 'HOME=/Users/alexcai claude --model claude-opus-4-8 --effort xhigh'

# 2. Wait for UI, then verify pane is alive and at prompt.
sleep 5
tmux has-session -t hermes-cc-<task>-<ts>
tmux capture-pane -t hermes-cc-<task>-<ts> -p -S -20

# 3. Only after prompt is stable, send context path / task.
```

Do **not** assume `claude --new-session` exists. If a clean session is required, first check `claude --help` or avoid the flag entirely by using a neutral workdir and `/clear`.

## Residual input guard

After CC says it is done:

```bash
tmux capture-pane -t <session> -p -S -30
```

Look at the last prompt line:

- Safe: bare `❯` with no queued text.
- Risky: `❯ rm ...`, `❯ git commit ...`, `❯ delete ...`, or any task text CC generated but the user did not authorize.

Recovery order:

1. Try `C-u` or `Escape` once to clear the input line.
2. Capture again.
3. If text remains or the session is no longer needed, `tmux kill-session -t <session>`.
4. Never press `Enter` on CC's own queued suggestion unless the user explicitly approved that exact action.

## When to prefer kill over reuse

Kill the session immediately if any of these are true:

- The queued line contains destructive commands (`rm`, delete, migration, remote deletion, commit/push not explicitly approved).
- The pane previously exited or showed launch-flag errors.
- Another agent may have touched the same session.
- The phase is already complete and preserving context has no value.

This is a safety pattern, not a task narrative: clean-start verification prevents silent launch failures; residual-input inspection prevents accidental execution of CC's unapproved next-step suggestions.
