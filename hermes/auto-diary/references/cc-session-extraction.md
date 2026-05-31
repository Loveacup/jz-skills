# Claude Code Session Extraction

`extract_cc_summary()` in `collect_data.py` scans CC session JSONL files
to extract conversation summaries for diary generation.

## Data Layout

```
~/.claude/projects/
├── -Users-alexcai--hermes-hermes-agent/   # hashed project dir
│   ├── <uuid>.jsonl                        # one file per session
│   └── <uuid>.jsonl
├── -Users-alexcai--jz-skills/
│   └── ...
└── agent-<hash>/
    └── ...
```

## JSONL Entry Types

| Type | Content | Used? |
|------|---------|-------|
| `user` | User message, `message` field → parse for `content` | ✅ topic extraction |
| `assistant` | Model response, `message` field → parse for `model` name | ✅ model detection |
| `attachment` | Session metadata (CLAUDE.md, hooks) | ❌ |
| `queue-operation` | enqueue/dequeue events | ❌ |
| `last-prompt` | Leaf UUID tracking | ❌ |

## `message` Field Dual Format

The `message` field can be **either** a native dict or a Python `repr` string.
Always use `_parse_cc_message()`:

```python
def _parse_cc_message(msg_raw):
    if isinstance(msg_raw, dict):
        return msg_raw
    if isinstance(msg_raw, str):
        return ast.literal_eval(msg_raw)  # may raise ValueError/SyntaxError
    return {}
```

The `content` field within is also dual-format:
- **List**: `[{"type": "text", "text": "..."}, ...]` — newer CC versions
- **String**: plain text — older CC versions / agent-injected messages

Use `_extract_cc_text()` to handle both.

## Noise Filtering

CC JSONL contains many internal/system messages that must be excluded
from topic extraction. `skip_prefixes` in `extract_cc_summary()`:

### Cross-tool system messages (from Hermes)
- `[System note:`
- `[Replying to:`
- `[IMPORTANT:`
- `[CONTEXT COMPACTION`
- `Your task is to`

### CC internal wrappers
- `<local-command-caveat>`
- `<command-name>`
- `<command-message>`
- `<local-command-stdout>`

### Observer tool (Claude-Mem)
- `<observed_from_primary_session>`
- `You are a Claude-Mem`
- `You are an AI assistant`
- `You are a specialized`

### CC mode-switch banners
- `--- MODE SWITCH:`
- `[Request interrupted`

## Date Filtering Strategy

Two-phase to handle 775+ JSONL files efficiently:

1. **Pre-filter**: `find ~/.claude/projects/ -name "*.jsonl" -newermt "YYYY-MM-DD"` — filters by file mtime (fast, filesystem-level)
2. **Validate**: parse first user message timestamp within each file, convert to Asia/Shanghai, check date matches target

Sessions where mtime matches but content timestamp doesn't are silently skipped
(e.g., files touched by post-processing outside the session window).

## Performance Notes

- May 31 test: 165 candidate files → 111 valid sessions after noise + date filtering
- ~30 seconds for a full day extraction (I/O-bound, ~775 files across 28 projects)
- Observer sessions (Claude-Mem) are included in counts but their topics are filtered
- Project label derived from `cwd` field (first user message); fallback to parent dir name
