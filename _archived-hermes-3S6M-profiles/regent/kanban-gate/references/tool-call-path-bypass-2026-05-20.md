# Hermes Kanban Gate: tool-call hook path and bypass notes (2026-05-20)

Session finding from reviewing how 三省六部 / `kanban_gate` should attach to Hermes tool execution, especially `pre_tool_call`.

## Core pre-tool-call path

Hermes already has a blocking seam before model-requested tool calls execute:

- `run_agent.py`
  - Sequential path: `AIAgent._execute_tool_calls_sequential` parses tool args, calls `hermes_cli.plugins.get_pre_tool_call_block_message(...)`, then either synthesizes a JSON error tool result or proceeds.
  - Concurrent path: `AIAgent._execute_tool_calls_concurrent` pre-checks each tool call before launching worker threads, then calls `_invoke_tool(..., pre_tool_block_checked=True)`.
  - `_invoke_tool` passes registry-dispatched tools to `model_tools.handle_function_call(..., skip_pre_tool_call_hook=True)` to preserve the single-fire invariant.
- `model_tools.py`
  - `handle_function_call(...)` also calls `get_pre_tool_call_block_message(...)` unless `skip_pre_tool_call_hook=True`, so direct callers are still protected.
  - After dispatch it fires `post_tool_call`, then `transform_tool_result`.
- `hermes_cli/plugins.py`
  - `get_pre_tool_call_block_message(...)` invokes all `pre_tool_call` hooks and accepts the first `{"action":"block","message":"..."}` response.

Invariant: `pre_tool_call` should fire exactly once per tool execution. If a caller pre-checks the hook, it must pass `skip_pre_tool_call_hook=True` downstream.

## Shell hook bridge

`agent/shell_hooks.py` can expose shell scripts as `pre_tool_call` hooks. It serializes payloads with:

- `hook_event_name`
- `tool_name`
- `tool_input`
- `session_id`
- `cwd`
- `extra`

For `pre_tool_call`, stdout JSON is normalized from either:

```json
{"action":"block","message":"..."}
```

or Claude-Code-style:

```json
{"decision":"block","reason":"..."}
```

into the canonical Hermes block shape.

## Gateway startup

Gateway startup loads plugins first, then shell hooks via `agent.shell_hooks.register_from_config(load_config(), accept_hooks=False)`, then event hooks. Therefore plugin or shell-hook `pre_tool_call` gates should apply to gateway-originated agent runs once config/profile loading is correct.

## Important bypass found

`PluginContext.dispatch_tool(...)` in `hermes_cli/plugins.py` directly calls `tools.registry.registry.dispatch(...)`. That bypasses `run_agent` and `model_tools.handle_function_call(...)`, so it bypasses `pre_tool_call` unless the plugin author manually calls the gate.

If a plugin slash command can call `ctx.dispatch_tool("kanban_complete", ...)`, native kanban tool execution may evade the kanban gate. Fix options:

1. Change `PluginContext.dispatch_tool(...)` to call `model_tools.handle_function_call(...)` for normal tools, preserving `parent_agent` where required.
2. Or add an explicit `get_pre_tool_call_block_message(...)` check inside `dispatch_tool` before `registry.dispatch(...)`.
3. Add tests proving `ctx.dispatch_tool("kanban_*", ...)` is blocked when the kanban gate hook blocks.

## Argument rewrite limitation

Current `pre_tool_call` contract is block-only. It cannot safely return cleaned/rewritten args. Layer 4 data cleaning in a hook can therefore either:

- reject dirty input, or
- log/suggest a cleaned value,

but cannot mutate the tool call unless Hermes adds a richer decision helper such as `get_pre_tool_call_decision(...)` supporting `allow` / `block` / `rewrite`.

If rewrite support is added, update both sequential and concurrent `run_agent.py` paths plus the direct `model_tools.handle_function_call(...)` path, and preserve the single-fire hook invariant.
