# Structured CQI Log Memory Pattern

Use this reference when designing or revising a Skill CQI workflow that currently relies on ad-hoc logs such as `issue-log.jsonl` / `evolution-log.jsonl`, especially when Kanban is used as an execution/control plane.

## Core lesson

For Skill CQI, it is useful to borrow the **memory-hub** idea from older modular plugin designs, but only as a **structured storage protocol**:

- Keep the truth source append-only and auditable.
- Add schema validation, provenance, locking, atomic writes, backups, and versioning.
- Do **not** recreate a plugin/MCP service just for CRUD.
- Do **not** let the memory layer make quality judgments or mutate skill bodies.

## Recommended layering

1. **Truth source: append-only JSONL**
   - `invocation_event.jsonl`
   - `issue_event.jsonl`
   - `proposal_event.jsonl`
   - `audit_result.jsonl`
   - `deployment_event.jsonl`
   - `quality_signal.jsonl`

2. **Manifest / registry JSON**
   - `skill_registry.json`
   - schema version map
   - active deployed-path hash map
   - source/deployed copy mapping

3. **Derived indexes only**
   - SQLite for fast queries and dashboards
   - qmd / Obsidian notes for human reading
   - Kanban cards for current execution state

Derived indexes must be rebuildable. They are not authority.

## Minimal event envelope

Every CQI event should carry a shared envelope:

```json
{
  "event_id": "evt_...",
  "event_type": "issue_event",
  "skill_name": "skill-authoring",
  "skill_version": "3.0.0",
  "source_path": ".../SKILL.md",
  "deployed_path": ".../profiles/regent/skills/.../SKILL.md",
  "source_hash": "sha256:...",
  "requester": "agent|cc|kanban|cron|user",
  "trigger": "manual_review|runtime_failure|scheduled_audit|user_correction",
  "timestamp": "2026-06-04T07:45:00+08:00",
  "session_id": "optional",
  "kanban_card_id": "optional",
  "payload": {}
}
```

## Writer contract

Prefer a small `mem_write`-style script over direct hand-edits for structured logs:

- validate schema before writing
- attach `requester` / provenance fields
- compute and store `source_hash` where relevant
- acquire a file lock
- write to a temp file then `rename()` atomically
- write backup for manifest rewrites
- return explicit exit codes
- on write failure: do not block the user's main task; record/report degraded logging

## Phase placement

- **Phase 1**: schema-first JSONL + manifest + writer script; manual gate remains.
- **Phase 1.5**: Kanban cards may reference log ids but must not become truth source.
- **Phase 2**: SQLite / dashboard / qmd mirrors as derived indexes.
- **Phase 3**: cron health summaries and drift detection over the structured log set.

## Red lines

- Kanban is control plane, not truth source.
- Goal/judge cards do not decide skill quality alone.
- Workers do not directly mutate skill bodies from log data.
- Long-term memory should not receive short-lived CQI event streams.
- The storage layer performs format/provenance integrity, not business judgment.
