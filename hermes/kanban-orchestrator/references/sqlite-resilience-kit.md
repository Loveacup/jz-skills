# SQLite Resilience Kit — Dead-Worker Reaper + Parent-Done Watchdog + Write-Lock Degradation

## Problem

D16 architecture review identified three superimposed risks from single-SQLite-as-truth-source:

1. **#23216 silent exit**: Worker exits `rc=0` without calling `kanban_complete`/`kanban_block` → child cards permanently stranded
2. **No parent-timeout provision**: Cards with `parents` have no mechanism to detect parent abandonment
3. **SQLite write-lock contention**: >2-3 concurrent writers cause `kanban_comment` to silently fail

## Solution: Three independent fixes

### Fix 1 — Dead-worker reaper

`no_agent=True` cronjob every 5 minutes. See `scripts/sqlite-resilience-kit.sh`.

Logic:
- List all `running` tasks via `hermes kanban list --json`
- For each, extract `runs[-1].pid`
- `kill -0 <pid>` — if process not found, auto-block with reason

### Fix 2 — Parent-done watchdog field

Every card with `parents` gets `metadata.parent_timeout_at` at creation:

```python
import time

kanban_create(
    title="...",
    parents=[parent_id],
    metadata={
        "parent_timeout_at": int(time.time()) + 3600,  # 1h default
    }
)
```

The same resilience kit cronjob checks: any `todo` card with `parent_timeout_at` in the past AND parents still `running`/`blocked` → escalate via comment.

### Fix 3 — Write-lock retry with file-track degradation

For all supervision-loop write paths, wrap with retry + fallback:

```python
import time, json

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds base, exponential backoff

def safe_kanban_write(write_fn, *args, fallback_file=None, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return write_fn(*args, **kwargs)
        except Exception as e:
            if "database is locked" in str(e).lower():
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                    continue
            if fallback_file:
                with open(fallback_file, "a") as f:
                    f.write(json.dumps({
                        "ts": time.time(),
                        "fn": write_fn.__name__,
                        "status": "degraded_to_file",
                        "error": str(e)[:200]
                    }) + "\n")
            raise
```

Usage in supervision loop:

```python
safe_kanban_write(
    kanban_comment, task_id,
    "[intervene-ack] applied steer...",
    fallback_file=f"/tmp/kanban-intervene-{task_id}.md"
)
```

## Integration

All three fixes combine into a single `no_agent=True` cronjob running every 5 minutes. The write-lock retry (Fix 3) lives in the holder worker's code, not the cronjob.
