# 🏛️ jz-skills · AI Agent Skills Hub

![skills](https://img.shields.io/badge/skills-47-blue)
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
| 🧩 Shared | `shared/` | 25 | Works across Hermes, Claude Code, and pi |
| ⚡ Hermes | `hermes/` | 20 | Hermes‑only (macOS orchestrator) |
| 🪟 Pi | `pi/` | 2 | Windows / pi‑only |
| 🗄️ Archived | `_archived-hermes-3S6M-profiles/` | 12 profiles | Retired 三省六部 governance profiles |
| **Total** | | **47 skills** | |

<details>
<summary>🌳 Full skill tree</summary>

```
shared/                              🧩 25 skills
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
├── skill-authoring              # 11步合规创作+七维评分
├── supermemory-maintenance      # Supermemory v7 参考
├── surge-gateway                # Surge 家庭代理网关
├── unifi-ops                    # UniFi AP/交换机/Controller 运维
├── vault-keeper                 # Obsidian 知识库生命周期治理
├── voice-to-markdown-workflow   # 语音/视频→结构化 Markdown
├── web-research-router          # 六引擎搜索路由+深度研究循环
├── xhs-crawler                  # 小红书 CDP 提取（CloakBrowser）
├── xhs-tech-writer              # 小红书 AI/科技短图文
└── xiaohongshu-cards            # 文章→小红书图文卡片

hermes/                              ⚡ 20 skills
├── arxiv                        # arXiv + Semantic Scholar 论文检索
├── auto-diary                   # 自动化日记：日→周→月→年金字塔聚合
├── calendar-manager             # 智能日历+提醒
├── cc-tmux                      # tmux 驱动 Claude Code（脚本强制护栏）
├── cccmux                       # cmux 原生 CC agent team 编排
├── claude-code                  # CC 编排桥（已由 cc-tmux 取代）
├── cron-worker                  # 定时任务 profile + 技能池看门狗
├── dingtalk-message-monitor     # 钉钉本地DB解密+消息监控
├── kanban-codex-lane            # Kanban→Codex CLI 通道
├── kanban-orchestrator          # 任务分解+Kanban 编排
├── llm-wiki                     # Karpathy's LLM Wiki 知识库
├── mac-doctor                   # macOS 六级健康巡检
├── morning-news-briefing        # 每日早新闻简报
├── openwrt-router               # OpenWrt/iStoreOS 路由器运维
├── supermemory-hermes           # Hermes Supermemory 配置
├── teach-hermes                 # Telegram 跨会话教学
├── tech-support-email           # 调查驱动的技术支持邮件
├── telegram-topic-manager       # Telegram Topic CRUD + /topic 命令
├── tradingagents                # A股/市场分析
└── tts-manager                  # TTS 供应商注册+语音测试

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

### 🖥️ cc-tmux · tmux 驱动 CC v1.13.1

> **10 commits in last 3 days** — THE hottest skill · 最活跃技能

Drive Claude Code via tmux with script-enforced safeguards. The active CC driver — replacing the older claude-code skill.
通过 tmux 驱动 Claude Code，脚本强制护栏。当前主力 CC 驱动技能，取代旧版 claude-code。

- **Turn内等待 · In-turn Wait:** Waits for CC response within the same tmux turn before proceeding / 同一 tmux turn 内等待 CC 响应再继续
- **📡 Progress Reporting · 中间过程可视性:** Real-time visibility into CC's intermediate reasoning and tool calls / CC 中间推理与工具调用的实时可见性
- **四阶段Hook演进:** Deploy automation → event-driven monitoring → passive contract — full hook lifecycle / 部署自动化→事件驱动监控→被动合约，完整 Hook 生命周期
- **冻结检测:** THINK_TIME timer prevents silent hangs when CC freezes mid-reasoning / 检测 CC 推理卡死的静默冻结
- **F1-F4 一致性修复 + Pre-Send 讨论可操作性:** Fixes function key consistency + pre-send discussion operability / 函数键一致性修复 + 发送前讨论可操作
- **TDD implementation:** 32/33 tests green — test-driven from the ground up / 测试驱动开发，32/33 通过
- **审计修复 F1-F9:** Full audit pass with 9 fixes across the codebase / 全量审计，9 项修复

→ [`hermes/cc-tmux/`](hermes/cc-tmux/)

### 🔍 web-research-router · 检索总控 v3.11

> **22 total commits, 3 recent** — 6-engine search router · 六引擎搜索路由

Multi-engine deep research router with anti-hallucination guardrails. Latest iterations: Agent-Reach platform mode + 6 deep-source optimizations.
六引擎搜索路由 + 深度研究循环 + 反幻觉护栏。近期迭代：Agent-Reach 平台模式 + 六项深源分析优化。

- **6-engine cascade · 六引擎级联:** Exa + Brave (dual-primary) → Tavily (deep) → web_search (broad) → Sogou/WeChat → SearXNG (fallback) / 双主力→深度→广扫→微信/搜狗→兜底
- **v3.10 Agent-Reach · 智能可达:** Platform-mode integration — mandatory 4-step local check before any web call / 平台模式集成，强制四步本地检查
- **v3.11 6 optimizations:** Deep source analysis driven — coverage, latency, and dedup improvements / 深源分析驱动，覆盖率、延迟、去重优化
- **Anti-hallucination · 反幻觉:** Verbatim quote extraction + `[s<id>]` inline citation + WeChat/Sogou encrypted link decryption / 逐字引用 + 内联标注 + 微信/搜狗加密链接解密

→ [`shared/web-research-router/`](shared/web-research-router/)

### 📔 auto-diary · 自动化日记 v3.8.0

> **26 total commits, 3 recent** — pyramid aggregation diary · 金字塔聚合日记

Automated daily/weekly/monthly/yearly diary generation from cron with pyramid aggregation from daily fragments to yearly retrospectives.
从 cron 触发的日记生成到金字塔聚合的年报体系。

- **v3.8.0 Codex session collection:** Codex session auto-collection + dedup cron ID + doc drift fix / Codex 会话自动采集 + cron ID 去重 + 文档漂移修复
- **v3.6.3 cron HOME fix:** `pwd.getpwuid()` bypass to survive cron's polluted HOME environment / 绕过 cron 污染的 HOME 环境变量
- **DingTalk group ingestion · 钉钉群消息采集:** Decrypt local DingTalk SQLite → extract group messages → auto-include in daily diary / 解密本地加密 SQLite → 提取群消息 → 自动写入日记
- **Silent cron failure fix · 静默故障修复:** Diagnosed and fixed silent skill degradation from empty array — documented in failure pattern library / 诊断修复空数组导致的静默退化，写入故障模式库

→ [`hermes/auto-diary/`](hermes/auto-diary/)

### 🏛️ vault-keeper · 知识库治理 NEW

> **2 commits** — BRAND NEW skill · 全新技能

Obsidian knowledge base lifecycle governance engine. Rapidly developing with three-gate architecture and confidence-matrix quality control.
Obsidian 知识库生命周期治理引擎。快速迭代中，三道闸架构 + 置信矩阵质控。

- **三道闸 · Three Gates:** Capture gate → Judgment gate → Backfill gate — full lifecycle governance / 采集闸→判定闸→回填闸，全生命周期治理
- **置信矩阵 · Confidence Matrix:** Quantified confidence scoring for every knowledge assertion / 每条知识断言的量化置信度评分
- **Lint巡检 · Lint Patrol:** Automated quality patrol across the vault with rule-based checks / 基于规则的自动化质量巡检
- **抽样自校准 · Sampling Self-Calibration:** Periodic random sampling to verify and recalibrate confidence scores / 定期随机抽样验证并重校准置信度
- **判定/确定性两层拆分:** Judgment (subjective assessment) vs. Determinism (objective verification) — two-layer architecture / 主观判定与客观确定性分离的双层架构

→ [`shared/vault-keeper/`](shared/vault-keeper/)

### 📊 cqi-plan-writer · CQI 计划写作 v2.0

> **v2.0 just landed** — domain-agnostic CQI methodology · 领域无关 CQI 方法论

General-purpose CQI (持续质量改进) writing methodology. Structured plan authoring with hard evidence anchoring and major decision protocol.
通用持续质量改进写作方法论。结构化计划创作，硬证据锚定 + 重大决策协议。

- **v2.0 domain-agnostic:** Stripped domain assumptions — writes CQI plans for any field / 剥离领域假设，可为任何领域撰写 CQI 计划
- **v1.2 restructure pattern:** Systematic restructuring methodology with hard evidence anchoring / 系统化重构方法论 + 硬证据锚定
- **Completed appendix:** Mandatory completed-appendix section for traceability / 强制完成的附录章节，确保可追溯性
- **Major decision protocol:** Structured protocol for capturing and justifying architectural decisions / 结构化协议，捕获并论证架构决策

→ [`shared/cqi-plan-writer/`](shared/cqi-plan-writer/)

> Previously featured skills like claude-code, skill-authoring, grill-with-docs, and memory-hub remain in the full catalog below but have been superseded or stabilized.
> 此前入选的技能如 claude-code、skill-authoring、grill-with-docs、memory-hub 仍保留在下方完整目录中，但已被取代或趋于稳定。

---

## 📋 Full Catalog · 完整目录

> **47 skills** across three platforms — shared foundations, Hermes agent operations, and pi extensions.
> **47 个技能**覆盖三大平台 — 共享基础层、Hermes 智能体操作层、pi 扩展层。

### shared/ — Cross-Platform Foundations · 跨平台基础技能 (25 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🐙 | [github](shared/github/) | Full GitHub ops / GitHub 全操作 |
| 📋 | [grill-with-docs](shared/grill-with-docs/) | Design review against governance docs / 设计审查 |
| ✍️ | [skill-authoring](shared/skill-authoring/) | 11-step, 7-dim scoring / 合规创作 |
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
| 🌐 | [web-research-router](shared/web-research-router/) | 6-engine search + deep loop / 检索总控 |
| 🕷️ | [xhs-crawler](shared/xhs-crawler/) | XHS CDP extraction / 小红书爬虫 |
| 🔖 | [bookmark-organizer](shared/bookmark-organizer/) | Bookmark curation / 书签策展 |

### hermes/ — Agent Operations · 智能体操作技能 (20 skills)

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 📔 | [auto-diary](hermes/auto-diary/) | Daily→yearly diary pyramid / 自动化日记 |
| 🍎 | [mac-doctor](hermes/mac-doctor/) | 6-tier macOS health / macOS 巡检 |
| ⏰ | [cron-worker](hermes/cron-worker/) | Cron profile + pool watchdog / 定时任务 |
| 🤖 | [claude-code](hermes/claude-code/) | CC orchestration v4.2.1 / CC 编排 |
| 🖥️ | [cc-tmux](hermes/cc-tmux/) | Drive CC via tmux / tmux 驱动 CC |
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
| 🧪 | [llm-wiki](hermes/llm-wiki/) | Karpathy's LLM Wiki / LLM Wiki 知识库 |
| 📋 | [kanban-orchestrator](hermes/kanban-orchestrator/) | Decomposition playbook / Kanban 编排 |
| 🛤️ | [kanban-codex-lane](hermes/kanban-codex-lane/) | Kanban→Codex CLI lane / Kanban Codex 通道 |
| 🎓 | [teach-hermes](hermes/teach-hermes/) | Cross-session teaching in Telegram / Telegram 教学 |

### pi/ — Personal Intelligence Extensions · 个人智能扩展

| | Skill | Purpose · 用途 |
|---|-------|----------------|
| 🛡️ | [pi-grill](pi/pi-grill/) | Ambiguity guardian v3.1 / 歧义守护 |
| 🔗 | [pi-hermes-setup](pi/pi-hermes-setup/) | Pi↔Hermes SSH+MCP / 联动设置 |

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
