# Coordinator batch-cleared delivery bridge

## Problem

A `kanban-watcher-poll` script can correctly detect that the board moved from active tasks to no active tasks, but still fail the user-facing delivery contract if it only prints:

```text
📌 Kanban 批次已清空：当前无活跃任务。成果信箱：...
```

That proves the batch ended, but not what the batch produced. The Regent then appears to "not know" completed Kanban results unless it manually opens the final-results JSON.

## Prior art: watchdog Delivery Bridge

The older `kanban-watchdog.py` Delivery Bridge solved short-lived task delivery by reading the completed task detail, then emitting a concise completion block when a delivery marker exists.

Summary lookup pattern:

1. `hermes kanban show <task_id> --json.latest_summary`
2. If needed, latest `task_runs.summary`
3. Emit a short stdout block; script-mode cron delivers stdout verbatim

Typical trigger markers: title starts with `smoke-`, title contains `汇总`, or summary includes `delivery_required=yes`.

## Coordinator fix pattern

For batch-cleared notifications, keep the coordinator's final-results JSON but enrich it:

- Fetch final rows for the previously-active task IDs.
- Join or separately query the latest `task_runs` row per task.
- For each task, persist:
  - `latest_summary`: `(tasks.result or latest task_runs.summary or '')[:800]`
  - optionally `latest_run_id`
  - optionally `latest_run_outcome`
- Print at most 5 human-readable lines:

```text
📌 Kanban 批次已清空
  ✓ <title> — <summary ≤180 chars>
  … 还有 N 个任务，详见成果信箱
  成果信箱：<path>
```

## Pitfall

Do not rely on `tasks.result` alone. Many successful Kanban workers leave `tasks.result` empty/null while their real handoff is stored in `task_runs.summary`; `hermes kanban show --json` surfaces this as `latest_summary`.

## Regression test

Add a fixture where:

- `tasks.result` is `''` or `NULL`
- `task_runs` has two rows for the same task
- the expected output contains the newest run's `summary`, not the old one and not a blank title-only line

Also keep tests for:

- one task with summary
- one task without summary
- more than five tasks
- mixed statuses, where done/archived tasks are displayed first
