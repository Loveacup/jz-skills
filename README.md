# 🏛️ jz-skills · AI Agent Skills Hub

![skills](https://img.shields.io/badge/skills-54-blue)
![platforms](https://img.shields.io/badge/platforms-Hermes_|_CC_|_pi-8A2BE2)
![sync](https://img.shields.io/badge/sync-bidirectional-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

> **A personal, multi‑CLI skill hub where AI agents author, audit, and evolve their own capabilities — deployed across Hermes, Claude Code, and pi (Windows).**
>
> 一个面向多 CLI AI Agent 的个人技能中心：技能由 AI Agent 自行编写、审计与演进，同时部署至 Hermes、Claude Code 与 pi (Windows) 三个平台。

---

## 📂 Structure

```
jz-skills/
├── shared/          ← 🧩 Cross‑platform skills (Hermes + CC + pi)
├── hermes/          ← ⚡ Hermes‑exclusive skills
├── pi/              ← 🪟 Windows / pi‑exclusive skills
├── _archived-hermes-3S6M-profiles/  ← 🗄️ Archived 三省六部 profiles
└── deploy/          ← 🔧 Sync‑back & drift tooling
```

| Layer | Directory | Skills | Scope |
|-------|-----------|--------|-------|
| 🧩 Shared | `shared/` | 18 | Works across Hermes, Claude Code, and pi |
| ⚡ Hermes | `hermes/` | 30 | Hermes‑only (macOS orchestrator) |
| 🪟 Pi | `pi/` | 6 | Windows / pi‑only |
| 🗄️ Archived | `_archived-hermes-3S6M-profiles/` | 12 profiles | Retired 三省六部 governance profiles |
| **Total** | | **54 skills** | |

<details>
<summary>🌳 Full skill tree</summary>

```
shared/                              🧩 18 skills
├── audio-transcriber
├── bookmark-organizer
├── china-legal-optimized
├── de-slop
├── destiny-matrix
├── github
├── goalgen
├── grill-with-docs
├── methodology-writer
├── obsidian
├── obsidian-md-ac
├── pdf
├── skill-authoring
├── supermemory-maintenance
├── vault-keeper
├── voice-to-markdown-workflow
├── xhs-tech-writer
└── xiaohongshu-cards

hermes/                              ⚡ 30 skills
├── arxiv
├── auto-diary
├── bilibili-video-analyzer
├── calendar-manager
├── cc-tmux
├── cccmux
├── claude-code
├── cqi-plan-writer
├── cron-worker
├── dingtalk-message-monitor
├── kanban-codex-lane
├── kanban-orchestrator
├── llm-wiki
├── mac-doctor
├── memory-hub
├── morning-news-briefing
├── news-assembly
├── openwrt-router
├── reply-context-retrieval
├── source-verification
├── supermemory-hermes
├── surge-gateway
├── teach
├── tech-support-email
├── telegram-topic-manager
├── tradingagents
├── tts-manager
├── unifi-ops
├── web-research-router
└── xhs-crawler

pi/                                  🪟 6 skills
├── pi-grill
├── pi-hermes-setup
├── pi-supermemory
├── pi-web-research
├── skill-creator
└── web-research-router

_archived-hermes-3S6M-profiles/      🗄️ 12 profiles
├── archivist
├── auditor
├── budget
├── common
├── gongbu
├── hanlinyuan
├── jiangzuojian
├── protocol
├── regent
├── registry
├── shangshu
└── tester
```

</details>

---

## 🔥 Active Skills · 高频迭代

Skills ranked by git commit count across the full repository history — reflecting sustained, multi-version iteration. Not hand-picked — data-driven.

> **Criteria · 入选标准:** ≥5 commits + ≥2 major versions + real functional evolution per version. A skill with 12 typo commits doesn't qualify. A skill with 4 commits across 4 major rewrites doesn't either — the floor keeps the section focused.

### 📔 auto-diary · 自动化日记 v3.6.2

> **26 commits** — the most-iterated skill in the repo · 仓库中迭代次数最多的技能

Automated daily/weekly/monthly/yearly diary generation from cron. Pyramid aggregation from daily fragments to yearly retrospectives.
从 cron 触发的日记生成到金字塔聚合的年报体系。

- **DingTalk class group · 钉钉班级群:** Decrypt local DingTalk SQLite → extract teacher messages → auto-include in daily diary / 解密本地加密 SQLite → 提取老师消息 → 自动写入日记
- **Silent cron failure fix · 静默故障修复:** `skills: []` empty array silently passed but diary degraded daily — diagnosed, fixed, and documented / 空技能数组静默通过但日记逐日退化，已诊断修复并写入故障模式库
- **Pyramid aggregation · 金字塔聚合:** Daily→weekly→monthly→yearly with cron scheduling + validation / 日→周→月→年四级聚合
- **CC classification · CC 三分类:** agent-team / independent / programmatic, with entrypoint+parentUuid tracking / 三类 CC 会话分类与溯源
- **OFM formatting · 标准化输出:** YAML frontmatter, callouts, section dividers in generated Obsidian output / Obsidian 标准化格式输出

→ [`hermes/auto-diary/`](hermes/auto-diary/)

### ✍️ skill-authoring · 合规创作 v3.0

> **25 commits** — absorbed SkillEvolver + EmbodiSkill (2026-05) · 吸收双子系统

11-step compliance-first skill authoring workflow with 7-dimension scoring. The governance backbone for every skill in this repo.
11 步合规创作工作流 + 七维评分。本仓库所有技能的治理骨架。

- **11-step flow · 11 步流程:** Capture → Grill → Progressive disclosure → Anti-rationalization → Rule positioning → Checklist → 7-dim scoring → Test cases → Deployment-grounded audit → Failure classification → Revision
- **7-dim scoring · 七维评分:** Progressive disclosure, anti-rationalization, rule positioning, checklist coverage, test coverage, deployment fit, failure resilience
- **v3.0 — Dual-role review · 双角色审查:** Advocate→Challenger→Synthesize pattern; deployment-grounded audit closes the loop / 双角色辩证审查 + 部署根基审计闭环

→ [`shared/skill-authoring/`](shared/skill-authoring/)

### 🤖 claude-code · CC 编排 v4.2.1

> **25 commits** — 685→446 line salience slim (-35%) · 大幅瘦身

Hermes↔Claude Code orchestration bridge with bidirectional grilling protocol and autonomous agent team coordination.
Hermes↔CC 编排桥梁，双向拷问协议 + 自治 agent team 协调。

- **Salience slim · 瘦身下沉:** 685→446 lines (-35%). 7 reference tables moved to `references/`; core body retains high-frequency skeleton only / 7 张参考表下沉，主体仅留高频骨架
- **Constitutional red lines · 红线宪法:** 2 iron rules — capture↔report 1:1 pairing + discussion protocol = no execution. 5 Gate Stamp disciplines / 2 条铁律红线 + 5 项 Gate Stamp
- **Bidirectional grilling · 双向拷问:** Hermes↔CC grill pattern (question-by-question / fact-check first) + multi-round dialectic + consensus termination / 逐问→先查事实→多轮辩证→共识终止
- **Autonomous agent teams · 自治团队:** Per-task isolated sessions, cross-session context via `/tmp/cc-context-{task}.md`, smart effort routing (5-level, signal-based)
- **Progress reporting · 进度汇报:** Mandatory 15s first-check → 30-60s polling → emoji status template. Silence >2min = anomaly

→ [`hermes/claude-code/`](hermes/claude-code/)

### 🔍 web-research-router · 检索总控 v3.11

> **22 commits** — 6-engine search router · 六引擎搜索路由

Multi-engine deep research router with anti-hallucination guardrails. The most architecturally complex skill in the repo.
六引擎搜索路由 + 深度研究循环 + 反幻觉护栏。仓库中架构最复杂的技能。

- **6 engines · 六引擎:** Exa + Brave (dual-primary) → Tavily (deep) → web_search (broad) → Sogou/WeChat → SearXNG (fallback) / 双主力→深度→广扫→微信/搜狗→兜底
- **Deep research loop · 深度循环:** Plan → Section (facts.jsonl) → Reflect → Merge + cross-language blind-spot detection / 分节→反思→合并+跨语言盲区检测
- **Anti-hallucination · 反幻觉:** Verbatim quote extraction, `[s<id>]` inline citation, 3-column output (Confirmed / Inference / Conflicts) / 逐字引用 + 内联标注 + 三分栏
- **WeChat/Sogou · 微信/搜狗:** Integrated Sogou + WeChat Official Account search with encrypted link decryption / 集成微信公众号搜索与加密链接解密
- **Agent-Reach · 智能可达:** Mandatory 4-step local check before any web call; SearXNG demoted after cross-platform validation / 强制四步本地检查，SearXNG 降级为兜底

→ [`hermes/web-research-router/`](hermes/web-research-router/)

### 🩺 mac-doctor · macOS 巡检 v2.4.1

> **16 commits** — 6-tier health monitoring · 六级健康巡检

Six-tier macOS system health monitoring with root-cause diagnosis and 27-item security audit.
六级 macOS 健康巡检，根因诊断 + 27 项安全审计。

- **6 tiers · 六层:** Health scoring + root-cause → Security audit (27 items) → Hardware → Network → Privacy → History / 评分+根因→27项安全→硬件→网络→隐私→追踪
- **Dual cron · 双调度:** LLM agent (daily deep audit) + Silent Watchdog (30min, `no_agent=true`, anomaly-only) / LLM 深审 + 静默看门狗
- **Root-cause diagnosis · 根因诊断:** Traces causal chains beyond symptom reporting (e.g., high CPU → specific process → known memory leak) / 追溯因果链而非仅报告症状
- **Multi-profile · 多 Profile 感知:** Cache deduplication across profiles, zombie process detection, awk escaping fixes

→ [`hermes/mac-doctor/`](hermes/mac-doctor/)

### 📋 grill-with-docs · 设计审查

> **11 commits** — governance-grounded design review · 基于治理文档的设计审查

Systematically cross-examines any design proposal or implementation plan against the repository's governance documents.
将任何设计提案或实现计划与治理文档体系进行系统性交叉审查。

- **Governance-grounded · 治理根基:** Every challenge must cite a specific governance document provision — no hand-waving / 每条质疑必须引用具体治理文档条款
- **Cross-profile · 跨 Profile:** Works across `default`, `regent`, and `cron-worker` profiles; governance docs sourced from shared pool / 跨三 Profile 工作
- **Systematic examination · 系统性审查:** Claim → document reference → contradiction/omission → recommendation / 主张→文档引用→矛盾/遗漏→建议

→ [`shared/grill-with-docs/`](shared/grill-with-docs/)

### 🧠 memory-hub · CC×CQI 自动归集回路 v0.2.1

> **9 commits** — Jz-Plugin v4.0 kernel · Jz-Plugin v4.0 内核

Append-only JSONL event log + CC handoff auto-ingest + CQI runtime auto-acknowledge + cron fallback. First Jz-Plugin component to reach full automated CQI closed loop.
Append-only JSONL 真相源 + CC 自动归集 + CQI 自动标记 + cron 兜底。首个跑通完整自动化 CQI 闭环的 Jz-Plugin 组件。

- **3-shard schema · 三 shard:** `issue` / `evolution` / `status_event` — append-only, no mutation, JSONL as source of truth / 追加写入，JSONL 为真相源
- **CC handoff auto-ingest · CC 自动归集:** CC session ends → `mem_ingest` → `cqi_runtime` → `mem_merge` → Obsidian `88-审计/` auto-output / CC 会话结束→四步自动链→审计输出
- **Cron fallback · cron 兜底:** Every-30m fallback ensures no event is missed if real-time pipeline is down / 每 30 分钟兜底
- **Single-write-entry · 单写入口:** stdlib validation gate — all writes go through one validated path / stdlib 校验闸门

→ [`hermes/memory-hub/`](hermes/memory-hub/)

---

## 📋 Full Catalog · 完整目录

> **54 skills** across three platforms — shared foundations, Hermes agent operations, and pi extensions.
> **54 个技能**覆盖三大平台 — 共享基础层、Hermes 智能体操作层、pi 扩展层。

### shared/ — Cross-Platform Foundations · 跨平台基础技能

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🐙 | [github](shared/github/) | Full GitHub ops / GitHub 全操作 |
| 📋 | [grill-with-docs](shared/grill-with-docs/) | Design review against governance docs / 设计审查 |
| ✍️ | [skill-authoring](shared/skill-authoring/) | 11-step, 7-dim scoring / 合规创作 |
| 🎯 | [goalgen](shared/goalgen/) | Multi-CLI goal instruction generator / 通用 goal 生成器 |
| 📄 | [pdf](shared/pdf/) | OCR, extract, markdown→PDF / PDF 全处理 |
| 🎙️ | [voice-to-markdown-workflow](shared/voice-to-markdown-workflow/) | Speech→structured markdown / 语音转文稿 |
| 🔊 | [audio-transcriber](shared/audio-transcriber/) | Denoise+diarization+Chinese ASR / 音频转录 |
| ⚖️ | [china-legal-optimized](shared/china-legal-optimized/) | 7 legal domains / 中国法务 |
| 🔮 | [destiny-matrix](shared/destiny-matrix/) | Jungian+BaZi+ZiWei+Astrology / 命运矩阵 |
| 📐 | [methodology-writer](shared/methodology-writer/) | Experience→structured methodology / 经验框架化 |
| 💎 | [obsidian](shared/obsidian/) | Vault ops, CLI, Bases, Defuddle / Obsidian 全操作 |
| 📓 | [obsidian-md-ac](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas / OFM 参考 |
| 🧠 | [supermemory-maintenance](shared/supermemory-maintenance/) | Supermemory v7 reference / 记忆参考 |
| 🧹 | [de-slop](shared/de-slop/) | Bilingual AI writing detection / 中英去 AI 味 |
| 🟥 | [xiaohongshu-cards](shared/xiaohongshu-cards/) | Article→RED card images / 小红书图文卡片 |
| 📱 | [xhs-tech-writer](shared/xhs-tech-writer/) | RED AI/tech short-form content / 小红书科技短图文 |
| 🏛️ | [vault-keeper](shared/vault-keeper/) | Obsidian lifecycle governance / 知识库治理 |
| 🔖 | [bookmark-organizer](shared/bookmark-organizer/) | Bookmark curation / 书签策展 |

### hermes/ — Agent Operations · 智能体操作技能

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🌐 | [web-research-router](hermes/web-research-router/) | 6-engine search + deep loop / 检索总控 |
| 📔 | [auto-diary](hermes/auto-diary/) | Daily→yearly diary pyramid / 自动化日记 |
| 🍎 | [mac-doctor](hermes/mac-doctor/) | 6-tier macOS health / macOS 巡检 |
| ⏰ | [cron-worker](hermes/cron-worker/) | Cron profile + pool watchdog / 定时任务 |
| 🤖 | [claude-code](hermes/claude-code/) | CC orchestration v4.2.1 / CC 编排 |
| 🖥️ | [cc-tmux](hermes/cc-tmux/) | Drive CC via tmux / tmux 驱动 CC |
| 🎛️ | [cccmux](hermes/cccmux/) | cmux-native CC agent teams / cmux 原生团队编排 |
| 📊 | [cqi-plan-writer](hermes/cqi-plan-writer/) | Signal-driven CQI writing / CQI 计划写作 |
| 🧲 | [memory-hub](hermes/memory-hub/) | CC→CQI auto-ingest loop / 自动归集回路 |
| 💾 | [supermemory-hermes](hermes/supermemory-hermes/) | Hermes Supermemory setup / 记忆配置 |
| 🗣️ | [tts-manager](hermes/tts-manager/) | TTS provider registry / TTS 管理 |
| ✉️ | [tech-support-email](hermes/tech-support-email/) | Investigation-first vendor emails / 技术支持邮件 |
| 📈 | [tradingagents](hermes/tradingagents/) | A-share market analysis / 交易分析 |
| 📰 | [news-assembly](hermes/news-assembly/) | Multi-source→briefing skeleton / 简报汇编 |
| ✅ | [source-verification](hermes/source-verification/) | Fact-checking + claim verification / 事实验证 |
| 📺 | [bilibili-video-analyzer](hermes/bilibili-video-analyzer/) | Bilibili video analysis / B站视频分析 |
| 🕷️ | [xhs-crawler](hermes/xhs-crawler/) | XHS CDP extraction / 小红书爬虫 |
| 📅 | [calendar-manager](hermes/calendar-manager/) | Smart calendar + reminders / 智能日历 |
| 🌅 | [morning-news-briefing](hermes/morning-news-briefing/) | Daily news briefing / 早新闻简报 |
| 💬 | [telegram-topic-manager](hermes/telegram-topic-manager/) | Telegram Topic CRUD / 话题管理 |
| 📚 | [arxiv](hermes/arxiv/) | arXiv + Semantic Scholar / 论文检索 |
| 📡 | [dingtalk-message-monitor](hermes/dingtalk-message-monitor/) | Decrypt + monitor DingTalk DB / 钉钉解密监控 |
| 🚪 | [surge-gateway](hermes/surge-gateway/) | Household proxy gateway / 家庭代理网关 |
| 📶 | [openwrt-router](hermes/openwrt-router/) | OpenWrt/iStoreOS router ops / 路由器运维 |
| 🛜 | [unifi-ops](hermes/unifi-ops/) | UniFi network operations / 网络运维 |
| 🧪 | [llm-wiki](hermes/llm-wiki/) | Karpathy's LLM Wiki / LLM Wiki 知识库 |
| ↩️ | [reply-context-retrieval](hermes/reply-context-retrieval/) | Telegram reply context / 回复上下文检索 |
| 📋 | [kanban-orchestrator](hermes/kanban-orchestrator/) | Decomposition playbook / Kanban 编排 |
| 🛤️ | [kanban-codex-lane](hermes/kanban-codex-lane/) | Kanban→Codex CLI lane / Kanban Codex 通道 |
| 🎓 | [teach](hermes/teach/) | Cross-session teaching in Telegram / Telegram 教学 |

### pi/ — Personal Intelligence Extensions · 个人智能扩展

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🌐 | [web-research-router](pi/web-research-router/) | TS SDK search routing / 检索总控 |
| 🔬 | [pi-web-research](pi/pi-web-research/) | Multi-engine deep research v3.4 / 深度研究 |
| 🛡️ | [pi-grill](pi/pi-grill/) | Ambiguity guardian v3.1 / 歧义守护 |
| 🔧 | [skill-creator](pi/skill-creator/) | Compliance-first authoring v6.0 / 合规创作 |
| 🔗 | [pi-hermes-setup](pi/pi-hermes-setup/) | Pi↔Hermes SSH+MCP / 联动设置 |
| 🗄️ | [pi-supermemory](pi/pi-supermemory/) | Windows Supermemory / 记忆 |

### 📦 Archived · 已归档

The [`_archived-hermes-3S6M-profiles/`](_archived-hermes-3S6M-profiles/) directory preserves the **三省六部** (Three Departments & Six Ministries) governance system — a 15-profile Hermes architecture for structured, role-separated agent operations. See the companion repo for the full A2A protocol: [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a).

[`_archived-hermes-3S6M-profiles/`](_archived-hermes-3S6M-profiles/) 目录保存了**三省六部**治理体系 —— 一套 15-profile 的 Hermes 架构。完整 A2A 协议实现见配套仓库：[hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a)。

---

## 🚀 Quick Start · 快速开始

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills
cd ~/code/jz-skills && ./deploy/sync-all.sh hermes   # → ~/.hermes/skills/
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

> ⚠️ **Before creating or modifying skills, read [CLAUDE.md](CLAUDE.md).** All skills must pass [skill-authoring](shared/skill-authoring/) compliance.
> 创作或修改 skill 前，先读 [CLAUDE.md](CLAUDE.md)。所有 skill 必须通过 [skill-authoring](shared/skill-authoring/) 合规审查。

---

## 🔄 Sync · 双向同步

**Always dry-run first · 始终先预览：**

```bash
# 📤 Push: Hermes → repo (required before commit · 提交前必做)
./deploy/sync-back.sh --dry-run   # ① Preview changes / 预览变更
./deploy/sync-back.sh             # ② Apply + auto-sanitize / 执行+脱敏
git diff && git commit -m '...' && git push

# 📥 Pull: repo → Hermes/CC/pi
git pull && ./deploy/sync-all.sh <platform>
```

`sync-back.sh` auto-sanitizes before commit: `$HOME` → `~/`, emails → redacted, private IPs → redacted, API keys → redacted.

🛂 **Gateway restart** when skills change for `regent` or `default`:

```bash
hermes gateway restart -p regent
hermes gateway restart -p default
```

---

## 📏 Governance · 治理规则

> **Full rules → [CLAUDE.md](CLAUDE.md)** · 完整规则见 CLAUDE.md

| # | Rule · 规则 | Requirement · 要求 |
|---|-------------|---------------------|
| 1 | **Naming · 命名** | `lowercase-hyphens` only. No `_`, no CamelCase. |
| 2 | **YAML frontmatter** | Every SKILL.md must have `name` + `description` + `version` + `author` + `license`. |
| 3 | **Compliance · 合规** | All skills must pass [skill-authoring v3.0](shared/skill-authoring/) (11-step, 7-dim). |
| 4 | **Cross-platform · 跨平台** | `shared/` skills: no hardcoded paths, no platform-specific tools. |
| 5 | **Commits · 提交** | Bilingual: `type(scope): EN description / 中文描述`. |
| 6 | **Sync · 同步** | Always `sync-back.sh --dry-run` before commit. Never skip sanitize. |
| 7 | **Archive · 归档** | Deprecate with `_archived-{name}/`, never delete. |
| 8 | **Active · 高频** | Ranked by full-history commit count. ≥5 commits + ≥2 versions + real functional evolution. |

### 🔥 Active Skill Criteria · 高频标准

Skills in the **Active Skills** section are not hand-picked — they earn their place:

- **≥5 commits** across the full repository history
- **≥2 major versions** (sustained iteration, not one-and-done)
- **Real functional evolution** — each version adds a distinct capability, not just typo fixes

A skill with 12 typo commits doesn't qualify. A skill with 4 commits across 4 major rewrites does — but won't appear because the 5-commit floor isn't met. The floor keeps the section focused on genuinely high-iteration skills.

高频技能不靠拍脑袋选——用数据说话：全历史 ≥5 提交 + ≥2 大版本 + 每次迭代有实质能力增量。

---

## 📜 License · 许可

MIT — see [LICENSE](LICENSE).
