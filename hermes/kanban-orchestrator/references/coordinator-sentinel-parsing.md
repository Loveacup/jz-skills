# Kanban coordinator sentinel parsing pitfall

## Trigger

Use this when a `kanban-watcher-poll` / coordinator cron is enabled and reports `last_status=ok`, but blocked tasks were not automatically recovered or user-facing `REPORT:` messages did not appear.

## Symptom

- `cronjob list` shows the coordinator script job is enabled and healthy.
- `~/.hermes/profiles/regent/state/kanban-coordinator-poll-state.json` updates normally.
- Child run logs under `~/.hermes/profiles/regent/state/regent-inbox/kanban-poll-runs/` have `returncode: 0`.
- But `stdout_preview` starts with CLI framing such as `Query: ...` or echoed prompt text rather than exactly `REPORT:` / `NO_REPORT`.
- The parent script checks `out.startswith("REPORT:")`, so a valid sentinel later in stdout is missed.

## Durable fix pattern

In the coordinator script that spawns `hermes chat`:

1. Run the child in quiet mode:

```python
cmd = [
    str(HERMES_BIN),
    "chat",
    "-Q",  # suppress banner/query echo so sentinels are not hidden
    "-q", prompt,
    ...
]
```

2. Still parse defensively, because future CLI output may add framing again:

```python
out = (p.stdout or "").strip()
if p.returncode != 0:
    return f"REPORT: ⚠️ Kanban 5分钟协调轮询失败：rc={p.returncode}; {err[:300]}"

for line in out.splitlines():
    s = line.strip()
    if s.startswith("REPORT:"):
        return s
    if s == "NO_REPORT":
        return s
return out
```

3. Verify with:

```bash
python3 ~/.hermes/profiles/regent/scripts/kanban-coordinator-poll.py
python3 -m py_compile ~/.hermes/profiles/regent/scripts/kanban-coordinator-poll.py
```

A healthy empty-board dry run exits 0 with no stdout.

## Important distinction

- `kanban-watchdog` is a no-agent status notifier; it does not repair blocked tasks.
- `kanban-watcher-poll` / coordinator is the repair actor; its sentinel parsing must be reliable.
- A cron `last_status=ok` only proves the script exited successfully, not that the child coordinator's `REPORT:`/`NO_REPORT` protocol was interpreted correctly.
