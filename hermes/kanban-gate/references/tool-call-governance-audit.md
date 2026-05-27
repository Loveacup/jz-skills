# Tool-call governance audit notes

Use this reference when hardening Regent / 三省六部 tool calls beyond prompt-level rules.

## Durable findings

- `pre_tool_call` is the right first-class interception seam for model-emitted tool calls. A plugin can return `{ "action": "block", "message": "..." }` to veto execution before registry dispatch.
- Native `kanban_*` tools call Hermes Kanban internals directly; CLI-only wrappers such as `scripts/kanban_gate.py` do not protect those calls unless a `pre_tool_call` plugin also gates them.
- A robust governance design should be layered:
  1. **Prompt / SOUL**: role identity and “do not bypass” reminders.
  2. **Toolset visibility**: only expose tools needed by a profile.
  3. **pre_tool_call plugin**: block high-risk model tool calls before dispatch.
  4. **CLI gate**: protect `hermes kanban ...` / terminal-driven operations.
  5. **Shared policy module**: one permission matrix + one state machine reused by plugin, CLI, diagnostics, and watchdog.
  6. **DB invariants**: only for transitions that must never be written invalidly; avoid breaking dispatcher internals without a clear actor model.
- Avoid multiple drifting state machines across SOUL.md, plugin gate, CLI gate, and Kanban DB. Prefer a shared policy module such as `hermes_cli/kanban_policy.py`.
- Mutation should generally fail closed when actor/profile/status is unknown; read-only operations may fail open.

## High-risk tools that need gates beyond Kanban

Prioritize hard/semihard gates for persistent or external side-effect tools:

- `cronjob`: create/update/resume/remove, especially high-frequency or visible notifications.
- `send_message`: explicit targets, group/DM/cross-platform sending, worker-originated messages, representing the user.
- `memory`: writes/deletes/replacements; require durable-fact classification and profile isolation.
- `terminal`, `patch`, `write_file`: protect control-plane paths such as profile config, SOUL.md, plugins, cron scripts, memory files, provider/gateway/tool config.
- `skill_manage`: governance skill edits should include reason and verification.
- `delegate_task`: require budget/timeout/acceptance criteria for complex or recursive delegation.

Do not hard-gate ordinary read-only discovery (`read_file`, `search_files`, `skill_view`, `kanban_show/list`) unless privacy or path scope requires it; over-gating read-only tools harms execution.

## Known bypass to check

`PluginContext.dispatch_tool(...)` can call `registry.dispatch(...)` directly. If a plugin dispatches tools internally, ensure it also goes through `get_pre_tool_call_block_message(...)` or `handle_function_call(...)`; otherwise it may bypass `pre_tool_call` policy.

## Watchdog direction

A Regent watchdog should not be a status spammer. It should stay silent unless it detects blocked/failed/high-risk/stale/dispatcher-crash/hook-disabled/fan-in-complete events. Prefer diagnostics + severity filtering over every status transition.