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
│   ├── skill-authoring/           # 合规创作
│   ├── pdf/                       # PDF 处理
│   ├── voice-to-markdown-workflow/# 语音转文稿
│   ├── audio-transcriber/         # 音频转录 (pyannote + Qwen3-MLX)
│   ├── china-legal-optimized/     # 中国法务 7 领域
│   ├── destiny-matrix/            # 命运矩阵 (荣格八维 + 八字 + 紫微)
│   ├── methodology-writer/        # 方法论文创作
│   ├── obsidian/                  # Vault ops + CLI + Bases
│   ├── obsidian-md-ac/            # OFM + Mermaid + Canvas
│   ├── supermemory-maintenance/   # Supermemory 参考 v6
│   ├── de-slop/                   # 中英去 AI 味
│   ├── xiaohongshu-cards/         # 小红书图文卡片
│   ├── xhs-tech-writer/           # 小红书 AI/科技短图文
│   └── _archived-strategic-insight-longform-slim/  # [已归档]
├── hermes/                        # ⚙️ Hermes 平台 (15)
│   ├── web-research-router/       # v3.8 · 检索总控 + 深度研究
│   ├── auto-diary/                # v3.5 · 自动化日记
│   ├── mac-doctor/                # v2.2 · macOS 六级巡检
│   ├── cron-worker/               # v1.3 · 定时任务 + 四种心跳
│   ├── claude-code/               # v3.5 · CC 编排
│   ├── tradingagents/             # 交易分析
│   ├── llm-wiki/                  # LLM 知识库
│   ├── arxiv/                     # 论文检索
│   ├── bilibili-video-analyzer/   # B站视频分析
│   ├── xhs-crawler/               # 小红书爬虫
│   ├── calendar-manager/          # 智能日历
│   ├── reply-context-retrieval/   # TG 引用回溯
│   ├── supermemory-hermes/        # 记忆架构手册
│   ├── tech-support-email/        # 技术支持邮件
│   └── tts-manager/               # TTS 聚合管理
├── hermes-3S6M-profiles/          # 🏯 三省六部 (23)
│   ├── common/                    # 全部门通用
│   │   ├── three-provinces-constitution/
│   │   └── financial-research-agents/
│   ├── regent/ (5)                # 👑 监国太子 · 唯一有 gateway
│   │   ├── morning-news-briefing/ # v4.0
│   │   ├── kanban-orchestrator/
│   │   ├── kanban-worker/
│   │   ├── kanban-gate/
│   │   └── 6m-smoke-test/
│   ├── gongbu/ (5)                # 🛠️ 工部
│   ├── tester/ (2)                # ⚖️ 刑部
│   ├── jiangzuojian/ (2)          # 🔧 将作监
│   └── <dept>/ (1 each × 10)      # 其余 10 部门
└── pi/                            # 🪟 Pi / Windows (6)
    ├── web-research-router/
    ├── pi-web-research/
    ├── pi-grill/
    ├── skill-creator/
    ├── pi-hermes-setup/
    └── pi-supermemory/
```

</details>

---

## 🔥 Active Skills · 高频更新

Skills with rapid iteration — multiple versions in recent months, significant complexity, or frequent improvement.
近期迭代密集的核心技能。

### 🔍 web-research-router · 检索总控 v3.8

**Multi-engine search router with deep research · 多引擎搜索路由 + 深度研究**

The most complex skill in the repo (22 reference files). 仓库中最复杂的技能（22 个引用文件）。

- **5 engines · 五引擎:** Exa + Brave (dual-primary 双主力) → Tavily (deep research 深度) → web_search (broad 广扫) → SearXNG (fallback 兜底)
- **Deep loop · 深度循环:** Plan → Section (facts.jsonl) → Reflect → Merge with cross-language blind-spot detection / 跨语言盲区检测
- **Anti-hallucination · 反幻觉:** Verbatim quote extraction, `[s<id>]` inline citation, 3-column output (Confirmed / Inference / Conflicts) / 逐字引用 + 三分栏
- **Step 0 mandatory · 强制四步本地:** Supermemory → session → qmd → CodeGraph before any web call / 先查本地再上公网

→ [`hermes/web-research-router/`](hermes/web-research-router/)

---

### 📔 auto-diary · 自动化日记 v3.5

**Daily/weekly/monthly/yearly diary generation · 日/周/月/年报自动生成**

Rapid evolution driven by structural improvements. 结构优化驱动的快速迭代。

- **v3.5:** Pyramid aggregation — daily → weekly → monthly → yearly with cron scheduling / 金字塔聚合 + cron 调度
- **v3.4:** Real validation loop, fixed internal contradictions / 真实校验闭环
- **v3.1:** CC session classification (3 types) + KB↔AI linking / CC 会话三分类 + 知识库关联
- **v3.0:** obsidian-md-ac formatted output / 标准化格式输出

→ [`hermes/auto-diary/`](hermes/auto-diary/)

---

### 🩺 mac-doctor · macOS 巡检 v2.2

**Six-tier macOS health monitoring · 六级系统巡检**

50+ checks, 19 files, 2,135 lines. Absorbed 9 OSS projects (mole, mactop P0).
50+ 检查项，19 个文件，2,135 行。吸收 9 个开源项目。

- **6 layers · 六层:** Health scoring → Security audit (27 items) → Hardware → Network → Privacy → History / 评分→安全→硬件→网络→隐私→追踪
- **Dual cron · 双调度:** LLM agent (daily deep audit) + Silent Watchdog (30min, anomaly-only) / LLM 深审 + 静默看门狗

→ [`hermes/mac-doctor/`](hermes/mac-doctor/)

---

### 🕐 cron-worker · 定时任务 Agent v1.3

**Dedicated cron profile with 4 heartbeat patterns + skill pool integrity watchdog · 四种心跳 + 技能池完整性看门狗**

- **4 heartbeats · 四种心跳:** Cron → Webhook → Change detection → Silent watchdog / 定时→事件→变更检测→静默
- **Watchdog:** Full-depth pool enumeration (132 vs glob's 124 blind-spotted), manifest baseline diff, 4-level alerting / 全深度枚举 + 基线比对 + 四级告警
- **Cross-profile pool · 跨 profile 共享池:** default (owner 拥有者) + regent + cron-worker share via `external_dirs` / 三方共读同池

→ [`hermes/cron-worker/`](hermes/cron-worker/)

---

### 🤖 claude-code · CC 编排 v3.5

**Orchestrate Claude Code CLI from Hermes · 从 Hermes 编排 Claude Code**

- **v3.5.0:** Smart effort routing + agent team enhancement / 智能路由 + agent team 增强
- **v3.5.1:** False-idle detection (CC appears stuck but is thinking) / 假空闲检测
- **Modes:** Print mode, interactive tmux, agent team / 三种模式

→ [`hermes/claude-code/`](hermes/claude-code/)

---

## 📋 Full Catalog · 完整目录

### 🌐 shared/ — Cross-platform · 跨平台 (16)

| Skill | Purpose · 用途 |
|:---|:---|
| 🐙 [`github`](shared/github/) | Full GitHub ops: auth, issues, PR, code review / GitHub 全操作 |
| 📋 [`grill-with-docs`](shared/grill-with-docs/) | Design review against governance docs / 设计审查 |
| ✍️ [`skill-authoring`](shared/skill-authoring/) | 7-dim compliance scoring, 11-step flow / 七维合规评分 |
| 📄 [`pdf`](shared/pdf/) | PDF: OCR, extract, markdown→PDF (mobile 430×932px) / PDF 全处理 |
| 🎙️ [`voice-to-markdown-workflow`](shared/voice-to-markdown-workflow/) | Speech transcript → structured markdown / 语音转文稿 |
| 🎧 [`audio-transcriber`](shared/audio-transcriber/) | Denoise + diarization + Chinese ASR (Qwen3-MLX) / 音频转录 |
| ⚖️ [`china-legal-optimized`](shared/china-legal-optimized/) | 合同/劳动/知产/公司/诉讼/个人/物业 7 领域 / 7 legal domains |
| 🔮 [`destiny-matrix`](shared/destiny-matrix/) | 荣格八维 + 八字 + 紫微 + 占星 / Multi-modal analysis |
| 📐 [`methodology-writer`](shared/methodology-writer/) | Experience → structured methodology / 经验框架化 |
| 📓 [`obsidian`](shared/obsidian/) | Vault ops, CLI, plugin dev, Bases / Obsidian 全操作 |
| 🧷 [`obsidian-md-ac`](shared/obsidian-md-ac/) | OFM + Mermaid + JSON Canvas reference / OFM 完整参考 |
| 🧠 [`supermemory-maintenance`](shared/supermemory-maintenance/) | Supermemory v6: architecture, SDK, diagnostics / 记忆架构 |
| ✂️ [`de-slop`](shared/de-slop/) | Bilingual AI writing detection & humanization / 中英去 AI 味 |
| 🎴 [`xiaohongshu-cards`](shared/xiaohongshu-cards/) | Article → 1080×1440 RED card images / 小红书图文卡片 |
| ✍️ [`xhs-tech-writer`](shared/xhs-tech-writer/) | 小红书 AI/科技短图文创作 / RED tech short-form content |

### ⚙️ hermes/ — Hermes platform (15)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](hermes/web-research-router/) | Multi-engine search + deep research — [§active](#-web-research-router--检索总控-v38) |
| 📔 [`auto-diary`](hermes/auto-diary/) | Daily/weekly/monthly/yearly diary — [§active](#-auto-diary--自动化日记-v35) |
| 🩺 [`mac-doctor`](hermes/mac-doctor/) | macOS 6-tier health monitor — [§active](#-mac-doctor--macos-巡检-v22) |
| 🕐 [`cron-worker`](hermes/cron-worker/) | Cron profile + 4 heartbeats + pool watchdog — [§active](#-cron-worker--定时任务-agent-v13) |
| 🤖 [`claude-code`](hermes/claude-code/) | CC orchestration — [§active](#-claude-code--cc-编排-v35) |
| 📈 [`tradingagents`](hermes/tradingagents/) | A-share / market analysis / 交易分析 |
| 🧠 [`llm-wiki`](hermes/llm-wiki/) | Karpathy-style LLM knowledge base / LLM 知识库 |
| 📚 [`arxiv`](hermes/arxiv/) | Academic paper search / 论文检索 |
| 📺 [`bilibili-video-analyzer`](hermes/bilibili-video-analyzer/) | Bilibili video deep analysis / B站视频分析 |
| 📕 [`xhs-crawler`](hermes/xhs-crawler/) | Xiaohongshu CDP content extraction / 小红书爬虫 |
| 📅 [`calendar-manager`](hermes/calendar-manager/) | Smart calendar & reminders / 智能日历 |
| ↩️ [`reply-context-retrieval`](hermes/reply-context-retrieval/) | Telegram reply context retrieval / TG 引用回溯 |
| 🧠 [`supermemory-hermes`](hermes/supermemory-hermes/) | Cabinet memory architecture manual / 记忆架构手册 |
| 📧 [`tech-support-email`](hermes/tech-support-email/) | Investigation-first vendor communication / 技术支持邮件 |
| 🎤 [`tts-manager`](hermes/tts-manager/) | TTS provider registry + voice testing / TTS 聚合管理 |

### 🏯 hermes-3S6M-profiles/ — 三省六部 (23)

> 三省六部 Agent 治理体系 — 15 profiles, Kanban task routing, A2A inter-agent protocol.
>
> **→ Full architecture & A2A docs · 完整架构与协议文档：** [hermes-s6m-a2a](https://github.com/Loveacup/hermes-s6m-a2a)

| Layer | Count | Key skills · 核心技能 |
|:---|:---:|:---|
| `common/` | 2 | `three-provinces-constitution` v3.0 · `financial-research-agents` |
| `regent/` 👑 | 5 | `kanban-orchestrator` `kanban-worker` `morning-news-briefing` v4.0 — 唯一有 gateway 的 profile |
| `gongbu/` 🛠️ | 5 | `disk-cleanup` `infra-health-check` `infra-monitoring` `surge-gateway` `agent-observability` |
| `tester/` ⚖️ | 2 | `code-review-toolkit` `agent-security-audit` |
| `jiangzuojian/` 🔧 | 2 | `delivery-gate` `specialist-engineer` |
| Other 10 depts · 其余部门 | 1 ea | archivist / auditor / budget / hanlinyuan / protocol / registry / shangshu ([A2A](https://github.com/Loveacup/hermes-a2a)) / dispatcher / engineer / planner |

### 🪟 pi/ — Pi / Windows (6)

| Skill | Purpose · 用途 |
|:---|:---|
| 🔍 [`web-research-router`](pi/web-research-router/) | TypeScript SDK search routing / 检索总控 (TS) |
| 🔍 [`pi-web-research`](pi/pi-web-research/) | Multi-engine deep research v3.4 / 多引擎深度研究 |
| 🛡️ [`pi-grill`](pi/pi-grill/) | Ambiguity guardian v3.1 / 歧义守护 |
| ✍️ [`skill-creator`](pi/skill-creator/) | Compliance-first authoring v6.0 / 合规创作 |
| 🔗 [`pi-hermes-setup`](pi/pi-hermes-setup/) | Pi ↔ Hermes SSH + MCP / 联动架构 |
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

> Other 13 3S6M profiles are internal-dispatch — no restart required. 其余 13 profile 走内部调度，无需重启。

---

## 🤝 Contributing · 贡献

1. Edit skills on your agent or directly in repo / 在 agent 上或直接编辑
2. `./deploy/sync-back.sh --dry-run` — preview / 预览
3. `./deploy/sync-back.sh` — sync with auto-sanitization / 同步 + 脱敏
4. Commit and push / 提交推送

---

## 📜 License · 许可

MIT — see [LICENSE](LICENSE).
