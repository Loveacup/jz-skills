# Kanban Gate Plugin Hook Architecture — 2026-05-20

Session finding: the regent profile now has an in-process `kanban-gate` plugin in addition to the historical CLI wrapper `scripts/kanban_gate.py`.

## Files inspected

- `~/.hermes/profiles/regent/plugins/kanban-gate/__init__.py` — plugin entrypoint; registers a `pre_tool_call` hook.
- `~/.hermes/profiles/regent/plugins/kanban-gate/gate_core.py` — five-layer validation core.
- `~/.hermes/profiles/regent/plugins/kanban-gate/plugin.yaml` — plugin manifest.
- `~/.hermes/profiles/regent/scripts/kanban_gate.py` — older CLI gate script.
- `~/.hermes/hermes-agent/hermes_cli/plugins.py` — Hermes plugin loading and `pre_tool_call` hook dispatch.
- `~/.hermes/hermes-agent/tools/kanban_tools.py` — kanban tool definitions and worker/orchestrator visibility rules.

## Architecture

The plugin registers `ctx.register_hook("pre_tool_call", _safe_handler)` and intercepts agent tool calls whose tool name starts with `kanban_`. It performs gate checks before the actual kanban tool handler runs, so it closes the old gap where `kanban_gate.py` only guarded explicit CLI calls.

Interception observed for: `kanban_create`, `kanban_complete`, `kanban_block`, `kanban_unblock`, `kanban_comment`, `kanban_heartbeat`, `kanban_show`, `kanban_link`, `kanban_list`.

## Five layers in the plugin

1. Permission matrix: command/profile policy in `gate_core.py`.
2. State machine: allowed transition sources checked against current task status.
3. High-risk interception: blocks sensitive transitions such as unsafe `running→done` unless ownership/claim conditions pass.
4. Data cleaning: title/reason/comment sanitization before execution.
5. Audit log: writes JSONL records with `source=plugin-hook` to `~/.hermes/kanban/audit_log.jsonl` unless overridden by `KANBAN_GATE_AUDIT_LOG`.

## Relationship to `scripts/kanban_gate.py`

- `scripts/kanban_gate.py` remains useful as a CLI-side gate and compatibility implementation.
- The plugin is the agent-tool-side hard gate and should be treated as the primary protection for `kanban_*` tool calls.
- Keep the policy tables synchronized; during this session a drift was found between plugin transition rules and the CLI script.

## Drift / follow-up checks

- Compare `ALLOWED_TRANSITION_SOURCES` in plugin with the CLI transition table before changing either one.
- Confirm `hermes plugins list` behavior: it returned no visible plugin output despite regent config enabling `plugins.kanban-gate`; do not infer absence of runtime loading solely from that command.
- Check kanban tool visibility separately from gate policy: `kanban_tools.py` hides tools unless worker env (`HERMES_KANBAN_TASK`) or profile toolset configuration allows them.
- Watchdog exists separately: `~/.hermes/profiles/regent/scripts/kanban-watchdog.py`, scheduled every 1m via regent cron jobs, reports state changes via stdout/Telegram delivery.

## Practical update rule

When improving Kanban governance, update three surfaces together:

1. Plugin hook policy (`plugins/kanban-gate/gate_core.py`).
2. CLI wrapper policy (`scripts/kanban_gate.py`) or explicitly mark it compatibility-only.
3. Skill/SOUL documentation so agents know the plugin is not merely prompt-level guidance.
