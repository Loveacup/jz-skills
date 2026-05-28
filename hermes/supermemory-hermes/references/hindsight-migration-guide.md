# Hindsight → Supermemory Migration Guide

Complete migration procedure from Hindsight to Supermemory. Referenced from `supermemory-hermes` SKILL.md.

## Overview

Hindsight has been **fully retired** as of Phase 1 (2026-05-29). All physical data has been cleaned. This reference is kept as a historical record of the migration procedure.

## Migration Steps

### 1. Extract existing memories

Current entries are visible in the system prompt under "MEMORY (your personal notes)" and "USER PROFILE (who the user is)". Each entry is a compact declarative fact.

### 2. Bulk-add via Python SDK

```python
from supermemory import Supermemory
import os

with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        if "SUPERMEMORY_API_KEY" in line:
            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

client = Supermemory(api_key=api_key)

memories = [
    ("Hermes: main deepseek-v4-pro, fallback kimi-k2.6", {"category": "environment"}),
    ("Prefers concise Chinese, plan-first workflow", {"category": "user_preference"}),
    # ... all existing entries
]

for content, metadata in memories:
    client.add(content=content, container_tag="hermes", metadata=metadata)
```

### 3. Verification

```python
results = client.search.memories(q="hermes", container_tag="hermes")
```

### 4. Cleanup

After migration verified:
```bash
rm -rf ~/.hermes/hindsight/
rm -rf ~/.hermes/profiles/regent/hindsight/
rm -rf ~/.hermes/profiles/regent/home/.hindsight/
rm -f ~/.hermes/logs/hindsight-*.log
rm -rf ~/.hermes/profiles/regent/home/.pg0/instances/hindsight-embed-*
```

**IMPORTANT**: Keep schema documents for historical reference:
- `skills/autonomous-ai-agents/hermes-agent/references/hindsight-*.md`
- `kanban/workspaces/t_*/hindsight-*`
- Backups under `~/.hermes/backups/hindsight-pilot-*`

### PITFALLS

1. **SDK not installed**: `ModuleNotFoundError` → install with venv python3 -m pip.
2. **Positional args to `client.add`**: Always keyword: `client.add(content="text", container_tag="tag")`.
3. **Token-sensitive strings**: Use string concatenation instead of f-strings for API keys to avoid sanitizer issues.
4. **`client.search.memories()` keyword-only**: Use `q=` parameter explicitly.
