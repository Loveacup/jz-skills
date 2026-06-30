# cc-wait-marker startup gate: IDLE/THINKING race

## Context

During a CC implementation session, `cc-wait-marker.sh --session <s> --timeout 900` returned:

```text
session is IDLE and no newer turn-done marker exists; task was not submitted
```

But an immediate `cc-monitor.sh --session <s>` and pane capture showed CC had actually begun:

```text
state=THINKING / TOOL
Read 2 files
Reading 3 files…
Spelunking…
```

This is a startup race: the wait-marker gate sampled the pane during a transient IDLE-looking moment before hook/monitor state caught up.

## Operational rule

When `cc-wait-marker` exits 4:

1. Do **not** assume the task is dead.
2. Immediately run:

```bash
cc-monitor.sh --session <session>
tmux capture-pane -t <session> -p -S -120 | tail -120
ls -lt /tmp/<expected-done-file> <expected-output-files>
```

3. If monitor/pane shows `THINKING`, `TOOL`, `Read`, `Write`, `Edit`, `Spelunking`, etc., treat wait-marker as a startup race and continue with monitor + artifact checks.
4. If pane shows residual input at `❯`, and the residual text is the freshly-sent task line, press Enter explicitly or rerun with an explicit auto-submit flag if appropriate.
5. If pane is clean `❯` with no activity and no artifacts, resend the single-line task referencing `/tmp/task.md`.

## Do not

- Do not hang another blind 900s wait without first checking monitor/pane.
- Do not conclude “CC failed” from wait-marker exit 4 alone.
- Do not auto-press Enter on unknown residual text; stale commands like “commit it” may be present.

## Preferred monitoring fallback

For sessions where wait-marker repeatedly false-fails but pane shows work, use bounded manual cadence:

```bash
sleep 90
cc-monitor.sh --session <session>
ls -lt /tmp/<done> <expected files>
tmux capture-pane -t <session> -p -S -100 | tail -100
```

Stop once the done file exists, then kill/clear the session if residual input appears and no further user authorization exists.
