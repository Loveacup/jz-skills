# Coordinator silent-success pitfall

## Trigger

Use this reference when a Telegram/Regent user says the Kanban watcher/coordinator did not seem to work, even though cron jobs report `last_status=ok`, or when a task was blocked but later recovery work appears to have happened off to the side.

## Observed pattern

In a Regent Obsidian-document update flow, the chain reached a legitimate `blocked` state because the auditor found qmd index verification had failed. The 5-minute `kanban-watcher-poll` script did run and automatically created a recovery chain (`qmd refresh` + follow-up audit), but the main chat still looked stuck because:

1. `kanban-watchdog` only reports status transitions; it does not coordinate.
2. `kanban-watcher-poll` only prints user-visible output when its child coordinator emits `REPORT:`.
3. The child coordinator created recovery cards but did not emit `REPORT:`, so cron output remained `silent (empty output)`.
4. The original blocked card remained visible until later archival, so manual status checks still showed the old blocker.
5. The Regent, not checking coordinator-created recovery cards first, manually created a duplicate recovery chain.

## Diagnostic checklist

When investigating “polling did not coordinate”:

1. Check cron jobs:
   - `kanban-watchdog` every 1m, `no_agent=True`, enabled, `last_status=ok`
   - `kanban-watcher-poll` every 5m, `no_agent=True`, enabled, `last_status=ok`
2. Inspect coordinator output files under the profile cron output directory; `silent` means no user-facing report, not necessarily no action.
3. Inspect coordinator event inbox:
   - `~/.hermes/profiles/regent/state/regent-inbox/kanban-poll/poll-*.json`
   - Look for active blocked/running signatures around the incident time.
4. Search board history for recovery cards created shortly after the blocked event before creating a manual recovery chain.
5. Inspect final-results inbox for batch-cleared records:
   - `~/.hermes/profiles/regent/state/regent-inbox/final-results/*.json`

## Required behavior for future Regent orchestration

Before manual recovery from a blocked Kanban chain, the Regent must first check whether the coordinator already created or completed a recovery chain. If it did, report that chain and only add missing closure steps; do not duplicate work.

Coordinator observability should be designed so that:

- child coordinator stdout/stderr/return code are logged to a local run-log directory for audit;
- when blocked/failed tasks trigger automatic recovery cards, the cron emits a concise `REPORT:` (≤6 lines);
- when a batch clears after blocked/failed state, the final clear notification states that recovery/archival occurred;
- no-task and unchanged-running states remain silent to avoid notification spam.

## Anti-pattern

Do not interpret `last_status=ok` + `silent` as “nothing happened.” It can mean “the script did useful work but suppressed the report.” Conversely, do not create a duplicate recovery chain until you have checked the event inbox and recent board tasks.