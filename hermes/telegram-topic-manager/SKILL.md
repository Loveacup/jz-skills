---
name: telegram-topic-manager
description: "Manages Telegram forum topics — create, edit, close, reopen, delete, hide/unhide, unpin, and query via Bot API. Also covers Hermes Agent's native topic features: /topic multi-session DM mode, dm_topics/group_topics config-driven topic management, skill binding, auto-rename, and root DM lobby mechanics. Use when the user says 话题/话题管理/create topic/edit topic/delete topic/改话题名/创建话题/关闭话题/topic mode/多会话模式/dm_topic, or when you need to manage Telegram forum topics programmatically or configure Hermes topic sessions."
type: routine
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [telegram, topic, forum, messaging, bot-api, hermes-config]
    related_skills: [cross-profile-api-bridge, hermes-agent]
---

# Telegram Topic Manager v2.0

Manage Telegram forum topics via two paths: **raw Bot API** for programmatic CRUD, and **Hermes config** for session-gating and skill binding.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just use send_message, topics aren't my thing" | Topic management is a distinct API surface — `sendMessage` can't rename, close, or delete topics. Using the wrong tool silently does nothing. |
| "I know the chat_id, no need to verify" | Private vs supergroup have different `chat_id` formats (`7931997806` vs `-1007931997806`). Using the wrong format returns 404. |
| "The token from .env is fine for any chat" | Each bot token is scoped. The bot must be **admin** with `can_manage_topics` in supergroups; for private chats, `has_topics_enabled` must be true in `getMe`. |
| "closeForumTopic works in DMs too" | `closeForumTopic` and `reopenForumTopic` are **supergroup only**. Private chats use a narrower method set (create, edit, delete, unpin). |
| "Hermes /topic handles everything" | `/topic` is for user-driven multi-session mode. `dm_topics` config is for operator-curated topic lists. They solve different problems. |

## 🔀 Decision Tree

```
User wants to manage Telegram topics?
├── Needs programmatic CRUD (scripts, external tooling)?
│   └── → Path 1: Raw Bot API. See references/bot-api-methods.md.
├── Wants session isolation + skill binding per topic?
│   └── → Path 2: Hermes config. See references/hermes-topic-system.md.
└── Just wants to send a message to a specific topic?
    └── Use send_message with target="telegram:chat_id:thread_id". No topic management needed.
```

### Quick Scope: Which path for which task?

| Task | Bot API | Hermes Config |
|------|:---:|:---:|
| Create a topic | ✅ | ✅ (dm_topics auto-creates) |
| Rename a topic | ✅ | ❌ (edit via API) |
| Close / reopen a topic | ✅ (supergroup only) | ❌ |
| Delete a topic + messages | ✅ | ❌ |
| Bind a skill to a topic | ❌ | ✅ (`skill` field) |
| Enable `/topic` multi-session | ❌ | ✅ (`/topic` in root DM) |
| Session isolation per topic | ❌ | ✅ (automatic) |

## Path 1: Raw Telegram Bot API

All 13 topic methods. For full parameter tables and error codes, see `references/bot-api-methods.md`.

**Always reference the official docs for the latest:** https://core.telegram.org/bots/api

### Prerequisites

```bash
# Get bot token
grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2
```

Verify the bot can manage topics:
```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
# Check getMe for private chat capability
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" | python3 -m json.tool | grep -E "has_topics_enabled|allows_users_to_create_topics"
```

### chat_id Format

| Chat Type | Format | Example |
|-----------|--------|---------|
| Private chat (DM) | Plain number | `7931997806` |
| Supergroup | `-100` prefix | `-1001234567890` |

**⚠️ Using `-100` prefix on a private chat returns 404. Using plain number for supergroup returns 400.**

### Method Summary (Bot API 10.0)

| Method | DM | Supergroup | Admin required? |
|--------|:---:|:---:|:---:|
| `createForumTopic` | ✅ | ✅ | Yes (supergroup only) |
| `editForumTopic` | ✅ | ✅ | Yes / topic creator |
| `deleteForumTopic` | ✅ | ✅ | Yes (`can_delete_messages`) |
| `unpinAllForumTopicMessages` | ✅ | ✅ | Yes (`can_pin_messages`) |
| `closeForumTopic` | ❌ | ✅ | Yes / topic creator |
| `reopenForumTopic` | ❌ | ✅ | Yes / topic creator |
| `editGeneralForumTopic` | ❌ | ✅ | Yes |
| `closeGeneralForumTopic` | ❌ | ✅ | Yes |
| `reopenGeneralForumTopic` | ❌ | ✅ | Yes |
| `hideGeneralForumTopic` | ❌ | ✅ | Yes |
| `unhideGeneralForumTopic` | ❌ | ✅ | Yes |
| `unpinAllGeneralForumTopicMessages` | ❌ | ✅ | Yes (`can_pin_messages`) |
| `getForumTopicIconStickers` | ✅ | ✅ | No |

### Usage Pattern

```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)

# Create topic in DM
curl -s "https://api.telegram.org/bot${TOKEN}/createForumTopic" \
  -F "chat_id=7931997806" \
  -F "name=My New Topic" \
  -F "icon_color=7322096"

# Rename topic
curl -s "https://api.telegram.org/bot${TOKEN}/editForumTopic" \
  -F "chat_id=7931997806" \
  -F "message_thread_id=38814" \
  -F "name=🧪 Renamed Topic"

# Delete topic
curl -s "https://api.telegram.org/bot${TOKEN}/deleteForumTopic" \
  -F "chat_id=7931997806" \
  -F "message_thread_id=38814"
```

For supergroups, change `chat_id` to `-100<group_id>`. Full API reference with all parameters: `references/bot-api-methods.md`.

## Path 2: Hermes Config-Driven Topics

Hermes has two topic management systems for session isolation + skill binding. Full details: `references/hermes-topic-system.md`.

### A. `dm_topics` — Operator-Curated Private Chat Topics

Config in `~/.hermes/config.yaml`:
```yaml
platforms:
  telegram:
    extra:
      dm_topics:
      - chat_id: 7931997806
        topics:
        - name: General
          icon_color: 7322096
        - name: Research
          skill: arxiv
```

- Hermes creates topics on gateway startup if `thread_id` is missing
- `thread_id` auto-saved to config after creation
- Session isolation: `agent:main:telegram:dm:{chat_id}:{thread_id}`
- `skill` auto-loads on new sessions
- `ignore_root_dm: true` → root DM becomes lobby (system commands only)

### B. `/topic` — User-Driven Multi-Session DM Mode

| Command | Context | Effect |
|---------|---------|--------|
| `/topic` | Root DM (first time) | Enable multi-session mode |
| `/topic` | Root DM (enabled) | Show status + unlinked sessions |
| `/topic` | Inside a topic | Show current session binding |
| `/topic off` | Root DM | Disable mode, clear bindings |
| `/topic <session-id>` | Inside a topic | Restore previous session |

Prerequisites: **BotFather → Threads Settings** → enable Threaded Mode + allow user topic creation.

### C. `group_topics` — Supergroup Forum Topic Skill Binding

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
```

- Topic creation is manual (admin via Telegram UI)
- Find `thread_id` from topic URL: `t.me/c/<group_id>/<thread_id>`
- Skill binding + session isolation work same as dm_topics

## ⚠️ Common Pitfalls

| Trap | Fix |
|------|-----|
| `-100` prefix on DM chat_id → 404 | DMs use plain numbers |
| Plain number for supergroup → 400 | Supergroups need `-100` prefix |
| Bot not admin in supergroup → 403 | Grant `can_manage_topics` admin right |
| `has_topics_enabled: false` → method not available | Enable Threaded Mode in BotFather |
| `closeForumTopic` on DM → error | Only `editForumTopic`/`deleteForumTopic`/`createForumTopic`/`unpinAllForumTopicMessages` work in DMs |
| Name > 128 chars → `TOPIC_NAME_INVALID` | Truncate to 128 UTF-8 chars |
| Topic ID doesn't exist → `TOPIC_ID_INVALID` | Verify thread_id exists in target chat |

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I verify chat_id format (plain for DM, `-100` for supergroup)?
- [ ] Did I check bot permissions for the target chat?
- [ ] If private chat: did I confirm `has_topics_enabled` via `getMe`?
- [ ] Did I use the correct method for the chat type?
- [ ] For Hermes config: did I note whether gateway restart is needed?

**Every box must honestly pass before returning results. If unchecked, go back.**
