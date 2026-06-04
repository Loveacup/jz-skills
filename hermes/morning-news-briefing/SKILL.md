---
name: morning-news-briefing
description: "Use when producing the daily morning news briefing — multi-engine search via web-research-router v3.9 (Brave/Exa 发现 + Exa Fetch/Tavily Extract 抓取), verbatim-quote anchored analysis, de-slop AI-pattern removal (55+ patterns), source-verification claim-level audit, TTS audio delivery via CosyVoice, and mobile PDF delivery (430×932px). Executes in hybrid mode: delegate_task for search (fast), Kanban for assembly+render (auditable). 触发词: 早新闻, morning news, daily briefing, 简报, 朝议. Do NOT use for single-topic deep dives, non-news content, A4 reports, or manual article curation."
version: 5.1.1
author: Hermes Agent (v5.1.1 — P2 fixes: source-verification skill 落地 + tts 经 text_to_speech/tts-manager + 清私网 IP + de-slop 引文保护区 + aihot 降级回环修正)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [productivity, news, briefing, mobile-pdf, daily, verbatim-quote, anti-hallucination]
    related_skills: [web-research-router, news-assembly, de-slop, source-verification, tts-manager, pdf, skill-authoring]
---

# 早新闻简报 v5.1

Hybrid execution: parallel search via delegate_task + auditable assembly/render via Kanban. Aligned with **web-research-router v3.9** — Brave/Exa 双主力发现 + Exa Fetch/Tavily Extract 抓取 + verbatim quote 抽取 + **de-slop AI 去味** + **source-verification 验证** + **TTS 语音播报**。

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll use yesterday's template, same CSS" | Style continuity gate: must auto-diff against last accepted baseline. Free-form styling = broken brand |
| "I'll just run web_search for each section" | v5.0 搜索经 web-research-router 路由（Brave/Exa 双主力发现 → Exa Fetch/Tavily Extract 抓取）。直接 `web_search` 跳过 WRR = 漏独立索引交叉 + 漏 verbatim quote 锚 |
| "SearXNG 广扫一把梭" | SearXNG 实例已损坏(WRR v3.9 判定)，仅 WRR 内部最后兜底。三 lane 按场景分工：中文=Brave 主、英文=Exa 主、科技=Brave+Exa（aihot 仅兜底辅助）。详见 `references/search-workflow.md` v3.0 |
| "The analysis is thin today, I'll pad it" | Analysis format is locked: 前提→推理→结论 + 📈趋势 + 为什么重要. No hedging — grep for 一方面/另一方面/可能/或许 → forced-answer rewrite 一次 → 仍 hedge 才 REJECT（v4.0 不再 reject-only） |
| "Banned phrases 太啰嗦 / fetch 完直接综合答案就行" | 详见 Core Rules #2（fetch-extract verbatim quote 必跑）+ #6（15 个禁词 + Sherman Kent 概率 regex）。两条都跳 = 简报满屏 "could potentially" + 引用不可追溯 |
| "Search results are in Kanban summaries, good enough" | All search output MUST land in persistent workspace paths. Scratch GC has eaten results 3+ times |
| "I'll render as soon as assembly starts" | Render card MUST wait for assembly completion (parent dependency). Rendering before content = blank/stale PDF |

## 🔀 Decision Tree

```
"早新闻" / "morning news" triggered?
├── Step 1: Parallel search via delegate_task (3 lanes, v5.0 经 web-research-router 路由)
│   ├── Lane A: 中国媒体 (Brave 主+Exa 发现 → Exa Fetch/Tavily Extract 抓取 → Tavily 校验数据, ≥15 sources)
│   ├── Lane B: 美国+国际 (Exa 主+Brave 发现 → Exa Fetch/Tavily Extract 抓取 → Tavily grounding, ≥18 sources)
│   └── Lane C: 市场+科技 (Brave+Exa 发现 → Exa Fetch/Tavily Extract 抓取 → Tavily 价格校验, ≥8 sources; aihot 仅兜底辅助)
│   每 lane 4 步：WRR 路由发现(Brave/Exa，aihot仅兜底) → query-decomposition → fetch-extract(Exa Fetch/Tavily Extract) → cross-check
│   Full routing spec: references/search-workflow.md (v3.0) · DESCRIPTORS 字典: references/keyword-expansion-dict.md
│   All results → persistent workspace: ~/.hermes/workspaces/morning-news-{date}/search/
│
├── Step 2: Assembly (Kanban → hanlinyuan, 调 news-assembly skill)
│   调 news-assembly: dedup + 事件合并 + 连续性检测 + 重要性打分 + 5 板块结构化 → assembled-{date}.json
│   早新闻在骨架上套 🔍 analysis-format 分析层 + banned-phrases 门禁
│   Write: morning-news-{date}.md → persistent path
│
├── Step 2.5: ★ de-slop 去 AI 味（汇编后、渲染前强制执行）
│   加载 de-slop skill → 语言检测 → 中文走 ZH Pipeline（密度×语体×功能三维修剪）
│   英文走 EN Pipeline（30+ 模式扫描 + 5 维评分 ≥35）
│   逐段重写 → Audit → Final → 写回 morning-news-{date}.md
│   🛡️ 保护区：含 `$数字`/价格/百分比 的句子与 citation 锚定（如 `[s3]`）的句子**不重写**，
│      只动其前后叙述——保住 verbatim quote 可追溯（Core Rule #2）。改写后跑 Sentinel 3 复检趋势/为什么重要未被剥离
│   ⚠️ 不可跳过：de-slop 覆盖 banned-phrases 外的 55+ AI 模式
│
├── Step 3: Render (Kanban → jiangzuojian, parent=assembly)
│   Two editions, sequenced:
│   ├── Mobile: Load assets/mobile-template.html → diff-check mobile-baseline.css
│   └── Standard: Load assets/standard-template.html → diff-check standard-baseline.css
│   Render HTML → Playwright PDF → PNG spot-checks (both editions)
│
├── Step 4: Audit (Kanban → auditor)
│   PyMuPDF extraction → 7 sentinels × 2 editions + anti-hedging + source count
│   ★ source-verification: 对价格/政策/声明类 claim 做结构化验证（verified/partial/contradicted/not found）
│
└── Step 5: Deliver (Kanban → reviewer)
    Final gate → deliver both MEDIA paths to user
    ★ tts-manager: 生成 CosyVoice 语音播报版（执行摘要 + 头条，≤2min），MEDIA 路径交付
```

## ⚡ Core Rules (Hermes Agent 执行规则)

1. **搜索经 web-research-router 路由 + 三路并行** — v5.0 每 lane 经 WRR 发现：Lane A 中文 = **Brave**(locale/时效)主 + **Exa** 语义补；Lane B 英文 = **Exa** 主 + **Brave** 独立交叉；Lane C 科技 = **Brave** 快讯 + **Exa** 深度（aihot 🔶 仅兜底辅助）。**Tavily** 做数字/价格 grounding。**SearXNG 实例已损坏(WRR v3.9 判定)，仅 WRR 内部最后兜底，绝不起手。**
2. **每条 source 必跑 fetch-extract → verbatim quote** — 抓取主力 `mcp_exa_web_fetch_exa` / `mcp_tavily_tavily_extract`（`urls: string[]` 数组）+ extractor prompt 抽 verbatim quote，入 `source_map.extracted_quotes[]`。**不让单次 LLM call 同时 fetch + 综合答案**（幻觉源头）。`web_extract` 已弃用（拦截所有 HTTPS）。详见 router `references/fetch-extract-pattern.md`。
3. **结果必须落盘持久 workspace** — 用 `~/.hermes/workspaces/morning-news-{date}/`。scratch GC 已吃掉 3+ 次搜索结果。搜索完立即写 JSON，不缓存内存。
4. **渲染必须等汇编完成** — 父子 Kanban 依赖不可跳。先渲染 = 空白/过期 PDF。
5. **CSS 必须 diff-check** — 渲染前跑 `assets/diff-check.sh` 双版验证，偏离 baseline >5% 警告。禁止自由调色/改布局。
6. **Anti-hallucination + banned-phrases 强制** — assembly 写完正文先跑 `references/banned-phrases-and-probability-scale.md` 的 regex 扫描（15 个禁词 + Sherman Kent 7 档概率）；命中 → 触发 anti-refusal forced-answer rewrite 一次 → 仍命中 → REJECT。规则详见 `references/anti-hallucination-rules.md`。
7. **交付前必须全量审计** — 7 sentinels × 2 editions，PyMuPDF 全量提取，反骑墙 + 反禁词 grep，源数校验。任一未过 = 不得交付。
8. **搜索失败不阻塞整路** — 单源 404/单引擎超时 = 跳过 + 标注。整路失败 = 其他路填补。三路全败 = 中止奏报，不等。
9. **Workspace 持久化卫生** — 新建 workspace `chmod 700`，含 `.gitignore`（`*` 全忽略）。保留 7 天，超期 `find -mtime +7 -delete`。
10. 🆕 **de-slop 去 AI 味（汇编后强制执行）** — 汇编产出 `morning-news-{date}.md` 后，加载 de-slop skill 扫描全文。中文走 ZH Pipeline（语体识别 + 密度三问 + AI 不敢写测试），英文走 EN Pipeline（30+ 模式 + 5 维评分 ≥35）。**保护区：含 `$数字`/价格/百分比及 citation 锚（`[sN]`）的句子不重写**，以保住 verbatim quote 可追溯（Core Rule #2）；改写后复检 Sentinel 3（趋势/为什么重要未被剥离）。改写后写回原文件，不可跳过。de-slop 覆盖 banned-phrases 未覆盖的 55+ AI 模式。
11. 🆕 **source-verification 声明级验证（审计阶段）** — 对含价格/数据/政策/排名的高风险 claim（抽样 ≤10 条/版）标置信度：verified / partial / contradicted / not found。**唯一硬阻塞 = contradicted** → 删除该 claim 并回退重写该段。`not found` → 标 `⚠️ 未验证` 保留、**不阻塞**（可能是推理层产出）；`partial` → 标 `📎 部分验证` 通过。放行条件：无 contradicted 残留。
12. 🆕 **TTS 语音播报（交付阶段）** — 从执行摘要 + 头条板块提取文本（≤500 字），调 Hermes `text_to_speech` 工具（后端由 **tts-manager** skill 管理，当前默认 CosyVoice/AlexCai 音色）生成 OGG 语音，MEDIA 路径随 PDF 一同交付。后端不可达 → 静默跳过，不阻塞 PDF。

## Content Specifications

### 执行摘要 (Executive Summary)
- Location: first page after cover
- Format: 3-5 bullet points, each ≤30 characters
- PyMuPDF check: page 1 must contain bullet markers or `<li>` elements

### 分析格式 (Analysis Format) — see `references/analysis-format.md`

Every analysis item MUST follow this structure:

```
🔍 分析：{标题}

前提：{1-2句事实陈述，引用具体数据/事件来源}
推理：{1-2句因果链，不骑墙，不含"可能/或许"}
结论：{1句明确判断}
趋势：📈/📉/⚠️ + 方向
为什么重要：{1句 impact statement}
```

**Anti-hedging hard check**: grep output for `一方面|另一方面|可能|或许|似乎`. Any hit → REJECT.

### 来源要求 (Source Requirements)

- Managed by web-research-router confidence-based routing
- Reference registry: `references/sources.json`
- Target: ≥50 outlets, routed by locale (zh/en)
- Cross-check: Tavily grounding + Brave verification for claims
- Per-source error resilience: single source failure ≠ chain failure

## Format Specifications

### Mobile Edition — see `assets/mobile-template.html`

| Property | Value | Reason |
|----------|-------|--------|
| page | 430×932px | Phone portrait |
| line-height | 1.8 | CJK text anti-overlap |
| card gap | 14px | ≥12px minimum |
| @page margin-right | 18px | ≥16px minimum |
| body font-size | 14px | Mobile readable |
| body background | #fffdf8 | Cream newsletter base |
| body color | #1b1a17 | Dark gray text |
| accent color | #b47a32 | Bronze gold accents |
| market grid | 1fr 1fr | 2-column cards |

### Standard Edition — see `assets/standard-template.html`

Based on `early-news-20260521-balanced-editorial.pdf`.

| Property | Value | Reason |
|----------|-------|--------|
| page | A4 (210×297mm) | Desktop/print |
| margins | 14mm 14mm 15mm | Compact editorial |
| body font-size | 12.5px | Dense reading |
| line-height | 1.72 | CJK editorial |
| cover | dark gradient #111827→#123c55→#0f172a | Financial brief style |
| h1 | Georgia/Songti SC serif 37px | Editorial masthead |
| section h2 | Georgia/Songti SC serif 20px | Blue #123c55 bottom border |
| body color | #171717 (#ink) | High contrast |
| accent color | #b6782b (#gold) | Warm editorial gold |
| market grid | repeat(3, 1fr) | 3-column quotes |
| analysis | drop-cap 21px gold serif em | Editorial callout |
| source list | columns: 2 82mm | 2-column compact |
| article flow | max-width 178mm | Centered readable column |
| footer | page numbers @bottom-center | Print convention |

### Pre-Render Diff Gate — see `assets/diff-check.sh`

```
# Mobile
bash assets/diff-check.sh output/morning-news-{date}-mobile.html assets/mobile-baseline.css

# Standard
bash assets/diff-check.sh output/morning-news-{date}-standard.html assets/standard-baseline.css
```

If deviation >5%, warn and use baseline.

## Style Continuity

- Baseline: `references/pdf-layout-accepted-variants.md` (last accepted)
- Render must explicitly reference baseline
- No free-form color/layout experimentation
- Gate: `references/style-continuity-gate.md`

## Sections (Fixed)

1. 🔥 **头条/中东** — Iran, Hormuz, UAE
2. 🇺🇸 **美国** — domestic, economy, Congress, tech
3. 🇨🇳 **中国** — politics, economy, tech, diplomacy, society
4. 🌍 **国际** — Russia-Ukraine, Asia-Pacific, Africa, LatAm
5. 📊 **市场** — oil, equities, forex, crypto

## 7 Sentinels (Missing Any = Rework)

| # | Sentinel | Check Method |
|---|----------|-------------|
| 1 | **执行摘要** | 3-5 bullet points on first page |
| 2 | **新闻正文** | ≥15 articles, each with `📡 来源` tag |
| 3 | **🔍 分析** | ≥4 items, each 前提→推理→结论 + 趋势 + 为什么重要 |
| 4 | **📌 今日总结** | Standalone card with core tension one-liner |
| 5 | **来源清单** | S01–SNN numbered list with outlet names + URLs |
| 6 | **Alex Cai** | Cover/header attribution |
| 7 | **日期** | Current date: YYYY年M月D日 format |

## References

| File | Content |
|------|---------|
| `references/sources.json` | Structured source registry — zh/en/ai_newsletter/aggregator/special（v4.0 扩到 62 条，含 BBC Chinese / Guardian World / AI Newsletter 7 个 / HN Algolia 24h API） |
| `references/analysis-format.md` | Fused analysis format specification |
| `references/search-workflow.md` ⭐ | v3.0 — 三 lane 信源分工(中文 Brave 主/英文 Exa 主/科技 Brave+Exa，aihot 仅兜底) + query-decomposition + fetch-extract(Exa Fetch/Tavily Extract) + Tavily grounding（对齐 web-research-router v3.9） |
| `references/anti-hallucination-rules.md` ⭐ | v4.0 新增 — Anti-Hallucination 规则 + Anti-Laziness Protocol + 时间戳/SVO/Empty Data 工程教训（cclank verbatim） |
| `references/banned-phrases-and-probability-scale.md` ⭐ | v4.0 新增 — 15 个禁词 + Sherman Kent 7 档概率刻度 + Critic regex（the-briefing verbatim） |
| `references/keyword-expansion-dict.md` ⭐ | v4.0 新增 — 每 lane 4-5 个 DESCRIPTORS 字典（zh-politics/economy/tech/society + us-politics/economy/tech + intl-conflict/economy + market-equities/crypto/commodities/forex）|
| `references/delegate-task-mcp-limitation.md` | MCP tool availability in delegate_task + fallback |
| `references/cache-schema.md` | Incremental cache design (coming in Phase 3) |
| `references/pdf-layout-accepted-variants.md` | Accepted CSS baselines |
| `references/mobile-pdf-layout-eight-commandments.md` | 8-commandment verification checklist |
| `references/mobile-pdf-visual-qa-lessons.md` | Visual QA lessons learned |
| `references/style-continuity-gate.md` | Style continuity enforcement |
| `references/dailybrief-lessons.md` | DailyBrief project absorption |
| `assets/mobile-template.html` | Locked CSS/HTML template (430×932px) |
| `assets/mobile-baseline.css` | Mobile CSS baseline (diff-check anchor) |
| `assets/standard-template.html` | Locked CSS/HTML template (A4, based on balanced-editorial) |
| `assets/standard-baseline.css` | Standard CSS baseline (diff-check anchor) |
| `assets/diff-check.sh` | Pre-render CSS diff against baseline |
| `scripts/incremental-cache.sh` | Save/diff/clean daily search cache |
| `references/p2-outsourcing-integration.md` 🆕 | P2 外包 skill 集成规范：de-slop / source-verification / tts-manager / pdf 接驳点与接口契约 |

## ⚠️ Critical Pitfalls (Top 5)

| Pitfall | Why it burns you |
|---------|-----------------|
| **裸调 web_search / web_extract 跳过 WRR** | 搜索必须经 web-research-router（Brave/Exa 发现 + Exa Fetch/Tavily Extract 抓取）。裸 `web_search` 漏独立索引交叉；`web_extract` 已弃用(拦截所有 HTTPS) → 伪引用 → 幻觉数字。盲 `git commit -am` 走 sanitize grep（见 Deployment 段） |
| **fetch-extract 跳过、直接综合答案** | 单次 LLM call 同时 fetch + 综合 = 幻觉高发。必须 extractor 抽 verbatim quote 后，独立 call 综合（详见 router fetch-extract-pattern.md） |
| **scratch workspace 丢产出** | 内存缓存被 GC 吃掉 3+ 次。搜索产物必须落盘持久 workspace |
| **先渲染后汇编** | 内容未完成就渲染 = 空白 PDF。Kanban 父子依赖不可跳过 |
| **反骑墙 + 反禁词 grep 未跑** | "一方面/另一方面/可能/或许/significant developments/remains to be seen" 等 19+ 词命中 = 骑墙或空话。v4.0 命中 → forced-answer rewrite 1 次 → 仍命中 REJECT |

### More Anti-Patterns

- Using free-form CSS instead of locked `assets/*-template.html`
- Hedging analysis with "on one hand… on the other…"
- Compressing news items to reduce page count
- Delivering before audit is `done`
- Rendering before assembly is complete (missing parent dependency)

## ✅ Verification Checklist (RUN BEFORE DELIVERY)

- [ ] **7 sentinels + anti-hallucination 全检** — PyMuPDF 双版提取；anti-hallucination-rules.md 第六节 audit 表逐项过。
- [ ] **Search trace** — 每 lane 的 search/`lane-*.json` 都有 `engines: ["brave"/"exa", ...]` 标记；`extracted_quotes[]` 非空（抓取走 Exa Fetch/Tavily Extract）。
- [ ] **Analysis** — 所有 🔍 分析项遵循 前提→推理→结论 + 趋势 + 为什么重要；概率词只用 Sherman Kent 7 档。
- [ ] **Anti-hedging + anti-banned-phrases** — 一方面/另一方面/可能/或许 + 15 个 banned phrases（"remains to be seen" / "could potentially" 等）全零命中；命中过的已 forced-answer rewrite 通过。
- [ ] **CSS diff-check** — 双版 `assets/diff-check.sh` <5% 偏离。
- [ ] **Source ledger** — `citation_id`（如 `[s3]`）在正文 inline 引用；S01–SNN 列表 + 外延 outlet 名 + URL 可验证。
- [ ] **Visual + delivery** — 4 关键页 × 2 版 PNG spot-check；PDF 文件本体（非路径）交付。
- [ ] 🆕 **de-slop** — 汇编后的 md 已跑 de-slop ZH+EN Pipeline；5 维评分 ≥35；AI 不敢写测试通过。
- [ ] 🆕 **source-verification** — 所有价格/数据/政策 claim 已逐条标置信度；无 contradicted claim 残留。
- [ ] 🆕 **TTS 语音** — CosyVoice 语音已生成（≤500 字，≤2min）；OGG 文件随 PDF 交付；MEDIA 路径存在。

**If any box is unchecked, go back.**

---

## Deployment & Sync

This is a **regent profile** skill. After ANY update:

```bash
# 1. Sync back from local to repo
cd ~/code/jz-skills && ./deploy/sync-back.sh

# 2. Sanitize — never blind commit (catches secrets, emails, IPs, home paths)
grep -rE '(/Users/[a-z]|gho_|sk-[0-9a-zA-Z]|10\.[0-9]+\.[0-9]+\.[0-9]+|172\.(1[6-9]|2[0-9]|3[01])\.[0-9]+|192\.168|@[a-zA-Z0-9.-]+\.(com|cn))' hermes-3S6M-profiles/regent/morning-news-briefing/ \
  && echo "⚠️  SENSITIVE DATA FOUND — sanitize before commit" && exit 1 || true

# 3. Stage skill directory only, then push
git add hermes-3S6M-profiles/regent/morning-news-briefing/ \
  && git commit -m "sync: morning-news-briefing" \
  && git push
```
