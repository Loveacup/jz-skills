# Configuration and Extension

## Settings Hierarchy (highest → lowest)
1. CLI flags — override everything
2. `.claude/settings.local.json` — personal, gitignored
3. `.claude/settings.json` — project, git-tracked
4. `~/.claude/settings.json` — global

## Permissions in Settings

```json
{
  "permissions": {
    "allow": ["Bash(npm run lint:*)", "WebSearch", "Read"],
    "ask": ["Write(*.ts)", "Bash(git push*)"],
    "deny": ["Read(.env)", "Bash(rm -rf *)"]
  }
}
```

## Memory Files (CLAUDE.md)

| Level | Path | Scope |
|-------|------|-------|
| Global | `~/.claude/CLAUDE.md` | All projects |
| Project | `./CLAUDE.md` | Git-tracked |
| Local | `.claude/CLAUDE.local.md` | Gitignored |

**Be specific:** "Use 2-space indentation for JS" > "Write good code".

### Rules Directory (Modular)
- `.claude/rules/*.md` — project rules, git-tracked
- `~/.claude/rules/*.md` — personal, global

### Auto-Memory
Claude stores learned context in `~/.claude/projects/<project>/memory/`. Limit: 25KB or 200 lines per project.

## Custom Subagents

Define in `.claude/agents/` (project), `~/.claude/agents/` (personal), or `--agents` (session).

```markdown
# .claude/agents/security-reviewer.md
---
name: security-reviewer
description: Security-focused code review
model: opus
tools: [Read, Bash]
---
You are a senior security engineer. Review code for injection, auth flaws, secrets, unsafe deserialization.
```

Invoke: `@security-reviewer review the auth module`

## Hooks (8 Event Types)

Configure in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write(*.py)",
      "hooks": [{"type": "command", "command": "ruff check --fix $CLAUDE_FILE_PATHS"}]
    }],
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'rm -rf'; then echo 'Blocked!' && exit 2; fi"}]
    }]
  }
}
```

| Hook | When | Use |
|------|------|-----|
| `UserPromptSubmit` | Before processing prompt | Input validation |
| `PreToolUse` | Before tool execution | Security gates (exit 2 = block) |
| `PostToolUse` | After tool finishes | Auto-format, lint |
| `Notification` | Permission requests / input waits | Desktop alerts |
| `Stop` | When Claude finishes response | Completion logging |
| `SubagentStop` | When subagent completes | Orchestration |
| `PreCompact` | Before context cleared | Backup transcripts |
| `SessionStart` | Session begins | Load dev context |

Environment: `CLAUDE_PROJECT_DIR`, `CLAUDE_FILE_PATHS`, `CLAUDE_TOOL_INPUT`.

## MCP Integration

```bash
claude mcp add -s user github -- npx @modelcontextprotocol/server-github
claude mcp add -s local postgres -- npx @anthropic-ai/server-postgres --connection-string postgresql://localhost/mydb
```

| Scope | Storage |
|-------|---------|
| `-s user` | `~/.claude.json` |
| `-s local` | `.claude/settings.local.json` (gitignored) |
| `-s project` | `.claude/settings.json` (git-tracked) |

Print/CI: `claude --bare -p 'query' --mcp-config mcp-servers.json --strict-mcp-config`

## Environment Variables

| Variable | Effect |
|----------|--------|
| `ANTHROPIC_API_KEY` | API key (alternative to OAuth) |
| `CLAUDE_CODE_EFFORT_LEVEL` | Default effort |
| `MAX_THINKING_TOKENS` | Cap thinking tokens (0 = disable) |
| `MAX_MCP_OUTPUT_TOKENS` | Cap MCP output |
| `CLAUDE_CODE_NO_FLICKER=1` | Alt-screen rendering |

## Syncing Between Macs

1. Probe: `claude --version`, `~/.claude/skills`, `~/.claude/plugins`, `~/.claude/settings.json`, `~/.agents/skills`
2. Backup: `~/.claude/backups/hermes-sync-<timestamp>/`
3. rsync with `--delete`: skills, plugins, settings (merge, don't overwrite)
4. Verify: `claude plugin list`, count resolvable skills, check for broken symlinks

⚠️ Pitfall: rsync `--delete` on broken symlinks may fail. Resolve by syncing symlink targets first.
