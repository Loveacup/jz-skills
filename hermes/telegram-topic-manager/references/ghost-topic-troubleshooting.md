# Ghost Topic Troubleshooting — Detailed Reference

## iOS-Specific Ghost Topics

When ghost topics appear **only on iOS** (not on macOS/Windows desktop), the root cause is iOS Telegram's local cache being out of sync with the server. This is the most common ghost topic scenario.

### Why iOS is different

- iOS Telegram uses SQLite-based local storage that caches topic lists aggressively
- Unlike desktop, iOS doesn't auto-refresh topic lists on app foreground
- "Clear Cache" in iOS Settings only clears media cache, not topic metadata
- Force-quitting the app may not invalidate the topic list cache

### iOS Fix Steps (in order)

1. **Clear Entire Cache** (not just media):
   - Settings → Data and Storage → Storage Usage
   - Tap "Clear Entire Cache" (not "Clear Media Cache")
   - This clears all local caches including topic metadata

2. **Force quit + reopen**:
   - Swipe up from bottom (or double-tap home) → swipe Telegram away
   - Wait 10+ seconds
   - Reopen Telegram

3. **Create-then-delete trick** (most reliable):
   - Use Bot API to create a temp topic in the same DM
   - Immediately delete it
   - This forces all connected clients (including iOS) to refresh topic lists
   - See the parent skill for the exact curl commands

4. **Logout + re-login on iOS**:
   - Settings → Edit (top-right) → Log Out
   - Log back in with phone number
   - All data re-syncs from server

5. **Uninstall + reinstall**:
   - Delete Telegram from iOS
   - Restart iPhone
   - Reinstall from App Store

### How to detect which topics are ghosts

**Preferred: Non-destructive `editForumTopic` probing** — no message sent, no cleanup:

```python
import urllib.request, urllib.error, json, os

token = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        if "BOT_TOKEN" in line and "8809" in line:
            token = line.strip().split(chr(61))[1].strip()
            break

chat_id = "7931997806"
topics_to_probe = [38739, 38796, 38786, 38814]  # from send_message list

for tid in topics_to_probe:
    url = f"https://api.telegram.org/bot{token}/editForumTopic"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "message_thread_id": str(tid),
        "name": "probe"
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        if result.get("ok"):
            print(f"thread={tid} ALIVE")
            # ⚠️ Topic was renamed to "probe" — rename it back or to desired name!
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "TOPIC_ID_INVALID" in body:
            print(f"thread={tid} GHOST")
        else:
            print(f"thread={tid} ERROR: {body[:100]}")
```

> **⚠️ Important**: This method renames the topic as a side effect. If probing for diagnosis, note the original name first or rename back after. If you're probing because the user wants to rename anyway (this session's case), just set the desired name directly — the one that succeeds is the right topic.

**Fallback: `sendMessage` + delete probe** (sends a dot, immediately deletes):

```python
import os, json, urllib.request, urllib.parse

# Read token
token = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        if "TELEGRAM_BOT_TOKEN" in line and not line.startswith("#"):
            token = line.strip().split("=", 1)[1]
            break

chat_id = "7931997806"
base = f"https://api.telegram.org/bot{token}"

def probe_topic(thread_id):
    """Send a dot message to probe if topic exists. Returns True if alive."""
    url = f"{base}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "message_thread_id": str(thread_id),
        "text": "."
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                # Clean up probe message
                msg_id = result["result"]["message_id"]
                urllib.request.urlopen(urllib.request.Request(
                    f"{base}/deleteMessage",
                    data=urllib.parse.urlencode({
                        "chat_id": chat_id,
                        "message_id": msg_id
                    }).encode()
                ))
                return True
    except:
        pass
    return False

# Check Hermes state DB for binding inconsistencies
```

### Hermes Gateway Symptoms

When `send_message list` shows topics that API probing confirms are ghosts:

1. The gateway caches topic lists on startup
2. Topics deleted externally (via Telegram UI or another bot) are not auto-detected
3. Fix: `hermes gateway restart` or manually clean `telegram_dm_topic_bindings` in `~/.hermes/state.db`

### DB Cleanup Commands

```sql
-- View all topic bindings for a chat
SELECT * FROM telegram_dm_topic_bindings WHERE chat_id = '7931997806';

-- View topic mode status
SELECT * FROM telegram_dm_topic_mode WHERE chat_id = '7931997806';

-- Remove a specific ghost binding
DELETE FROM telegram_dm_topic_bindings 
WHERE chat_id = '7931997806' AND thread_id = '<ghost_id>';
```
