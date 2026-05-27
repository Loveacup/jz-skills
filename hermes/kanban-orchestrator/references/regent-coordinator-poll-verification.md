# Regent coordinator poll verification

Use this when a regent/Telegram orchestrator has a 5-minute Kanban coordinator poll and the user asks whether it is actually working.

## Durable lesson

Cron `last_status=ok` proves only that the script exited successfully. It does **not** prove the script saw the real Kanban board or woke a coordinator. Script-mode cron may run with `HERMES_HOME` set to the profile home (`~/.hermes/profiles/regent`), while the board DB lives at root (`~/.hermes/kanban.db`). If the script derives `BOARD_DB = HERMES_HOME / "kanban.db"`, it can silently see an empty/nonexistent board and produce no events.

## Verification checklist

1. Inspect cron status:
   - job enabled
   - schedule correct
   - `last_status=ok`
   - `last_run_at` recent
2. Independently query the live Kanban board for active tasks (`status not in done/archived`).
3. Inspect the coordinator state/event directory, usually:
   - `~/.hermes/profiles/regent/state/kanban-watcher-poll-state.json`
   - `~/.hermes/profiles/regent/state/regent-inbox/kanban-poll/*.json`
4. Confirm the latest poll event lists the same active task IDs/statuses as the live board.
5. If not, run the script manually under the same profile-like environment and check paths:
   - `HERMES_HOME=~/.hermes/profiles/regent python3 ~/.hermes/profiles/regent/scripts/kanban-coordinator-poll.py`
6. Fix by separating explicit paths:
   - root home / board: `~/.hermes/kanban.db`
   - profile state/inbox: `~/.hermes/profiles/regent/state/...`

## Reporting rule

Say “normal” only after both layers pass: scheduler health + fresh event/state evidence matching the live board. If scheduler is ok but event/state is stale or missing, report “executing but ineffective/空转” and fix the path or state bug.
