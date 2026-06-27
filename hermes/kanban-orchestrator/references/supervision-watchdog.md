# Supervision Watchdog — Out-of-Band Intervention Bridge

## Problem

The supervision loop (§8.7 of the Kanban architecture) relies on the **holder worker** polling `kanban_show` in its own monitor tick. When the worker itself is stuck deep in a blocking tool call (CC multi-minute tool, Codex network hang, `process(action="wait")`), it never reaches the polling point — exactly when intervention is most needed.

## Solution: Dual-signal intervention delivery

Keep the in-loop poll as **audit-only**, and add an **out-of-band watchdog** as the primary intervention signal:

```
  watchdog (no_agent cronjob, independent process)
  │
  ├─ every N seconds:
  │   kanban_show <task_id>
  │   grep "[watchdog-intervene]" in comments
  │   write to /tmp/kanban-intervene-{task_id}.md
  │
  └─ self-terminate when task reaches done/blocked

            │
            ▼ file write (always works)

  /tmp/kanban-intervene-{task_id}.md
  (primary signal — read by worker, even when stuck)

            │
            ▼

  holder worker
  │
  ├─ in-tick: poll kanban_show (audit-only)
  ├─ every tick ALSO: stat /tmp/kanban-intervene-*
  │   if mtime > last_seen → apply intervention
  └─ ack via kanban_comment "[intervene-ack]"
```

## Implementation

### Watchdog script

Run as `no_agent=True` cronjob. See `scripts/supervision-watchdog.sh`.

### Holder worker changes

In the supervision tick, add before the Kanban poll:

```python
import os

INTERVENE_FILE = f"/tmp/kanban-intervene-{task_id}.md"
try:
    mtime = os.path.getmtime(INTERVENE_FILE)
    if mtime > self._last_intervene_mtime:
        with open(INTERVENE_FILE) as f:
            instruction = f.read().strip()
        self._last_intervene_mtime = mtime
        # apply instruction via lane-native channel
        # then ack: kanban_comment("[intervene-ack] applied: ...")
except FileNotFoundError:
    pass  # no intervention pending
```

## Fail-safe properties

- Watchdog is **independent process** — survives worker crash/hang
- File write is **decoupled from worker liveness** — signal arrives even if worker is blocked
- `no_agent=True` means **zero LLM tokens** — pure shell polling
- Self-terminates when task reaches terminal state — no orphan processes
- Falls back to in-loop poll if watchdog is not configured
