# Continuing an unsafe or stale Claude Code session

Use when the user asks to “延续会话 / continue the CC session” but the existing tmux/Claude Code pane is not safe to reuse.

## Problem pattern

A prior CC session may show a completed answer but the input line still contains a residual command or suggestion, e.g. `❯ 导入 organized.html 到 Chrome 验收效果`. Pressing Enter could perform an unapproved side effect. `C-u`, `Escape`, or `C-c` may fail to visibly clear the line in the TUI.

Occupancy scanners can also misclassify a finished session as `THINKING` when old scrollback still contains `✻ Cooked/Sautéed for ...`. Treat the scanner as a guard, not a verdict: always `capture-pane` and inspect the bottom input line before deciding whether the session is active, unsafe-stale, or reusable.

## Safe continuation protocol

1. Capture the pane and inspect the last input line.
2. If `❯` has any residual text with potential side effects, do **not** press Enter.
3. Try to clear with `C-u`; if still visible, try `Escape` then `C-c` once.
4. If the residual text remains, declare the old session unsafe to reuse.
5. Start a new isolated `hermes-cc-{task}-{ts}` session.
6. Write a context handoff file containing:
   - the previous session’s goal and decisions
   - artifact paths and verification evidence
   - the user’s new request
   - explicit scope: discussion-only vs execute
7. Send the new session to read the handoff file and continue from there.
8. Report to the user that this is “同题新隔离 session，等效延续” and why it is safer.
9. If the phase is now complete and a residual input line still cannot be cleared, kill only that finished execution session as the final input-line safety gate; do this after artifact/commit/disk verification, not before.

## What not to do

- Do not press Enter hoping the old session will ignore the residual line.
- Do not kill the old session mid-stage unless the user has confirmed the phase is over; retain it as read-only evidence if needed.
- Do not use `--continue` if the old session has input-line contamination or scrollback ambiguity.

## User preference captured

When the user says “延续会话”, they often care about continuity of context and decisions, not literal reuse of the same tmux pane at any cost. A fresh session with a precise handoff file is acceptable when the old pane is unsafe.
