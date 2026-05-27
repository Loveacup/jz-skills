# Kanban Watchdog Pattern — Self-Discovering Cron Monitor

> The watchdogs detects Kanban task status changes and pushes notifications to the user's chat without the orchestrator needing to be active between user messages. Essential for messaging-platform orchestrators (Telegram/Discord) that cannot run polling loops.

## Architecture

- **Cron job** (`no_agent=True`): runs every 1 minute, zero LLM cost
- **Script** (`scripts/kanban-watchdog.py`): polls `hermes kanban list --json`, compares current state against last-known state, outputs changes to stdout
- **Delivery**: cron delivers non-empty stdout to user's chat (origin)
**Silent when nothing changes**: empty stdout = no delivery = no spam

## v3.1: Stale Blocked Card Suppression (2026-05-25)

The watchdog now suppresses A-level alerts from old v1 blocked reviewer cards that have been
superseded by v2/v3 revision chains. The `_is_blocked_superseded()` heuristic checks if a newer
version of the same task base-name exists in `running`/`done` status, and if so, downgrades the
alert to C-level (silent). See `references/stale-blocked-card-suppression.md` for the full
heuristic, test scenarios, and integration details.

## Key Design Decisions

1. **Absolute paths**:
|---------|-----------|------------|--------|
| v1 | Manual track file | Required | Bare: `📡 Kanban 状态变更` |
| v2 | Auto-discovery via `kanban list --json` | Not needed | Bare |
| v3 | Auto-discovery | Not needed | Ceremonial: `【尚书省 · Kanban 奏报】` |

## v3 Ceremonial Output Format

```
【尚书省 · Kanban 奏报】
  门下省 · morning-news-final-synthesis → 已完结 ✅
  将作监 · kanban-gate-step3-implement → 阻绝 🚫
  中书省 · edict-repo-assessment → 施行中 🔄
  工部 · morning-news-final-fix → 已完结 ✅
```

- Roles mapped via `ROLE_MAP` (planner→中书省, reviewer→门下省, engineer→工部, etc.)
- Statuses mapped via `STATUS_ZH` (done→已完结 ✅, running→施行中 🔄, todo→待命 ⏳, blocked→阻绝 🚫)
- All non-done tasks auto-discovered; no hand-maintained track file

## Deployment

```bash
# Script lives at:
~/.hermes/profiles/regent/scripts/kanban-watchdog.py

# Cron job (one-time setup):
cronjob(action="create", name="kanban-watchdog", schedule="every 1m",
         script="kanban-watchdog.py", no_agent=True, deliver="origin")
**Silent when nothing changes**: empty stdout = no delivery = no spam

## v3.1: Stale Blocked Card Suppression (2026-05-25)

The watchdog now suppresses A-level alerts from old v1 blocked reviewer cards that have been
superseded by v2/v3 revision chains. The `_is_blocked_superseded()` heuristic checks if a newer
version of the same task base-name exists in `running`/`done` status, and if so, downgrades the
alert to C-level (silent). See `references/stale-blocked-card-suppression.md` for the full
heuristic, test scenarios, and integration details.

## Key Design Decisions

1. **Absolute paths**:
2. **State file**: `~/.hermes/profiles/regent/state/kanban-watchdog-state.json` tracks last-known status of every observed task
3. **Auto-cleanup**: Archived/completed tasks naturally drop from `kanban list` output → no stale references
4. **No rate limiting needed for A/B events**: max 1 notification/minute (cron frequency), silent when nothing changes
5. **D-level daily summary must be non-annoying**: emit at most once per calendar day, and only when there are active non-`done`/non-`archived` tasks. Do **not** send a summary like `已完结: 216` when the board has no active tasks — this violates the user's low-notification preference and looks like a script malfunction. Store the sent date in metadata such as `__meta__.last_daily_summary_date` inside the state file.

## Orchestrator Integration

The orchestrator (regent) still needs **start-of-turn awareness**: before addressing any user request, check the board for state changes. The watchdog delivers to the user, not the orchestrator.

```bash
# At start of every turn:
hermes kanban list --json | python3 -c "
import json,sys
tasks=json.load(sys.stdin)
for t in tasks:
    if t.get('status') in ('blocked','failed'):
        print(f'🚫 {t[\"id\"][:10]} {t.get(\"assignee\",\"?\")} {t.get(\"title\",\"\")[:30]}')
"
```
