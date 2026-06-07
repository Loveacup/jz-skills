---
name: reply-context-retrieval
description: "Use when the user replies to a previous message via Telegram's reply mechanism and the quoted fragment is truncated — the agent needs full context of the quoted message. Also triggers when user says '引用给你了'、'你看一下我的引用'、'我回复了你一条消息'、or message starts with [Replying to:. DO NOT use when the user provides complete context in their current message, when the reply fragment is self-explanatory, or for regular conversations without reply markers."
version: 1.0.0
author: Hermes Agent (小黄)
tags: [telegram, context, session-search, reply]
---

# Reply Context Retrieval — Full Context from Telegram Reply Fragments

When a user replies to a message on Telegram, the agent only receives a truncated snippet (typically `[Replying to: "..."]`). This skill retrieves the full message and surrounding context from session history.

## 🚨 Red Flags: DO NOT GUESS WHAT THE USER REPLIED TO

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "The reply fragment tells me enough, I can just answer directly" | Fragments are truncated and lose critical nuance, data, numbers, or constraints. |
| "It's just a quick reply, no need for full context" | The user chose reply instead of forward — they want the link to the original message preserved. |
| "I'll just look at the last few messages, doesn't need session_search" | The quoted message could be far back in the conversation or in a different session entirely. |

## 🔀 Decision Tree

```
User message starts with [Replying to: "..."], or user says "引用/回复/reply"?
├── YES
│   ├── Reply fragment is self-explanatory (<15 chars, obvious question)?
│   │   └── YES → Skip retrieval, answer directly
│   ├── Extract search terms from fragment
│   ├── Search current session: session_search(query, sort="newest")
│   ├── Found match with anchor message?
│   │   ├── YES → Extract full context (anchor ± 5 messages). Continue.
│   │   └── NO → Fallback: session_search(query, sort="newest") without session_id
│   │       ├── Found? → Extract context. Continue.
│   │       └── NOT FOUND → Tell user: "引用片段找不到完整上下文，请转发原文给我"
│   └── Reply incorporates the full context
└── NO → Normal conversation flow
```

## 📋 Step-by-Step

### 1. Parse the Reply Fragment

Telegram delivers replies as: `[Replying to: "TRUNCATED_TEXT..."]`

Extract the visible text between the quotes. Note:
- Fragments ending in `...` were truncated by Telegram
- Fragments may contain line breaks replaced by spaces
- The fragment preserves the role tag (e.g., `💭 Reasoning:`)

### 2. Extract Search Terms

From the fragment, extract 3-5 distinctive keywords. Prioritize:
- **Nouns and named entities** (product names, technical terms, numbers)
- **Unique phrases** unlikely to appear elsewhere
- **NOT** common words like "the", "this", "应该", "这个"

Example: fragment `"腾讯云将向您在步骤6提交的银行对公账户转入0.01 - 0.99元..."`
→ search terms: `腾讯云 对公账户 0.01 0.99 银行`

### 3. Search Current Session First

```python
session_search(query="<search terms>", sort="newest")
```

If `match_message_id` exists, the anchor message IS the quoted message. Read messages around it.

### 4. Fallback: Search All Sessions

If current session search returns nothing:

```python
session_search(query="<search terms>", sort="newest")
# Use broader terms on second attempt
```

### 5. Extract and Incorporate Context

Once found, the discovery result gives you:
- `match_message_id` — the quoted message
- `messages` — ±5 around the anchor
- `bookend_start` / `bookend_end` — session opening and closing

Use this to understand the full conversation context, then answer the user's new question.

## ⚠️ Edge Cases

| Situation | Action |
|-----------|--------|
| Fragment is <10 meaningful characters | Ask user to forward the original message: "引用太短，请转发原文" |
| Fragment is entirely in Chinese/English but session is mixed | Use original language of the fragment for search terms |
| Two sessions match equally well | Prefer the most recent session (`sort="newest"`) |
| Match found but anchor message is NOT the quoted one | Scroll around: `session_search(session_id, around_message_id, window=10)` to find nearby |
| Fragment mentions something from many sessions ago (>3 days) | It's likely a cross-session reply — go straight to all-sessions search |
| User replies to an image/media message | Fragment will describe the media — search for the description text |

---

## ✅ Verification Checklist (RUN BEFORE RESPONDING)

- [ ] Did I extract search terms from the reply fragment (not guess)?
- [ ] Did I search current session before falling back to all sessions?
- [ ] Did I read the full context (anchor ± 5 messages), not just the snippet?
- [ ] Did I incorporate the retrieved context into my response?
- [ ] If NOT FOUND — did I ask the user to forward the original message instead of guessing?

**If any box is unchecked, go back.**
