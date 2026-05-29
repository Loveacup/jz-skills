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
├── New cron-worker profile → Step 1: Create profile
├── Existing profile, want to migrate jobs → Step 3: Migrate cron jobs
├── Already have cron-worker, want to add trigger pattern → Step 4: Heartbeat patterns
├── Cron job failed silently, want observability → Step 5: Artifact logging
└── Just exploring the concept → Read the Obsidian doc first
```

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

### 2d. Model Downgrade

```bash
hermes --profile cron-worker config set model.default deepseek-v4-flash
```

Routine cron tasks don't need reasoning. v4-flash is 60%+ cheaper than v4-pro. For script-mode jobs (no_agent=true), model is irrelevant — still worth setting for the one agent-mode job.

### 2e. Verify

```bash
hermes --profile cron-worker config show | grep -E "model|external"
ls -la ~/.hermes/profiles/cron-worker/SOUL.md  # should show symlink
```

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

**⚠️ The default gateway's scheduler spawns the job under the specified profile.** No separate gateway needed for cron-worker — it runs as a transient process on each tick.

---

## Step 4: Three Heartbeat Patterns

Reference: Knowlee *Heartbeat Patterns (2026)*.

### 4a. Cron Heartbeat — Time-Driven

Standard Hermes cron. Best for fixed-cadence tasks where work is identical each cycle.

```python
cronjob(
    name="daily-digest",
    schedule="0 23 * * *",
    prompt="Generate today's diary...",
    profile="cron-worker",
    model={"provider": "deepseek", "model": "deepseek-v4-flash"},
)
```

### 4b. Signal Heartbeat — Event-Driven (Hook)

Use Hermes webhooks as the signal channel. External system POSTs → webhook endpoint → cron-worker handles.

```bash
# Create webhook endpoint
hermes webhook subscribe github-push --profile cron-worker
```

Then configure the external system (GitHub, CI, monitoring) to POST to the webhook URL.

### 4c. Change-Detection Heartbeat — State-Diff-Driven

**Highest cost-saving leverage.** Run frequently, but only invoke the LLM when state changed.

```python
cronjob(
    name="pipeline-monitor",
    schedule="*/15 * * * *",
    script="monitor-hash.py",   # ← script computes hash first (no LLM cost)
    prompt="State changed. Analyze and alert if needed:\n{SCRIPT_OUTPUT}",
    profile="cron-worker",
    no_agent=False,  # agent mode — but only fires when script detected change
)
```

The `script` runs first. Its stdout is injected into the prompt. Design the script to output nothing (empty stdout) when no change detected → agent loop never fires → zero LLM cost on idle ticks. See `references/change-detection-pattern.py` for a template.

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
| No gateway for cron-worker means no Telegram delivery | Correct. Use `deliver="local"` + artifact log, or `deliver="origin"` (which routes through the default gateway's delivery). |
| Change-detection script always outputs → LLM always fires | Script must output EMPTY stdout when no change. Use `sys.exit(0)` with no print. |
| Forgot to pin model on cron job | Always set `model` explicitly in `cronjob()` calls. Default model may be rate-limited or wrong tier. |
| Hermes upgrade breaks symlinks | `hermes update` may refresh profile files. After any upgrade, re-run Step 2a-2b to re-apply SOUL.md + memory symlinks. |

---

## ✅ Verification Checklist (RUN AFTER SETUP)

- [ ] `ls -la ~/.hermes/profiles/cron-worker/SOUL.md` shows symlink → `~/.hermes/SOUL.md`
- [ ] `ls -la ~/.hermes/profiles/cron-worker/memories` shows symlink → `~/.hermes/memories`
- [ ] `grep external_dirs ~/.hermes/profiles/cron-worker/config.yaml` returns `~/.hermes/skills`
- [ ] `hermes --profile cron-worker config show | grep model.default` shows `deepseek-v4-flash`
- [ ] Migrated cron jobs show `profile: cron-worker` in `hermes cron list`
- [ ] No gateway plist at `~/Library/LaunchAgents/ai.hermes.gateway-cron-worker.plist`
- [ ] Artifact log path exists and first entry written after a test run

**Every box must honestly pass. If unchecked, go back.**
