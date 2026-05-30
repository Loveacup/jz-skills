---
name: cron-worker
description: "Use when the user wants to create, configure, or migrate a dedicated cron-worker Hermes profile for scheduled/background tasks. Covers profile creation with symlink-based identity sharing (SOUL.md, memory), skill external_dirs configuration, model downgrade for cost savings, cron job migration, three heartbeat patterns (cron, signal/hook, change-detection), and artifact logging discipline. Triggers on: 创建cron-worker, 定时任务agent, 迁移cron job, cron profile, background agent profile, scheduled task worker, 后台任务profile, 分离定时任务. DO NOT use for one-off cron job creation or general Hermes config/debugging questions — use hermes-agent or hermes-setup instead."
version: 1.0.0
author: Hermes Agent + Alex
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, cron, profile, worker, scheduled-tasks, background, cost-optimization]
    related_skills: [hermes-agent, hermes-setup, calendar-manager]
---

# Cron-Worker Profile

Create a dedicated Hermes profile for scheduled/background tasks — isolated sessions, cheaper model, shared identity with the default assistant.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just create the profile and figure it out" | Symlink + external_dirs order matters. Wrong order = broken identity sync. Follow Step 2 exactly. |
| "The cron job works fine on default, why move it" | Agent-mode cron jobs on default burn expensive models (v4-pro) for routine work. Moving to cron-worker with v4-flash cuts cost 60%+. |
| "I don't need change-detection, cron is enough" | Blindly running every tick costs LLM tokens on 95% of ticks where nothing changed. A hash pre-check pays for itself within days. |
| "I'll add the artifact log later" | Silent failures are indistinguishable from healthy idle. Without per-run logging, you're debugging by intuition. |

## 🔀 Decision Tree

```
User wants to set up cron/background task isolation?
├── Haven't audited existing cron jobs yet → Step 0: Audit first
├── New cron-worker profile → Step 1: Create profile
├── Existing profile, want to migrate jobs → Step 3: Migrate cron jobs
├── Already have cron-worker, want to add trigger pattern → Step 4: Heartbeat patterns
├── Cron job failed silently, want observability → Step 5: Artifact logging
├── Want to interact with cron-worker directly (DM the bot) → Step 2g: Optional gateway
└── Just exploring the concept → Read the Obsidian doc first
```

## Step 0: Audit Existing Cron Jobs

**Before creating a worker profile, audit what's already running.** List all jobs and classify each one:

```bash
hermes cron list
```

For each job, ask:
- **Is it still needed?** → If no → `cronjob(action="remove", job_id="...")`
- **Is it agent-mode or script-mode?** → Agent-mode = candidate for model downgrade
- **Does it deliver to Telegram?** → May want to switch to `local` delivery
- **Is it redundant?** (e.g., sync scripts superseded by Supermemory)

> [!tip] 💡 本会话经验：从 4 个 cron job 开始，删掉 3 个（季度归档、memory sync、MCP 同步），只保留 1 个（每日日记），再设计 worker。先瘦身再建架构。

---

## Step 1: Create the Cron-Worker Profile

```bash
hermes profile create cron-worker --clone
```

This clones the current default profile (personality, skills, config, memory).

## Step 2: Set Up Identity Sharing (Symlink + External Dirs)

**Order matters.** Do symlinks first, then external_dirs.

### 2a. SOUL.md — Symlink to Default

```bash
rm ~/.hermes/profiles/cron-worker/SOUL.md
ln -sf ~/.hermes/SOUL.md ~/.hermes/profiles/cron-worker/SOUL.md
```

Hermes explicitly supports SOUL.md symlinks (`utils.py:62-82`, GitHub #16743). Modifications write through to the original file.

### 2b. Memory — Symlink to Default

```bash
rm -rf ~/.hermes/profiles/cron-worker/memories
ln -sf ~/.hermes/memories ~/.hermes/profiles/cron-worker/memories
```

This syncs both MEMORY.md and USER.md. Corrections/preferences learned in default propagate to cron-worker.

### 2c. Skills — External Dirs (Prefer Over Symlink)

Add to `~/.hermes/profiles/cron-worker/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.hermes/skills
```

`agent/skill_utils.py:241` — first-class feature. `os.walk(followlinks=True)` ensures symlinked skill dirs are followed. Cleaner than symlinking the entire skills/ directory — the curator won't accidentally touch externally-referenced skills, and cron-worker can still add its own.

### 2d. Long-Term Memory — Auto-Match Main Agent

Cron-worker must share long-term memory with the default profile. Hermes supports two providers — auto-detect which one is active and mirror it.

**Detection:**

```bash
hermes memory status | awk '/^  Provider:/ {print $2}'
```

| Output | Provider | Action |
|--------|----------|--------|
| `provider: supermemory` | Supermemory | Copy config + ensure API key |
| `provider: hindsight` | Hindsight | Copy config + use same `bank_id` |
| `provider: ""` | None (built-in only) | Skip — built-in MEMORY.md already symlinked |

#### If Supermemory

```bash
# Copy config (same container_tag = same pool)
cp ~/.hermes/supermemory.json ~/.hermes/profiles/cron-worker/supermemory.json

# Ensure API key (if cron-worker has independent .env)
grep -q SUPERMEMORY_API_KEY ~/.hermes/profiles/cron-worker/.env 2>/dev/null || \
  grep SUPERMEMORY_API_KEY ~/.hermes/.env >> ~/.hermes/profiles/cron-worker/.env
```

Verify `container_tag` is `"hermes"` in the copied JSON.

#### If Hindsight

```bash
# Copy config
cp ~/.hermes/hindsight/config.json ~/.hermes/profiles/cron-worker/hindsight/config.json

# IMPORTANT: Change bank_id_template → bank_id to share the same bank
# Edit ~/.hermes/profiles/cron-worker/hindsight/config.json:
#   Remove "bank_id_template": "hermes-{profile}"
#   Add    "bank_id": "hermes"
```

Without this edit, `bank_id_template` auto-generates `"hermes-cron-worker"` — a separate bank, defeating the purpose. Explicit `bank_id: "hermes"` forces the same bank as default.

Then enable:

```bash
hermes --profile cron-worker config set memory.provider hindsight
```

**⚠️ Only one external provider is active at a time.** If you switch the main agent from Hindsight to Supermemory later, re-run this section for cron-worker.

### 2e. Model Downgrade

```bash
hermes --profile cron-worker config set model.default deepseek-v4-flash
```

Routine cron tasks don't need reasoning. v4-flash is 60%+ cheaper than v4-pro. For script-mode jobs (no_agent=true), model is irrelevant — still worth setting for the one agent-mode job.

### 2f. Verify

```bash
hermes --profile cron-worker config show | grep -E "model|external"
ls -la ~/.hermes/profiles/cron-worker/SOUL.md  # should show symlink
```

### 2g. Gateway Decision — Choose Communication Channel

> [!important] **MUST use `clarify()` here.** After completing Steps 2a–2f, ask the user whether to add a gateway. Do NOT assume — the resource impact is meaningful, and a wrong choice wastes either a bot token or the ability to DM.

**Clarify prompt template:**

```
question: "给 cron-worker 加独立 gateway 吗？加了可以 DM bot 交互、webhook 触发；不加更轻量，cron job 走 scheduler 投递。"
choices:
  - "加 gateway，我去 @BotFather 创建新 bot"
  - "加 gateway，我已有 token 直接配"
  - "不加 gateway，cron-only 就够了"
```

**Full instructions → `references/gateway-decision.md`** — covers Path A (get token, write .env, install, verify, harmless errors, resource impact) and Path B (delivery mechanism, `deliver` target matrix, code examples, recommendation table).

**Quick summary:**

| Path | What you get | What you need |
|------|-------------|---------------|
| A: Add gateway | DM the bot, webhook triggers, direct Telegram interaction | Separate bot token, ~104MB RSS |
| B: Skip gateway | Lighter, cron jobs deliver via scheduler (`deliver="origin"`) | Nothing extra |

**Default recommendation:** start without gateway (Path B). Add anytime with `hermes --profile cron-worker gateway install`.

---

## Step 3: Migrate Existing Cron Jobs

Use `cronjob(action="update", job_id="...", profile="cron-worker")` to reassign jobs.

```python
cronjob(action="update", job_id="1ca6e7d692fa", profile="cron-worker")
```

Then verify:

```bash
hermes cron list  # should show profile: cron-worker
```

**⚠️ Delivery mechanism:** The default gateway's cron scheduler handles delivery for ALL cron jobs, regardless of which profile they run under. `deliver="origin"` routes output through the scheduler back to your Telegram — cron-worker does NOT need its own gateway for cron job delivery. Cron jobs are transient processes that fire on each tick; the gateway only matters if you want to DM the bot interactively (see Step 2g).

---

## Step 4: Three Heartbeat Patterns

Reference: Knowlee *Heartbeat Patterns (2026)*.

### 4a. Cron Heartbeat — Time-Driven

Standard Hermes cron. Best for fixed-cadence tasks where work is identical each cycle.

```python
cronjob(
    action="create",
    name="daily-digest",
    schedule="0 23 * * *",
    prompt="Generate today's diary...",
    profile="cron-worker",
    model={"model": "deepseek-v4-flash", "provider": "deepseek"},
)
```

### 4b. Signal Heartbeat — Event-Driven (Hook)

Use Hermes webhooks as the signal channel. External system POSTs → webhook endpoint → cron-worker handles.

```bash
# Create webhook endpoint
hermes --profile cron-worker webhook subscribe github-push
```

Then configure the external system (GitHub, CI, monitoring) to POST to the webhook URL.

### 4c. Change-Detection Heartbeat — State-Diff-Driven

**Highest cost-saving leverage.** Run frequently, but only invoke the LLM when state changed.

```python
cronjob(
    action="create",
    name="pipeline-monitor",
    schedule="*/15 * * * *",
    script="monitor-hash.py",   # ← script runs first, output auto-prepended as "## Script Output"
    prompt="State changed. Analyze and alert if needed.",
    profile="cron-worker",
    model={"model": "deepseek-v4-flash", "provider": "deepseek"},
)
```

The `script` runs first — its stdout is auto-prepended to the prompt as `## Script Output` by the scheduler. To skip the agent run when no change detected, the script's **last non-empty line** must be the JSON `{"wakeAgent": false}`. Any other output triggers the agent. See `scripts/change-detection.py` for a complete template with hash persistence.

---

## Step 5: Artifact Logging

Every cron run must produce an artifact, even when the answer is "nothing to do." Without this, silent failures are indistinguishable from healthy idle.

### Minimum Viable Log

Add this line to the END of every agent-mode cron prompt:

```
After completing (or determining no action is needed), append ONE line to
~/Obsidian/AlexCai/50-Self/01_日记/cron-artifact-log.md:
- `[CRON] [YYYY-MM-DD HH:MM] [job_name] [OK|FAIL|SKIP] [key_metric] [action_taken]`
```

Example output:
```markdown
- `[CRON] [2026-05-30 23:02] 每日日记草稿 OK 1 entry written`
- `[CRON] [2026-05-31 06:00] pipeline-monitor SKIP no_change`
- `[CRON] [2026-05-31 06:15] pipeline-monitor FAIL API timeout`
```

---

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Symlink replaced by profile update | `hermes profile create` writes fresh files. Re-apply symlinks after any profile recreation. |
| external_dirs path uses `~` but not expanded | `agent/skill_utils.py:305` calls `os.path.expanduser()` — `~` is safe. |
| Cron job still runs on default after update | Verify with `hermes cron list` — check the `profile` column. |
| Gateway: when to add vs skip | Without gateway, cron jobs still deliver via scheduler (`deliver="origin"`). Add a gateway (Step 2g) only if you want to DM the bot interactively. Gateway requires a **separate Telegram bot token** — one gateway = one bot. Adds ~104MB RSS per gateway process. |
| Gateway: api_server port 8460 conflict | Expected and harmless — default gateway already owns 8460. Telegram polling works without api_server. Ignore the error. |
| Gateway: wrong bot token after profile clone | `hermes profile create --clone` copies default's TELEGRAM_BOT_TOKEN into cron-worker's .env. After cloning, always `grep -n TELEGRAM_BOT_TOKEN` and replace with the correct bot token. |
| Change-detection script doesn't skip idle ticks | Script's last non-empty stdout line must be `{"wakeAgent": false}` JSON. Any other output wakes the agent. Empty stdout ALSO wakes the agent — do not rely on silence. |
| Forgot to pin model on cron job | Always set `model` explicitly in `cronjob()` calls. Default model may be rate-limited or wrong tier. |
| Hermes upgrade breaks symlinks | `hermes update` may refresh profile files. After any upgrade, re-run Step 2a-2b to re-apply SOUL.md + memory symlinks. |

---

## ✅ Verification Checklist (RUN AFTER SETUP)

- [ ] `ls -la ~/.hermes/profiles/cron-worker/SOUL.md` shows symlink → `~/.hermes/SOUL.md`
- [ ] `ls -la ~/.hermes/profiles/cron-worker/memories` shows symlink → `~/.hermes/memories`
- [ ] `grep external_dirs ~/.hermes/profiles/cron-worker/config.yaml` returns `~/.hermes/skills`
- [ ] `hermes --profile cron-worker config show | grep model.default` shows `deepseek-v4-flash`
- [ ] Migrated cron jobs show `profile: cron-worker` in `hermes cron list`
- [ ] **Gateway:** Path A → `gateway status` shows connected + test DM. Path B → no plist + `deliver` set on jobs. (Details → `references/gateway-decision.md`)
- [ ] Artifact log path exists and first entry written after a test run

**Every box must honestly pass. If unchecked, go back.**
