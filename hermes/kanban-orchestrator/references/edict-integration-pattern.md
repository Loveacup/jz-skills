# Edict Integration Pattern — Governance Engine on Hermes

> How to port edict's (github.com/cft0808/edict, 15.6k⭐) hard-enforcement governance engine to Hermes Kanban.

## Core Architecture

edict's key innovation: a **single CLI governance gate** (`kanban_update.py`, ~800 lines) that ALL agents must route through. Agents never touch the data store directly — they call `python3 scripts/kanban_update.py create ...` and the script enforces rules before writing.

## Five-Layer Hard Enforcement

| Layer | Mechanism | Hermes Equivalent |
|-------|-----------|-------------------|
| Permission matrix | `AGENT_POLICY` → `_check_permission()` → `sys.exit(1)` | `ALLOWED_DISPATCH.yaml` + validator |
| State machine | `_VALID_TRANSITIONS` → `cmd_state()` rejects illegal jumps | `kanban_gate.py` state validator |
| High-risk intercept | `HIGH_RISK_TRANSITIONS` → `PendingConfirm` state | `confirm approve/reject` flow |
| Data cleaning | `_sanitize_title()` 7-step pipeline | `task_spec_cleaner.py` 5-stage |
| Audit log | `_append_audit()` atomic JSON write | Hindsight retain or file |

## Porting to Hermes

The `kanban_gate.py` project (in progress, session 2026-05-19) creates the same governance gate:

1. **Step 1 — Spec**: Define state machine, permission matrix, cleaning rules, command mapping
2. **Step 2 — Review**: 门下省 validates spec against Hermes native Kanban capabilities
3. **Step 3 — Implement**: Single-file `kanban_gate.py` with 5-layer validation, calling `hermes kanban` CLI for actual operations
4. **Step 4 — Audit**: 御史台 checks state consistency, permission completeness
5. **Step 5 — Test**: Integration tests for create/state/flow/done/block/confirm/progress
6. **Step 6 — Archive**: 史馆 records the governance engine

## Key Differences from edict

| Aspect | edict | Hermes kanban_gate |
|--------|-------|-------------------|
| Data store | JSON file (tasks_source.json) | SQLite via `hermes kanban` CLI |
| State model | Custom 9-state | Hermes native: todo/ready/running/blocked/done |
| Agent invocation | `python3 scripts/kanban_update.py create ...` | `python3 scripts/kanban_gate.py create ...` |
| Audit storage | `data/audit_log.json` | Hindsight or local file |
| Deployment | Part of OpenClaw repo | Standalone script in regent profile |

## Hermes State Machine Mapping

edict states → Hermes equivalents:

| edict State | Hermes State | Transition via |
|-------------|-------------|----------------|
| Pending | todo | `kanban_create` |
| Taizi | (regent handles) | — |
| Zhongshu | running (planner) | `kanban claim` |
| Menxia | running (reviewer) | `kanban claim` |
| Assigned | ready | dispatcher auto-promotes |
| Doing | running | `kanban claim` |
| Review | running (auditor) | `kanban claim` |
| Done | done | `kanban complete` |
| Blocked | blocked | `kanban block` |
| Cancelled | archived | `kanban archive` |

Note: edict's `PendingConfirm` (high-risk gate) has no direct Hermes equivalent — implemented as gate-internal logic in kanban_gate.py.

## Pitfalls Discovered

1. **State machine mismatch**: edict's state machine allows transitions Hermes doesn't support (e.g., blocked→todo). Must design gate state machine around Hermes native capabilities, not edict's.

2. **Multi-parent blocking**: When a downstream task is linked to both an old blocked parent and a new review, it stays stuck in todo. Always `kanban unlink` the old blocked parent.

3. **Worker self-block with stale references**: Workers may complete work but self-block citing archived task IDs from earlier chains. Pattern: unblock → complete (work was done, reference was stale).
