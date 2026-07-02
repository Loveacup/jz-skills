# Residual input submit pitfall — 2026-06-30

## Context

During `cc-bili-p2b1`, Hermes created a fresh tmux session, sent a single-line task with `tmux send-keys ... Enter`, then ran:

```bash
cc-wait-decision.sh --session cc-bili-p2b1 --timeout 900 --expect /tmp/cc-bilibili-p2b1-done.txt
```

`cc-wait-decision` returned rc=6:

```text
prompt_text_needs_clear
reason: prompt_text_stale_or_unknown
stderr_summary: pane has residual input; refusing to auto-submit unknown text
```

The pane still visually showed exactly the freshly sent task line, wrapped across two display lines. It was not stale human input; it was the task line that had not been submitted/recognized by the guard.

## Correct recovery

Do **not** resend the task, because duplicate task submission can create repeated work or conflicting edits.

If all of these are true:

1. The pane visually shows exactly the freshly sent task text.
2. The prompt input box contains no unrelated/stale text.
3. The task was sent moments ago by Hermes.
4. No tool execution has started yet.

Then press Enter once:

```bash
tmux send-keys -t <session> Enter
```

Then rerun monitor/wait. In this case CC moved to `Forging…` and later produced the expected done/result files.

## Follow-up state

A later `cc-wait-decision` may return rc=5 with:

```text
state: active_no_resend
reason: monitor_state=THINKING
```

That means the task is active. Do not resend or press Enter again. Use `cc-monitor.sh --force-capture` or wait for the expected artifact.

## Rule of thumb

- rc=6 + visible exact freshly sent line → one manual Enter, no resend.
- rc=5 + THINKING/TOOL/Forging → monitor only, no resend.
- Unknown/stale prompt text → clear or ask; do not auto-submit.

This is a guardrail recovery pattern, not a bypass: the agent must visually/semantically verify the line before pressing Enter.