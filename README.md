# 🏛️ jz-skills · AI Agent Skills Hub

<p align="center">
  <b>🇺🇸 English</b> · <b>🇨🇳 中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-44-blue" alt="44 skills">
  <img src="https://img.shields.io/badge/profiles-15%20三省六部-orange" alt="15 profiles">
  <img src="https://img.shields.io/badge/platforms-Hermes%20%7C%20CC%20%7C%20pi-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/sync-bidirectional-green" alt="bidirectional sync">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT license">
</p>

> 🤖 **AI agent skills for Hermes (三省六部 15-profile governance), Claude Code, and pi — one repo, four layers, three platforms.**
>
> 🏯 **服务于 Hermes（三省六部 15 部门多智能体体系）、Claude Code 和 pi 的 AI 技能仓库 — 一库四层，三端同步。**

---

## 📖 目录

- [✨ Features · 特性](#-features--特性)
- [🚀 Quick Start · 快速开始](#-quick-start--快速开始)
- [📐 Architecture · 四层结构](#-architecture--四层结构)
- [📋 Skill Catalog · 技能目录](#-skill-catalog--技能目录)
- [🏯 三省六部 · 15 Profiles](#-三省六部--15-profiles)
- [🔄 Sync Workflow · 同步流程](#-sync-workflow--同步流程)
- [📦 Skill Format · 技能格式](#-skill-format--技能格式)
- [🤝 Contributing · 贡献](#-contributing--贡献)

---

## ✨ Features · 特性

| Category · 类别 | What you get · 你得到的 |
|:---|:---|
| 🌐 **Cross-platform** · 跨平台 | One skill, three agents — Hermes, Claude Code, and pi deploy from the same source |
| 🏯 **15-profile governance** · 三省六部 | 监国三省六部制: task routing, escalation, handoff across 15 specialized profiles |
| 🔄 **Bidirectional sync** · 双向同步 | `sync-back.sh` (local → GitHub, auto-sanitized) + `sync-all.sh` (GitHub → local) |
| 📋 **44 compliance-reviewed skills** · 合规审计 | Every skill passes 7-dimension audit: progressive disclosure, anti-rationalization, positioning |
| 🧹 **Auto-sanitization** · 自动脱敏 | Home paths → `~/`, emails → redacted, private IPs → redacted, API keys stripped before commit |
| 🤖 **AI-authored** · AI 创作 | Skills created, audited, evolved by AI agents — following skill-authoring v3.0 |

---

## 🚀 Quick Start · 快速开始

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills

# Deploy everything · 全量部署
cd ~/code/jz-skills && ./deploy/sync-all.sh all

# Deploy one platform · 单平台部署
./deploy/sync-all.sh hermes   # → ~/.hermes/skills/ + all 15 profiles
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

> **Prerequisites:** Hermes Agent, Claude Code CLI, or pi runtime. Each platform resolves its own dependencies.

---

## 📐 Architecture · 四层结构

```
🌐 Layer 1: shared/                    跨平台通用 (Hermes + CC + pi)
⚙️ Layer 2: hermes/                    Hermes 平台通用 (非三省六部)
🏯 Layer 3: hermes-3S6M-profiles/      三省六部体系
           ├── common/                全部门通用
           └── <dept>/                部门专属
🪟 Layer 4: pi/                        Pi (Windows) 专属
```

| Layer · 层 | Directory | Skills | Scope · 范围 |
|:---|:---|:---:|:---|
| 🌐 1 | `shared/` | 6 | Cross-platform — deployed to all 3 agents · 三端同步 |
| ⚙️ 2 | `hermes/` | 10 | Hermes platform — not 3S6M-specific · 平台通用 |
| 🏯 3a | `hermes-3S6M-profiles/common/` | 2 | 3S6M-wide — deployed to all 15 profiles · 全部门 |
| 🏷️ 3b | `hermes-3S6M-profiles/<dept>/` | 21 | Department-specific — deployed to one profile · 部门专属 |
| 🪟 4 | `pi/` | 5 | Pi (Windows) platform — authored by Pi itself · Pi 自创作 |

---

## 📋 Skill Catalog · 技能目录

### 🌐 Layer 1 — `shared/` · 跨平台通用

Deployed to Hermes + Claude Code + Pi · 三端同步。

| Skill | Purpose · 用途 |
|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub operations: auth, issues, PR, code review, exploration, README — 7 skills consolidated |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs + ADR · 设计审查 |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | Skill compliance: 11-step flow, 7-dim scoring, deployment-grounded audit · 合规创作 |
| 📄 [`pdf`](shared/pdf/) | PDF manipulation: OCR, extract, edit, convert · PDF 处理 |
| 📝 [`strategic-insight-longform`](shared/strategic-insight-longform/) | Long-form strategy analysis with multi-agent pipeline · 战略洞察长文 |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech/audio transcript → structured markdown · 语音转文稿 |

### ⚙️ Layer 2 — `hermes/` · 平台通用

Deployed to main Hermes + all 15 profiles. Not tied to 三省六部 governance.

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | Search routing: Exa / Tavily / Brave / arXiv / GitHub · 检索总控 |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis via TradingAgents · 交易分析 |
| 🧠 [`llm-wiki`](hermes/llm-wiki/) | LLM knowledge base builder (Karpathy's wiki) · LLM 知识库 |
| 📚 [`arxiv`](hermes/arxiv/) | Academic paper search and retrieval · 论文检索 |
| 📔 [`auto-diary`](hermes/auto-diary/) | Automated daily diary + weekly summary generation · 日记生成 |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video deep analysis with subtitle/transcription · B站视频分析 |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | Xiaohongshu (RED) content extraction via CDP · 小红书爬虫 |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar & reminders management for family · 智能日历管理 |
| ✂️ [`de-slop`](hermes/de-slop/) | Bilingual EN/ZH AI writing detector & humanizer · 中英双语去 AI 味 |
| 🤖 [`claude-code`](hermes/claude-code/) | Orchestrate Claude Code CLI: print mode, interactive tmux, agent team · CC 编排 |

### 🏯 Layer 3a — `hermes-3S6M-profiles/common/` · 全部门通用

Deployed to all 15 profiles. Foundation of the governance system · 治理体系基石。

| Skill | Purpose · 用途 |
|:---|:---|
| 📜 `three-provinces-constitution` | 三省六部 governance constitution v3.0 — task routing, escalation, handoff |
| 💹 `financial-research-agents` | Financial research via Kanban multi-profile orchestration |

### 🏷️ Layer 3b — `hermes-3S6M-profiles/<dept>/` · 部门专属

Deployed only to matching profile · 仅部署到对应部门。

| Department · 部门 | Profile | Skills |
|:---|:---|:---|
| 👑 监国太子 | `regent` | `kanban-orchestrator`, `kanban-worker`, `kanban-gate`, `6m-smoke-test`, `morning-news-briefing` |
| 🛠️ 工部 | `gongbu` | `disk-cleanup`, `infra-health-check`, `infra-monitoring`, `surge-gateway`, `agent-observability` |
| ⚖️ 刑部 | `tester` | `code-review-toolkit`, `agent-security-audit` |
| 🔧 将作监 | `jiangzuojian` | `delivery-gate`, `specialist-engineer` |
| 📡 尚书省 | `shangshu` | `a2a-protocol` |
| 🎭 礼部 | `protocol` | `md-to-pdf` |
| 🔎 御史台 | `auditor` | `agent-audit-evaluation` |
| 📖 史馆 | `archivist` | `agent-memory-manager` |
| 💰 户部 | `budget` | `agent-cost-manager` |
| 👥 吏部 | `registry` | `agent-registry` |
| 🎓 翰林院 | `hanlinyuan` | `deep-research-agent` |

### 🪟 Layer 4 — `pi/` · Windows 专属

Authored by Pi itself · Pi 自行创作。Deployed only to `~/.pi/skills/`.

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 `web-research-router` | Pi-native search routing (TypeScript SDK) · 检索总控 |
| 🛡️ `pi-grill` | Proactive ambiguity guardian v3.1 · 歧义守护 |
| ✍️ `skill-creator` | Compliance-first skill authoring v6.0 · 合规创作 |
| 🔗 `pi-hermes-setup` | Pi ↔ Hermes cross-machine SSH + MCP · 联动架构 |
| 🩹 `recover-hindsight-mcp` | Hindsight MCP recovery: ECONNRESET 6-step fix · MCP 恢复 |

---

## 🏯 三省六部 · 15 Profiles

> 监国三省六部制 Agent 架构 — 用户授权，监国统筹；中书拟案，门下封驳，尚书派工；六部分职，御史监察，史馆留痕。

| 三省 | Profile | 职能 |
|:---|:---|:---|
| 📝 中书省 | `planner` | 拟制方案 |
| 🚫 门下省 | `reviewer` | 封驳审核 |
| 📡 尚书省 | `shangshu` | 派工调度 |

| 六部 | Profile | 职能 |
|:---|:---|:---|
| ⚔️ 兵部 | `engineer` | 代码实现、架构、重构 |
| 🛠️ 工部 | `gongbu` | 基础设施、部署、监控 |
| 💰 户部 | `budget` | 数据搜索、统计、报表 |
| 🎭 礼部 | `protocol` | 文档编制、PDF 渲染 |
| ⚖️ 刑部 | `tester` | 代码审查、测试、安全 |
| 👥 吏部 | `registry` | Agent 管理、培训 |

| 独立机构 | Profile | 职能 |
|:---|:---|:---|
| 👑 监国太子 | `regent` | 总揽仲裁 |
| 🔎 御史台 | `auditor` | 独立审计 |
| 📖 史馆 | `archivist` | 全程归档 |
| 🔧 将作监 | `jiangzuojian` | 外聘工程专家 |
| 🎓 翰林院 | `hanlinyuan` | 知识研究 |

> v0.13 · 15/15 active · 六部 smoke test 全线闭环

---

## 🔄 Sync Workflow · 同步流程

Bidirectional sync between GitHub and local agents · GitHub ↔ 本地双向同步。

```bash
# 📤 Push: local changes → GitHub (auto-sanitized · 自动脱敏)
./deploy/sync-back.sh --dry-run   # 👀 preview · 预览
./deploy/sync-back.sh             # ✅ apply (strips home paths, emails, IPs, API keys)
git diff && git add <changed skills> && git commit -m "sync: <what changed>" && git push

# 📥 Pull: GitHub → local
git pull && ./deploy/sync-all.sh hermes
```

> 🧹 **Auto-sanitization:** `/Users/<name>/` → `~/`, emails → `<redacted>`, private IPs → `<redacted>`, API keys → `<redacted>`

---

## 📦 Skill Format · 技能格式

All skills follow the [Agent Skills standard](https://skills.sh):

```
skill-name/
├── 📄 SKILL.md          ← YAML frontmatter + markdown body (required)
├── 📁 references/        ← Progressive disclosure docs
├── 🐍 scripts/           ← Runnable helpers
├── 🖼️ templates/         ← Output templates
└── 🎨 assets/            ← Static assets
```

SKILL.md frontmatter:

```yaml
---
name: my-skill
description: "What it does · 做什么"
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [research, github]
---
```

---

## 🤝 Contributing · 贡献

1. ✏️ Edit skills on your agent, or directly in the repo
2. 👀 `./deploy/sync-back.sh --dry-run` — preview changes
3. ✅ `./deploy/sync-back.sh` — sync back with auto-sanitization
4. 📦 Commit and push
5. 🔄 Other machines: `git pull && ./deploy/sync-all.sh <platform>`

---

## 📜 License · 许可

MIT — see [LICENSE](LICENSE).
