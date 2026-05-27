# Regent Kanban Coordinator Poll Pattern

Use this when the user’s pain is not merely “notify me when Kanban changes,” but “the orchestrator does not know progress changed, so it cannot coordinate the next step unless I remind it.”

## Problem

A messaging-platform orchestrator such as Telegram Regent is request/response. Once a reply finishes, that exact session is not alive to poll Kanban. A plain watchdog that sends status-change text to the user solves notification, but not coordination: the Regent may still fail to create downstream cards, recover blocked tasks, or summarize final results until the user asks.

## Pattern

Deploy a second, low-frequency script-mode cron in addition to the fast watchdog:

- `kanban-watchdog`: every 1 minute, no-agent script, detects status transitions and notifies only on meaningful events.
- `kanban-watcher-poll`: every 5 minutes, no-agent script, runs only when the board has unfinished tasks. It wakes a short Regent coordinator run to inspect active tasks and either coordinate silently or report only if necessary.

The coordinator run is not the same Telegram conversation instance. It is a fresh `regent` profile run that acts as值房太子. Persist any final artifacts to Kanban summaries / workspaces / a fixed inbox path so future Regent turns can retrieve them.

## Minimal implementation shape

1. Script queries the Kanban board directly or via `hermes -p regent kanban list --json`.
2. If no active tasks (`done`/`archived` excluded) and the previous state also had no active tasks, exit with empty stdout. If previous state had active tasks, treat this as a **batch cleared** transition: write a final-results JSON and emit one concise completion notice.
3. If active tasks exist, compute a signature over task id/status/assignee/failure fields for dedupe.
4. Write an event file under profile state, e.g. `profiles/regent/state/regent-inbox/kanban-poll/*.json`.
5. Invoke a short coordinator run:
   ```bash
   hermes -p regent chat -q "Read <event.json>; coordinate Kanban; output NO_REPORT unless user-facing report is required" \
     --source kanban-watcher-poll \\
     --skills kanban-orchestrator,hermes-agent \
     --quiet
   ```
6. In script-mode cron, print nothing unless the coordinator output starts with a sentinel such as `REPORT:`. Strip the sentinel before delivery.
7. Use a lock file and stale-lock timeout to prevent overlapping coordinator runs.

## Coordinator prompt rules

The prompt should be narrow:

- Read the event file and relevant Kanban tasks.
- For `blocked`/`crashed`/`timed_out`/`gave_up`, diagnose and recover if safe; ask/report only when a user decision is required.
- For completed stages, create downstream fan-in / review / audit / archive cards when missing.
- If normal `running`/`ready`/`todo` progress needs no action, output exactly `NO_REPORT`.
- If the user must be notified, output `REPORT:` followed by a concise message.
- Do not create cron jobs recursively or start new polling loops.

## Pitfalls

- Do not claim this makes the current Telegram conversation “know” in real time. It creates a fresh Regent run and leaves durable traces for later turns.
- Do not notify on every poll. Empty stdout must mean silent.
- Do not run the LLM every minute; keep the coordinator poll slower, e.g. 5 minutes, and only when active tasks exist.
- A watchdog is not a coordinator. The watchdog reports transitions; the coordinator poll owns “what should happen next.”
- Persist final results to Kanban/root-card summaries or an inbox path; otherwise the next main-channel Regent may still need to rediscover them.
- **Cron `ok` can still be an empty no-op.** Verify effectiveness, not just scheduler status: check that the poll wrote/updated `state/regent-inbox/kanban-poll/*.json` and `kanban-watcher-poll-state.json` when active tasks exist, and that a coordinator-created downstream card or final-result trace appears when coordination is needed.
- **Profile-home vs root-home path trap.** Script-mode cron may run with `HERMES_HOME` set to the profile home (`~/.hermes/profiles/regent`). The global Kanban DB may still live at root (`~/.hermes/kanban.db`). Coordinator scripts should use an explicit root home / board path (or `HERMES_KANBAN_BOARD`) for the board, and an explicit profile home for state/inbox files. Otherwise the script exits silently because it sees no board.
- **Status is not artifact receipt.** A board with all children `done` is not complete if the orchestrator has not read the child artifacts and checked whether downstream fan-in/review/audit/final-report cards are missing. The coordinator prompt should explicitly inspect completed sibling artifacts and create missing downstream cards.
- **Active coordination means taking the next action, not merely observing.** If the coordinator sees `done` fan-in work, it must create the next review/audit/final-delivery card if missing. If it sees a valid reviewer rejection (`blocked` with concrete blockers), it must create an immediate revision card plus a fresh rereview card; do not wait for the Emperor to ask “进度?”. The old blocked reviewer remains as audit trail and should not be used as a parent for the revision card.
- **Main-channel recovery must check the inbox first.** Because the coordinator run is a fresh Regent instance, the visible Telegram Regent should, at the start of a later user turn, inspect the fixed inbox/final-result paths before answering Kanban status questions. Otherwise the background coordinator can succeed while the main Regent still appears unaware.
- **Timeout budget must be nested.** Script-mode cron has its own scheduler timeout; the coordinator subprocess timeout must be shorter (for example 90s under a 120s cron timeout) and should return `NO_REPORT`/empty stdout on timeout rather than producing noisy failure notifications.