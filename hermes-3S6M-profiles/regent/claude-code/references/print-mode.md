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

## Session Continuation

```bash
# Start
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

## Bare Mode (CI/Scripting)

```bash
claude --bare -p 'Run all tests and report failures' --allowedTools 'Read,Bash' --max-turns 10
```

Skips hooks, plugins, MCP, CLAUDE.md. Requires `ANTHROPIC_API_KEY`.

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
- `--max-budget-usd` for cost caps (minimum ~$0.05 for cache creation)
- `--effort low` for simple tasks
- `--model haiku` for cheap tasks
- `--no-session-persistence` in CI
