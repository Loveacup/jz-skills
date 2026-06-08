# Manual patrol after report — do not end on a promise

## Trigger

Use this note when a user explicitly demands that the current Hermes agent keep monitoring a Claude Code/tmux session every 30–60 seconds, especially after frustration like:

- “你持续 sleep 30-60 啊”
- “汇报之后你还是不执行轮巡命令”
- “别等我每次问，自己轮巡”

## Failure pattern

Bad sequence:

1. `tmux capture-pane ...`
2. Send a correct `📡 CC Agent Team [...]` block.
3. End the turn with “我会继续监控 / 后续继续轮巡”.
4. No tool call is running, so the next patrol never happens until the user complains.

This is an **execution lapse** even if the report content and template are correct. The user asked for ongoing patrol, not a promise.

## Correct sequence

When the task is still running and the user has requested manual patrol:

1. Capture current state.
2. Report immediately with the required `📡 CC Agent Team [Xmin · 距上次 Xs]` block.
3. If still running, immediately start the next patrol tool call instead of ending with a promise:

```bash
sleep 30; tmux capture-pane -t <session> -p -S -140
```

4. After the tool returns, send the next `📡` block.
5. Repeat until one of these stop conditions is met:
   - CC is complete and disk verification passes.
   - CC asks a real decision question that Hermes cannot answer.
   - User explicitly says pause/stop/kill/do not monitor.

## Relationship to Pitfall #47

Pitfall #47 warns that `sleep N && capture-pane` creates user-visible silence if used as a substitute for reporting. It does **not** authorize ending the turn after a report without scheduling/running the next patrol.

Practical interpretation:

- Do not hide multiple capture cycles inside one silent tool call.
- Do not end with a promise when the user asked for continuous patrol.
- A single `sleep 30; capture-pane` tool call after a `📡` report is acceptable when the user explicitly asked for current-agent manual patrol and rejected cron/script/watchdog automation.

## Verification checklist

Before ending any turn during manual patrol:

- [ ] Did I just show the latest `📡` block for the most recent capture?
- [ ] If CC is still running, did I actually start the next patrol tool call, not merely promise it?
- [ ] If I stopped, is there a valid stop condition and did I state it?
