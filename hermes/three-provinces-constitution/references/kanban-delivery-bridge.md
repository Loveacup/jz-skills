# Kanban Delivery Bridge for fast tasks

## Context

A real smoke test exposed a visibility gap in the regent Kanban automation: a task chain can be created and completed between two coordinator cron ticks. If the coordinator only polls active/nonterminal tasks every ~5 minutes, it may see no active window and remain silent even though the task produced a result that should be delivered.

## Durable lesson

Do not rely on a slow coordinator alone for user-facing completion delivery. Pair it with a faster watchdog that observes state transitions and emits a concise delivery block for tasks that explicitly request delivery.

## Recommended pattern

1. Keep coordinator polling responsible for blocked recovery, fan-in/fan-out coordination, and higher-level orchestration.
2. Let watchdog detect state transitions (`running -> done`, `ready -> done`, etc.) at a shorter interval.
3. Add a Delivery Bridge layer to the watchdog:
   - Trigger only for explicit delivery signals, e.g. title prefix `smoke-`, title contains `汇总`, or task summary contains `delivery_required=yes`.
   - Output a short structured block containing task id, assignee, and summary.
   - Cap visible summary to about 6 lines.
   - Empty/no-change polling remains silent.
4. Preserve notification discipline: ordinary leaf-task completion should not notify the user unless explicitly marked for delivery.
5. Verify with a real short-lived Kanban task that completes before the next coordinator tick.

## Acceptance evidence for future changes

A proper test should demonstrate all of the following:

- A fast task completes within the coordinator interval.
- Coordinator may remain silent without treating that as failure.
- Watchdog emits the delivery block exactly when the task is done and explicitly marked for delivery.
- Empty subsequent watchdog runs stay silent.
- No Hermes core changes are required; prefer profile-local scripts/hooks.

## Pitfall

If a task is important enough for the user/太子 to see, require an explicit delivery marker such as `delivery_required=yes` in the summary or handoff. Otherwise the system may correctly complete work while leaving the main channel unaware.