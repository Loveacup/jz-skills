# Print Mode — Deep Dive

## JSON Output

```bash
claude -p 'Analyze auth.py for security issues' --output-format json --max-turns 5
```

Returns:
```json
{
  "type": "result", "subtype": "success",
  "result": "The analysis text...",
  "session_id": "75e2167f-...",
  "num_turns": 3, "total_cost_usd": 0.0787, "duration_ms": 10276,
  "stop_reason": "end_turn", "terminal_reason": "completed",
  "usage": {"input_tokens": 5, "output_tokens": 603},
  "modelUsage": {"claude-sonnet-4-6": {"costUSD": 0.078, "contextWindow": 200000}}
}
```

`subtype`: `success`, `error_max_turns`, `error_budget`.

## Streaming JSON

```bash
claude -p "Write a summary" --output-format stream-json --verbose --include-partial-messages
```

Filter for live text:
```bash
claude -p "Explain X" --output-format stream-json --verbose --include-partial-messages | \
  jq -rj 'select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text'
```

## Piped Input

```bash
cat src/auth.py | claude -p 'Review for bugs' --max-turns 1
cat src/*.py | claude -p 'Find all TODO comments' --max-turns 1
git diff HEAD~3 | claude -p 'Summarize these changes' --max-turns 1
```

## JSON Schema for Structured Extraction

```bash
claude -p 'List all functions in src/' \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}' \
  --max-turns 5
```

Parse `structured_output` from the JSON result.

⚠️ Structured output may consume an extra tool-use turn. Do not set `--max-turns 1` for JSON Schema probes; it can stop with `subtype=error_max_turns`, `stop_reason=tool_use` before producing `structured_output`. For smoke tests, use at least `--max-turns 3` and a budget that covers cache creation (for example `$0.45` on the user's current Opus route).

## Session Continuation

```bash
# Start — do NOT include --no-session-persistence if you plan to resume later
claude -p 'Start refactoring the database layer' --output-format json --max-turns 10 > /tmp/session.json

# Resume
claude -p 'Continue and add connection pooling' \
  --resume $(cat /tmp/session.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])') \
  --max-turns 5

# Or resume most recent in same directory
claude -p 'What did you do last time?' --continue --max-turns 1

# Fork (new ID, keeps history)
claude -p 'Try a different approach' --resume <id> --fork-session --max-turns 10
```

⚠️ `--no-session-persistence` and `--resume` are mutually opposed workflows. Print-mode JSON still returns a `session_id` when persistence is disabled, but a later `--resume <that-id>` can fail with `No conversation found with session ID`. Use `--no-session-persistence` for one-shot CI/smoke tests only; omit it for any session you intend to continue.

## Bare Mode (CI/Scripting)

```bash
claude --bare -p 'Run all tests and report failures' --allowedTools 'Read,Bash' --max-turns 10
```

Skips hooks, plugins, MCP, CLAUDE.md. Requires `ANTHROPIC_API_KEY`.

⚠️ Bare mode does not necessarily reuse the normal Claude Code first-party `claude.ai` login. If a normal `claude -p` succeeds but `claude --bare -p ...` returns `Not logged in · Please run /login`, treat that as a bare-mode auth/config issue, not a print-mode failure. Configure `ANTHROPIC_API_KEY` or the bare-mode auth path before using it in CI.

To selectively load context in bare mode:
| To load | Flag |
|---------|------|
| System prompt additions | `--append-system-prompt "text"` or `--append-system-prompt-file path` |
| Settings | `--settings <file-or-json>` |
| MCP servers | `--mcp-config <file-or-json>` |
| Custom agents | `--agents '<json>'` |

## Fallback Model

```bash
claude -p 'task' --fallback-model haiku --max-turns 5
```

Auto-falls back when default model is overloaded (print mode only).

## Cost Control

- `--max-turns 5-10` for most tasks
- `--max-budget-usd` for cost caps (minimum ~$0.05 for cache creation; on the user's Opus 4.8 route even tiny prompts have exceeded `$0.2`, so use `$0.35+` for one-shot smoke tests and `$0.45+` for JSON Schema probes unless explicitly optimizing cost)
- `--effort low` for simple tasks
- `--model haiku` for cheap tasks, but verify `modelUsage` in JSON output — local routing/config may still show Opus usage despite the alias
- `--no-session-persistence` in CI when you will not resume the session
