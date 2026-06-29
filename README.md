# 🏛️ jz-skills · AI Agent Skills Hub

![skills](https://img.shields.io/badge/skills-49-blue)
![platforms](https://img.shields.io/badge/platforms-Hermes_|_CC_|_OMP_|_pi-8A2BE2)
![sync](https://img.shields.io/badge/sync-bidirectional-green)
![license](https://img.shields.io/badge/license-MIT-lightgrey)

> **A personal, multi‑CLI skill hub where AI agents author, audit, and evolve their own capabilities — deployed across Hermes, Claude Code, OMP, and pi (Windows).**
>
> 一个面向多 CLI AI Agent 的个人技能中心：技能由 AI Agent 自行编写、审计与演进，同时部署至 Hermes、Claude Code、OMP 与 pi (Windows) 四个平台。

---

## 📂 Structure

```
jz-skills/
├── shared/          ← 🧩 Cross‑platform skills (Hermes + CC + OMP + pi)
├── hermes/          ← ⚡ Hermes‑exclusive skills
├── omp/             ← 🎯 OMP‑exclusive skills (NEW)
├── pi/              ← 🪟 Windows / pi‑exclusive skills
├── codex-automation/  ← 🔧 Codex COA deployment scripts
├── _archived-hermes-3S6M-profiles/  ← 🗄️ Archived 三省六部 profiles
└── deploy/          ← 🔧 Sync‑back & drift tooling
```

| Layer | Directory | Skills | Scope |
|-------|-----------|--------|-------|
| 🧩 Shared | `shared/` | 25 | Works across Hermes, Claude Code, OMP, and pi |
| ⚡ Hermes | `hermes/` | 20 | Hermes‑only (macOS orchestrator) |
| 🎯 OMP | `omp/` | 2 | OMP‑only — STDD methodology + operations |
| 🪟 Pi | `pi/` | 2 | Windows / pi‑only |
| 🗄️ Archived | `_archived-hermes-3S6M-profiles/` | 12 profiles | Retired 三省六部 governance profiles |
| **Total** | | **49 skills** | |

<details>
<summary>🌳 Full skill tree</summary>

```
shared/                              🧩 25 skills (+1 archived)
├── audio-transcriber            # 音频转录：降噪+声纹+中文ASR
├── bilibili-video-analyzer      # B站视频深度分析
├── bookmark-organizer           # 书签策展
├── china-legal-optimized        # 中国法务（7大领域）
├── cqi-plan-writer              # 通用 CQI 写作方法论
├── de-slop                      # 中英双语去AI味
├── destiny-matrix               # 命运矩阵：荣格八维+八字+紫微
├── github                       # GitHub 全操作
├── goalgen                      # 多CLI通用 goal 指令生成器
├── grill-with-docs              # 基于治理文档的设计审查
├── memory-hub                   # CC×CQI 自动归集回路（Jz-Plugin内核）
├── methodology-writer           # 经验→结构化方法论
├── obsidian                     # Vault 操作、CLI、Bases、Defuddle
├── obsidian-md-ac               # OFM + Mermaid + JSON Canvas 参考
├── pdf                          # PDF 全处理：OCR/提取/Markdown→PDF
├── skill-authoring              # 技能合规创作+七维评分（v4.0.0）
├── supermemory-maintenance      # Supermemory v7 参考
├── surge-gateway                # Surge 家庭代理网关
├── unifi-ops                    # UniFi AP/交换机/Controller 运维
├── vault-keeper                 # Obsidian 知识库生命周期治理
├── voice-to-markdown-workflow   # 语音/视频→结构化 Markdown
├── web-research-router          # 多引擎搜索路由+深度研究循环
├── xhs-crawler                  # 小红书 CDP 提取（CloakBrowser）
├── xhs-tech-writer              # 小红书 AI/科技短图文
├── xiaohongshu-cards            # 文章→小红书图文卡片
└── _archived-strategic-insight-longform-slim  ← 🗄️ 已归档

hermes/                              ⚡ 20 skills
├── arxiv                        # arXiv + Semantic Scholar 论文检索
├── auto-diary                   # 自动化日记：日→周→月→年金字塔聚合
├── calendar-manager             # 智能日历+提醒
├── call-omp                     # 🆕 三通道调用 OMP v16.2.4（Shell/RPC/ACP）
├── cc-tmux                      # tmux 驱动 CC v1.31.0：脚本强制护栏 · 15 测试文件 / 136 测试
├── cccmux                       # cmux 原生 CC agent team 编排
├── claude-code                  # CC 编排桥（已由 cc-tmux 取代）
├── cron-worker                  # 定时任务 profile + 技能池看门狗
├── dingtalk-message-monitor     # 钉钉本地DB解密+消息监控
├── kanban-codex-lane            # Kanban→Codex CLI 通道
├── kanban-orchestrator          # 任务分解+Kanban 编排
├── mac-doctor                   # macOS 六级健康巡检
├── morning-news-briefing        # 每日早新闻简报
├── openwrt-router               # OpenWrt/iStoreOS 路由器运维
├── supermemory-hermes           # Hermes Supermemory 配置
├── teach-hermes                 # Telegram 跨会话教学
├── tech-support-email           # 调查驱动的技术支持邮件
├── telegram-topic-manager       # Telegram Topic CRUD + /topic 命令
├── tradingagents                # A股/市场分析
└── tts-manager                  # TTS 供应商注册+语音测试

omp/                                 🎯 2 skills
├── omp-ops                      # OMP 配置、模型、API Key、search 提供商运维
└── stdd-omp                     # STDD 方法论 OMP 侧实现：三梁+四步循环+独立验收

pi/                                  🪟 2 skills
├── pi-grill                     # 歧义守护 v3.1
└── pi-hermes-setup              # Pi↔Hermes SSH+MCP 联动

_archived-hermes-3S6M-profiles/      🗄️ 12 profiles — 已归档的三省六部治理体系
```

</details>

---

## 🔥 Active Skills · 高频迭代

> Ranked by recent activity (last 7 days). Not hand-picked — data-driven.
> 按近 7 天活跃度排序，数据驱动而非人工挑选。

### 🖥️ cc-tmux · tmux 驱动 CC v1.31.0

> **21 commits in last 7 days** — THE hottest skill · 最活跃技能

Drive Claude Code via tmux with script-enforced safeguards. The active CC driver — replacing the older claude-code skill.
通过 tmux 驱动 Claude Code，脚本强制护栏。当前主力 CC 驱动技能，取代旧版 claude-code。

- **R10 消息路由层 · Message routing:** Full delivery of the R10 message routing layer — structured inter-agent communication backbone / 完整的 R10 消息路由层交付，结构化 agent 间通信骨干
- **Turn内等待 · In-turn Wait:** Waits for CC response within the same tmux turn before proceeding / 同一 tmux turn 内等待 CC 响应再继续
- **📡 Progress Reporting · 中间过程可视性:** Real-time visibility into CC's intermediate reasoning and tool calls / CC 中间推理与工具调用的实时可见性
- **Hook 状态权威 · Status authority:** Hook events atomically write the authoritative `cc-status-<s>.json`; esc-to-interrupt gold standard for BUSY / Hook 事件原子写权威状态文件 + esc 金标准判 BUSY
- **fswatch 事件驱动等待:** In-turn wait from sleep-poll to fswatch event-driven with ≤3s TOCTOU watchdog / 等待从轮询升级为 fswatch 事件驱动 + 看门狗兜底
- **用量管理 + Session GC:** cc-usage pre/post baseline-delta + cc-gc 4-trigger garbage collection with 3 safety rules / 用量基线增量汇报 + 会话垃圾回收四触发三安全规则
- **TDD implementation:** 136/136 tests green across 15 test files — test-driven from the ground up / 测试驱动开发，15 个测试文件 136/136 全绿

→ [`hermes/cc-tmux/`](hermes/cc-tmux/)

### 🎯 omp-ops · OMP 运维核心 v16.2.4

> **18 commits in last 7 days** — OMP operations backbone · OMP 运维骨干

Operations skill for Oh My Pi (OMP) — configuration, model providers, API keys, search providers, `config.yml`, `models.yml`, `agent.db`, `.env` precedence, and `modelRoles`.
OMP 运维核心技能 — 配置管理、模型供应商、API Key、搜索提供商、配置文件优先级与模型角色。

- **v16.2.4 同步:** Synced from upstream OMP 16.2.4-0 with full configuration surface / 从上游 OMP 16.2.4-0 同步，覆盖完整配置面
- **config.yml 管理:** Full configuration surface — providers, models, search backends, tool routing / 完整配置面 — 供应商、模型、搜索后端、工具路由
- **modelRoles 编排:** Agent role → model mapping with fallback chains / Agent 角色→模型映射 + 降级链
- **自愈式部署:** `omp-ops-sync.coa.md` + codex-automation directory for automated sync / COA 脚本自动同步

→ [`omp/omp-ops/`](omp/omp-ops/)

### 📐 stdd-omp · STDD 方法论 OMP 实现

> **13 commits in last 7 days** — autonomous verification loops · 自主验证闭环

STDD (Spec-and-Test Driven Development) methodology skill for OMP. Runs the full STDD micro-loop inside OMP with objective gates, independent auditor wiring, and autonomous verification.
STDD 方法论在 OMP 侧的完整实现。在 OMP 内运行完整 STDD 微循环，客观门控 + 独立审计接线 + 自主验证。

- **三梁架构 · Three Beams:** Beam 1 (spec alignment) → Beam 2 (test coverage) → Beam 3 (evidence verification) — full verification chain / 三梁验证链：规格对齐→测试覆盖→证据验证
- **四步循环 · Four-Step Loop:** Spec → Accept → Build → Verify — autonomous iteration with human only inputting requirements / 规格→验收→构建→验证 — 自主迭代，人只输入需求
- **独立验收 · Independent Audit:** Reviewer + Claim Verify dual advisors; evidence ladder + claimcheck for anti-hallucination / 双 advisor 委员会；证据阶梯+claimcheck 反幻觉
- **量化档 · Quantitative Scoring:** Upstream truth calibration + quantitative scoring tiers for objective gating / 上游真相校准+量化档客观门控
- **Agent-Reach 式自部署:** `--text` mode for agent-actionable output; forced entrypoint rewrite + compliance Red Flags table / agent 可操作的文本输出模式 + 强制入口重写 + 合规红旗表

→ [`omp/stdd-omp/`](omp/stdd-omp/)

### 🔍 web-research-router · 检索总控 v5.2

> **12 commits in last 7 days** — 6-engine search router with local search layer · 六引擎搜索路由+本地搜索层

Multi-engine deep research router with anti-hallucination guardrails and a new local search layer spanning 4 engine types.
多引擎搜索路由+深度研究循环+反幻觉护栏。最新：v5.2 本地搜索层（4引擎+248测试）。

- **v5.2 本地搜索层 · Local Search:** 4 local engines — Supermemory + Session + QMD + Obsidian — integrated into the routing decision tree / 四个本地引擎接入路由决策树
- **256/256 全量测试:** Complete test coverage across unit, integration, and engine-level tests / 单元+集成+引擎级全覆盖
- **v5.1 Doctor 命令:** `wrr doctor` — probe all 5 external dependencies with health status and fix commands / 探测全部 5 个外部依赖的健康状态+修复命令
- **v5.0 Mode-based routing:** Intent classification → mode selection → engine chain assembly — replacing flat fallback / 意图分类→模式选择→引擎链组装 — 取代扁平降级
- **Exa 主引擎:** `x-api-key` auth header fix; 3-endpoint unification / 三端点认证统一
- **社区引擎上线:** OpenCLI 通道 — Reddit/Twitter/XHS/V2EX + last30days 中英文 / 社区渠道全覆盖

→ [`shared/web-research-router/`](shared/web-research-router/)

### 🚀 call-omp · Hermes→OMP 沙箱逃生通道 v0.7.0

> **7 commits in last 7 days · 🔥 全新技能** — sandbox escape + independent execution · 沙箱逃生+独立执行

Standardized 3-channel (Shell / RPC / ACP) interface for Hermes to call OMP v16.2.4 — providing a **sandbox escape** execution channel plus independent audit, governance, and code assistance. OMP is a full CLI agent, not just an auditor.
Hermes 通过三通道（Shell/RPC/ACP）标准化调用 OMP v16.2.4，提供跳出沙箱的执行通道+独立审计+治理+编码辅助。OMP 是完整 CLI agent。

- **v0.7.0 Execute 模式:** OMP as a full CLI agent — can run arbitrary shell tasks (build/test/lint, `launchctl kickstart` to rescue Hermes gateway, etc.) / OMP 作为完整 CLI agent 执行任意 shell 任务
- **v0.6.0 智能技能路由:** Auto-detect which OMP capability (audit/govern/code/execute) the task needs / 自动检测任务所需的 OMP 能力面
- **v0.5.0 STDD 闭环:** Acceptance checklist + tests + independent audit for every release / 每次发布验收清单+测试+独立审计
- **三通道标准化:** Shell (direct command) / RPC (structured request-response) / ACP (agent communication protocol) — full monitorability and interruptibility / 全程可监控、可干预

→ [`hermes/call-omp/`](hermes/call-omp/)

### ✍️ skill-authoring · 技能创作合规 v4.0.0

> **5 commits in last 7 days** — SROF framework + v4.0.0 redesign · SROF 框架+v4.0.0 重构

11-step compliance creation + 7-dimension scoring for skills. Latest: v4.0.0 first-principles redesign + SROF (Skill Runtime Orchestration Framework).
11步合规创作+七维评分。最新：v4.0.0 第一性原理重构 + SROF 运行时编排框架。

- **v4.0.0 重构:** First-principles redesign — streamlined 11-step workflow with sharper quality gates / 第一性原理重构，精简流程+更锐利的质量门
- **SROF v1.1:** Skill Runtime Orchestration Framework — gate scripts + setup engine + lock generator for reproducible skill execution / 技能运行时编排框架 — 门控脚本+安装引擎+锁生成器
- **独立审计闭环:** SROF v1.0 received CONDITIONAL PASS independent audit from OMP / SROF v1.0 获 OMP 独立审计 CONDITIONAL PASS

→ [`shared/skill-authoring/`](shared/skill-authoring/)

> Previously featured skills like cqi-plan-writer, vault-keeper, and auto-diary remain in the full catalog below but have been superseded or stabilized.
> 此前入选的技能如 cqi-plan-writer、vault-keeper、auto-diary 仍保留在下方完整目录中，但已被取代或趋于稳定。

---

## 📋 Full Catalog · 完整目录

> **49 skills** across four platforms — shared foundations, Hermes agent operations, OMP methodology & operations, and pi extensions.
> **49 个技能**覆盖四大平台 — 共享基础层、Hermes 智能体操作层、OMP 方法论与运维层、pi 扩展层。

### shared/ — Cross-Platform Foundations · 跨平台基础技能 (25 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🐙 | [github](shared/github/) | Full GitHub ops / GitHub 全操作 |
| 📋 | [grill-with-docs](shared/grill-with-docs/) | Design review against governance docs / 设计审查 |
| ✍️ | [skill-authoring](shared/skill-authoring/) | v4.0.0 11-step, 7-dim scoring / 合规创作 |
| 🎯 | [goalgen](shared/goalgen/) | Multi-CLI goal instruction generator / 通用 goal 生成器 |
| 📄 | [pdf](shared/pdf/) | OCR, extract, markdown→PDF / PDF 全处理 |
| 🎙️ | [voice-to-markdown-workflow](shared/voice-to-markdown-workflow/) | Speech→structured markdown / 语音转文稿 |
| 🔊 | [audio-transcriber](shared/audio-transcriber/) | Denoise+diarization+Chinese ASR / 音频转录 |
| 📺 | [bilibili-video-analyzer](shared/bilibili-video-analyzer/) | Bilibili video analysis / B站视频分析 |
| ⚖️ | [china-legal-optimized](shared/china-legal-optimized/) | 7 legal domains / 中国法务 |
| 📊 | [cqi-plan-writer](shared/cqi-plan-writer/) | Signal-driven CQI writing / CQI 计划写作 |
| 🔮 | [destiny-matrix](shared/destiny-matrix/) | Jungian+BaZi+ZiWei+Astrology / 命运矩阵 |
| 📐 | [methodology-writer](shared/methodology-writer/) | Experience→structured methodology / 经验框架化 |
| 🧲 | [memory-hub](shared/memory-hub/) | CC→CQI auto-ingest loop / 自动归集回路 |
| 💎 | [obsidian](shared/obsidian/) | Vault ops, CLI, Bases, Defuddle / Obsidian 全操作 |
| 📓 | [obsidian-md-ac](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas / OFM 参考 |
| 🧠 | [supermemory-maintenance](shared/supermemory-maintenance/) | Supermemory v7 reference / 记忆参考 |
| 🚪 | [surge-gateway](shared/surge-gateway/) | Household proxy gateway / 家庭代理网关 |
| 🛜 | [unifi-ops](shared/unifi-ops/) | UniFi network operations / 网络运维 |
| 🧹 | [de-slop](shared/de-slop/) | Bilingual AI writing detection / 中英去 AI 味 |
| 🟥 | [xiaohongshu-cards](shared/xiaohongshu-cards/) | Article→RED card images / 小红书图文卡片 |
| 📱 | [xhs-tech-writer](shared/xhs-tech-writer/) | RED AI/tech short-form content / 小红书科技短图文 |
| 🏛️ | [vault-keeper](shared/vault-keeper/) | Obsidian lifecycle governance / 知识库治理 |
| 🌐 | [web-research-router](shared/web-research-router/) | Multi-engine search + deep loop / 检索总控 |
| 🕷️ | [xhs-crawler](shared/xhs-crawler/) | XHS CDP extraction / 小红书爬虫 |
| 🔖 | [bookmark-organizer](shared/bookmark-organizer/) | Bookmark curation / 书签策展 |

> 🗄️ `shared/_archived-strategic-insight-longform-slim/` — 已归档的战略洞察长文技能

### hermes/ — Agent Operations · 智能体操作技能 (20 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 📔 | [auto-diary](hermes/auto-diary/) | Daily→yearly diary pyramid / 自动化日记 |
| 🍎 | [mac-doctor](hermes/mac-doctor/) | 6-tier macOS health / macOS 巡检 |
| ⏰ | [cron-worker](hermes/cron-worker/) | Cron profile + pool watchdog / 定时任务 |
| 🤖 | [claude-code](hermes/claude-code/) | CC orchestration v4.2.1 / CC 编排 |
| 🖥️ | [cc-tmux](hermes/cc-tmux/) | Drive CC via tmux v1.31.0 / tmux 驱动 CC |
| 🎛️ | [cccmux](hermes/cccmux/) | cmux-native CC agent teams / cmux 原生团队编排 |
| 💾 | [supermemory-hermes](hermes/supermemory-hermes/) | Hermes Supermemory setup / 记忆配置 |
| 🗣️ | [tts-manager](hermes/tts-manager/) | TTS provider registry / TTS 管理 |
| ✉️ | [tech-support-email](hermes/tech-support-email/) | Investigation-first vendor emails / 技术支持邮件 |
| 📈 | [tradingagents](hermes/tradingagents/) | A-share market analysis / 交易分析 |
| 📅 | [calendar-manager](hermes/calendar-manager/) | Smart calendar + reminders / 智能日历 |
| 🌅 | [morning-news-briefing](hermes/morning-news-briefing/) | Daily news briefing / 早新闻简报 |
| 💬 | [telegram-topic-manager](hermes/telegram-topic-manager/) | Telegram Topic CRUD / 话题管理 |
| 📚 | [arxiv](hermes/arxiv/) | arXiv + Semantic Scholar / 论文检索 |
| 📡 | [dingtalk-message-monitor](hermes/dingtalk-message-monitor/) | Decrypt + monitor DingTalk DB / 钉钉解密监控 |
| 📶 | [openwrt-router](hermes/openwrt-router/) | OpenWrt/iStoreOS router ops / 路由器运维 |
| 📋 | [kanban-orchestrator](hermes/kanban-orchestrator/) | Decomposition playbook / Kanban 编排 |
| 🛤️ | [kanban-codex-lane](hermes/kanban-codex-lane/) | Kanban→Codex CLI lane / Kanban Codex 通道 |
| 🎓 | [teach-hermes](hermes/teach-hermes/) | Cross-session teaching in Telegram / Telegram 教学 |
| 🚀 | [call-omp](hermes/call-omp/) | 🆕 3-channel OMP bridge v0.7.0 / OMP 三通道桥接 |

### omp/ — OMP Methodology & Operations · OMP 方法论与运维 (2 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| ⚙️ | [omp-ops](omp/omp-ops/) | OMP config, models, API keys, search providers / OMP 配置运维 |
| 📐 | [stdd-omp](omp/stdd-omp/) | STDD micro-loop: spec→accept→build→verify / STDD 微循环 |

### pi/ — Personal Intelligence Extensions · 个人智能扩展 (2 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🛡️ | [pi-grill](pi/pi-grill/) | Ambiguity guardian v3.1 / 歧义守护 |
| 🔗 | [pi-hermes-setup](pi/pi-hermes-setup/) | Pi↔Hermes SSH+MCP / 联动设置 |

### 📦 Archived · 已归档

| | Path | Description · 说明 |
|---|------|-------------------|
| 🗄️ | [`_archived-hermes-3S6M-profiles/`](_archived-hermes-3S6M-profiles/) | 12 profiles — 三省六部 governance system. Companion repo: [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a) |
| 🗄️ | `shared/_archived-strategic-insight-longform-slim/` | Archived strategic insight longform skill |

---

## 🚀 Quick Start · 快速开始

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills
cd ~/code/jz-skills && ./deploy/sync-all.sh hermes   # → ~/.hermes/skills/
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh omp       # → ~/.omp/skills/
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

# 📥 Pull: repo → Hermes/CC/OMP/pi
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
| 3 | **Compliance · 合规** | All skills must pass [skill-authoring v4.0](shared/skill-authoring/) (11-step, 7-dim). |
| 4 | **Cross-platform · 跨平台** | `shared/` skills: no hardcoded paths, no platform-specific tools. |
| 5 | **Commits · 提交** | Bilingual: `type(scope): EN description / 中文描述`. |
| 6 | **Sync · 同步** | Always `sync-back.sh --dry-run` before commit. Never skip sanitize. |
| 7 | **Archive · 归档** | Deprecate with `_archived-{name}/`, never delete. |
| 8 | **Active · 高频** | Ranked by recent activity (last 7 days). Data-driven, not hand-picked. |

### 🔥 Active Skill Criteria · 高频标准

Skills in the **Active Skills** section are ranked by **recent activity** — not total historical commits:

- **Last 7 days** — activity window, reflecting what's being actively developed *right now*
- **Commit velocity** — higher commit frequency in the window ranks higher, regardless of lifetime totals
- **New skills welcome** — brand-new skills with rapid iteration can appear alongside mature ones

A skill with 50 lifetime commits but zero in the last week won't appear. A skill with 2 commits but both this week will. This keeps the section focused on what's hot *now*, not what was hot 3 months ago.

高频技能按近 7 天活跃度排序——反映当下而非历史。全新技能与成熟技能同台竞技，只看近期迭代速度。

---

## 📜 License · 许可

MIT — see [LICENSE](LICENSE).
