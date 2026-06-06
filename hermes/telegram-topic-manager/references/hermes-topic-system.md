# Hermes Agent — Topic Management Features

> **Source:** Hermes Agent documentation — `website/docs/user-guide/messaging/telegram.md`  
> **Last checked:** 2026-06-06

Hermes has three topic-related features for session isolation and skill binding.

---

## A. Private Chat Topics (`dm_topics`)

Operator-curated topic list in `config.yaml`. Hermes creates and manages these topics automatically.

### Configuration

```yaml
platforms:
  telegram:
    extra:
      dm_topics:
      - chat_id: 7931997806
        topics:
        - name: General
          icon_color: 7322096
        - name: Website
          icon_color: 9367192
        - name: Research
          icon_color: 16766590
          skill: arxiv
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Topic display name |
| `icon_color` | No | Telegram icon color code (integer, 6 options) |
| `icon_custom_emoji_id` | No | Custom emoji ID for topic icon |
| `skill` | No | Skill to auto-load on new sessions |
| `thread_id` | No | **Auto-populated** — don't set manually |

### How It Works

1. On gateway startup, Hermes calls `createForumTopic` for each topic without a `thread_id`
2. `thread_id` is saved back to `config.yaml` automatically — subsequent restarts skip API calls
3. Each topic → isolated session: `agent:main:telegram:dm:{chat_id}:{thread_id}`
4. Messages in each topic have independent history, memory, and context

### Prerequisites

Before adding topics to config, the user must enable Topics mode in the DM:
1. Open private chat with the bot
2. Tap bot's name → chat info
3. Enable **Topics** toggle

Without this, Hermes logs `The chat is not a forum` on startup and skips topic creation.

### Root DM Handling

- Default: root DM messages are processed normally
- `ignore_root_dm: true` → root DM becomes lobby (system commands only: `/start`, `/help`, `/status`, etc.)
- Only affects users with entries in `dm_topics`

### Skill Binding

Topics with `skill` field auto-load that skill when a new session starts. Equivalent to typing `/skill-name` at conversation start.

### Auto-Discovery

Topics created outside config (e.g., manual API call) are discovered when `forum_topic_created` service message arrives. Config additions during gateway runtime are picked up on next cache miss.

---

## B. Multi-Session DM Mode (`/topic`)

User-driven, no-config mode. The user flips it on with `/topic`, then creates topics freely via Telegram UI.

### `/topic` Subcommands

| Command | Context | Effect |
|---------|---------|--------|
| `/topic` | Root DM (first time) | Enable multi-session mode: checks `getMe()`, creates System topic, shows unlinked sessions |
| `/topic` | Root DM (already enabled) | Show status: unlinked sessions available for restore |
| `/topic` | Inside a topic | Show current topic's session binding (title + session ID) |
| `/topic help` | Any | Inline usage |
| `/topic off` | Root DM | Disable mode, clear all `(thread_id → session_id)` bindings |
| `/topic <session-id>` | Inside a topic | Restore a previous Telegram session into current topic |

Only authorized users (via `TELEGRAM_ALLOWED_USERS` / platform auth config) can run `/topic`.

### Prerequisites

**BotFather → Threads Settings**:
1. Turn on **Threaded Mode** (enables `has_topics_enabled`)
2. **Do not** disable users creating topics (keeps `allows_users_to_create_topics` on)

When `/topic` first runs, Hermes verifies both flags via `getMe()`. Either off → sends BotFather screenshot + stops.

### Activation Flow

From root DM, send `/topic`. Hermes:
1. Checks `getMe().has_topics_enabled` + `allows_users_to_create_topics`
2. Enables multi-session topic mode for this DM
3. Creates + pins a **System** topic (best-effort)
4. Replies with unlinked Telegram sessions list

After activation:
- Root DM = **lobby**: normal prompts rejected with guidance → use All Messages
- System commands (`/status`, `/sessions`, `/usage`, `/help`, etc.) still work in root
- Root-lobby reminders rate-limited: 1 per 30 seconds per chat

### Creating Topics (End-User)

1. Open bot DM → tap **All Messages** → send any message
2. Telegram creates a new topic
3. Hermes responds inside that topic → standalone session
4. After first exchange, Hermes auto-renames topic to match session title

### Auto-Rename

Hermes renames the Telegram topic to match the session title after the first exchange. To disable:
```yaml
gateway:
  platforms:
    telegram:
      extra:
        disable_topic_auto_rename: true
```

DM topics declared in `extra.dm_topics` are **never auto-renamed** — operator-chosen names are preserved.

### Under the Hood

- Persisted to `state.db` tables: `telegram_dm_topic_mode` + `telegram_dm_topic_bindings`
- `ON DELETE CASCADE` on `session_id` → pruning a session clears its binding
- Migration is **opt-in**: runs on first `/topic`, not on gateway startup
- Each inbound DM message looks up `(chat_id, thread_id)` → routes to bound session
- `/new` inside a topic rewrites binding to new session ID
- General topic (pinned top) in forum-enabled DM = root lobby

### Disabling

```
/topic off
```

Flips mode off, clears bindings. Existing topics not deleted — just stop being gated as independent sessions.

### Manual Cleanup

```bash
sqlite3 ~/.hermes/state.db \
  "UPDATE telegram_dm_topic_mode SET enabled = 0 WHERE chat_id = '<chat_id>';
   DELETE FROM telegram_dm_topic_bindings WHERE chat_id = '<chat_id>';"
```

### DM Topics vs Multi-Session Mode

| | `dm_topics` (config-driven) | `/topic` (user-driven) |
|---|---|---|
| Who activates | Operator, in `config.yaml` | End user, via `/topic` |
| Topic list | Fixed set in config | User creates/deletes freely |
| Topic names | Chosen by operator | User-chosen; auto-renamed to session title |
| Root DM | Normal chat (lobby if `ignore_root_dm`) | System lobby (non-command messages rejected) |
| Use case | Permanent workspaces + optional skill binding | Ad-hoc parallel sessions |
| Persistence | `extra.dm_topics` in config | SQLite tables in `state.db` |

Both features can coexist on the same bot.

---

## C. Group Forum Topic Skill Binding (`group_topics`)

For supergroups with Topics mode enabled. Auto-loads skills in specific forum topics.

### Configuration

```yaml
platforms:
  telegram:
    extra:
      group_topics:
      - chat_id: -1001234567890
        topics:
        - name: Engineering
          thread_id: 5
          skill: software-development
        - name: Research
          thread_id: 12
          skill: arxiv
        - name: General
          thread_id: 1
          # No skill — general purpose
```

| Field | Required | Description |
|-------|----------|-------------|
| `chat_id` | Yes | Supergroup numeric ID (`-100` prefix) |
| `name` | No | Human-readable label (informational) |
| `thread_id` | Yes | Telegram forum topic ID |
| `skill` | No | Skill to auto-load on new sessions |

### How It Works

1. Message arrives in mapped group topic → look up `(chat_id, thread_id)`
2. Matching entry with `skill` → auto-loads that skill
3. Topics without `skill` → session isolation only (existing behavior)
4. Unmapped topics → silent fall-through

### Finding thread_id

Open topic in Telegram Web/Desktop → URL: `t.me/c/<group_id>/<thread_id>` → the last number is `thread_id`.

### Differences from DM Topics

| | DM Topics | Group Topics |
|---|---|---|
| Config key | `extra.dm_topics` | `extra.group_topics` |
| Topic creation | Hermes creates via API | Admin creates in Telegram UI |
| `thread_id` | Auto-populated | Must be set manually |
| `icon_color` / `emoji` | Supported | N/A (admin controls appearance) |
| Skill binding | ✅ | ✅ |
| Session isolation | ✅ | ✅ (built-in for forum topics) |

---

## Other Topic-Related Features

### `ignored_threads`

Keep Hermes silent in specific forum topics:

```yaml
platforms:
  telegram:
    extra:
      ignored_threads: [31, 42]
```

Messages in these topics are ignored before mention/free-response checks.

### `telegram.ignored_threads` Config

A simpler comma-separated list in the main config:
```yaml
telegram:
  ignored_threads: "31,42"
```

### Cron Delivery to Topics

```bash
--deliver telegram:-1001234567890:17585  # specific topic
```

Or set `TELEGRAM_CRON_THREAD_ID=<thread_id>` for cron messages to land in a dedicated topic.

### Webhook Delivery to Topics

```json
{
  "deliver_extra": {
    "message_thread_id": "42"
  }
}
```

### Ephemeral System Prompts per Topic

```yaml
telegram:
  ephemeral_prompts:
    "5": "You are the Engineering bot. Be technical and concise."
    "-1001234567890": "General group prompt"
```

Topic-level prompts override group-level prompts.

### Hermes Gateway Internals

- Session isolation key format: `agent:main:telegram:dm:{chat_id}:{thread_id}`
- `build_session_key()` in `gateway/session.py` — never construct keys manually
- Topics created outside config auto-discovered via `forum_topic_created` service messages
- `/handoff` from CLI creates new topics on platforms that support threads

---

## Version History

- **Bot API 9.0** — `editForumTopic` + `deleteForumTopic` support private chats
- **Bot API 9.4 (Feb 2026)** — Private Chat Topics: `createForumTopic` in DMs. Hermes uses for `dm_topics` + `/topic`.
- **Bot API 9.5 (Mar 2026)** — Native streaming (`sendMessageDraft`) — DM only, not group topics
- **Bot API 10.0 (May 2026)** — `createForumTopic`, `deleteForumTopic`, `unpinAllForumTopicMessages` all confirmed for private chats
