---
name: morning-news-briefing
description: "Use when producing the daily morning news briefing — multi-source parallel search via web-research-router, fused analysis format (前提→推理→结论 + 趋势 + 为什么重要), mobile + A4 PDF delivery, and TTS voice edition. Supports dual execution mode: Cron (shell-parallel search + sequential pipeline) and Interactive (Kanban Swarm with auto-decomposition). Do NOT use for single-topic deep dives, non-news content, or manual article curation."
version: 4.0.1
author: Hermes Agent (v4.0.1 — 2026-06-04 Cron 验证：parallel tool calls 替代 shell background，零路径问题)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [productivity, news, briefing, mobile-pdf, daily, tts, kanban]
    related_skills: [web-research-router, source-verification, de-slop, tts-manager, news-assembly]
---

# 早新闻简报 v4.0

CC 设计审查驱动升级。三大修复：新闻数量保障（新增「今日要闻」摘要层）、TTS 语音版（Step 6）、Kanban v0.15 Swarm 双模式执行。

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll use yesterday's template, same CSS" | Style continuity gate: must auto-diff against last accepted baseline. Free-form styling = broken brand |
| "I'll just run web_search for each section" | web-research-router picks the best engine per query type. Brave for broad coverage, Exa for semantic discovery, Tavily for fact grounding. Direct web_search skips all three |
| "The analysis is thin today, I'll pad it" | Analysis format is locked: 前提→推理→结论 + 📈趋势 + 为什么重要. No hedging — grep for 一方面/另一方面/可能/或许 → auto-reject |
| "10 articles is fine, they're all deep" | Sentinel #2 demands ≥15 独立新闻条目 in 📰 今日要闻, NOT just deep analysis items. Assembly must not collapse multiple sources into one entry |
| "I'll render as soon as assembly starts" | Render card MUST wait for assembly completion (parent dependency). Rendering before content = blank/stale PDF |
| "TTS is optional, skip it" | v4.0 mandate: TTS generation (Step 6) is part of the pipeline. If text_to_speech tool unreachable, skip + annotate — never silently omit |

## 🔀 Execution Modes

v4.0 supports two execution modes. The skill detects which environment it's running in and picks the right path.

### Mode A: Cron (scheduled, batch)

Cron jobs run single-threaded without gateway dispatcher. Use shell background for search parallelism:

```
Trigger: cron scheduler (daily 08:00)
├── Step 0: Workspace setup
│   mkdir -p ~/.hermes/workspaces/morning-news-{date}/{search,output,audit}
│
├── Step 1: Parallel search — PREFERRED: parallel tool calls in one turn
│   4 lanes × 3 engines = up to 12 queries, all in a single turn
│   Each engine call is independent → they execute in parallel
│   web_search (broad) + Exa (semantic) + Brave (cross-check) per lane
│   Enrich with Tavily follow-ups where depth needed
│   Direct markdown assembly from tool results — skip intermediate JSON
│   Fallback: shell background jobs only if tool-call parallelism unavailable
│
├── Step 2: Assembly (sequential)
│   Read search artifacts → deduplicate → structure with new layers
│   Write: morning-news-{date}.md → workspace root
│
├── Step 2.5: de-slop (citation-protected)
│   Run de-slop on non-citation blocks only
│
├── Step 3: Source verification
│   Claim extraction → 2-path evidence → 4-level confidence on key claims
│
├── Step 4: Render PDF (two editions)
│   Mobile: 430×932px + A4: 210×297mm
│
├── Step 5: Audit (7 sentinels + anti-hedging + source count)
│
├── Step 6: TTS Generation ← NEW
│   Extract 摘要→分析→总结 from markdown → text_to_speech
│
└── Step 7: Deliver (MEDIA: PDFs + audio to user)
```

### Mode B: Interactive / Kanban Swarm (manual trigger)

**状态：✅ 已验证（2026-06-04）** — 并行搜索 + 验证通过，publisher gateway 需修端口配置。

When triggered interactively (not cron), use Kanban v0.15 Swarm for full multi-agent pipeline:

```bash
# 实测语法 — 2026-06-04 验证
hermes kanban swarm \
  --worker "lane-zh:中文搜索:productivity/morning-news-briefing,web-research-router" \
  --worker "lane-en:英文搜索:productivity/morning-news-briefing,web-research-router" \
  --worker "lane-mixed:市场数据:productivity/morning-news-briefing,web-research-router" \
  --worker "lane-tech:科技新闻:productivity/morning-news-briefing,web-research-router" \
  --verifier auditor \
  --synthesizer publisher \
  "生成 {date} 早新闻简报：四路并行搜索 → 汇编 → 深度分析 → 渲染 PDF → TTS → 交付"
```

**实测结果（2026-06-04）**：

| Worker | 产出 | 状态 |
|--------|------|:--:|
| lane-zh (flash) | 20 条中文新闻 | ✅ |
| lane-en (flash) | 18 条英文新闻 6 板块 | ✅ |
| lane-mixed (flash) | 8 板块市场数据 | ✅ |
| lane-tech (flash) | 10 条科技新闻 | ✅ |
| auditor (pro) | PASS — 仅 1 处轻微不一致 | ✅ |
| publisher (pro) | 合成+渲染+TTS | ⚠️ 54 次崩溃 |

**Publisher 崩溃根因**：`platforms.api_server.extra.port` 需为每个 profile 分配独立端口（当前默认为 8460，与 default 冲突）。修复后 publisher 应正常完成合成。

⚠️ **注意**：
- `--worker` 格式是 `PROFILE:TITLE[:SKILL,SKILL]`，每个并行 worker 一个独立 flag
- **没有** `--workers N`（数量 flag）、`--worker-model`、`--verifier-model` 这些 flag
- Model 由各 profile 的 `config.yaml` 控制：搜索 worker 用便宜模型，verifier 用高质量模型
- 详见 `references/kanban-swarm-workflow.md`

Swarm topology:
```
Root (Blackboard)
  ├── Worker 1: Lane ZH search (Brave → Tavily)
  ├── Worker 2: Lane EN search (Exa → Tavily)
  ├── Worker 3: Lane Mixed + Tech search (Brave → Exa → Tavily)
  └── Worker 4: Assembly + de-slop + source-verification
        ↓
  Verifier: Audit (7 sentinels + anti-hedging)
        ↓
  Synthesizer: Render PDFs + TTS + Deliver
```

Kanban advantages over cron:
- Per-task model override: cheap models for search, expensive for verification
- Artifact auto-delivery: `kanban_complete(artifacts=[...])` → Telegram
- Audit trail: every worker run persisted in task_runs
- Crash recovery: zombie detection + auto-reclaim

See `references/kanban-swarm-workflow.md` for full Kanban integration spec.

## ⚡ Core Rules

1. **搜索必须三+路并行** — 不走单引擎。Brave 中文广撒网 + Exa 英文深度发现 + Tavily 事实校验。缺一路 = 缺信息维度。
2. **结果必须落盘持久 workspace** — 用 `~/.hermes/workspaces/morning-news-{date}/`。搜索完立即写 JSON。
3. **渲染必须等汇编完成** — 父子依赖不可跳。
4. **CSS 必须 diff-check** — 渲染前跑 `assets/diff-check.sh` 双版验证，偏离 baseline >5% 警告。
5. **交付前必须全量审计** — 7 sentinels × 2 editions，PyMuPDF 全量提取，反骑墙 grep，源数校验。任一未过 = 不得交付。
6. **搜索失败不阻塞整路** — 单源 404/单引擎超时 = 跳过 + 标注。整路失败 = 其他路填补。三路全败 = 中止。
7. **Workspace 持久化卫生** — 新建 workspace `chmod 700`，含 `.gitignore`（`*` 全忽略）。保留 7 天。
8. **TTS 属于 pipeline，不是可选项** — Text-to-speech 工具不可达时跳过并标注，但不得静默省略。

## Content Specifications

### 📰 今日要闻 (Today's Headlines) — NEW in v4.0

- **Purpose**: Quick-scan summary before deep analysis.
- **Count**: 15-20 条独立新闻条目（展开后每条 2-3 句完整描述，非标题碎片）
- **Format**: 每条 2-3 句完整描述 + 信源编号 [sN] + 可选小时间线
- **Source**: 从四路搜索中提取，保留独立性，不在此层融合
- **Organization**: 按板块分组（🔥 中东/俄乌 / 🇺🇸 美国 / 🇨🇳 中国 / 🌍 国际 / 📊 市场+科技）

### 🕐 历史时间线 (v4.1 NEW)

每个有历史纵深的板块开头放**分区脉络框**（.sec-timeline），梳理事件来龙去脉。每条相关新闻上方放**小时间线**（.story-tl），紧凑箭头链。

格式：
```
分区脉络框：灰底 + 左侧 IKB 粗线 + mono 日期 + 箭头链
小时间线：  mono 小字 + accent 色日期 + → 箭头
```

Example:
```markdown
## 📰 今日要闻

### 🔥 中东·俄乌
- 美伊停火濒临破裂，伊朗导弹击中科威特机场，美军打击格什姆岛 [s1]
- 俄罗斯发动战争以来最大规模空袭：73枚导弹+656架无人机，22死130伤 [s2]

### 🇺🇸 美国
- Trump-Xi北京峰会后续：$14B对台军售成最大悬念 [s3]
- ...

总计: ≥15 items
```

### 执行摘要 (Executive Summary)
- Location: first page after cover
- Format: 3-5 bullet points distilled from 今日要闻

### 🔍 深度分析 (Deep Analysis) — v4.0 adjusted count

Each analysis item follows the locked structure:

```
🔍 分析：{标题}

前提：{1-2句事实陈述，引用具体数据/事件来源}
推理：{1-2句因果链，不骑墙，不含"可能/或许"}
结论：{1句明确判断}
趋势：📈/📉/⚠️ + 方向
为什么重要：{1句 impact statement}
```

- **Count**: 5-8 items (not the same as article count!)
- **Selection**: pick top stories from 今日要闻 for deep dive
- **Anti-hedging hard check**: grep for `一方面|另一方面|可能|或许|似乎`. Any hit → REJECT.

### 📌 今日总结 (Daily Summary)
- Standalone card after all analysis
- Core tension one-liner
- 2-3 forward-looking observations

### TTS 语音稿 (Step 6 output)

See §TTS Generation below for full specification.

## TTS Generation (Step 6) — ⛔ NOT OPTIONAL

> **EXECUTION LAPSE GUARD**: 2026-06-03 测试中 agent 跳过了此步骤。Step 6 不是 "如果时间允许就做"，是 v4.0 pipeline 的硬步骤。必须在 audit 通过后、交付前用 `text_to_speech` 工具实际调用，产出 `output/morning-news-{date}.mp3`。不调用 = 未完成。

Triggered after audit passes, before delivery. Produces `output/morning-news-{date}.mp3`.

### Content Structure (三段式)

| Segment | Source | Length | Style |
|---------|--------|--------|-------|
| **开场摘要** | 执行摘要 → 口语化 | 30-45s | "早上好，今天是{date}。三件大事：…" |
| **深度分析** | Top 3 分析条目 | 60-90s | 每条压缩为"事件 + 为什么重要"（≤50字/条）|
| **收尾总结** | 📌 今日总结 | 20-30s | 核心张力 + 一句话前瞻 |

**Total**: ≤5 分钟语音

### Generation Flow

```
1. 从 morning-news-{date}.md 提取三段内容
2. 改写为口语化脚本 → tts-script-{date}.txt
3. 调用 Hermes text_to_speech(text=script)
4. 保存 output/morning-news-{date}.mp3
5. 质检：试听 30s 片段，确认无吞字/断句
```

### Fallback

If `text_to_speech` tool unreachable (CosyVoice down, no TTS provider):
- Log: "TTS skipped — text_to_speech unavailable"
- Continue delivery without audio
- Do NOT silently omit the step

## Sections (Fixed)

1. 📰 **今日要闻** — 15-20 条快速摘要（NEW in v4.0）
2. 🔥 **深度分析** — 5-8 条 前提→推理→结论 分析
3. 🇺🇸 **美国** — domestic, economy, Congress, tech
4. 🇨🇳 **中国** — politics, economy, tech, diplomacy, society
5. 🌍 **国际** — Russia-Ukraine, Asia-Pacific, Africa, LatAm
6. 📊 **市场+科技** — oil, equities, forex, crypto, AI/tech
7. 📌 **今日总结** — core tension + outlook

Note: 今日要闻 is a flat list, not sectional. The sections below it organize the deep analysis.

## 7 Sentinels (Missing Any = Rework)

| # | Sentinel | Check Method |
|---|----------|-------------|
| 1 | **执行摘要** | 3-5 bullet points on first page |
| 2 | **📰 今日要闻** | ≥15 独立新闻条目（来源计数以 📰 来源清单 S01-SNN 为准），按板块分组 |
| 3 | **🔍 深度分析** | 5-8 items, each 前提→推理→结论 + 趋势 + 为什么重要 |
| 4 | **📌 今日总结** | Standalone card with core tension one-liner |
| 5 | **来源清单** | S01–SNN numbered list with outlet names + URLs |
| 6 | **Alex Cai** | Cover/header attribution |
| 7 | **日期** | Current date: YYYY年M月D日 format |

## Source Requirements

- Managed by web-research-router confidence-based routing
- Reference registry: `references/sources.json`
- Target: ≥50 outlets, routed by locale (zh/en)
- Cross-check: Tavily grounding + Brave verification for claims
- Per-source error resilience: single source failure ≠ chain failure
- **Article count**: 今日要闻 must contain ≥15 independent news items. Sources counted by 📰 来源清单 numbering (S01-SNN).

## Format Specifications

**v4.1 起全部使用 Swiss Hybrid 设计系统。** 详见 `references/swiss-hybrid-design-system.md`。

模板：`assets/mobile-template.html`（手机）、`assets/standard-template.html`（A4）。均为 v7 Swiss IKB + serif 编辑体。

### Mobile Edition — Swiss Hybrid (430×932px)

| Property | Value |
|----------|-------|
| body font-size | 14px（不得低于此值！） |
| content font-size | 12px |
| section heading | 16px Inter sans-serif |
| line-height | 1.65 |
| @page margin | 14px 16px 14px |
| body font | Noto Serif SC (serif) |
| accent | #002FA7 IKB Blue |
| paper | #fafaf8 |
| layout | 自然流，不硬断页 |
| timeline | 分区脉络框 + 每条新闻小时间线（见 design-system ref） |
| KPI | 6 列紧凑数据条 |

### Key Layout Rules

1. **不硬断页。** 内容自然填满，不留大片底部空白。仅封面独立一页。
2. **正文 14px 底线。** 用户多次迭代确定。12px 以下不可接受。
3. **时间线必加。** 有历史纵深的板块加分区脉络框，每条相关新闻加小时间线。
4. **信源 50+。** 来源清单从 sources.json 的 50+ outlets 拉取。

## References

| File | Content |
|------|---------|
| `references/sources.json` | Structured source registry with locale/tier/status |
| `references/analysis-format.md` | Fused analysis format specification |
| `references/search-workflow.md` | web-research-router integration + search lanes |
| `references/kanban-swarm-workflow.md` | Kanban v0.15 Swarm integration spec |
| `references/tts-script-spec.md` | TTS 三段式脚本规范 |
| `references/pdf-layout-accepted-variants.md` | Accepted CSS baselines |
| `references/mobile-pdf-layout-eight-commandments.md` | 8-commandment verification checklist |
| `references/mobile-pdf-visual-qa-lessons.md` | Visual QA lessons learned |
| `references/style-continuity-gate.md` | Style continuity enforcement |
| `references/swiss-hybrid-design-system.md` | Swiss Hybrid 设计系统：token、字号、时间线、布局规则 |
| `assets/mobile-template.html` | 🆕 v7 Swiss Hybrid mobile template (430×932px) — IKB + serif 编辑体 |
| `assets/standard-template.html` | 🆕 v7 Swiss Hybrid A4 template — 5 列市场 grid + 3 列来源 |
| `assets/diff-check.sh` | Pre-render CSS diff against baseline |

## 🔧 P0 修复记录 (2026-06-03)

### 问题：Cron-worker 无法加载本 skill

两层大门锁死，导致 v3.0 cron job 运行整整一周从未真正加载本 skill：

**门一：顶层裸目录不被索引**

Hermes skill 索引器只扫描分类子目录（如 `productivity/`、`devops/`），直接放在 `skills/` 顶层的不被收录。旧部署脚本 `cp -r` 把内容拷到 `cron-worker/skills/` 顶层 → 索引器跳过。

→ **修复：symlink 到分类子目录**
```bash
ln -s ~/.hermes/skills/productivity/morning-news-briefing \
      ~/.hermes/profiles/cron-worker/skills/productivity/morning-news-briefing
```

**门二：platforms 字段白名单（硬编码）**

源码 `agent/skill_utils.py:21-25`：
```python
PLATFORM_MAP = {
    "macos":   "darwin",
    "linux":   "linux",
    "windows": "win32",
}
```

`skill_matches_platform()` 将 SKILL.md 的 `platforms` 值通过 MAP 映射后与 `sys.platform` 比对。MAP 外的任何值（如 `cron`、`telegram`）不经过映射，直接用原始字符串去比 `sys.platform`（macOS 上是 `darwin`）→ 恒不匹配 → `unsupported`。

→ **结论：platforms 字段只能取 `macos`/`linux`/`windows` 三者之一。**

### ⚠️ Bait-Mistake：cp -r 到顶层是陷阱

旧部署命令（SKILL.md 之前写的 `cp -r ...morning-news-briefing cron-worker/skills/`）会在 cron-worker 的 `skills/` 顶层创建裸目录 → 索引器不扫描 → skill 永不加载。**永远用 cp 到分类子目录**。

## ⚠️ Critical Pitfalls

| Pitfall | Why it burns you |
|---------|-----------------|
| **单引擎搜索** | 直接 web_search 不走三引擎路由 = 丢失深度发现和事实校验 |
| **汇编截断新闻数** | 把 20 条新闻 fusion 成 10 条分析 = Sentinel #2 失败。📰 今日要闻必须在分析之前独立产出 |
| **静默跳过 TTS** | v4.0 TTS 是 pipeline 步骤，不可达时标注但不得省略 |
| **盲 `git commit -am`** | .env/缓存/API 原始响应一并推上 GitHub |
| **反骑墙 grep 未跑** | "一方面/另一方面/可能/或许" 任一命中 = 骑墙分析 |
| **Cron 中用 delegate_task 做搜索并行** | delegate_task batch 模式支持最多 3 个 subagent 真并行搜索，cron 下完全可用。parallel tool calls 亦是可行方案 |
| **Cron 搜索用 shell background 而非 parallel tool calls** | shell background 写入的 JSON 文件可能因 cron-worker 的 execute_code 路径偏移落在错误的 workspace（`~/.hermes/profiles/cron-worker/home/...`），导致后续 assembly 读不到。parallel tool calls 直接在主 Agent 上下文处理结果，无此问题。2026-06-04 验证：12 查询单轮次并行 → 直接汇编，零路径问题 |
| **cp 到 skills 顶层** | 索引器只扫描分类子目录。顶层裸目录 = skill 永不加载。必须放 `skills/productivity/` 下 |
| **反骑墙 grep 写了但没跑** | SKILL.md 规定 `grep 可能/或许/似乎 → REJECT`，但 agent 在汇编阶段不会主动跑 grep。必须在 Step 2 汇编完成后用 `execute_code` 或 `terminal` 机械执行 grep，命中任一即阻断渲染，不是 checklist 里的可选项 |

## ✅ Verification Checklist (RUN BEFORE DELIVERY)

- [ ] All 7 sentinels verified via PyMuPDF full-text extraction (both editions)?
- [ ] 📰 今日要闻: ≥15 独立新闻条目? (NOT analysis count!)
- [ ] 🔍 深度分析: 5-8 items, each 前提→推理→结论 + 趋势 + 为什么重要?
- [ ] Anti-hedging: zero hits for 一方面/另一方面/可能/或许?
- [ ] CSS diff-check passed for BOTH editions (deviation <5%)?
- [ ] Source ledger: S01–SNN numbered with outlet names + verifiable URLs?
- [ ] TTS: `output/morning-news-{date}.mp3` exists and 试听通过? (if unreachable: annotated skip)
- [ ] PDF files delivered directly (not just path)?
- [ ] Audio file delivered alongside PDFs?

**If any box is unchecked, go back.**

---

## Deployment & Sync

This is a **morning-news-briefing** skill. After ANY update:

```bash
# 1. Symlink to cron-worker profile (NOT cp to顶层 — 索引器不扫顶层目录)
mkdir -p ~/.hermes/profiles/cron-worker/skills/productivity/
ln -sf ~/.hermes/skills/productivity/morning-news-briefing \
        ~/.hermes/profiles/cron-worker/skills/productivity/morning-news-briefing

# 2. Restart cron-worker gateway to clear skill cache
#    (PID from `ps aux | grep 'hermes.*cron-worker'`)

# 3. Sanitize — never blind commit
grep -rE '(gho_|sk-[0-9a-zA-Z]{20,}|192\.168|172\.(1[6-9]|2[0-9]|3[0-1])\.)' \
  . && echo "⚠️ SENSITIVE DATA FOUND" && exit 1 || true

# 4. Verify: skill_view('productivity/morning-news-briefing') returns readiness_status=available

# 5. Git sync
git add . && git commit -m "v4.0.X: update" && git push
```

### Cron Job Configuration

Cron 只需要引用 skill，不需要内联 prompt。用 `hermes cron create` 或直接写 `jobs.json`：

```json
{
  "name": "早新闻简报",
  "skill": "productivity/morning-news-briefing",
  "skills": [
    "productivity/morning-news-briefing",
    "web-research-router",
    "research/source-verification",
    "creative/de-slop",
    "hermes/tts-manager",
    "productivity/news-assembly"
  ],
  "schedule": "0 8 * * *",
  "profile": "cron-worker",
  "model": "deepseek-v4-pro",
  "provider": "deepseek",
  "deliver": "origin",
  "prompt": "你是早新闻生产 Agent。严格按 morning-news-briefing SKILL.md 的 Mode A (Cron) 流程执行。\n\n执行顺序：\nStep 0: 创建 workspace ~/.hermes/workspaces/morning-news-{date}/\nStep 1: 四路并行搜索（parallel tool calls）→ 直接汇编\nStep 2: 汇编 → morning-news-{date}.md\nStep 3: 来源校验\nStep 4: 渲染双版 PDF（mobile 430×932 + A4）\nStep 5: 7 sentinels 审计\nStep 6: TTS 语音版\nStep 7: 交付（MEDIA: PDFs + audio）"
}
```

**关键规则**：
- `skill` + `skills` 字段让 cron 启动时自动注入 SKILL.md 到 system prompt，agent 无需自己调 `skill_view`
- `prompt` 仅作任务触发，具体流程由 SKILL.md 的 Mode A 章节定义
- `profile: "cron-worker"` 确保在 cron-worker profile 下运行，使用其 skill 索引
- 搜索可用 parallel tool calls（同轮次批量发起 MCP 调用）或 `delegate_task` batch 模式（最多 3 个 subagent 并行搜索），两者均为真并行
- `delegate_task` 在汇编/渲染/审计等重推理阶段仍可用，按需使用
