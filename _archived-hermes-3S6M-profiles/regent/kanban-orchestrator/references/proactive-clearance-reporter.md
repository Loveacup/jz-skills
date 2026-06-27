# Proactive Kanban Clearance Reporter (Agent Mode)

Agent-mode cron that detects Kanban board clearance and delivers a
ceremonial report to the Emperor via Telegram — **as the 监国太子,
not as a script**.

## Problem

When the Kanban board clears (all tasks done/archived), the Telegram
request-response model prevents the regent from independently waking up
and reporting. The Emperor explicitly dislikes script notifications:
> "算是收到了吧，但看上去像脚本，你没激活agent回复我"
> "我再强调一下，只想要你主动和我对话"

The fix: an agent-mode cron that synthesizes a proper ceremonial report
in the 监国太子's voice, with the script layer only serving as a wake-gate.

## Architecture

```
Kanban board clears (active → 0)
  ↓ ≤5min
coordinator-poll / watchdog writes final-results/kanban-cleared-*.json
  ↓ ≤2min
kanban-clearance-reporter.py --agent-mode (wake-gate script)
  → detects new unreported final-result → outputs JSON task data
  → OR: already reported → outputs nothing → agent skipped
  ↓
agent (kimi-k2.6) receives JSON as context via cron framework
  → synthesizes ceremonial report as 监国太子
  → outputs to final response (NO send_message)
  ↓
cron auto-delivers agent's response to Telegram origin
```

## Components

### 1. Wake-gate script: `kanban-clearance-reporter.py --agent-mode`

Path: `~/.hermes/profiles/regent/scripts/kanban-clearance-reporter.py`
Wrapper: `~/.hermes/profiles/regent/scripts/kanban-clearance-reporter-agent.sh`

Behavior:
- Scans `active_count` from Kanban DB and `final-results/*.json` for latest.
- Compares `latest_final_result` against `last_reported_final_result` in state.
- **New clearance detected** → outputs JSON with `status: "cleared"` and task data → agent wakes up.
- **Already reported** → outputs nothing → `_build_job_prompt` returns None → `[SILENT]` → agent skipped.
- State file: `~/.hermes/profiles/regent/state/kanban-clearance-reporter-state.json`

JSON output format (agent mode):
```json
{
  "status": "cleared",
  "reason": "unreported_final_result|transition",
  "final_result_path": "/path/to/kanban-cleared-*.json",
  "active_count": 0,
  "tasks": [
    {"id": "t_xxx", "title": "...", "assignee": "reviewer", "summary": "..."}
  ]
}
```

### 2. Agent-mode cron job

Job: `kanban-clearance-reporter` (ID: `72af3d2fd31a`)
```json
{
  "no_agent": false,
  "deliver": "origin",
  "script": "kanban-clearance-reporter-agent.sh",
  "model": "MiniMax-M2.7",
  "provider": "minimax-cn",
  "schedule": "every 2m"
}
```

Key design decisions:
- **`no_agent=false`**: Agent synthesizes the report — this is the whole point.
- **`deliver=origin`**: Cron framework auto-delivers the agent's final response.
- **DO NOT use `send_message`** in the prompt — the cron hint already says "Your final response will be automatically delivered." Using `send_message` creates a conflict → agent outputs `[SILENT]`.
- **Model: MiniMax-M2.7** (via minimax-cn, Anthropic Messages API). Requires `extra_body: {thinking: {type: "disabled"}}` in config to prevent thinking layer from consuming tokens on this simple synthesis task. Latency ~4s vs kimi-k2.6's ~10s. Text-only model, sufficient for this task class.

### 3. Agent prompt

The key instruction to embed in the agent prompt:
```
你是监国太子奏报官。读取上下文中的 Script Output JSON。若 status=cleared：
以监国太子身份，用正式奏对礼仪向父皇复命。角色名译中文。
输出格式：📜 *奏事处呈 · 父皇御览* → 任务摘要 → 伏请圣鉴 → 📨 成果信箱。
**不要用 send_message**，系统自动投递你的回复。
若上下文无有效任务数据，只输出 [SILENT]。
```

### 4. Ceremonial output format (agent synthesized)

```
📜 *奏事处呈 · 父皇御览*
──── 看板清空 ────
启禀圣上，三省六部本批案件已全部完结，谨奏：

✅ 门下省 · morning-news-20260525-mobile-pdf-layout-v2-delivery —— PDF 13页/323×690pt，来源台账合规。

伏请圣鉴。
📨 成果信箱：`/path/to/kanban-cleared-*.json`
```

## Deployment checklist

- [x] `kanban-clearance-reporter.py --agent-mode` outputs JSON when clearance detected
- [x] `kanban-clearance-reporter-agent.sh` wrapper created and executable
- [x] Cron job `72af3d2fd31a` set to `no_agent=false`, `deliver=origin`
- [x] Agent prompt does NOT mention `send_message`
- [x] Test: script `--dry-run` produces correct JSON
- [x] Test: agent cron run → `delivered to telegram:7931997806 via live adapter`
- [x] Test: agent response uses ceremonial format (not script format)
- [x] Test: second run → script outputs empty → agent skipped → `[SILENT]`
- [x] Test: third run remains silent (dedup confirmed)

## Pitfalls

**"Script notification feels impersonal" (第8/9次纠正).** The Emperor rejected script-mode notifications: "看上去像脚本，你没激活agent回复我." Always use agent mode for user-facing clearance reports. The script is ONLY a wake-gate + data provider.

**send_message conflict.** The cron hint says "do NOT use send_message" while a prompt that says "use send_message" creates a conflict → agent outputs [SILENT]. Fix: remove all send_message instructions from the agent prompt; let cron auto-deliver.

**Double-fire on first agent run.** When switching from script mode to agent mode, the state file may have `last_reported_final_result: null` even though the previous script-mode run already delivered. Result: agent fires once (correctly filling the gap), then the state is updated and subsequent runs are silent. This is acceptable — one extra notification during the mode switch is better than missing one.

**Must test after any change.** Any modification to this cron/script/prompt MUST be tested end-to-end: compile check, dry-run logic, agent synthesis quality (ceremonial vs script format), dedup, and actual cron delivery log. The Emperor explicitly ordered testing after each optimization.

## Cost

Agent fires only when clearance detected (typically 1-3×/day). At ~$0.01/run (kimi-k2.6, 1 turn): ~$0.30-0.90/month. Zero cost while board has active work (script returns empty → agent skipped).

## Files

| File | Purpose |
|---|---|
| `scripts/kanban-clearance-reporter.py` | Wake-gate + data collection script |
| `scripts/kanban-clearance-reporter-agent.sh` | Wrapper passing `--agent-mode` |
| `state/kanban-clearance-reporter-state.json` | Tracks `last_reported_final_result` for dedup |
| `state/regent-inbox/final-results/kanban-cleared-*.json` | Coordinator-poll output consumed by reporter |
| `cron/jobs.json` | Job `72af3d2fd31a` definition |
| `cron/output/72af3d2fd31a/` | Historical run output (agent responses + prompts) |
