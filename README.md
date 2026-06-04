# 🏛️ jz-skills · AI Agent Skills Hub

<p align="center">
  <b>🇺🇸 English</b> · <b>🇨🇳 中文</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/skills-37-blue" alt="37 skills">
  <img src="https://img.shields.io/badge/platforms-Hermes%20%7C%20CC%20%7C%20pi-lightgrey" alt="platforms">
  <img src="https://img.shields.io/badge/sync-bidirectional-green" alt="bidirectional sync">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="MIT license">
</p>

> 🤖 **Hermes + Claude Code + pi 三端 AI agent 技能仓库 — 37 skills, 三层结构, 双向同步。**
>
> Skills authored, audited, and evolved by AI agents following [skill-authoring](shared/skill-authoring/). Deployed to a Hermes, Claude Code, and pi (Windows).
>
> 所有技能由 AI agent 按 [skill-authoring v3.0](shared/skill-authoring/) 创作、审计和迭代。部署于Hermes、Claude Code 和 pi (Windows)。

---

## 🌲 Structure · 四层结构

```
jz-skills/
├── shared/   🌐 跨平台 · Cross-platform (16)
├── hermes/   ⚙️ Hermes (16)
├── pi/       🪟 Pi / Windows (6)
└── _archived-hermes-3S6M-profiles/ 🗄️ 三省六部 · 已归档 (23)
```

| Layer | Directory | Skills | Scope · 范围 |
|:---|:---|:---:|:---|
| 🌐 | `shared/` | 16 | All 3 platforms · 三端同步 |
| ⚙️ | `hermes/` | 15 | Hermes platform · 平台通用 |
| 🪟 | `pi/` | 6 | Pi (Windows), self-authored · Pi 自创作 |

<details>
<summary><b>🌲 Full tree · 完整结构树</b></summary>

```
jz-skills/
├── shared/                        # 🌐 Cross-platform · 跨平台 (16)
│   ├── github/                    # GitHub 全操作
│   ├── grill-with-docs/           # 设计审查
│   ├── skill-authoring/           # 合规创作 (11-step, 7-dim scoring)
│   ├── pdf/                       # PDF 处理 (OCR/extract/Markdown→PDF)
│   ├── voice-to-markdown-workflow/# 语音/视频→结构化 Markdown
│   ├── audio-transcriber/         # 音频转录 (降噪+声纹+Qwen3-MLX)
│   ├── china-legal-optimized/     # 中国法务 (7 领域)
│   ├── destiny-matrix/            # 命运矩阵 (荣格八维+八字+紫微)
│   ├── methodology-writer/        # 经验→结构化方法论
│   ├── obsidian/                  # Vault ops + CLI + Bases + Defuddle
│   ├── obsidian-md-ac/            # OFM + Mermaid + Canvas 参考
│   ├── supermemory-maintenance/   # Supermemory v6 参考
│   ├── de-slop/                   # 中英双语去 AI 味
│   ├── xiaohongshu-cards/         # 文章→小红书图文卡片
│   ├── xhs-tech-writer/           # 小红书 AI 科技短图文
│   └── _archived-*/               # [已归档]
├── hermes/                        # ⚙️ Hermes 平台 (15)
│   ├── web-research-router/       # v3.8 · 5 引擎深度研究
│   ├── auto-diary/                # v3.5 · 日/周/月/年金字塔聚合
│   ├── mac-doctor/                # v2.2 · macOS 六级巡检
│   ├── cron-worker/               # v1.3 · 定时任务 + 四种心跳
│   ├── claude-code/               # v4.1 · CC 编排+双向拷问+自治团队
│   ├── tts-manager/               # TTS 聚合管理
│   ├── tech-support-email/        # v1.1 · 技术支持邮件
│   ├── supermemory-hermes/        # Hermes Supermemory 配置
│   ├── tradingagents/             # 交易分析
│   ├── news-assembly/             # 多源搜索→简报骨架
│   ├── source-verification/       # 事实验证 + Claim 溯源
│   ├── bilibili-video-analyzer/   # B站视频分析
│   ├── xhs-crawler/               # 小红书爬虫 (CloakBrowser)
│   ├── calendar-manager/          # 智能日历
│   ├── morning-news-briefing/     # 早新闻 · 每日新闻简报
└── pi/                            # 🪟 Pi / Windows (6)
    ├── web-research-router/       # TS SDK 检索总控
    ├── pi-web-research/           # v3.4 多引擎深度研究
    ├── pi-grill/                  # v3.1 歧义守护
    ├── skill-creator/             # v6.0 合规创作
    ├── pi-hermes-setup/           # Pi↔Hermes 联动
    └── pi-supermemory/            # Windows Supermemory
```

</details>

---

## 🔥 Active Skills · 高频迭代

Skills ranked by total commit count across the full repository history — reflecting sustained, multi-version iteration rather than recent burst activity.
按全仓库历史的提交总数排名——反映的是经历多个版本、持续迭代的技能，而非仅近期活跃。

> **Criteria · 入选标准:** ≥5 commits + ≥2 major versions + real functional evolution per version. Not hand-picked — data-driven. [Full rules ↓](#active-skill-criteria--高频标准)
> 入选硬指标：≥5 提交 + ≥2 大版本 + 每版实质能力增量。不靠主观，靠数据说话。

### ✍️ skill-authoring · 合规创作 v3.0

> **16 commits** — the most iterated skill in the repo · 仓库中迭代最多的技能

11-step compliance-first skill authoring workflow with 7-dimension scoring. Absorbed SkillEvolver + EmbodiSkill (2026-05) for deployment-driven skill evolution.
11 步合规创作工作流 + 七维评分。吸收 SkillEvolver + EmbodiSkill 实现部署驱动的技能进化。

- **11-step flow · 11 步流程:** Capture → Grill → Progressive disclosure → Anti-rationalization → Rule positioning → Checklist → 7-dim scoring → Test cases → Deployment-grounded audit → Failure classification → Revision / 捕获→审查→渐进披露→反合理化→规则定位→清单→七维评分→测试→部署审计→故障分类→修订
- **7-dim scoring · 七维评分:** Progressive disclosure, anti-rationalization, rule positioning, checklist coverage, test coverage, deployment fit, failure resilience / 渐进披露、反合理化、规则定位、清单覆盖、测试覆盖、部署适配、故障韧性
- **v3.0:** Dual-role review pattern (Advocate→Challenger→Synthesize), deployment-grounded audit / 双角色审查+部署根基审计

→ [`shared/skill-authoring/`](shared/skill-authoring/)

---

### 📔 auto-diary · 自动化日记 v3.5.1

> **14 commits** — evolved through six major versions (v2.0 → v3.5.1) · 历经六个大版本迭代

Automated daily diary + weekly/monthly/yearly report generation from cron. Evolved through six major versions (v2.0 → v3.5.1) with progressive structural refinement.
从 cron 触发的日记生成到金字塔聚合的年报体系，历经 v2.0→v3.5.1 六个大版本。

- **v3.5.1 — Silent cron failure fix · 静默故障修复:** 🔴 Cron `skills: []` 空数组仍然 status 'ok' 运行，但日记因缺少 skill 逐日退化（CC=0, 知识库=0, 裸模板）。诊断+修复命令已写入 skill Red Flags + Common Pitfalls + Troubleshooting
- **v3.5 — Pyramid aggregation · 金字塔聚合:** Daily→weekly→monthly→yearly with cron scheduling + validation / 日→周→月→年四级聚合
- **v3.4 — Validation loop · 校验闭环:** Real validation fixing internal contradictions between config and output / 修复配置与输出矛盾
- **v3.2 — CC classification · CC 三分类:** agent-team / independent / programmatic, entrypoint+parentUuid tracking / 三类 CC 会话分类
- **v3.0 — OFM formatting · 标准化:** YAML frontmatter, callouts, section dividers in generated output / 标准化 Obsidian 格式输出
- **Fixes · 修复:** `~` expansion bug, event-bridge exclusion, 助理体系 vs 治理体系 separation, SQLite session extraction / 路径 bug、体系分离、SQLite 迁移

→ [`hermes/auto-diary/`](hermes/auto-diary/)

---

### 🔍 web-research-router · 检索总控 v3.8

> **14 commits** — 5 major versions (v3.1→v3.8), 22 reference files · 22 个引用文件

Multi-engine search router with deep research loop. The most architecturally complex skill in the repo, evolved through five versions each adding a distinct capability layer.
五引擎搜索路由 + 深度研究循环。仓库中架构最复杂的技能，五个版本各叠加一层能力。

- **5 engines · 五引擎:** Exa + Brave (dual-primary) → Tavily (deep research) → web_search (broad) → SearXNG (fallback) / 双主力→深度→广扫→兜底
- **v3.2 — Deep research loop · 深度循环:** Plan → Section (facts.jsonl) → Reflect → Merge + cross-language blind-spot detection / 分节→反思→合并+跨语言盲区
- **v3.4 — Anti-hallucination · 反幻觉:** Verbatim quote extraction, `[s<id>]` inline citation, 3-column output (Confirmed/Inference/Conflicts) / 逐字引用+三分栏
- **v3.7 — Output contract + Step 0 · 输出契约+本地优先:** Mandatory 4-step local check before any web call + SearXNG demoted after cross-platform validation / 强制四步本地+降级 SearXNG
- **v3.8 — Auxiliary grounding · 辅助验证:** Claude Code WebSearch as unstable auxiliary source (pre-flight check gated) / CC 引擎作为辅助验证

→ [`hermes/web-research-router/`](hermes/web-research-router/)

---

### 🤖 claude-code · CC 编排 v4.1

> **12 commits** — 7 versions (v3.0→v4.1.0) · 29 reference files · Hermes↔CC 双向拷问 + 自治团队编排

Hermes-to-Claude Code orchestration bridge with bidirectional grilling protocol and autonomous agent team coordination. v4.1 adds constitutional red lines + Gate Stamp discipline — a correctness layer before execution.
从 Hermes 编排 Claude Code，v4.1 新增红线宪法 + Gate Stamp 执行前签章。

- **v4.1.0 — Constitutional red lines · 红线宪法:** 2 条铁律红线（📡 capture↔report 1:1 成对 + 讨论协议=不执行）+ 4 项 Gate Stamp（方案审定/effort/占用检测/session 时间戳）+ effort 路由下沉到 references/；红线上限→立即标记+补做禁下轮改
- **Discussion protocol · 讨论协议:** Hermes↔CC 双向拷问 — grill pattern（逐问/带推荐答案/先查事实）+ 多轮辩证 + 共识终止条件 + 讨论简报模板。吸收 `mattpocock/skills` grill-me + Du et al. 2023 multiagent debate
- **Session architecture · 会话架构:** 默认每次新建独立 session `hermes-cc-{agent}-{ts}`（废除共享 longterm），跨会话上下文走 `/tmp/cc-context-{task}.md`
- **v3.5.x — Stability fixes · 稳定性修复:** Smart effort routing（5 级，signal-based）+ Pitfall #24 假空闲检测 + #25 会话劫持 + #26 权限表单不可靠 + #27 自动恢复旧会话
- **v4.0.0 — Debt cleanup · 清债:** Pitfall 编号重排（#18–#27 连续无重复）、3 个 detail 补全、2 个坏链修复、6 个孤儿 reference 收编、共享 longterm 策略矛盾消除
- **Progress reporting · 进度汇报:** 强制 15s 首检 → 30-60s 轮询 → emoji 状态模板；沉默 >2min = 异常

→ [`hermes/claude-code/`](hermes/claude-code/)

---

### 🩺 mac-doctor · macOS 巡检 v2.2

> **10 commits** — 19 files, 2,135 lines · 仓库中最全面的系统运维技能

Six-tier macOS system health monitoring with root-cause diagnosis and dual cron scheduling. Sustained iteration fixing edge cases and adding diagnostic depth.
六级 macOS 健康巡检，含根因诊断和双 cron 调度。持续迭代修复边界情况和增强诊断深度。

- **6 layers · 六层:** Health scoring + root-cause → Security audit (27 items) → Hardware → Network → Privacy → History / 评分+根因→27项安全→硬件→网络→隐私→追踪
- **Dual cron · 双调度:** LLM agent (daily deep audit) + Silent Watchdog (30min, `no_agent=true`, anomaly-only) / LLM 深审+静默看门狗
- **v2.3:** Watchdog threshold-vs-anomaly silent logic; `None`-handling robustness / 看门狗静默逻辑+空值处理
- **Fixes · 修复:** pgrep browser false-positive (Arc/Edge), disk-cleanup safety gates, sustained-CPU threshold tuning / 进程误报、安全门、CPU 阈值

→ [`hermes/mac-doctor/`](hermes/mac-doctor/)

---

### 🕐 cron-worker · 定时任务 Agent v1.3

> **6 commits** — architectural foundation for all scheduled agent workloads · 定时任务基础设施

Dedicated cron-worker profile with four heartbeat patterns and cross-profile skill pool integrity watchdog. Defines the architecture for separating background tasks from interactive sessions.
专用定时任务 profile 架构 + 四种心跳模式 + 技能池完整性看门狗。

- **4 heartbeats · 四种心跳:** Cron (time) → Webhook (event) → Change detection (state-diff, zero-LLM idle) → Silent watchdog (anomaly-only) / 定时→事件→变更检测→静默
- **Skill pool watchdog · 技能池看门狗:** Full-depth `find` enumeration (132 skills vs glob's 124 blind-spotted), manifest baseline diff, 4-level alerting (CRITICAL/WARN/INFO/CLEAN) / 全深度枚举+基线比对+四级告警
- **Cross-profile pool · 跨 profile 共享池:** default (pool owner) + regent + cron-worker via `external_dirs` / 三方共读同池
- **Defense · 防御:** L1 prevention (`skill_sync.py` patch) + L2 monitoring (watchdog) + L2 cleanup (daily shell)

→ [`hermes/cron-worker/`](hermes/cron-worker/)

---

### 🧠 supermemory-maintenance · 记忆参考 v6

> **6 commits** — cross-platform memory infrastructure reference · 跨平台记忆基础设施参考

General reference for Supermemory — long-term memory infrastructure shared across Hermes, Claude Code, and pi. Architecture, SDK usage, container tags, processing pipeline, and diagnostic protocols. Platform-specific execution delegated to `supermemory-hermes` and `pi-supermemory`.
跨 Hermes/CC/pi 三端的 Supermemory 长期记忆参考。架构、SDK 使用、容器标签、管线、诊断协议。

- **4 references · 4 引用:** SDK divergence diagnosis, migration recipes, JSON schema, tri-test protocol / SDK 分歧诊断、迁移配方、schema、三测协议
- **Evolved through:** Initial pi-only → general reference v3 → v6 with cross-platform scope / 从 pi 专属演进到跨平台通用 v6

→ [`shared/supermemory-maintenance/`](shared/supermemory-maintenance/)

---

## 📋 Full Catalog · 完整目录

### 🌐 shared/ — Cross-platform · 跨平台 (16)

| Skill | Purpose · 用途 |
|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub ops / GitHub 全操作 |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs / 设计审查 |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | 11-step, 7-dim scoring — [§active](#-skill-authoring--合规创作-v30) |
| 📄 [`pdf`](shared/pdf/) | PDF: OCR, extract, markdown→PDF (A4 + mobile) / PDF 全处理 |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech→structured markdown / 语音转文稿 |
| 🎧 [`audio-transcriber`](shared/audio-transcriber/) | Denoise + diarization + Chinese ASR / 音频转录 |
| ⚖️ [`china-legal-optimized`](shared/china-legal-optimized/) | 合同/劳动/知产/公司/诉讼/个人/物业 / 7 legal domains |
| 🔮 [`destiny-matrix`](shared/destiny-matrix/) | 荣格八维 + 八字 + 紫微 + 占星 / Multi-modal analysis |
| 📐 [`methodology-writer`](shared/methodology-writer/) | Experience→structured methodology / 经验框架化 |
| 📓 [`obsidian`](shared/obsidian/) | Vault ops, CLI, plugin dev, Bases, Defuddle / Obsidian 全操作 |
| 🧷 [`obsidian-md-ac`](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas / OFM 参考 |
| 🧠 [`supermemory-maintenance`](shared/supermemory-maintenance/) | Supermemory v6 — [§active](#-supermemory-maintenance--记忆参考-v6) |
| ✂️ [`de-slop`](shared/de-slop/) | Bilingual AI writing detection / 中英去 AI 味 |
| 🎴 [`xiaohongshu-cards`](shared/xiaohongshu-cards/) | Article→RED card images / 小红书图文卡片 |
| ✍️ [`xhs-tech-writer`](shared/xhs-tech-writer/) | RED AI/tech short-form content / 小红书科技短图文 |

### ⚙️ hermes/ — Hermes platform (15)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | 5-engine search + deep loop — [§active](#-web-research-router--检索总控-v38) |
| 📔 [`auto-diary`](hermes/auto-diary/) | Daily→yearly diary — [§active](#-auto-diary--自动化日记-v35) |
| 🩺 [`mac-doctor`](hermes/mac-doctor/) | macOS 6-tier health — [§active](#-mac-doctor--macos-巡检-v22) |
| 🕐 [`cron-worker`](hermes/cron-worker/) | Cron profile + pool watchdog — [§active](#-cron-worker--定时任务-agent-v13) |
| 🤖 [`claude-code`](hermes/claude-code/) | CC orchestration v4.1 — discussion protocol + agent team — [§active](#-claude-code--cc-编排-v41) |
| 🧠 [`supermemory-hermes`](hermes/supermemory-hermes/) | Hermes Supermemory setup + multi-profile |
| 🎤 [`tts-manager`](hermes/tts-manager/) | TTS provider registry + voice testing |
| 📧 [`tech-support-email`](hermes/tech-support-email/) | Investigation-first vendor emails v1.1 |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis / 交易分析 |
| 📰 [`news-assembly`](hermes/news-assembly/) | Multi-source search→briefing skeleton / 简报汇编 |
| 🔬 [`source-verification`](hermes/source-verification/) | Fact-checking + claim verification / 事实验证 |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video analysis / B站视频 |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | XHS CDP extraction (CloakBrowser) / 小红书爬虫 |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar + reminders / 智能日历 |
| 📰 [`morning-news-briefing`](hermes/morning-news-briefing/) | Daily news briefing / 早新闻简报 |

### 🏯 hermes-3S6M-profiles/ — 三省六部 (23)

> 三省六部 Agent 治理体系 — 15 profiles, Kanban task routing, A2A protocol.
>
> **→ 完整架构与协议：** [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a)

| Layer | Count | Key skills · 核心技能 |
|:---|:---:|:---|
| `common/` | 2 | `three-provinces-constitution` v3.0 · `financial-research-agents` |
| `regent/` 👑 | 5 | `kanban-orchestrator` `kanban-worker` `kanban-gate` `6m-smoke-test` `morning-news-briefing` v4.0 |
| `gongbu/` 🛠️ | 5 | `disk-cleanup` `infra-health-check` `infra-monitoring` `surge-gateway` `agent-observability` |
| `tester/` ⚖️ | 2 | `code-review-toolkit` `agent-security-audit` |
| `jiangzuojian/` 🔧 | 2 | `delivery-gate` `specialist-engineer` |
| Other 10 | 1 ea | archivist / auditor / budget / dispatcher / engineer / hanlinyuan / planner / protocol / registry / shangshu ([A2A](https://github.com/Loveacup/hermes-a2a)) |

### 🪟 pi/ — Pi / Windows (6)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](pi/web-research-router/) | TypeScript SDK search routing / 检索总控 |
| 🔍 [`pi-web-research`](pi/pi-web-research/) | Multi-engine deep research v3.4 |
| 🛡️ [`pi-grill`](pi/pi-grill/) | Ambiguity guardian v3.1 |
| ✍️ [`skill-creator`](pi/skill-creator/) | Compliance-first authoring v6.0 |
| 🔗 [`pi-hermes-setup`](pi/pi-hermes-setup/) | Pi ↔ Hermes SSH + MCP |
| 🧠 [`pi-supermemory`](pi/pi-supermemory/) | Windows Supermemory |

---

## 🚀 Quick Start · 快速开始

```bash
git clone git@github.com:Loveacup/jz-skills.git ~/code/jz-skills

# Deploy to one platform · 单平台部署
cd ~/code/jz-skills && ./deploy/sync-all.sh hermes   # → ~/.hermes/skills/
./deploy/sync-all.sh cc        # → ~/.claude/skills/
./deploy/sync-all.sh pi        # → ~/.pi/skills/
```

> ⚠️ **Before creating or modifying skills, read [CLAUDE.md](CLAUDE.md) —** it defines naming, YAML frontmatter, commit standards, and cross-platform rules. All skills must pass [skill-authoring v3.0](shared/skill-authoring/) compliance.
> 创作或修改 skill 前，先读 [CLAUDE.md](CLAUDE.md) 了解命名、YAML、提交规范和跨平台规则。所有 skill 必须通过 [skill-authoring v3.0](shared/skill-authoring/) 合规审查。

---

## 🔄 Sync · 同步

**Always dry-run first · 始终先预览：**

```bash
# 📤 Push: Hermes → repo (required before commit · 提交前必做)
./deploy/sync-back.sh --dry-run   # ① Preview changes / 预览变更
./deploy/sync-back.sh             # ② Apply + auto-sanitize / 执行+脱敏
git diff && git commit -m '...' && git push

# 📥 Pull: repo → Hermes/CC/pi
git pull && ./deploy/sync-all.sh <platform>
```

`sync-back.sh` auto-sanitizes before commit: `$HOME` → `~/`, emails → redacted, private IPs → redacted, API keys → redacted. **Never commit without running sync-back first** — live Hermes changes won't be reflected.
`sync-back.sh` 提交前自动脱敏：路径/邮箱/内网IP/API密钥 → 替换。**不跑 sync-back 就提交 = 丢失 Hermes 端实时修改。**

🛂 **Gateway restart** when skills change for `regent` or `default`:

```bash
hermes gateway restart -p regent
hermes gateway restart -p default
```

---

## 📏 Governance · 治理规则

> **Full rules → [CLAUDE.md](CLAUDE.md)** · 完整规则见 CLAUDE.md

| Rule · 规则 | Requirement · 要求 |
|:---|:---|
| 📦 **Naming** | `lowercase-hyphens` only. No `_`, no CamelCase. |
| 📋 **YAML frontmatter** | Every SKILL.md must have `name` + `description` + `version` + `author` + `license`. |
| ✍️ **Compliance** | All skills must pass [skill-authoring v3.0](shared/skill-authoring/) (11-step, 7-dim). |
| 🌐 **Cross-platform** | `shared/` skills: no hardcoded paths, no platform-specific tools. |
| 💬 **Commits** | Bilingual: `type(scope): EN description / 中文描述`. |
| 🔄 **Sync** | Always `sync-back.sh --dry-run` before commit. Never skip sanitize. |
| 🗄️ **Archive** | Deprecate with `_archived-{name}/`, never delete. |
| 🔥 **Active** | Ranked by full-history commit count — sustained iteration over burst. Active means 5+ commits across 2+ versions. |

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
