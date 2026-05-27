# CLI Flags — Complete Reference

## Session & Environment

| Flag | Effect |
|------|--------|
| `-p, --print` | Non-interactive one-shot mode |
| `-c, --continue` | Resume most recent conversation |
| `-r, --resume <id>` | Resume specific session by ID or name |
| `--fork-session` | New session ID instead of reusing original |
| `--session-id <uuid>` | Use specific UUID |
| `--no-session-persistence` | Don't save session to disk (print only) |
| `--add-dir <paths...>` | Grant access to additional directories |
| `-w, --worktree [name]` | Isolated git worktree at `.claude/worktrees/<name>` |
| `--tmux` | Create tmux session for worktree |
| `--ide` | Auto-connect to IDE on startup |
| `--chrome` / `--no-chrome` | Enable/disable Chrome integration |
| `--from-pr [number]` | Resume session linked to GitHub PR |
| `--file <specs...>` | File resources at startup |

## Model & Performance

| Flag | Effect |
|------|--------|
| `--model <alias>` | `sonnet`, `opus`, `haiku`, or full name |
| `--effort <level>` | `low`, `medium`, `high`, `max`, `auto` |
| `--max-turns <n>` | Limit agentic loops (print only) |
| `--max-budget-usd <n>` | Cap API spend (print only) |
| `--fallback-model <model>` | Auto-fallback on overload (print only) |
| `--betas <betas...>` | Beta headers (API key users) |

## Permission & Safety

| Flag | Effect |
|------|--------|
| `--dangerously-skip-permissions` | Auto-approve ALL tool use |
| `--allow-dangerously-skip-permissions` | Enable bypass as option |
| `--permission-mode <mode>` | `default`, `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions` |
| `--allowedTools <tools...>` | Whitelist tools |
| `--disallowedTools <tools...>` | Blacklist tools |
| `--tools <tools...>` | Override built-in tools |

## Output & Input Format

| Flag | Effect |
|------|--------|
| `--output-format <fmt>` | `text`, `json`, `stream-json` |
| `--input-format <fmt>` | `text` or `stream-json` |
| `--json-schema <schema>` | Force structured JSON output |
| `--verbose` | Full turn-by-turn output |
| `--include-partial-messages` | Include partial chunks (stream-json) |
| `--replay-user-messages` | Re-emit user messages (bidirectional) |

## System Prompt & Context

| Flag | Effect |
|------|--------|
| `--append-system-prompt <text>` | Add to default system prompt |
| `--append-system-prompt-file <path>` | Add file to system prompt |
| `--system-prompt <text>` | Replace entire system prompt |
| `--bare` | Skip hooks, plugins, MCP, CLAUDE.md, OAuth |
| `--agents '<json>'` | Define custom subagents as JSON |
| `--mcp-config <path>` | Load MCP servers from JSON |
| `--strict-mcp-config` | Only use specified MCP config |
| `--settings <file-or-json>` | Load additional settings |
| `--plugin-dir <paths...>` | Load plugins for this session |
| `--disable-slash-commands` | Disable all skills/slash commands |
| `--teammate-mode <mode>` | Agent team display: `auto`, `in-process`, `tmux` |
| `--brief` | Enable SendUserMessage tool |

## Debugging

| Flag | Effect |
|------|--------|
| `-d, --debug [filter]` | Enable debug logging |
| `--debug-file <path>` | Write debug logs to file |

## Tool Name Syntax

```
Read                    # All file reading
Edit                    # File editing (existing)
Write                   # File creation (new)
Bash                    # All shell commands
Bash(git *)             # Only git commands
Bash(git commit *)      # Only git commit
Bash(npm run lint:*)    # Pattern matching
WebSearch               # Web search
WebFetch                # Web page fetching
mcp__<server>__<tool>   # Specific MCP tool
```
