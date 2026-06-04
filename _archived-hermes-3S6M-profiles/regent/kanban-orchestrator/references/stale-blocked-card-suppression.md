# Stale Blocked Card Suppression — Watchdog Heuristic

> Added 2026-05-25 after two false A-level alerts from superseded v1 blocked cards.

## Problem

When a reviewer REJECTs a plan (`kanban_block verdict=reject`), the governance creates a
revision chain (v2, v3). The **original blocked reviewer card stays blocked** on the board
as audit trail. The watchdog sees `blocked` status, counts minutes since block, and once
`BLOCKED_ESCALATE_MINUTES` (30 min) passes, fires an A-level "needs Emperor decision" alert.

But the v1 card is **stale** — v2/v3 chain already resolved the blockers and is running/done.
The watchdog has no context to distinguish stale blocks from genuine blocks.

## Fix: `_is_blocked_superseded()` heuristic

Added to `kanban-watchdog.py` (v3 → v3.1). Before escalating a blocked card to A-level,
check if a newer version chain exists in `running`/`done` status.

### Heuristic

1. Strip trailing role suffix from blocked card title (`-review`, `-plan`, `-shangshu`, etc.)
2. Strip any existing `-vN` suffix from the base
3. Check all tasks for a card with same base prefix + `-v{N}` (N >= 2) in `running`/`done`
4. If found → downgrade to C-level (silent); if not → normal A-level escalation

### Tested scenarios

| Scenario | Blocked card | Board state | Result |
|----------|-------------|-------------|--------|
| S1 | `edict-demo-recompare-plan-review` (v1 blocked) | `edict-demo-recompare-plan-v3-hanlinyuan` (done) | **Superseded** → silent |
| S2 | `p0-implement-plan-review` (v1 blocked) | `p0-implement-plan-v2-review` (done) | **Superseded** → silent |
| S3 | `genuine-blocked-review` (blocked) | No v2+ variant exists | NOT superseded → A-level alert |
| S4 | `p0-implement-plan-v2-review` (v2 blocked) | `p0-implement-plan-review` (v1 done) | NOT superseded (v2 is the newest) |

### Integration

The function is called inside `grade_event()` before the A-level escalation path:

```python
if blocked_minutes > BLOCKED_ESCALATE_MINUTES:
    if all_tasks and _is_blocked_superseded(task, all_tasks):
        return ('C', f'{role} · {label}  已取代', '旧链 blocked 卡，新版链已取代，静默')
    return ('A', ...)  # genuine block → escalate
```

## Related

- `_ROLE_SUFFIXES` list in watchdog defines which title suffixes are stripped
- `references/blocked-final-review-mirror-sync.md` for the mirror-drift blocked-review pattern
- `references/coordinator-sentinel-parsing.md` for the other watchdog/coordinator parsing fix
