# Kanban Ghost Task Investigation

> When a kanban task completes with `result_len=0, summary=None` — no meaningful output from the worker. How to find out what happened.

## Checklist (run in order)

### 1. Metadata (`hermes kanban show <task_id>`)

Check: status, assignee, workspace type, skills loaded, timestamps (created→completed gap), events.

Key signals:
- `result_len=0` + `summary=None` → ghost task (worker called `kanban_complete()` with no data)
- `workspace: scratch` → directory likely cleaned up after completion
- Short completion gap (<5min) → worker likely hit an error and bailed, or had nothing to do

### 2. Raw DB row

```bash
sqlite3 ~/.hermes/kanban.db "SELECT * FROM tasks WHERE id='<task_id>';"
```

Check the body column — sometimes `kanban show` truncates or the body has useful context.

### 3. Session search (ALL profiles)

Kanban workers run under specific profiles. You don't know which one — search them all:

```python
session_search(query="<task_id or task title keywords>", profile="default")
session_search(query="<same>", profile="regent")
session_search(query="<same>", profile="cron-worker")
# ... add any other profiles from `hermes profile list`
```

If the worker ran in a profile that has its own session DB, the session will only appear under that profile. Searching just `default` will miss it.

### 4. Workspace directory

```bash
ls -la ~/.hermes/kanban/workspaces/<task_id>/
```

- `scratch` workspaces are cleaned up after completion → won't exist
- `dir:` workspaces persist → may contain artifacts even if summary was empty

### 5. Audit log

```bash
grep "<task_id>" ~/.hermes/kanban/audit_log.jsonl
```

Contains dispatch events, completion events, hallucination warnings. Empty = no audit trail for this task.

### 6. Worker log

```bash
ls ~/.hermes/kanban/logs/<task_id>.log
```

Worker stdout/stderr. If missing, the worker process didn't produce log output or the log was never written.

## Interpretation

| Finding | Likely cause |
|---|---|
| No session anywhere | Worker dispatched under a profile you didn't search, or short-lived ephemeral worker |
| No workspace, no log, no audit | Task ran as ephemeral scratch worker — designed to leave no trace |
| 4-minute gap, `summary=None` | Worker completed immediately, either: (a) condition already resolved, or (b) worker hit an error and bailed silently |
| Workspace exists but summary empty | Artifacts may be in workspace files; check directory contents |

## When to escalate

If the task matters and all checks are empty, ask the user. The honest answer is: "The task completed but left no trace — I can't confirm what it did. Want me to re-run it with a stable workspace and explicit acceptance criteria?"
