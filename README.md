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
> Skills authored, audited, and evolved by AI agents following [skill-authoring](shared/skill-authoring/). Deployed to a 15-profile Hermes governance system (三省六部), Claude Code, and pi (Windows).
>
> 所有技能由 AI agent 按 [skill-authoring v3.0](shared/skill-authoring/) 创作、审计和迭代。部署于三省六部 15-profile 体系、Claude Code 和 pi (Windows)。

---

## 🌲 Structure · 四层结构

```
jz-skills/
├── shared/         🌐 跨平台 · Cross-platform (16 skills)
├── hermes/         ⚙️ Hermes 平台 (15 skills)
├── hermes-3S6M-profiles/ 🏯 三省六部 (23 skills) → [详情](https://github.com/Loveacup/hermes-s6m-a2a)
└── pi/             🪟 Pi / Windows (6 skills)
```

| Layer | Directory | Skills | Scope · 范围 |
|:---|:---|:---:|:---|
| 🌐 | `shared/` | 16 | All 3 platforms · 三端同步 |
| ⚙️ | `hermes/` | 15 | Hermes platform · 平台通用 |
| 🏯 | `hermes-3S6M-profiles/` | 23 | 三省六部 governance → [s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a) |
| 🪟 | `pi/` | 6 | Pi (Windows), self-authored · Pi 自创作 |

<details>
<summary><b>🌲 Full tree · 完整结构树</b></summary>

```
jz-skills/
├── shared/                        # 🌐 Cross-platform · 跨平台 (16)
│   ├── github/                    # GitHub 全操作
│   ├── grill-with-docs/           # 设计审查
│   ├── skill-authoring/           # 合规创作 (11-step, 7-dim scoring)
│   ├── pdf/                       # PDF 处理 (OCR/extract/Markdown→PDF/移动端)
│   ├── voice-to-markdown-workflow/# 语音/视频转录文本→结构化 Markdown
│   ├── audio-transcriber/         # 音频转录 (降噪+声纹分离+Qwen3-MLX ASR)
│   ├── china-legal-optimized/     # 中国法务 (7 领域: 合同/劳动/知产/公司/诉讼/个人/物业)
│   ├── destiny-matrix/            # 命运矩阵 (荣格八维+八字+紫微+占星)
│   ├── methodology-writer/        # 经验→结构化方法论文档
│   ├── obsidian/                  # Vault ops + CLI + plugin dev + Bases + Defuddle
│   ├── obsidian-md-ac/            # OFM + Mermaid + JSON Canvas 完整参考
│   ├── supermemory-maintenance/   # Supermemory v6 参考 (架构/SDK/诊断/容器标签)
│   ├── de-slop/                   # 中英双语 AI 味检测与人性化
│   ├── xiaohongshu-cards/         # 文章→小红书图文卡片 (Playwright + QA loop)
│   ├── xhs-tech-writer/           # 小红书 AI/科技短图文创作工作流
│   └── _archived-strategic-insight-longform-slim/  # [已归档]
├── hermes/                        # ⚙️ Hermes 平台 (15)
│   ├── web-research-router/       # v3.8 · 5 引擎深度研究 + 逐字引用反幻觉
│   ├── auto-diary/                # v3.5 · 日/周/月/年报金字塔聚合
│   ├── mac-doctor/                # v2.2 · macOS 六级巡检 (评分/安全/硬件/网络/隐私/追踪)
│   ├── cron-worker/               # v1.3 · 定时任务 profile + 4 种心跳 + 技能池看门狗
│   ├── claude-code/               # v3.5 · CC 编排 (print/tmux/agent team + 假空闲检测)
│   ├── tts-manager/               # TTS 聚合管理 (provider 注册/音色测试/后备策略)
│   ├── tech-support-email/        # v1.1 · 调查优先的技术支持邮件工作流
│   ├── supermemory-hermes/        # Hermes Supermemory 配置/多 profile 架构
│   ├── tradingagents/             # A 股/市场分析
│   ├── llm-wiki/                  # Karpathy 式 LLM 知识库
│   ├── arxiv/                     # 学术论文检索
│   ├── bilibili-video-analyzer/   # B站视频深度分析
│   ├── xhs-crawler/               # 小红书 CDP 内容提取 (CloakBrowser 反检测)
│   ├── calendar-manager/          # 智能日历+提醒管理
│   └── reply-context-retrieval/   # Telegram 回复上下文回溯
├── hermes-3S6M-profiles/          # 🏯 三省六部 (23)
│   ├── common/                    # 全部门通用 (2)
│   │   ├── three-provinces-constitution/  # v3.0 · 三省六部宪法
│   │   └── financial-research-agents/     # 金融研究多 profile 调度
│   ├── regent/ (5)                # 👑 监国太子 · 唯一有 gateway 的 profile
│   │   ├── morning-news-briefing/ # v4.0 · 晨报生成
│   │   ├── kanban-orchestrator/   # Kanban 任务编排
│   │   ├── kanban-worker/         # Kanban 任务执行
│   │   ├── kanban-gate/           # Kanban 质量门
│   │   └── 6m-smoke-test/         # 六部冒烟测试
│   ├── gongbu/ (5)                # 🛠️ 工部 · 基础设施运维
│   ├── tester/ (2)                # ⚖️ 刑部 · 代码审查+安全审计
│   ├── jiangzuojian/ (2)          # 🔧 将作监 · 交付把关+专家评审
│   └── <dept>/ (1 each × 10)      # 其余 10 部门 (详见 s6m-a2a)
└── pi/                            # 🪟 Pi / Windows (6)
    ├── web-research-router/       # TypeScript SDK 检索总控
    ├── pi-web-research/           # v3.4 · 多引擎深度研究
    ├── pi-grill/                  # v3.1 · 歧义守护
    ├── skill-creator/             # v6.0 · 合规创作
    ├── pi-hermes-setup/           # Pi↔Hermes SSH+MCP 联动
    └── pi-supermemory/            # Windows Supermemory 集成
```

</details>

---

## 🔥 Active Skills · 高频更新

Skills with the most commit activity and rapid iteration in recent months. Ranked by update frequency.
以下技能在近几个月提交最密集、迭代最快，按活跃度排列。

### 📔 auto-diary · 自动化日记 v3.5

> **11 commits** — the most actively developed skill in the repo · 仓库中提交最密集的技能

Automated daily diary + weekly/monthly/yearly report generation triggered by cron. Rapid structural evolution driven by format and accuracy improvements.
从 cron 触发的日记生成到金字塔聚合的年报体系，因格式和准确性持续优化而快速迭代。

- **v3.5 — Pyramid aggregation · 金字塔聚合:** Daily→weekly→monthly→yearly with cron scheduling and report validation / 日→周→月→年四级聚合 + cron 调度 + 校验闭环
- **v3.4 — Real validation loop · 真实校验:** Fixed internal contradictions between config and output / 修复配置与输出矛盾
- **v3.2 — CC session classification · CC 会话三分类:** agent-team / independent / programmatic, with entrypoint+parentUuid tracking / 三类 CC 会话分类追踪
- **v3.0 — obsidian-md-ac formatting · 标准化输出:** YAML frontmatter, callouts, section dividers in generated diaries / 生成日记采用 OFM 标准格式
- **Fixes · 修复:** `~` expansion bug, event-bridge exclusion, emoji corrections, 助理体系 vs 治理体系 separation / 路径展开 bug、event-bridge 排除、emoji 修正、体系分离

→ [`hermes/auto-diary/`](hermes/auto-diary/)

---

### 🩺 mac-doctor · macOS 巡检 v2.2

> **10 commits** — 19 files, 2,135 lines · 仓库中最全面的系统运维技能

Six-tier macOS system health monitoring with root-cause diagnosis.
六级 macOS 健康巡检，含根因诊断。

- **6 layers · 六层体系:** Health scoring + root-cause → Security audit (27 items) → Hardware diagnostics → Network → Privacy → History / 评分+根因→27项安全审计→硬件→网络→隐私→追踪
- **Dual cron · 双调度:** LLM agent (daily deep audit) + Silent Watchdog (30min, `no_agent=true`, anomaly-only push) / LLM 深审 + 静默看门狗
- **v2.3:** Watchdog threshold-vs-anomaly silent logic; `None`-handling robustness
- **Fixes · 修复:** pgrep browser false-positive, disk-cleanup safety gates, sustained-CPU threshold tuning / 进程误报修复、清理安全门、CPU 阈值调优
- **Smart alerts · 智能告警:** E1 sustained-CPU window alerts with cleanup safety gates / CPU 持续异常窗口告警 + 清理安全门

→ [`hermes/mac-doctor/`](hermes/mac-doctor/)

---

### 🔍 web-research-router · 检索总控 v3.8

> **5 commits** — 22 reference files, the most complex skill in the repo · 仓库中最复杂的技能

Multi-engine search router with deep research loop and verbatim-quote anti-hallucination. Five engines coordinated through a decision tree with mandatory Step 0 local-first check.
五引擎聚合搜索路由 + 深度研究循环 + 逐字引用反幻觉。通过决策树协调引擎，强制 Step 0 本地优先。

- **5 engines · 五引擎:** Exa + Brave (dual-primary) → Tavily (deep research) → web_search (broad) → SearXNG (fallback) / 双主力→深度→广扫→兜底
- **Deep loop · 深度循环:** Plan → Section research (facts.jsonl) → Reflect → Merge + cross-language blind-spot detection / 规划→分节研究→反思→合并+跨语言盲区
- **Anti-hallucination · 反幻觉:** Verbatim quote extraction, `[s<id>]` inline citation, 3-column output (Confirmed / Inference / Conflicts) / 逐字引用+三分栏
- **v3.8:** Claude Code WebSearch as auxiliary grounding engine / CC 引擎作为辅助验证
- **v3.7:** SearXNG demoted to fallback after cross-platform validation / 跨平台交叉验证后降级 SearXNG
- **v3.7:** Step 0 mandatory 4-step local check (Supermemory→session→qmd→CodeGraph) / 强制四步本地检查

→ [`hermes/web-research-router/`](hermes/web-research-router/)

---

### 🕐 cron-worker · 定时任务 Agent v1.3

> **5 commits** — architectural foundation for all scheduled agent workloads · 定时任务基础设施

Dedicated cron-worker profile with four heartbeat patterns and cross-profile skill pool integrity watchdog. Defines the architecture for separating background tasks from interactive agent sessions.
专用定时任务 profile 架构 + 四种心跳模式 + 技能池完整性看门狗。定义了后台任务与交互式 agent 分离的架构。

- **4 heartbeats · 四种心跳:** Cron (time) → Webhook (event) → Change detection (state diff, zero-LLM idle) → Silent watchdog (anomaly-only, `no_agent=true`) / 定时→事件→变更检测→静默看门狗
- **Skill pool watchdog · 技能池看门狗:** Full-depth `find` enumeration (132 skills vs glob's 124 blind-spotted), manifest baseline diff, 4-level alerting (CRITICAL/WARN/INFO/CLEAN), 595-line script / 全深度枚举+基线比对+四级告警
- **Cross-profile pool · 跨 profile 共享池:** default (pool owner) + regent + cron-worker via `external_dirs` — base skills auto-sync / 三方共读同池，基础 skill 自动同步
- **Defense layers · 防御体系:** L1 prevention (`skill_sync.py` patch) + L2 monitoring (watchdog) + L2 cleanup (daily shell)

→ [`hermes/cron-worker/`](hermes/cron-worker/)

---

### 🤖 claude-code · CC 编排 v3.5

> **4 commits** — Hermes-to-Claude Code orchestration bridge · Hermes 编排 Claude Code 的桥接层

Orchestrate Claude Code CLI from Hermes with three modes and false-idle detection. The primary bridge for delegating heavy engineering work to Claude Code's agent team.
从 Hermes 编排 Claude Code，三种模式 + 假空闲检测。将重型工程任务委托给 CC agent team 的主通道。

- **3 modes · 三种模式:** Print (one-shot) → Interactive tmux → Agent team (multi-agent coordination) / 单次打印→交互终端→多 agent 协作
- **v3.5.1 · Pitfall #24:** False-idle detection — CC appears stuck but is actually in deep thinking / 假空闲检测：CC 看似卡住实则在深度思考
- **v3.5.0:** Smart effort routing + agent team workflow enhancement / 智能路由 + agent team 增强
- **Progress reporting · 进度汇报:** Mandated template — 15s first check → 30-60s polling → emoji status / 强制汇报模板

→ [`hermes/claude-code/`](hermes/claude-code/)

---

### 🎤 tts-manager · TTS 聚合管理

> **4 commits** — rapidly evolving new skill · 快速迭代的新技能

Unified text-to-speech management for Hermes agent workflows. Provider registry, voice testing, fallback policy, resource benchmarking, and artifact quality checks.
Hermes agent 工作流的统一 TTS 管理层。Provider 注册、音色测试、后备策略、资源基准、产物质量检查。

- **Provider registry · Provider 注册:** edge-tts, Qwen3-TTS, custom voice providers with fallback chains / 多 provider 注册+后备链
- **Voice testing · 音色测试:** Sample generation, voice comparison, quality benchmarks / 样本生成+音色对比+质量基准
- **Architecture · 架构:** Voice director pattern with speakable text optimization / Voice director 模式+可朗读文本优化

→ [`hermes/tts-manager/`](hermes/tts-manager/)

---

### 🧠 supermemory-maintenance · 记忆参考 v6

> **4 commits** — evolving cross-platform reference · 持续演进的跨平台参考

General reference for Supermemory — the long-term memory infrastructure shared across Hermes, Claude Code, and pi. Architecture, SDK usage, container tags, processing pipeline, and diagnostic protocols.
跨 Hermes/CC/pi 三端的 Supermemory 长期记忆基础设施参考。架构、SDK、容器标签、处理管线、诊断协议。

- **4 references · 4 个引用文档:** SDK divergence diagnosis, migration recipes, JSON schema, tri-test protocol / SDK 分歧诊断、迁移配方、json-schema、三测协议
- **Cross-platform · 跨平台:** Shared reference deployed to all 3 platforms, with platform-specific skills for execution (`supermemory-hermes`, `pi-supermemory`) / 通用参考三端部署，执行层由平台专属 skill 负责

→ [`shared/supermemory-maintenance/`](shared/supermemory-maintenance/)

---

### 📧 tech-support-email · 技术支持邮件 v1.1

> **2 commits** — brand new, rapidly evolving · 全新技能，快速迭代

Investigation-first workflow for drafting technical support emails to SaaS/API vendors. Deep-dive investigation → config audit against official docs → multi-angle testing → bilingual (CN/EN) tone-calibrated output.
调查优先的技术支持邮件工作流。深度调查→对照官方文档审计→多角度测试→中英双语输出。

- **v1.1 — Evidence gate · 证据门:** Evidence sufficiency check before drafting + vendor tier matrix (SaaS/API/Enterprise) / 证据充分性门槛 + 供应商级别矩阵
- **Core workflow · 核心流程:** Incident reproduction → log/error evidence → official doc cross-reference → hypothesis testing → tone-calibrated email / 故障复现→证据收集→文档对照→假设验证→语气校准邮件

→ [`hermes/tech-support-email/`](hermes/tech-support-email/)

---

## 📋 Full Catalog · 完整目录

### 🌐 shared/ — Cross-platform · 跨平台 (16)

| Skill | Purpose · 用途 |
|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub ops: auth, issues, PR, code review, exploration / GitHub 全操作 |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs + ADR / 设计审查 |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | 11-step flow, 7-dim compliance scoring, deployment-grounded audit / 十一维合规创作 |
| 📄 [`pdf`](shared/pdf/) | PDF: OCR, extract, markdown→PDF (A4 + mobile 430×932px), forms / PDF 全处理 |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech/audio transcript → structured markdown with scene detection / 语音转文稿 |
| 🎧 [`audio-transcriber`](shared/audio-transcriber/) | Noise-gated denoise + speaker diarization (pyannote) + Chinese ASR (Qwen3-MLX) / 音频转录 |
| ⚖️ [`china-legal-optimized`](shared/china-legal-optimized/) | 合同/劳动/知产/公司/诉讼/个人/物业 7 领域 / 7 legal domains |
| 🔮 [`destiny-matrix`](shared/destiny-matrix/) | 荣格八维 + 八字 + 紫微 + 占星 / Multi-modal personality analysis |
| 📐 [`methodology-writer`](shared/methodology-writer/) | Experience → structured, evidence-backed methodology documents / 经验框架化 |
| 📓 [`obsidian`](shared/obsidian/) | Vault ops, CLI, plugin dev, Bases (.base), Defuddle / Obsidian 全操作 |
| 🧷 [`obsidian-md-ac`](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas full reference / OFM 完整参考 |
| 🧠 [`supermemory-maintenance`](shared/supermemory-maintenance/) | Supermemory v6 reference — [§active](#-supermemory-maintenance--记忆参考-v6) |
| ✂️ [`de-slop`](shared/de-slop/) | Bilingual AI writing detection & humanization / 中英去 AI 味 |
| 🎴 [`xiaohongshu-cards`](shared/xiaohongshu-cards/) | Article → Notion-style 1080×1440 RED card images / 小红书图文卡片 |
| ✍️ [`xhs-tech-writer`](shared/xhs-tech-writer/) | AI/科技领域小红书短图文创作 / RED tech short-form content |

### ⚙️ hermes/ — Hermes platform (15)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | 5-engine search + deep research — [§active](#-web-research-router--检索总控-v38) |
| 📔 [`auto-diary`](hermes/auto-diary/) | Daily→yearly diary pyramid — [§active](#-auto-diary--自动化日记-v35) |
| 🩺 [`mac-doctor`](hermes/mac-doctor/) | macOS 6-tier health monitor — [§active](#-mac-doctor--macos-巡检-v22) |
| 🕐 [`cron-worker`](hermes/cron-worker/) | Cron profile + 4 heartbeats + pool watchdog — [§active](#-cron-worker--定时任务-agent-v13) |
| 🤖 [`claude-code`](hermes/claude-code/) | CC orchestration bridge — [§active](#-claude-code--cc-编排-v35) |
| 🎤 [`tts-manager`](hermes/tts-manager/) | TTS provider registry + voice testing — [§active](#-tts-manager--tts-聚合管理) |
| 📧 [`tech-support-email`](hermes/tech-support-email/) | Investigation-first vendor emails — [§active](#-tech-support-email--技术支持邮件-v11) |
| 🧠 [`supermemory-hermes`](hermes/supermemory-hermes/) | Hermes Supermemory setup, multi-profile, cabinet architecture |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis / 交易分析 |
| 🧠 [`llm-wiki`](hermes/llm-wiki/) | Karpathy-style LLM knowledge base / LLM 知识库 |
| 📚 [`arxiv`](hermes/arxiv/) | Academic paper search / 论文检索 |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video deep analysis / B站视频分析 |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | Xiaohongshu CDP content extraction / 小红书爬虫 (CloakBrowser) |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar & reminders / 智能日历 |
| ↩️ [`reply-context-retrieval`](hermes/reply-context-retrieval/) | Telegram reply context retrieval / TG 引用回溯 |

### 🏯 hermes-3S6M-profiles/ — 三省六部 (23)

> 三省六部 Agent 治理体系 — 15 profiles, Kanban task routing, A2A inter-agent protocol.
>
> **→ 完整架构与 A2A 协议文档：** [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a)

| Layer | Count | Key skills · 核心技能 |
|:---|:---:|:---|
| `common/` | 2 | `three-provinces-constitution` v3.0 · `financial-research-agents` |
| `regent/` 👑 | 5 | `kanban-orchestrator` `kanban-worker` `kanban-gate` `6m-smoke-test` `morning-news-briefing` v4.0 — 唯一有 gateway |
| `gongbu/` 🛠️ | 5 | `disk-cleanup` `infra-health-check` `infra-monitoring` `surge-gateway` `agent-observability` |
| `tester/` ⚖️ | 2 | `code-review-toolkit` `agent-security-audit` |
| `jiangzuojian/` 🔧 | 2 | `delivery-gate` `specialist-engineer` |
| Other 10 depts | 1 ea | archivist / auditor / budget / dispatcher / engineer / hanlinyuan / planner / protocol / registry / shangshu ([A2A](https://github.com/Loveacup/hermes-a2a)) |

### 🪟 pi/ — Pi / Windows (6)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](pi/web-research-router/) | TypeScript SDK search routing / 检索总控 (TS SDK) |
| 🔍 [`pi-web-research`](pi/pi-web-research/) | Multi-engine deep research v3.4 / 多引擎深度研究 |
| 🛡️ [`pi-grill`](pi/pi-grill/) | Ambiguity guardian v3.1 / 歧义守护 |
| ✍️ [`skill-creator`](pi/skill-creator/) | Compliance-first skill authoring v6.0 / 合规创作 |
| 🔗 [`pi-hermes-setup`](pi/pi-hermes-setup/) | Pi ↔ Hermes SSH + MCP integration / 联动架构 |
| 🧠 [`pi-supermemory`](pi/pi-supermemory/) | Windows Supermemory integration / 记忆集成 |

---

## 🚀 Quick Start · 快速开始

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills

# Deploy to one platform · 单平台部署
cd ~/code/jz-skills && ./deploy/sync-all.sh hermes   # → ~/.hermes/skills/
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

---

## 🔄 Sync · 同步

```bash
# 📤 Push: local → GitHub (auto-sanitized · 自动脱敏)
./deploy/sync-back.sh --dry-run   # preview · 预览
./deploy/sync-back.sh             # apply (strips paths, emails, API keys)

# 📥 Pull: GitHub → local · 拉取部署
git pull && ./deploy/sync-all.sh <platform>
```

🛂 **Gateway restart · 网关重启** — needed when skills change for `regent` or `default`:

```bash
hermes gateway restart -p regent
hermes gateway restart -p default
```

---

## 🤝 Contributing · 贡献

1. Edit skills on your agent or directly in repo / 在 agent 上或直接编辑
2. `./deploy/sync-back.sh --dry-run` — preview / 预览
3. `./deploy/sync-back.sh` — sync with auto-sanitization / 同步 + 脱敏
4. Commit and push / 提交推送

---

## 📜 License · 许可

MIT — see [LICENSE](LICENSE).
