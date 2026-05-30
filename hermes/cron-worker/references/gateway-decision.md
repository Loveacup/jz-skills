# Gateway Decision — Full Step-by-Step

> Load this from Step 2g of SKILL.md after the user picks Path A or Path B via `clarify()`.

## Path A: Add Gateway — Full Telegram Integration

### 1. Get bot token

If user chose option 1 → tell them to go to [@BotFather](https://t.me/BotFather), run `/newbot`, and paste the token.  
If user chose option 2 → ask them to paste the token with `clarify(question="请把 bot token 发过来")`.

### 2. Write token to .env

```bash
# Check if TELEGRAM_BOT_TOKEN already exists
grep -n TELEGRAM_BOT_TOKEN ~/.hermes/profiles/cron-worker/.env

# If found (line N): replace that line
sed -i '' 'Ns/.*/TELEGRAM_BOT_TOKEN=PASTED_TOKEN/' ~/.hermes/profiles/cron-worker/.env

# If NOT found: append
echo 'TELEGRAM_BOT_TOKEN=PASTED_TOKEN' >> ~/.hermes/profiles/cron-worker/.env
```

> [!caution] `hermes profile create --clone` copies the default profile's .env including its TELEGRAM_BOT_TOKEN. After cloning, cron-worker's .env has the WRONG bot token. Always run the detection step above and replace it.

### 3. Install and start gateway

```bash
hermes --profile cron-worker gateway install
```

This creates `~/Library/LaunchAgents/ai.hermes.gateway-cron-worker.plist` and loads it via launchd.

### 4. Verify gateway is running

```bash
hermes --profile cron-worker gateway status
# Should show: ✓ Gateway service is loaded, PID: XXXXX
```

Check the log for Telegram connection:

```bash
tail -20 ~/.hermes/profiles/cron-worker/logs/gateway.log
# Look for: ✓ telegram connected (polling mode)
```

### 5. Expected warnings — HARMLESS

```
✗ api_server failed to connect
ERROR Port 8460 already in use
```

The default gateway already owns port 8460. Cron-worker doesn't need the API server — Telegram polling mode works independently. **No action needed.**

### 6. Resource impact

| Metric | Without Gateway | With Gateway |
|--------|----------------|--------------|
| RAM | 0 extra | ~104MB RSS |
| Processes | 0 extra | 1 Python gateway daemon |
| Ports | 0 extra | 0 (api_server skipped; Telegram is outbound polling) |
| Bot token | Not needed | **Separate bot required** (one gateway = one bot) |

> [!tip] Gateway is up! DM `@YourBotName` on Telegram to interact with cron-worker directly. It shares identity (SOUL, memory, skills) with default but uses the cheaper model in its own session.

---

## Path B: Skip Gateway — Cron-Only, Lighter

No gateway installation. All interaction is via cron jobs or CLI (`hermes --profile cron-worker "task"`).

### Cron job delivery mechanism

Cron jobs running under `profile="cron-worker"` are delivered by the **default gateway's cron scheduler** — the scheduler spawns the job, the agent runs, and the scheduler handles output delivery. Cron-worker does NOT need its own gateway for this.

### Delivery targets for cron jobs

| `deliver` value | Behavior | Use case |
|-----------------|----------|----------|
| `"origin"` | Routes via default gateway → Telegram Home channel | **Default.** Results land in your main Telegram chat |
| `"local"` | Saves to `~/.hermes/cron/output/` only, **no notification** | Purely archival jobs, disk-audit reports, no human review needed |
| `"all"` | Broadcasts to all connected home channels | Multi-platform setups (Telegram + Discord + etc.) |
| `"telegram:<chat_id>"` | Specific Telegram chat/channel/group | Separate log channel, team notification, topic-specific delivery |

### Set delivery when creating/updating jobs

```python
# Creating a new job — always set deliver explicitly
cronjob(
    action="create",
    name="daily-digest",
    schedule="0 23 * * *",
    prompt="Generate today's diary...",
    profile="cron-worker",
    deliver="origin",      # ← MUST set explicitly
    model={"model": "deepseek-v4-flash", "provider": "deepseek"},
)

# Changing an existing job's delivery
cronjob(action="update", job_id="1ca6e7d692fa", deliver="local")
```

> [!warning] **Without a gateway, you CANNOT:** DM the bot on Telegram, use webhook triggers (`hermes webhook subscribe`), or trigger one-off tasks from Telegram. Only `hermes --profile cron-worker "task"` from CLI + scheduled cron jobs work.

---

## Recommendation

| Scenario | Recommendation |
|----------|---------------|
| Cron-only: only scheduled jobs, no one-off DM tasks | **Skip gateway** (Path B). Use `deliver="origin"` for results. |
| Want to DM the worker, webhook triggers, manual Telegram tasks | **Add gateway** (Path A). 30s setup. |
| Not sure yet | **Start without.** Add later with `hermes --profile cron-worker gateway install` anytime. |
| Want both cron delivery AND DM capability | **Add gateway** — gives you both. The extra 104MB RSS is negligible on a 16GB machine. |
