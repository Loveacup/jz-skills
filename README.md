# 🏛️ jz-skills · AI Agent Skills Hub

<p align="center">
  <b>🇺🇸 English</b> · <b>🇨🇳 中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-60-blue" alt="60 skills">
  <img src="https://img.shields.io/badge/platforms-Hermes%20%7C%20CC%20%7C%20pi-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/sync-bidirectional-green" alt="bidirectional sync">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT license">
</p>

> 🤖 **Hermes + Claude Code + pi 三端 AI agent 技能仓库 — 60 skills, 四层结构, 双向同步。**
>
> Skills authored, audited, and evolved by AI agents following [skill-authoring v3.0](shared/skill-authoring/). Deployed to a 15-profile Hermes governance system (三省六部), Claude Code, and pi (Windows).

---

## 🌲 Structure · 四层结构

```
jz-skills/
├── shared/         🌐 跨平台通用 (Hermes + CC + pi) — 16 skills
├── hermes/         ⚙️ Hermes 平台 — 15 skills
├── hermes-3S6M-profiles/ 🏯 三省六部体系 — 23 skills → [详情](https://github.com/Loveacup/hermes-s6m-a2a) → [详情](https://github.com/Loveacup/hermes-s6m-a2a)
└── pi/             🪟 Pi (Windows) — 6 skills
```

| Layer | Directory | Skills | Scope |
|:---|:---|:---:|:---|
| 🌐 | `shared/` | 16 | All 3 platforms |
| ⚙️ | `hermes/` | 15 | Hermes (non-3S6M) |
| 🏯 | `hermes-3S6M-profiles/` | 23 | 三省六部 governance → [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a) |
| 🪟 | `pi/` | 6 | Pi (Windows), self-authored |

---

## 🔥 Active Skills · 高频更新

Skills with rapid iteration cycles — multiple versions in recent months, significant complexity, or frequent improvement.

### 🔍 web-research-router · 检索总控 v3.8

Multi-engine search router with deep research capabilities. **22 reference files**, the most complex skill in the repo.

- **5 engines:** Exa + Brave (dual-primary) → Tavily (deep research) → web_search (broad scan) → SearXNG (fallback)
- **Deep loop:** Plan → Section (facts.jsonl) → Reflect → Merge with cross-language blind-spot detection
- **Anti-hallucination:** Verbatim quote extraction, `[s<id>]` inline citation contract, 3-column output (Confirmed / Inference / Conflicts)
- **Step 0 mandatory:** Supermemory → session → qmd/Obsidian → CodeGraph before any public web call
- **Recent:** v3.8 Claude Code WebSearch backup engine; v3.7 SearXNG demoted after cross-platform validation

→ [`hermes/web-research-router/`](hermes/web-research-router/) · references: 22 · [MCP config](hermes/web-research-router/#-mcp-configuration--deployment)

---

### 📔 auto-diary · 自动化日记 v3.5

Daily diary + weekly/monthly/yearly report generation triggered by cron. Rapidly evolving architecture.

- **v3.5 (latest):** Pyramid aggregation — daily → weekly → monthly → yearly with cron scheduling + validation
- **v3.4:** Real validation loop, fixed internal contradictions
- **v3.1:** CC session classification (3 types: agent-team / independent / programmatic) + KB↔AI cross-linking
- **v3.0:** Obsidian-md-ac formatted output with YAML frontmatter, callouts, section dividers
- **Format fixes:** `~` expansion bug, event-bridge exclusion, emoji corrections (🦞→💻)

→ [`hermes/auto-diary/`](hermes/auto-diary/)

---

### 🩺 mac-doctor · macOS 系统巡检 v2.2

Six-tier macOS health monitoring — 50+ checks, 19 files, 2,135 lines. Absorbed 9 OSS projects (mole, mactop P0).

- **6 layers:** Health scoring + root-cause diagnosis → Security audit (27 items) → Hardware diagnostics → Network check → Privacy scan → Historical tracking
- **Dual cron:** LLM agent (daily deep audit) + Silent Watchdog (30min, no_agent, anomaly-only push)
- **v2.3:** Watchdog threshold-vs-anomaly silent logic fix; None-handling robustness

→ [`hermes/mac-doctor/`](hermes/mac-doctor/)

---

### 🕐 cron-worker · 定时任务 Agent v1.3

Dedicated cron-worker profile architecture with four heartbeat patterns and cross-profile skill pool integrity watchdog.

- **4 heartbeat patterns:** Cron (time-driven) → Signal/Webhook (event-driven) → Change detection (state diff) → Silent watchdog (anomaly-only)
- **Skill integrity watchdog:** Full-depth enumeration (132 skills, find vs glob's 124 blind-spotted), manifest baseline diff, 4-level alerting (CRITICAL/WARN/INFO/CLEAN)
- **Cross-profile pool:** default (owner) + regent + cron-worker share one pool via `external_dirs` — base skills (including github) auto-sync across all three
- **Defense layers:** L1 prevention (`skill_sync.py` patch) + L2 monitoring (watchdog) + L2 cleanup (daily shell)

→ [`hermes/cron-worker/`](hermes/cron-worker/) · [skill-integrity-watchdog 595 lines](hermes/cron-worker/scripts/skill-integrity-watchdog.py)

---

### 🤖 claude-code · CC 编排 v3.5

Orchestrate Claude Code CLI from Hermes — print mode, interactive tmux, agent team.

- **v3.5.0:** Smart effort routing + agent team enhancement
- **v3.5.1:** Pitfall #24 — false-idle detection (CC appears stuck but is actually thinking)
- **Progress reporting:** Mandated template for CC session progress monitoring (15s first check → 30-60s polling)

→ [`hermes/claude-code/`](hermes/claude-code/)

---

### 📝 strategic-insight-longform · 战略洞察长文 v5.0

Long-form strategy analysis with multi-agent pipeline.

- **v5.0:** CC-native pipeline + 4-layer quality gate + dual-axis methodology
- **Architecture:** 16-agent pipeline (internal) + S-T-D framework + GoT adaptive pathing
- **Genre mapping:** Strategic reports, industry analysis, market scans, competitive intelligence

→ [`shared/strategic-insight-longform/`](shared/strategic-insight-longform/)

---

## 📋 Full Skill Catalog · 完整目录

### 🌐 shared/ — 跨平台通用 (16)

| Skill | Purpose |
|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub ops: auth, issues, PR, code review, exploration, README |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs + ADR |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | 7-dim compliance scoring, 11-step flow, dual-role review |
| 📄 [`pdf`](shared/pdf/) | PDF: OCR, extract, edit, Markdown→PDF (mobile 430×932px) |
| 📝 [`strategic-insight-longform`](shared/strategic-insight-longform/) | Strategy analysis, multi-agent pipeline — see [§active](#-strategic-insight-longform--战略洞察长文-v50) |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech transcript → structured markdown |
| 🎧 [`audio-transcriber`](shared/audio-transcriber/) | Noise-gated denoise + speaker diarization + Chinese ASR (Qwen3-MLX) |
| ⚖️ [`china-legal-optimized`](shared/china-legal-optimized/) | 中国法务：合同/劳动/知产/公司/诉讼/个人/物业 7 领域 |
| 🔮 [`destiny-matrix`](shared/destiny-matrix/) | 荣格八维 + 八字 + 紫微 + 占星 multi-modal analysis |
| 📐 [`methodology-writer`](shared/methodology-writer/) | Experience → structured methodology documents |
| 📓 [`obsidian`](shared/obsidian/) | Vault ops, CLI, plugin dev, Bases, Defuddle |
| 🧷 [`obsidian-md-ac`](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas reference |
| 🧠 [`supermemory-maintenance`](shared/supermemory-maintenance/) | Supermemory reference v6: architecture, SDK, diagnostics |
| 🎴 [`xiaohongshu-cards`](shared/xiaohongshu-cards/) | Article → 1080×1440 RED card images via Playwright |

### ⚙️ hermes/ — Hermes 平台 (15)

| Skill | Purpose |
|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | Multi-engine search + deep research — see [§active](#-web-research-router--检索总控-v38) |
| 📔 [`auto-diary`](hermes/auto-diary/) | Daily/weekly/monthly/yearly diary — see [§active](#-auto-diary--自动化日记-v35) |
| 🩺 [`mac-doctor`](hermes/mac-doctor/) | macOS 6-tier health monitor — see [§active](#-mac-doctor--macos-系统巡检-v22) |
| 🕐 [`cron-worker`](hermes/cron-worker/) | Cron profile + 4 heartbeats + pool watchdog — see [§active](#-cron-worker--定时任务-agent-v13) |
| 🤖 [`claude-code`](hermes/claude-code/) | CC orchestration — see [§active](#-claude-code--cc-编排-v35) |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis |
| 🧠 [`llm-wiki`](hermes/llm-wiki/) | Karpathy-style LLM knowledge base |
| 📚 [`arxiv`](hermes/arxiv/) | Academic paper search |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video deep analysis |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | Xiaohongshu CDP content extraction |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar & reminders |
| ↩️ [`reply-context-retrieval`](hermes/reply-context-retrieval/) | Telegram reply context retrieval |
| ✂️ [`de-slop`](shared/de-slop/) | Bilingual AI writing detection & humanization |
| 🧠 [`supermemory-hermes`](hermes/supermemory-hermes/) | Cabinet memory architecture manual |

### 🏯 hermes-3S6M-profiles/ — 三省六部 (23)

> 三省六部 Agent 治理体系 — 15 profiles, 23 skills, Kanban task routing.
>
> **→ 完整架构与 A2A 协议文档：** [Loveacup/hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a)

| Layer | Count | Highlights |
|:---|:---:|:---|
| `common/` | 2 | [`three-provinces-constitution`](hermes-3S6M-profiles/common/three-provinces-constitution/) v3.0 · [`financial-research-agents`](hermes-3S6M-profiles/common/financial-research-agents/) |
| `regent/` 👑 | 5 | `kanban-orchestrator` `kanban-worker` `morning-news-briefing` v4.0 — **only 3S6M profile with gateway** |
| `gongbu/` 🛠️ | 5 | Infrastructure, monitoring, Surge gateway |
| `tester/` ⚖️ | 2 | Code review, security audit |
| `jiangzuojian/` 🔧 | 2 | Delivery gate, specialist review |
| Other 10 depts | 1 each | archivist, auditor, budget, hanlinyuan, protocol, registry, shangshu ([A2A](https://github.com/Loveacup/hermes-a2a)), dispatcher, engineer, planner |

### 🪟 pi/ — Pi (Windows) (6)

| Skill | Purpose |
|:---|:---|
| 🔍 `web-research-router` | TypeScript SDK search routing |
| 🔍 `pi-web-research` | Multi-engine deep research v3.4 |
| 🛡️ `pi-grill` | Ambiguity guardian v3.1 |
| ✍️ `skill-creator` | Compliance-first authoring v6.0 |
| 🔗 `pi-hermes-setup` | Pi ↔ Hermes SSH + MCP |
| 🧠 `pi-supermemory` | Windows Supermemory integration |

---

## 🚀 Quick Start

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills

# Deploy to one platform
cd ~/code/jz-skills && ./deploy/sync-all.sh hermes   # → ~/.hermes/skills/
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

---

## 🔄 Sync · 同步

```bash
# 📤 Push: local → GitHub (auto-sanitized)
./deploy/sync-back.sh --dry-run   # preview
./deploy/sync-back.sh             # apply (strips paths, emails, API keys)

# 📥 Pull: GitHub → local
git pull && ./deploy/sync-all.sh <platform>
```

🛂 **Gateway restart needed** when skills change for `regent` or `default`:

```bash
hermes gateway restart -p regent
hermes gateway restart -p default
```

> Other 13 3S6M profiles are internal-dispatch — no gateway restart required.

---

## 🤝 Contributing

1. Edit skills on your agent or directly in repo
2. `./deploy/sync-back.sh --dry-run` — preview
3. `./deploy/sync-back.sh` — sync with auto-sanitization
4. Commit and push

---

## 📜 License

MIT — see [LICENSE](LICENSE).
