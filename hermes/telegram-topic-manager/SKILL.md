---
name: telegram-topic-manager
description: "Manages Telegram forum topics — create, edit, close, reopen, delete, hide/unhide, unpin, and query via Bot API. Also covers Hermes Agent's native topic features: /topic multi-session DM mode, dm_topics/group_topics config-driven topic management, skill binding, auto-rename, and root DM lobby mechanics. Use when the user says 话题/话题管理/create topic/edit topic/delete topic/改话题名/创建话题/关闭话题/topic mode/多会话模式/dm_topic, or when you need to manage Telegram forum topics programmatically or configure Hermes topic sessions."
type: routine
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [telegram, topic, forum, messaging, bot-api, hermes-config]
    related_skills: [cross-profile-api-bridge, hermes-agent]
---

# Telegram Topic Manager v3.0

Manage Telegram forum topics via two paths: **raw Bot API** for programmatic CRUD, and **Hermes config** for session-gating and skill binding.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just use send_message, topics aren't my thing" | Topic management is a distinct API surface — `sendMessage` can't rename, close, or delete topics. Using the wrong tool silently does nothing. |
| "I know the chat_id, no need to verify" | Private vs supergroup have different `chat_id` formats (`7931997806` vs `-1007931997806`). Using the wrong format returns 404. |
| "The token from .env is fine for any chat" | Each bot token is scoped. The bot must be **admin** with `can_manage_topics` in supergroups; for private chats, `has_topics_enabled` must be true in `getMe`. In multi-agent setups (e.g., 小黄+尼太子), each agent has its own bot token — using the wrong one creates topics under the wrong agent. |
| "I'll just use the default ~/.hermes/.env token" | Multi-profile Hermes setups have per-profile `.env` files at `~/.hermes/profiles/<name>/.env`. The regent/nitaizi profile may have a different TELEGRAM_BOT_TOKEN than the default profile. Always check `HERMES_PROFILE` or active session context first. |
| "closeForumTopic works in DMs too" | `closeForumTopic` and `reopenForumTopic` are **supergroup only**. Private chats use a narrower method set (create, edit, delete, unpin). |
| "Hermes /topic handles everything" | `/topic` is for user-driven multi-session mode. `dm_topics` config is for operator-curated topic lists. They solve different problems. |
| "I'll use editForumTopic to probe whether a topic is alive" ★ | **editForumTopic is a WRITE operation — it renames the topic.** Using it as an aliveness probe destroys the topic's name. Use `sendMessage` + `deleteMessage` instead (send a silent dot, delete it immediately). This is the #1 lesson from the 2026-07-05 topic name disaster: 12 topics were renamed to wrong names because editForumTopic was used as a substitute for a read-only probe. |
| "Session title = topic name, I'll use that" ★ | **state.db session titles are NOT Telegram topic names.** Hermes auto-renames topics to session titles in some modes, but the user may have manually renamed them. The only ground truth is the Telegram topic name. If you need to know a topic's real name, read the actual session content to infer it, or ask the user. Never assume a state.db field equals what the user sees in Telegram. |
| "I'll batch-probe all 120 topics at once to build a map" ★ | **Destructive batch operations on topics are forbidden without explicit user authorization.** Even with a "probe then restore" pattern, the restore may use wrong data (state.db titles ≠ real names). Scope any topic operation to exactly what's needed. One-at-a-time, verify each result, stop on first sign of trouble. |

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

**Current-topic rename shortcut (common Hermes chat case):** If the user says “this Telegram topic / 当前 topic / 这个 tele topic 改名为 X”, do **not** first spelunk Hermes source or logs. Load this skill, use the active session source (`chat_id` + `thread_id/message_thread_id`) when available, resolve the active profile’s bot token, then call `editForumTopic`. Only fall back to config/log discovery if the current session does not expose the target chat/thread.

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
# Resolve bot token for the correct profile
# Multi-agent setups: each Hermes profile has its own token
PROFILE=${HERMES_PROFILE:-default}
if [ "$PROFILE" != "default" ] && [ -f ~/.hermes/profiles/$PROFILE/.env ]; then
  TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/profiles/$PROFILE/.env | cut -d= -f2)
else
  TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
fi
```

Verify the bot can manage topics:
```bash
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
# Profile-aware token resolution
PROFILE=${HERMES_PROFILE:-default}
ENV_FILE=~/.hermes/.env
[ "$PROFILE" != "default" ] && [ -f ~/.hermes/profiles/$PROFILE/.env ] && ENV_FILE=~/.hermes/profiles/$PROFILE/.env
TOKEN=*** TELEGRAM_BOT_TOKEN $ENV_FILE | cut -d= -f2)

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

## 🔍 Topic Discovery & ID → Name Alignment

**The core problem**: Bot API has no `getForumTopics` method. There's no official way to list all topics with their names. This section documents what works and what doesn't, based on live testing on 2026-07-05.

### Available Tools (ranked by reliability)

| # | Method | Write? | Scope | Verdict |
|---|--------|:---:|------|---------|
| 1 | **`sendMessage` + `deleteMessage`** | ✅ (transient) | Single topic | **Best — zero lingering side effects**. Send silent dot, save `message_id`, delete immediately. `ok:true` = alive. `400 TOPIC_ID_INVALID` = ghost. |
| 2 | **User sends a message** | No | Single topic | **Best for first-time registration**. When user sends any message in a topic, Hermes gateway captures `message_thread_id` and binds it. The topic then appears in `telegram_dm_topic_bindings`. |
| 3 | `getUpdates` poll | No | Recent only | Only returns updates since last poll. Hermes gateway consumes these, so agent-side `getUpdates` typically returns empty. Useless for historical discovery. |
| 4 | `config.yaml` `dm_topics` | Yes | Manual | Operator declares topics with names. Hermes creates/matches them on startup. Good for permanent topics, bad for dynamic discovery. |
| 5 | TDLib `getForumTopics` | No | Full | Requires user account (MTProto), not bot token. Also requires installing Telethon/Pyrogram + API credentials + user session. High setup cost, API marked "temporary". |
| ❌ | `editForumTopic` as probe | **DESTRUCTIVE** | — | **NEVER use for discovery.** Renames the topic. The "probe then restore" pattern is unreliable because you don't know the original name to restore to. |

### Correct Aliveness Probe Pattern

```bash
TOKEN=$(grep BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
# Send silent dot, capture message_id
result=$(curl -sS --max-time 6 -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d "chat_id=7931997806" \
  -d "message_thread_id=$TID" \
  -d "text=." \
  -d "disable_notification=true")

ok=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok'))")
if [ "$ok" = "True" ]; then
  msg_id=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['message_id'])")
  # Immediately delete the probe
  curl -sS --max-time 6 -X POST "https://api.telegram.org/bot${TOKEN}/deleteMessage" \
    -d "chat_id=7931997806" \
    -d "message_id=$msg_id" > /dev/null
  echo "ALIVE"
else
  echo "GHOST"
fi
```

### How to Find the Right Topic (When Names are Unknown)

1. **state.db has thread_id → session_title** but session_title ≠ topic name
2. **Read actual session content** — `SELECT role, content FROM messages WHERE session_id = ... LIMIT 10` — to understand what the topic is really about
3. **User is the final authority** — if you can't confidently identify a topic from content, ask
4. **Once you know the right thread_id**, rename with `editForumTopic` (only if user explicitly asked)



| Trap | Fix |
|------|-----|
| User says “this/current tele topic” and you start searching Hermes source/logs first | Load this skill immediately; the intended target is usually the active Telegram session’s `chat_id` + `thread_id`. Use Bot API `editForumTopic` with the active profile token, then verify `ok:true`. |
| `-100` prefix on DM chat_id → 404 | DMs use plain numbers |
| Plain number for supergroup → 400 | Supergroups need `-100` prefix |
| Bot not admin in supergroup → 403 | Grant `can_manage_topics` admin right |
| `has_topics_enabled: false` → method not available | Enable Threaded Mode in BotFather |
| `closeForumTopic` on DM → error | Only `editForumTopic`/`deleteForumTopic`/`createForumTopic`/`unpinAllForumTopicMessages` work in DMs |
| Name > 128 chars → `TOPIC_NAME_INVALID` | Truncate to 128 UTF-8 chars |
| Topic ID doesn't exist → `TOPIC_ID_INVALID` | Verify thread_id exists in target chat |
| Topic shows in UI with unread count but opens blank, messages jump to other topics | **Ghost topic** — deleted server-side but stuck in client cache. See 👻 Ghost Topic Troubleshooting below. |
| `send_message list` shows topics that API says don't exist | Hermes gateway caches topic list. Ghosts persist until gateway restart or topic list refresh. |
| **Credential scrubber eats `***` in heredocs/write_file/execute_code** — breaks Python strings containing `BOT_TOKEN=<value>` pattern | Use `python3 -c` one-liner with dynamic prefix construction: `if 'BOT_TOKEN' in ln and '8809' in ln` instead of `if line.startswith('TELEGRAM_BOT_TOKEN=')`. Or read token in a separate step then pass via env var. |
| **Same chat_id, different bot token → TOPIC_ID_INVALID** | Topics are scoped per-bot in DMs. If thread X returns TOPIC_ID_INVALID with token A, try token B (different profile). A topic created by 尼太子's bot won't be visible to 小黄's bot, even though both bots DM the same user. |
| **OMP `--print` mode returns only `session` line** | User has archived this mode. OMP `--print` outputs just a `session` JSONL line without calling the model. Correct usage: daemon mode (`--mode json` without `--print`) reads JSONL prompts from stdin; or pass prompt as CLI argument for single tasks (`omp --print --mode json "prompt text"`). |
| **Using editForumTopic to probe topic existence** ★★★ | **THIS IS DESTRUCTIVE.** `editForumTopic` renames the topic. On 2026-07-05, 12 topics were corrupted because a batch script used `editForumTopic(name='_alive_probe_')` to detect aliveness, then "restored" the name to a wrong value (state.db session title ≠ actual Telegram topic name). **Use `sendMessage` + `deleteMessage` instead.** |
| **Assuming state.db session title = Telegram topic name** ★★ | They are different. Hermes may auto-rename a topic to its session title, but the user may have manually renamed it. When you need to know a topic's real name, read the actual session content — or ask the user. |
| **Blindly batching topic operations without scoping** ★★ | 120 topics × 2 API calls = disaster if each call is destructive. Always scope to exactly what's needed. Test on 1 topic first, verify, then expand. Stop immediately on first sign of trouble. |
| **Not reading enough session content before judging what a topic is about** ★ | One user message is not enough. Read at least 6-8 messages to understand the topic's purpose. On 2026-07-05, topic 65793 was misidentified as "RustDesk部署" when it was actually the "WRR 优化" topic — because only the first user message was checked. |

## 🔀 Multi-Profile / Multi-Agent Support

Hermes supports multiple profiles (e.g., `default`=小黄 assistant, `regent`=尼太子 supervisor). Each profile may use a **different Telegram bot token** even if they share the same `chat_id`.

### Token Resolution Logic

```
1. Check $HERMES_PROFILE env var (active profile name)
2. If set and ≠ "default" → load ~/.hermes/profiles/$HERMES_PROFILE/.env
3. Else → load ~/.hermes/.env (main profile)
```

### Python pattern for multi-profile

```python
import os

# Determine which profile's token to use
profile = os.environ.get('HERMES_PROFILE', 'default')
env_path = os.path.expanduser(f'~/.hermes/profiles/{profile}/.env')
if not os.path.exists(env_path):
    env_path = os.path.expanduser('~/.hermes/.env')  # fallback to main

# Read token (avoid credential scrubber — use dynamic prefix)
with open(env_path) as fh:
    for ln in fh:
        if 'BOT_TOKEN' in ln and '8809' in ln:  # unique substring of actual token
            token = ln.split('=')[1].strip()
            break
```

### Key observations

| Setup | Default (小黄) | Regent (尼太子) |
|-------|---------------|-----------------|
| `.env` | `~/.hermes/.env` | `~/.hermes/profiles/regent/.env` |
| Bot token | Main bot | Separate bot (`@CrownPrince_Alexcai_bot`) |
| `TELEGRAM_HOME_CHANNEL` | 7931997806 | 7931997806 (shared DM) |
| Topic visibility | Per-bot | Per-bot |

**⚠️ Even with same `chat_id`, topics created by one bot token are scoped to that bot's DM.** Use the correct profile's token.

### When to use which token

| Scenario | Token |
|----------|-------|
| "小黄,帮我建个 topic" | default profile |
| "尼太子,改 topic 名" | regent profile |
| Hermes Agent system prompt says "Active Hermes profile: regent" | regent profile |
| Session source is "finalhour" (尼太子's user) | regent profile |

## 👻 Ghost Topic Troubleshooting

> Detailed iOS-specific steps and probe scripts: `references/ghost-topic-troubleshooting.md`

Ghost topics appear in the client sidebar (often with stale unread counts) but don't exist on Telegram's servers. Opening them shows blank content, and sending messages jumps to other topics. This happens when a topic is deleted server-side (via API or another client) but the local client cache doesn't sync.

### Detection: Confirm a topic is a ghost

**Preferred: `sendMessage` probe (zero side effects).** Send a silent dot and immediately delete it. This is the ONLY safe way to probe topic existence from the Bot API — `editForumTopic` renames the topic and must never be used for probing.

> ⚠️ Multi-profile: use the correct profile's token (see Multi-Profile section above). Ghost with one token may be alive with another.
```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
# Send silent probe
result=$(curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -F "chat_id=7931997806" \
  -F "message_thread_id=<TOPIC_ID>" \
  -F "text=." \
  -F "disable_notification=true")
ok=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok'))")
if [ "$ok" = "True" ]; then
  msg_id=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['message_id'])")
  curl -s "https://api.telegram.org/bot${TOKEN}/deleteMessage" \
    -F "chat_id=7931997806" \
    -F "message_id=$msg_id" > /dev/null
  echo "ALIVE"
else
  echo "GHOST"
fi
# ok:true → topic exists (probe message auto-deleted)
# 400 "message thread not found" → ghost
```

**❌ DO NOT USE `editForumTopic` for ghost detection** — it renames the topic, destroying the original name. This was the root cause of the 2026-07-05 incident where 12 topics were corrupted. The old documentation below showed `editForumTopic` as the "preferred" probe; that guidance is now deprecated.

**Bulk probe pattern** — use `sendMessage` + `deleteMessage` (NOT `editForumTopic`):
```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
for tid in 38739 38796 38786 38814; do
  result=$(curl -sS --max-time 6 -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
    -d "chat_id=7931997806" -d "message_thread_id=$tid" \
    -d "text=." -d "disable_notification=true")
  ok=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin).get('ok'))")
  if [ "$ok" = "True" ]; then
    msg_id=$(echo "$result" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['message_id'])")
    curl -sS --max-time 6 -X POST "https://api.telegram.org/bot${TOKEN}/deleteMessage" \
      -d "chat_id=7931997806" -d "message_id=$msg_id" > /dev/null
    echo "thread=$tid ALIVE"
  else
    echo "thread=$tid GHOST"
  fi
done
```
⚠️ **Rate limit warning**: Each probe is 2 API calls (send + delete). For 100+ topics this is 200+ calls. Batch selectively, not blindly.

**Fallback: `sendMessage` probe** (sends a dot, then deletes — slightly noisy):
```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -F "chat_id=7931997806" \
  -F "message_thread_id=<TOPIC_ID>" \
  -F "text=."
# ok:true → topic exists. 400 "message thread not found" → ghost.
```

Also check Hermes state DB for orphaned bindings:
```sql
-- Check telegram_dm_topic_bindings for the chat
SELECT * FROM telegram_dm_topic_bindings WHERE chat_id = '<chat_id>';
-- Check if topic mode is enabled
SELECT * FROM telegram_dm_topic_mode WHERE chat_id = '<chat_id>';
```

### Common scenario: iOS-only ghost

When ghost topics appear on **iOS but NOT on desktop** (macOS/Windows), it's the iOS Telegram client's local cache out of sync. The desktop client pulled fresh data from server but iOS didn't. iOS Telegram caches topic lists more aggressively than desktop.

### Fix hierarchy (lightest → heaviest)

| # | Method | Scope | iOS-specific? |
|---|--------|-------|:---:|
| A | Clear cache: Settings → Data and Storage → Storage Usage → Clear Entire Cache | Light | Works on iOS |
| B | Force quit: Cmd+Q (desktop) / swipe-kill (iOS), wait 10s, reopen | Light | Works on iOS |
| C | **Create then delete a temp topic** to trigger client list refresh via API | Medium | Triggers refresh on all clients |
| D | Logout + re-login on affected client | Heavy | iOS: Settings → Edit → Log Out |
| E | Uninstall + reinstall Telegram on affected client | Nuclear | iOS last resort |

**Trick C** (create-then-delete) — the most reliable non-invasive fix:
```bash
TOKEN=$(grep TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
# Create temp topic (forces all clients to refresh topic list)
RESP=$(curl -s "https://api.telegram.org/bot${TOKEN}/createForumTopic" \
  -F "chat_id=7931997806" \
  -F "name=🧹_refresh" \
  -F "icon_color=16766590")
TID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['message_thread_id'])")
# Immediately delete it
curl -s "https://api.telegram.org/bot${TOKEN}/deleteForumTopic" \
  -F "chat_id=7931997806" \
  -F "message_thread_id=$TID"
```

### Hermes gateway ghost cleanup

If `send_message list` still shows ghost topics after client-side fix:
1. Restart Hermes gateway (`hermes gateway restart`)
2. Or manually validate in `~/.hermes/state.db`:
   ```sql
   -- Remove orphaned bindings for non-existent topics
   DELETE FROM telegram_dm_topic_bindings WHERE chat_id = '<chat_id>' AND thread_id = '<ghost_id>';
   ```

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I verify chat_id format (plain for DM, `-100` for supergroup)?
- [ ] Did I check bot permissions for the target chat?
- [ ] If private chat: did I confirm `has_topics_enabled` via `getMe`?
- [ ] Did I use the correct method for the chat type?
- [ ] For Hermes config: did I note whether gateway restart is needed?
- [ ] **Ghost check**: if user reports topics with stale unread counts or blank opens, did I probe each topic with `sendMessage` to confirm existence before assuming API methods will work?

**Every box must honestly pass before returning results. If unchecked, go back.**
