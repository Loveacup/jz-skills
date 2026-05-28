# Cross-Profile Evidence Gathering

When grilling a design that involves other Hermes profiles (三省六部 departments, regent, etc.), your own Hindsight bank is **incomplete** — it only captures YOUR profile's conversations. The other profile may have had extensive discussions, decisions, and iterations you cannot see.

## Filesystem Query Toolkit

Before designing or asking the user, exhaust these filesystem checks on the target profile:

### 1. Profile state snapshot
```bash
# Does the profile exist and have sessions?
ls ~/.hermes/profiles/<name>/sessions/ | wc -l
cat ~/.hermes/profiles/<name>/config.yaml | head -20
cat ~/.hermes/profiles/<name>/memories/user.md 2>/dev/null
```

### 2. Hindsight configuration
```bash
cat ~/.hermes/profiles/<name>/hindsight/config.json
# Key fields: bank_id, memory_mode, auto_recall, auto_retain
```

### 3. Skills inventory
```bash
ls ~/.hermes/profiles/<name>/skills/
```

### 4. Cron jobs
```bash
ls ~/.hermes/profiles/<name>/cron/
```

### 5. Recent session titles (if sessions.json is readable)
```bash
python3 -c "
import json
with open('~/.hermes/profiles/<name>/sessions/sessions.json') as f:
    data = json.load(f)
# Structure varies by Hermes version
"
```

## Communication Channels

When filesystem queries aren't enough and you need the profile to answer questions:

1. **User relay** — Ask the user to forward a structured brief to the profile's Telegram chat. Fastest for one-off questions.

2. **Shared Telegram group** — If a group exists with both profiles' bots, send directly via `send_message`.

3. **Hermes send** — If you know the profile's platform target:
   ```bash
   hermes send -t telegram:<chat_id> "message"
   ```
   Check available targets: `hermes send -l`

4. **File-based handoff** — Write to `~/.hermes/tmp/` and have the other profile poll or be notified.

## Known Pitfall (2026-05-27)

When designing the 三省六部 cross-department memory sharing architecture, the default assistant designed an entire three-layer agentmemory + Hindsight方案 based only on default's Hindsight. The regent had already iterated through v3.0.0 with extensive discussions about EmpireThread, Kanban watchers, and memory isolation — none visible to default. Lesson: **never design cross-profile architecture without first exhausting filesystem queries on ALL involved profiles.**
