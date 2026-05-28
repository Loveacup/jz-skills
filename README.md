# 🏛️ jz-skills · AI Agent Skills Hub

<p align="center">
  <b>🇺🇸 English</b> · <b>🇨🇳 中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-50-blue" alt="50 skills">
  <img src="https://img.shields.io/badge/profiles-15%20三省六部-orange" alt="15 profiles">
  <img src="https://img.shields.io/badge/platforms-Hermes%20%7C%20CC%20%7C%20pi-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/sync-bidirectional-green" alt="bidirectional sync">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT license">
</p>

> 🤖 **AI agent skills for Hermes (三省六部 15-profile governance), Claude Code, and pi — one repo, four layers, three platforms.**
>
> 🏯 **服务于 Hermes（三省六部 15 部门多智能体体系）、Claude Code 和 pi 的 AI 技能仓库 — 一库四层，三端同步。**

---

## 🌲 Full Structure · 全结构视图

```
jz-skills/
├── shared/                        # 🌐 跨平台通用 (Hermes + CC + pi) — 12 skills
│   ├── github/                    # GitHub 全操作
│   ├── grill-with-docs/           # 设计审查
│   ├── skill-authoring/           # 合规创作
│   ├── pdf/                       # PDF 处理
│   ├── strategic-insight-longform/# 战略洞察长文
│   ├── voice-to-markdown-workflow/# 语音转文稿
│   ├── audio-transcriber/         # 音频转录 (pyannote + Qwen3-MLX)
│   ├── china-legal-optimized/     # 中国法务七大领域
│   ├── destiny-matrix/            # 命运矩阵 (荣格八维 + 八字 + 紫微)
│   ├── methodology-writer/        # 方法论文创作
│   ├── obsidian-md-ac/            # Obsidian Markdown 完整参考
│   └── xiaohongshu-cards/         # 小红书图文卡片
├── hermes/                        # ⚙️ Hermes 平台通用 — 10 skills
│   ├── web-research-router/       # v3.2 · SearXNG + deep research + verbatim quote
│   ├── tradingagents/             # 交易分析
│   ├── llm-wiki/                  # LLM 知识库
│   ├── arxiv/                     # 论文检索
│   ├── auto-diary/                # 日记生成
│   ├── bilibili-video-analyzer/   # B站视频分析
│   ├── xhs-crawler/               # 小红书爬虫
│   ├── calendar-manager/          # 智能日历
│   ├── de-slop/                   # 中英双语去 AI 味
│   └── claude-code/               # CC 编排
├── hermes-3S6M-profiles/          # 🏯 三省六部体系
│   ├── common/                    # 全部门通用 — 2 skills
│   │   ├── three-provinces-constitution/  # 三省六部宪法 v3.0
│   │   └── financial-research-agents/     # 金融研究 Kanban 调度
│   └── <dept>/                    # 部门专属 — 21 skills
│       ├── regent/ (5)            # 👑 监国太子 · 唯一有 gateway 的 3S6M profile
│       │   └── morning-news-briefing/ v4.0 · SearXNG + verbatim + Sherman Kent
│       ├── gongbu/ (5)            # 🛠️ 工部 · 内部调度
│       ├── tester/ (2)            # ⚖️ 刑部 · 内部调度
│       ├── jiangzuojian/ (2)      # 🔧 将作监 · 内部调度
│       ├── archivist/ (1)         # 📖 史馆 · 内部调度
│       ├── auditor/ (1)           # 🔎 御史台 · 内部调度
│       ├── budget/ (1)            # 💰 户部 · 内部调度
│       ├── hanlinyuan/ (1)        # 🎓 翰林院 · 内部调度
│       ├── protocol/ (1)          # 🎭 礼部 · 内部调度
│       ├── registry/ (1)          # 👥 吏部 · 内部调度
│       └── shangshu/ (1)          # 📡 尚书省 · 内部调度
└── pi/                            # 🪟 Pi (Windows) — 5 skills
    ├── web-research-router/       # 检索总控 (TypeScript SDK)
    ├── pi-grill/                  # 歧义守护
    ├── skill-creator/             # 合规创作
    ├── pi-hermes-setup/           # 联动架构
    └── recover-hindsight-mcp/     # MCP 恢复
```

> 🛂 **Gateway 治理：** 三省六部 15 profile 中**只有 `regent`（监国太子）** 配置了对外 gateway（Telegram / iMessage / 邮件 等通道）。其余 14 个 profile 走 **内部调度，无对外通信**——由 regent 统一收发、按职能转派。`default`（小黄_主频道，非 3S6M）独立配 gateway，与 regent 互通走 A2A。

---

## 📖 目录

- [🌲 Full Structure · 全结构视图](#-full-structure--全结构视图)
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
| 📋 **50 compliance-reviewed skills** · 合规审计 | Every skill passes 7-dimension audit: progressive disclosure, anti-rationalization, positioning |
| 🧹 **Auto-sanitization** · 自动脱敏 | Home paths → `~/`, emails → redacted, private IPs → redacted, API keys stripped before commit |
| 🤖 **AI-authored** · AI 创作 | Skills created, audited, evolved by AI agents — following skill-authoring v3.0 |
| 🔬 **Deep research** · 深度研究 | Multi-step research loop with verbatim quote extraction, anti-refusal, query decomposition — based on 5 OSS projects · 多步深度研究：逐字引用、反拒绝、查询分解 |
| 🛂 **Gateway governance** · 网关治理 | 15 profile 中**仅 `regent` 配 gateway**（Telegram/iMessage/邮件），其余 14 个内部调度无对外通信。external 通信收口于太子 + A2A 走 `default` · Only `regent` has external gateway; all other 14 profiles are internal-only, dispatched by regent |

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
| 🌐 1 | `shared/` | 12 | Cross-platform — deployed to all 3 agents · 三端同步 |
| ⚙️ 2 | `hermes/` | 10 | Hermes platform — not 3S6M-specific · 平台通用 |
| 🏯 3a | `hermes-3S6M-profiles/common/` | 2 | 3S6M-wide — deployed to all 15 profiles · 全部门 |
| 🏷️ 3b | `hermes-3S6M-profiles/<dept>/` | 21 | Department-specific — deployed to one profile · 部门专属 |
| 🪟 4 | `pi/` | 5 | Pi (Windows) platform — authored by Pi itself · Pi 自创作 |

---

## 📋 Skill Catalog · 技能目录

### 🌐 Layer 1 — `shared/` · 跨平台通用

Deployed to Hermes + Claude Code + Pi · 三端同步。

| Skill | Purpose · 用途 | Refs · 引用 |
|:---|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub operations: auth, issues, PR, code review, exploration, README — 7 skills consolidated | ← `web-research-router` `grill-with-docs` `skill-authoring` |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs + ADR · 设计审查 | → `web-research-router` `github` |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | Skill compliance: 11-step flow, 7-dim scoring, deployment-grounded audit · 合规创作 | → `grill-with-docs` `web-research-router` `github` |
| 📄 [`pdf`](shared/pdf/) | PDF manipulation: OCR, extract, edit, convert · PDF 处理 | |
| 📝 [`strategic-insight-longform`](shared/strategic-insight-longform/) | Long-form strategy analysis with multi-agent pipeline · 战略洞察长文 | |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech/audio transcript → structured markdown · 语音转文稿 | |
| 🎧 [`audio-transcriber`](shared/audio-transcriber/) | Noise-gated denoise + speaker diarization (pyannote 4.x) + Chinese ASR (Qwen3-MLX) · 音频转录、声纹分离、降噪 | |
| ⚖️ [`china-legal-optimized`](shared/china-legal-optimized/) | 中国法务综合：合同审核 / 劳动 / 知产 / 公司 / 诉讼 / 个人 / 物业七大领域 · China legal review across 7 domains | |
| 🔮 [`destiny-matrix`](shared/destiny-matrix/) | 性格本位多维命运解析：荣格八维 + 八字 + 紫微 + 占星 · Multi-modal personality-first destiny analysis | |
| 📐 [`methodology-writer`](shared/methodology-writer/) | Turn lived experience into structured, evidence-backed methodology documents · 经验框架化、方法论成稿 | |
| 🧷 [`obsidian-md-ac`](shared/obsidian-md-ac/) | Obsidian Flavored Markdown + Mermaid full reference (wikilinks, callouts, diagrams) · OFM 完整参考 | |
| 🎴 [`xiaohongshu-cards`](shared/xiaohongshu-cards/) | Article → Notion-style 1080×1440 RED card images via Playwright + QA loop · 小红书图文卡片 | |

### ⚙️ Layer 2 — `hermes/` · 平台通用

Deployed to main Hermes + all 15 profiles. Not tied to 三省六部 governance.

| Skill | Purpose · 用途 | Refs · 引用 |
|:---|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | Multi-engine search router (SearXNG 默认起手 + Exa / Tavily / Brave) + deep research with verbatim quote extraction · 检索总控：多引擎聚合 + 深度研究 + 反幻觉 · v3.2.0 · 25 refs | ← `skill-authoring` `grill-with-docs` → `github` |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis via TradingAgents · 交易分析 | |
| 🧠 [`llm-wiki`](hermes/llm-wiki/) | LLM knowledge base builder (Karpathy's wiki) · LLM 知识库 | |
| 📚 [`arxiv`](hermes/arxiv/) | Academic paper search and retrieval · 论文检索 | |
| 📔 [`auto-diary`](hermes/auto-diary/) | Automated daily diary + weekly summary generation · 日记生成 | |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video deep analysis with subtitle/transcription · B站视频分析 | |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | Xiaohongshu (RED) content extraction via CDP · 小红书爬虫 | |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar & reminders management for family · 智能日历管理 | |
| ✂️ [`de-slop`](hermes/de-slop/) | Bilingual EN/ZH AI writing detector & humanizer · 中英双语去 AI 味 | |
| 🤖 [`claude-code`](hermes/claude-code/) | Orchestrate Claude Code CLI: print mode, interactive tmux, agent team · CC 编排 | |

### 🏯 Layer 3a — `hermes-3S6M-profiles/common/` · 全部门通用

Deployed to all 15 profiles. Foundation of the governance system · 治理体系基石。

| Skill | Purpose · 用途 |
|:---|:---|
| 📜 `three-provinces-constitution` | 三省六部 governance constitution v3.0 — task routing, escalation, handoff · 三省六部治理宪法 — 任务路由、升级、交接 |
| 💹 `financial-research-agents` | Financial research via Kanban multi-profile orchestration · 金融研究多部门调度，Kanban 多 profile 编排 |

### 🏷️ Layer 3b — `hermes-3S6M-profiles/<dept>/` · 部门专属

Deployed only to matching profile · 仅部署到对应部门。

| Department · 部门 | Profile | Skills | Role · 职责 |
|:---|:---|:---|:---|
| 👑 监国太子 | `regent` | `kanban-orchestrator` `kanban-worker` `kanban-gate` `6m-smoke-test` `morning-news-briefing` **v4.0** | 总揽仲裁、任务编排、六部巡检、晨报生成 · Oversight & orchestration · 🛂 唯一 gateway |
| 🛠️ 工部 | `gongbu` | `disk-cleanup` `infra-health-check` `infra-monitoring` `surge-gateway` `agent-observability` | 基础设施运维、部署监控、网关管理 · Infrastructure & monitoring |
| ⚖️ 刑部 | `tester` | `code-review-toolkit` `agent-security-audit` | 代码审查、测试、安全审计 · Code review & security |
| 🔧 将作监 | `jiangzuojian` | `delivery-gate` `specialist-engineer` | 交付把关、专家评审 · Delivery gate & expert review |
| 📡 尚书省 | `shangshu` | [`a2a-protocol`](https://github.com/Loveacup/hermes-a2a) | Agent 间互通协议、任务派发 · [A2A interop](https://github.com/Loveacup/hermes-a2a) |
| 🎭 礼部 | `protocol` | `md-to-pdf` | 文档编制、PDF 渲染 · Document formatting |
| 🔎 御史台 | `auditor` | `agent-audit-evaluation` | 独立审计、合规评估 · Audit & compliance |
| 📖 史馆 | `archivist` | `agent-memory-manager` | 全程归档、记忆管理 · Archival & memory |
| 💰 户部 | `budget` | `agent-cost-manager` | 数据搜索、成本管理 · Data & cost tracking |
| 👥 吏部 | `registry` | `agent-registry` | Agent 注册、培训管理 · Registry & training |
| 🎓 翰林院 | `hanlinyuan` | `deep-research-agent` | 深度研究、知识探索 · Deep research |

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

> v0.13 · 15/15 active · 六部 smoke test 全线闭环 · [A2A 架构 →](https://github.com/Loveacup/hermes-a2a)

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
