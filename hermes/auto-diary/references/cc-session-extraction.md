# Claude Code Session Extraction

`extract_cc_summary()` in `collect_data.py` scans CC session JSONL files
to extract conversation summaries for diary generation.

## Data Layout

```
~/.claude/projects/
├── -Users-alexcai--hermes-hermes-agent/    # hashed project dir
│   ├── <sessionUuid>.jsonl                  # root session file
│   │   └── subagents/
│   │       ├── agent-<hash>.jsonl           # direct subagent
│   │       └── workflows/
│   │           └── wf_<uuid>/
│   │               └── agent-<hash>.jsonl   # workflow subagent
│   └── <sessionUuid>.jsonl
├── -Users-alexcai--jz-skills/
│   └── ...
└── -Users-alexcai--claude-mem-observer-sessions/
    └── ...
```

**Subagent directory variants** (v3.2 discovery):
- Simple: `{sessionUuid}/subagents/agent-{hash}.jsonl` — direct subagents
- Workflow: `{sessionUuid}/subagents/workflows/wf_{uuid}/agent-{hash}.jsonl` — extra `workflows/` layer
- Parent inference uses `Path(fp).parents` loop (not fixed-depth) to handle both

## JSONL Entry Fields

### User entry (`type: "user"`)

| Field | Type | Example | Used for |
|-------|------|---------|----------|
| `entrypoint` | string | `cli` / `sdk-cli` / `sdk-ts` | Session surface classification |
| `uuid` | string | `ba14e757-...` | Parent-child linking (target of `parentUuid`) |
| `parentUuid` | string or null | `319930f1-...` or `null` | Links to parent session's first user `uuid` |
| `sessionId` | string | `77936ee8-...` | Groups subagents under same orchestrator |
| `userType` | string | `external` | Always external for user messages |
| `version` | string | `2.1.153` | CC CLI version |
| `gitBranch` | string | `main` | Project git branch |
| `cwd` | string | `~/code/jz-skills` | Working directory → project label |
| `message` | dict or str | see below | Contains `content` (text) and `metadata` |

### Other entry types

| Type | Key fields | Used? |
|------|-----------|-------|
| `assistant` | `message.model` | Model detection |
| `last-prompt` | `leafUuid`, `sessionId` | Session identity |
| `ai-title` | `aiTitle` | Auto-generated session title (39/43 coverage) |
| `attachment` | hook metadata, CLAUDE.md content | ❌ filtered |
| `mode` / `permission-mode` | session flags | ❌ |

## Three-Phase Classification (v3.2)

Replaced old text-pattern matching with CC-native metadata:

### Phase 1: Collect metadata
For each candidate JSONL file, read the first user entry (after skip_prefixes filtering) to extract `entrypoint`, `uuid`, `parentUuid`, and `is_subagent`.

### Phase 2: Build relationship graph
- Subagent files (`/subagents/` in path) → child of parent session
- `parentUuid` matching → links child session to the session whose `uuid` == `parentUuid`
- Parent inference: walk `ancestor.parents` from subagent file until `ancestor.name + ".jsonl"` exists in `session_meta`

### Phase 3: Classify
```
has_parent OR has_children  →  "agent-team"
entrypoint starts with "sdk"  →  "program-call"
otherwise                      →  "standalone"
```

**Why not Hermes/Alex distinction**: CC JSONL has NO field distinguishing "Hermes via tmux" from "Alex directly" — both use `entrypoint=cli`. The information is at launch time, not in the session log. The three-type classification based on structure (parent/child relationships + entrypoint surface) is reliable without modifying CC invocation.

## `message` Field Dual Format

The `message` field can be **either** a native dict or a Python `repr` string.
Always use `_parse_cc_message()`:

```python
def _parse_cc_message(msg_raw):
    if isinstance(msg_raw, dict):
        return msg_raw
    if isinstance(msg_raw, str):
        return ast.literal_eval(msg_raw)
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

## Key Pitfalls

| Trap | Symptom | Fix |
|------|---------|-----|
| Subagent `workflows/` subdirectory | Parent not detected, classified as standalone | Use `ancestor.parents` loop, not fixed `parent.parent` |
| `parentUuid` only links first-level chains | Multi-hop agent teams broken | Phase 2 builds full graph, handles chains via `uuid_to_file` map |
| Observer sessions inflate counts | CC session_count includes 14+ observer sessions | Program-call group makes them visible but distinct |
| `entrypoint=cli` for both Hermes and Alex | Can't distinguish caller | By design — structural classification, not caller classification |

## Performance Notes

- May 31 test: 165 candidate files → 111 valid sessions after noise + date filtering
- ~30 seconds for a full day extraction (I/O-bound, ~775 files across 28 projects)
- Three-phase approach adds one extra file-read pass (~5s) but eliminates text-based misclassification
- Observer sessions (Claude-Mem) are included in counts but their topics are filtered
- Project label derived from `cwd` field (first user message); fallback to parent dir name
