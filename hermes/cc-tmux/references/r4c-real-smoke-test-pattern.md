# R4c real smoke test pattern

## When to use

Use this when verifying changes to cc-tmux monitoring / progress / checkpoint rules. Do not treat prose-only review as a real test: exercise a real Claude Code tmux session, but keep the task readonly and low-risk.

## Minimal real smoke test

1. Start a real CC session with `cc-start.sh` for a readonly target. If active sessions exist, honor the gate: ask the user before `--ack-active`.
2. Send a context file that explicitly says:
   - readonly only;
   - no git add/commit/push/reset/clean;
   - no kill session / no C-c;
   - no AskUserQuestion;
   - first restate understanding and stop for confirmation.
3. Perform the startup in-turn control loop before leaving:
   - confirm `cc-send.sh` output;
   - capture pane and verify the context was consumed;
   - verify no `❯` residual input, queued messages, or AskUserQuestion;
   - if residual input remains, use the existing mechanical recovery path (`Enter` once, then `Escape` + resend via `cc-send.sh` if needed), and report it as progress.
4. After CC confirms understanding, send a readonly execution confirmation and wait for turn-done with `cc-wait-marker.sh` in-turn.
5. Dispatch one `delegate_task` one-shot checkpoint worker only after startup is stable. For a smoke test, shorten the wait (e.g. 45s) but keep the same permissions boundary: read `/tmp/cc-status-*`, heartbeat, turn-done, freeze, and `tmux capture-pane`; do not kill/C-c/semantic-send.
6. Read and independently verify the artifact CC writes (size + content). Do not accept CC's self-report without reading the file.
7. Run `cc-finish.sh --release-lock` only. Do not `--kill-session` unless the user explicitly approves.

## What counts as pass

- CC can read and correctly explain the new rule.
- The startup loop catches or clears residual input / queued states before handoff.
- The checkpoint worker dispatch path is exercised.
- Artifacts are verified from disk.
- Lock release succeeds.

## Honesty rule for async checkpoint

If the checkpoint worker is dispatched but its async result has not re-entered the conversation by the time you finish the test, report exactly that: dispatch was tested, but async callback delivery was not yet verified. Do not claim callback success until the result appears in the main conversation.

## Drift check

A real smoke test should compare runtime skill and source skill when both exist:

- runtime: `~/.hermes/skills/.../cc-tmux/SKILL.md`
- source: `~/code/jz-skills/hermes/cc-tmux/SKILL.md`
- references under both trees

If both have the same version but different content, merge before pushing. Preserve operational pitfall content from runtime and structural clarity from source; verify parity by hash after sync.

## Monitor failure fallback

If `cc-monitor.sh` itself crashes (for example shell `set -u` unbound variable), do not classify that as CC failure. Immediately fallback to `tmux capture-pane`, report that monitor failed, and continue judging CC state from pane evidence. Then record the monitor bug as a follow-up fix.
