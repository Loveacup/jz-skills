# Hermes Session Extraction for Auto-Diary

How `extract_hermes_conversations.py` queries Hermes sessions, and the pitfalls
that led to the v2.0 rewrite.

## Architecture (v2.0)

The script queries Hermes **state.db** SQLite databases — NOT JSON files.

### Data sources

| Source | DB path | Profile label |
|--------|---------|---------------|
| Main Hermes | `$HERMES_HOME/state.db` | `default` |
| Regent / profiles | `$HERMES_HOME/profiles/<name>/state.db` | profile name |

`$HERMES_HOME` defaults to `~/.hermes` when the env var is not set.

### Relevant tables

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,       -- 'telegram', 'cron', 'api_server', 'cli'
    model TEXT,
    started_at REAL NOT NULL,  -- Unix timestamp (UTC)
    message_count INTEGER,
    title TEXT,
    ...
);

-- Messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    role TEXT NOT NULL,         -- 'user', 'assistant', 'tool'
    content TEXT,
    timestamp REAL NOT NULL,
    ...
);
```

### Query pattern

```python
# 1. Find sessions for target date (local time)
SELECT id, source, model, started_at, message_count, title
FROM sessions
WHERE date(started_at, 'unixepoch', 'localtime') = ?
ORDER BY started_at ASC

# 2. Extract user messages per session (for topic hints)
SELECT role, content FROM messages
WHERE session_id = ? ORDER BY timestamp ASC
```

### Topic extraction

- Takes first 5 user messages per session
- Skips system prefixes: `[System note:`, `[Replying to:`, `[IMPORTANT:`, `[CONTEXT COMPACTION`
- Uses first line of each message, truncated to 80 chars
- These are RAW HINTS — the agent generalizes during diary writing

### Profile aggregation

- `default` profile sessions → "Hermes / default" section
- All non-default profiles → collapsed into "太子 / 三省六部工作概览"
- `_interesting_topics()` applies a second skip-prefix filter for kanban noise

## Why v1.0 (JSON) broke

Hermes migrated session storage from individual `session_*.json` files
to a centralized `state.db` SQLite database in May 2026.

| Approach | Status |
|----------|--------|
| v1.0: read `~/.hermes/sessions/session_*.json` | ⛔ JSON files stale (latest: 2026-05-25) |
| v2.0: query `state.db` SQLite | ✅ live data (2026-05-27 sessions included) |

## The `$HOME` Profile Pitfall

Scripts running under non-default Hermes profiles have `$HOME` set to the
profile's home directory (e.g., `/Users/x/.hermes/profiles/regent/home`).
This causes THREE failure modes:

1. **`Path("~/...").expanduser()`** → resolves under profile home, not real home
2. **`Path.home()`** → same problem — uses `$HOME` env var
3. **Shell `~` in subprocess commands** → expanded by shell using `$HOME`

**Fix**: Use absolute paths (`~/...`) for any path that lives in the
real user home, not the profile home. This includes the Obsidian vault,
`~/.hermes/skills/`, and any other shared resources.

### Affected paths in auto-diary

| Variable | Wrong | Right |
|----------|-------|-------|
| `vault_root` | `Path("~/Documents/Obsidian/AlexCai")` | `Path("~/Documents/Obsidian/AlexCai")` |
| `diary_path` | same pattern | same fix |
| `$HOME/.hermes/skills/...` in shell | `~/.hermes/...` | `~/.hermes/...` |
