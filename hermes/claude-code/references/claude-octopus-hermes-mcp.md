# Claude Octopus as a Hermes MCP bridge

Use this when Hermes needs a less brittle way to command Claude Code than tmux `send-keys` / `capture-pane`, especially for read-only probes, bounded code review, or delegating a task as a normal Hermes tool call.

## Config shape

Hermes MCP server entry:

```yaml
mcp_servers:
  claude_octopus:
    command: npx
    args:
      - -y
      - claude-octopus@latest
    env:
      CLAUDE_SERVER_NAME: claude-octopus
      CLAUDE_TOOL_NAME: cc
      CLAUDE_DESCRIPTION: Claude Code agent via Claude Octopus; supports prompt/reply/timeline/transcript/report.
    timeout: 300
    connect_timeout: 90
```

Expected Hermes tool names after registration:

- `mcp_claude_octopus_cc` — start a Claude Code task
- `mcp_claude_octopus_cc_reply` — continue by `session_id`
- `mcp_claude_octopus_cc_timeline` — inspect workflow runs
- `mcp_claude_octopus_cc_transcript` — fetch a session transcript
- `mcp_claude_octopus_cc_report` — generate an HTML run report

## Verification

Run:

```bash
cd ~/.hermes/hermes-agent
venv/bin/hermes mcp test claude_octopus
```

A successful test reports 5 tools. Then run a bounded read-only smoke test through the registered tool, preferably with:

- `permissionMode: plan`
- `maxTurns: 1`
- `maxBudgetUsd: 0.2` or higher
- explicit prompt: do not edit files, do not run shell commands

Do not set `maxBudgetUsd` too low. A `$0.05` cap can fail before the one-turn probe completes because Claude Code's startup/system-prompt cost can already exceed it.

## Pitfall: Hermes CLI arg forwarding

If `hermes mcp add ... --args -y claude-octopus@latest` is parsed as Hermes flags instead of MCP command args, write the MCP entry into `config.yaml` programmatically or via `hermes config edit`, then verify with `hermes mcp list` and `hermes mcp test claude_octopus`.

This is a config/arg-parsing workaround, not a claim that the MCP server is broken.
