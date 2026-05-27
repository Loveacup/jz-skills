# Planner: Check Existing Code Before Designing

> Trigger: any planner/implementer task that proposes new functions or validation layers.

## The Rule

Before designing a new implementation, grep the relevant source tree for existing code with matching purpose. Extend, don't replace.

## Known Existing Implementations (as of 2026-05-25)

These live in `~/.hermes/profiles/regent/scripts/` and are NOT in Hermes core:

| File | Contains | Purpose |
|------|----------|---------|
| `kanban_policy.py` | `VALID_TRANSITIONS`, `is_valid_task_title()`, `append_audit()` | State machine validation, title sanitization, audit logging |
| `kanban_gate.py` | `pre_tool_call` hook, tool categorization | Tool-call interception for Kanban profiles |
| `kanban-watchdog.py` | Auto-discovering watchdog, status transition detection, delivery bridge | No-agent cron that pushes Kanban state changes |
| `kanban-coordinator-poll.py` | 5-min poll, `REPORT:`/`NO_REPORT` sentinel, recovery chain creation | Agent-mode cron for blocked-task coordination |
| `kanban-clearance-reporter.py` | Board-cleared → trigger file → agent cron → `send_message` | Proactive delivery when all chains complete |

## Verification Commands

```bash
# Check what's already in kanban_policy.py
grep -n 'def \|VALID_\|_TRANSITIONS\|is_valid\|append_audit' \
  ~/.hermes/profiles/regent/scripts/kanban_policy.py

# Check kanban_gate.py for existing tool categories
grep -n 'class \|def \|ALLOWED_\|KANBAN_\|CRITICAL_' \
  ~/.hermes/profiles/regent/scripts/kanban_gate.py
```

## Failure Pattern

A planner proposed `VALID_TRANSITIONS` matrix + `sanitize_title()` + `append_audit()` as new implementations. 门下 REJECT-ed: all three already existed in `kanban_policy.py`. The plan also missed the `ready→done` transition in the existing matrix.

## Task Body Template

When creating planner tasks that touch existing scripts, include:

```
先 grep/读 ~/.hermes/profiles/regent/scripts/kanban_policy.py 和 kanban_gate.py
确认是否已有相关实现。在已有代码基础上扩展，不另起炉灶。
```
