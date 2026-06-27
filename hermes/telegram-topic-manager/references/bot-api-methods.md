# Telegram Bot API — All Topic Methods (Bot API 10.0)

> **Source:** https://core.telegram.org/bots/api  
> **Last checked:** 2026-06-06 (Bot API 10.0, May 2026)  
> **Note:** The official docs are the authoritative source. This reference is a snapshot — always check the live docs for breaking changes.

## Common Patterns

All methods follow the same HTTP pattern:
```
POST https://api.telegram.org/bot<TOKEN>/<method>
Content-Type: multipart/form-data
```

**chat_id format:**
- Private chat (DM): plain integer → `7931997806`
- Supergroup: `-100` prefix → `-1001234567890`

**Token sourcing:**
```bash
TOKEN=*** TELEGRAM_BOT_TOKEN ~/.hermes/.env | cut -d= -f2)
```

---

## 1. createForumTopic

Create a topic in a forum supergroup chat or a private chat with a user.

**Bot API 10.0:** Now supports private chats (DMs).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat or @username |
| `name` | String | Yes | Topic name, 1-128 characters |
| `icon_color` | Integer | No | RGB color: `7322096` (0x6FB9F0), `16766590` (0xFFD67E), `13338331` (0xCB86DB), `9367192` (0x8EEE98), `16749490` (0xFF93B2), or `16478047` (0xFB6F5F) |
| `icon_custom_emoji_id` | String | No | Custom emoji ID for topic icon |

**Returns:** `ForumTopic` object with `message_thread_id`, `name`, `icon_color`, `icon_custom_emoji_id`.

**Admin required:** Yes for supergroups (must have `can_manage_topics`). Not required for private chats.

```bash
curl -s "https://api.telegram.org/bot${TOKEN}/createForumTopic" \
  -F "chat_id=7931997806" \
  -F "name=New Topic" \
  -F "icon_color=7322096"
```

---

## 2. editForumTopic

Edit name and icon of a topic.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat |
| `message_thread_id` | Integer | Yes | Topic ID to edit |
| `name` | String | No | New name, 0-128 chars. Omit to keep current. |
| `icon_custom_emoji_id` | String | No | New icon emoji ID. Pass empty string `""` to remove icon. Omit to keep current. |

**Returns:** `True` on success.

**Admin required:** Only in supergroups; topic creator exempt. Not required for private chats.

**Error codes:**
| Code | Error | Meaning |
|------|-------|---------|
| 400 | `TOPIC_NAME_INVALID` | Name > 128 chars |
| 400 | `TOPIC_ID_INVALID` | thread_id doesn't exist |
| 400 | `TOPIC_NOT_MODIFIED` | New name == old name |
| 400 | `CHANNEL_FORUM_MISSING` | Supergroup is not a forum |
| 403 | `CHAT_ADMIN_REQUIRED` | Bot lacks `can_manage_topics` |

---

## 3. closeForumTopic

Close an open topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |
| `message_thread_id` | Integer | Yes | Topic ID |

**Returns:** `True`.

---

## 4. reopenForumTopic

Reopen a closed topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |
| `message_thread_id` | Integer | Yes | Topic ID |

**Returns:** `True`.

---

## 5. deleteForumTopic

Delete a forum topic along with all its messages.

**Bot API 10.0:** Now supports private chats.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat |
| `message_thread_id` | Integer | Yes | Topic ID |

**Returns:** `True`.

**Admin required:** In supergroups, bot needs `can_delete_messages` admin right.

**⚠️ Irreversible.** Deletes the topic AND all messages inside it. General topic (id=1) cannot be deleted.

---

## 6. editGeneralForumTopic

Edit the name of the 'General' topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |
| `name` | String | Yes | New name, 1-128 chars |

**Returns:** `True`.

---

## 7. closeGeneralForumTopic

Close the 'General' topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |

**Returns:** `True`.

---

## 8. reopenGeneralForumTopic

Reopen the 'General' topic. **Supergroup only.** Automatically unhides if hidden.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |

**Returns:** `True`.

---

## 9. hideGeneralForumTopic

Hide the 'General' topic. **Supergroup only.** Automatically closes if open.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |

**Returns:** `True`.

---

## 10. unhideGeneralForumTopic

Unhide the 'General' topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |

**Returns:** `True`.

---

## 11. unpinAllForumTopicMessages

Clear all pinned messages in a forum topic.

**Bot API 10.0:** Now supports private chats.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target chat |
| `message_thread_id` | Integer | Yes | Topic ID |

**Returns:** `True`.

**Admin required:** In supergroups, bot needs `can_pin_messages` admin right.

---

## 12. unpinAllGeneralForumTopicMessages

Clear all pinned messages in the General topic. **Supergroup only.**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | Target supergroup |

**Returns:** `True`.

---

## 13. getForumTopicIconStickers

Get custom emoji stickers usable as forum topic icons.

**Parameters:** None.

**Returns:** Array of `Sticker` objects.

```bash
curl -s "https://api.telegram.org/bot${TOKEN}/getForumTopicIconStickers"
```

---

## Key Objects

### ForumTopic (returned by createForumTopic)

| Field | Type | Description |
|-------|------|-------------|
| `message_thread_id` | Integer | Unique topic identifier |
| `name` | String | Topic name |
| `icon_color` | Integer | RGB icon color |
| `icon_custom_emoji_id` | String (optional) | Custom emoji ID for icon |

### Service Message Types

| Type | Description |
|------|-------------|
| `forum_topic_created` | New topic created |
| `forum_topic_edited` | Topic name/icon changed |
| `forum_topic_closed` | Topic closed |
| `forum_topic_reopened` | Topic reopened |
| `general_forum_topic_hidden` | General topic hidden |
| `general_forum_topic_unhidden` | General topic unhidden |

### getMe Fields (private chat topics)

| Field | Type | Description |
|-------|------|-------------|
| `has_topics_enabled` | Boolean | Bot has topic mode in private chats |
| `allows_users_to_create_topics` | Boolean | Users can create/delete topics in DM |

---

## Chat Type Support Matrix

| Method | Private Chat | Supergroup |
|--------|:---:|:---:|
| `createForumTopic` | ✅ (API 10.0) | ✅ |
| `editForumTopic` | ✅ | ✅ |
| `deleteForumTopic` | ✅ (API 10.0) | ✅ |
| `unpinAllForumTopicMessages` | ✅ (API 10.0) | ✅ |
| `closeForumTopic` | ❌ | ✅ |
| `reopenForumTopic` | ❌ | ✅ |
| `editGeneralForumTopic` | ❌ | ✅ |
| `closeGeneralForumTopic` | ❌ | ✅ |
| `reopenGeneralForumTopic` | ❌ | ✅ |
| `hideGeneralForumTopic` | ❌ | ✅ |
| `unhideGeneralForumTopic` | ❌ | ✅ |
| `unpinAllGeneralForumTopicMessages` | ❌ | ✅ |
| `getForumTopicIconStickers` | ✅ | ✅ |
