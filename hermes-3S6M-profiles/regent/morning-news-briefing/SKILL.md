---
name: morning-news-briefing
description: "Use when producing the daily morning news briefing — SearXNG-first multi-engine search via web-research-router v3.2, verbatim-quote anchored analysis (fetch-extract-pattern, anti-hallucination rules, Sherman Kent probability), and mobile PDF delivery (430×932px). Executes in hybrid mode: delegate_task for search (fast), Kanban for assembly+render (auditable). 触发词: 早新闻, morning news, daily briefing, 简报, 朝议. Do NOT use for single-topic deep dives, non-news content, A4 reports, or manual article curation."
version: 4.0.0
author: Hermes Agent (v4.0 — web-research-router v3.2 alignment + verbatim-quote anchoring + banned-phrases gate)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [productivity, news, briefing, mobile-pdf, daily, searxng, verbatim-quote, anti-hallucination]
    related_skills: [web-research-router, source-verification, md-to-pdf, skill-authoring]
---

# 早新闻简报 v4.0

Hybrid execution: parallel search via delegate_task + auditable assembly/render via Kanban. Aligned with **web-research-router v3.2** — SearXNG 默认起手 + verbatim quote 抽取 + 反幻觉规则集 + Sherman Kent 概率刻度。

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll use yesterday's template, same CSS" | Style continuity gate: must auto-diff against last accepted baseline. Free-form styling = broken brand |
| "I'll just run web_search for each section" | v4.0 起步必走 SearXNG（`mcp_searxng_searxng_web_search`，6+ 引擎聚合）— Brave/Exa/Tavily 已降为 cross-check 补强。直接 `web_search` 跳过广扫 = 漏 30%+ 候选源 |
| "搜索还是按 v3.0 的 Brave/Exa/Tavily 三 lane 一刀切" | `references/search-workflow.md` 已升 v2.0，三 lane 统一走 SearXNG 广扫 → 按需 cross-check。沿用 v3.0 路径 = 多打 3× LLM call、漏多引擎独家收录 |
| "The analysis is thin today, I'll pad it" | Analysis format is locked: 前提→推理→结论 + 📈趋势 + 为什么重要. No hedging — grep for 一方面/另一方面/可能/或许 → forced-answer rewrite 一次 → 仍 hedge 才 REJECT（v4.0 不再 reject-only） |
| "Banned phrases 太啰嗦 / fetch 完直接综合答案就行" | 详见 Core Rules #2（fetch-extract verbatim quote 必跑）+ #6（15 个禁词 + Sherman Kent 概率 regex）。两条都跳 = 简报满屏 "could potentially" + 引用不可追溯 |
| "Search results are in Kanban summaries, good enough" | All search output MUST land in persistent workspace paths. Scratch GC has eaten results 3+ times |
| "I'll render as soon as assembly starts" | Render card MUST wait for assembly completion (parent dependency). Rendering before content = blank/stale PDF |

## 🔀 Decision Tree

```
"早新闻" / "morning news" triggered?
├── Step 1: Parallel search via delegate_task (3 lanes, v4.0 SearXNG-first)
│   ├── Lane A: 中国媒体 (SearXNG 广扫 → fetch-extract → Tavily 校验数据, ≥15 sources)
│   ├── Lane B: 美国+国际 (SearXNG 广扫 → fetch-extract → Exa/Brave 补强, ≥18 sources)
│   └── Lane C: 市场+科技 (SearXNG 广扫 → fetch-extract → Tavily 价格校验, ≥8 sources)
│   每 lane 4 步：SearXNG 起手 → query-decomposition → fetch-extract → cross-check (Brave/Exa/Tavily)
│   Full routing spec: references/search-workflow.md (v2.0) · DESCRIPTORS 字典: references/keyword-expansion-dict.md
│   All results → persistent workspace: ~/.hermes/workspaces/morning-news-{date}/search/
│
├── Step 2: Assembly (Kanban → hanlinyuan)
│   Read search artifacts, deduplicate, structure 5 sections
│   Write: morning-news-{date}.md → persistent path
│
├── Step 3: Render (Kanban → jiangzuojian, parent=assembly)
│   Two editions, sequenced:
│   ├── Mobile: Load assets/mobile-template.html → diff-check mobile-baseline.css
│   └── Standard: Load assets/standard-template.html → diff-check standard-baseline.css
│   Render HTML → Playwright PDF → PNG spot-checks (both editions)
│
├── Step 4: Audit (Kanban → auditor)
│   PyMuPDF extraction → 7 sentinels × 2 editions + anti-hedging + source count
│
└── Step 5: Deliver (Kanban → reviewer)
    Final gate → deliver both MEDIA paths to user
```

## ⚡ Core Rules (Hermes Agent 执行规则)

1. **搜索默认 SearXNG 起手 + 三路并行** — v4.0 每 lane 第一步必跑 `mcp_searxng_searxng_web_search`（6+ 引擎聚合）。Brave/Exa/Tavily **降为 cross-check 补强**：价格/数据 → Tavily grounding；本地化/突发 → Brave；语义精准 → Exa。SearXNG 不可达时按 `references/search-workflow.md` 降级到 v3.0 单引擎链。
2. **每条 source 必跑 fetch-extract → verbatim quote** — `mcp_searxng_web_url_read` 抓页面 + extractor prompt 抽 verbatim quote，入 `source_map.extracted_quotes[]`。**不让单次 LLM call 同时 fetch + 综合答案**（幻觉源头）。详见 router `references/fetch-extract-pattern.md`。
3. **结果必须落盘持久 workspace** — 用 `~/.hermes/workspaces/morning-news-{date}/`。scratch GC 已吃掉 3+ 次搜索结果。搜索完立即写 JSON，不缓存内存。
4. **渲染必须等汇编完成** — 父子 Kanban 依赖不可跳。先渲染 = 空白/过期 PDF。
5. **CSS 必须 diff-check** — 渲染前跑 `assets/diff-check.sh` 双版验证，偏离 baseline >5% 警告。禁止自由调色/改布局。
6. **Anti-hallucination + banned-phrases 强制** — assembly 写完正文先跑 `references/banned-phrases-and-probability-scale.md` 的 regex 扫描（15 个禁词 + Sherman Kent 7 档概率）；命中 → 触发 anti-refusal forced-answer rewrite 一次 → 仍命中 → REJECT。规则详见 `references/anti-hallucination-rules.md`。
7. **交付前必须全量审计** — 7 sentinels × 2 editions，PyMuPDF 全量提取，反骑墙 + 反禁词 grep，源数校验。任一未过 = 不得交付。
8. **搜索失败不阻塞整路** — 单源 404/单引擎超时 = 跳过 + 标注。整路失败 = 其他路填补。三路全败 = 中止奏报，不等。
9. **Workspace 持久化卫生** — 新建 workspace `chmod 700`，含 `.gitignore`（`*` 全忽略）。保留 7 天，超期 `find -mtime +7 -delete`。

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
| `references/search-workflow.md` ⭐ | v2.0 — SearXNG 默认起手 + query-decomposition + fetch-extract + Brave/Exa/Tavily cross-check（对齐 web-research-router v3.2） |
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

## ⚠️ Critical Pitfalls (Top 5)

| Pitfall | Why it burns you |
|---------|-----------------|
| **跳过 SearXNG 起手 / 沿用 v3.0 单引擎一刀切** | v4.0 SearXNG 一次聚合 6+ 引擎 + 学术/代码/中文。沿用 v3.0 Brave/Exa/Tavily lane = 漏 30%+ 候选源 + 多打 3× LLM call。盲 `git commit -am` 走 sanitize grep（见 Deployment 段） |
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
- [ ] **Search trace** — 每 lane 的 search/`lane-*.json` 都有 `engines: ["searxng", ...]` 标记；`extracted_quotes[]` 非空。
- [ ] **Analysis** — 所有 🔍 分析项遵循 前提→推理→结论 + 趋势 + 为什么重要；概率词只用 Sherman Kent 7 档。
- [ ] **Anti-hedging + anti-banned-phrases** — 一方面/另一方面/可能/或许 + 15 个 banned phrases（"remains to be seen" / "could potentially" 等）全零命中；命中过的已 forced-answer rewrite 通过。
- [ ] **CSS diff-check** — 双版 `assets/diff-check.sh` <5% 偏离。
- [ ] **Source ledger** — `citation_id`（如 `[s3]`）在正文 inline 引用；S01–SNN 列表 + 外延 outlet 名 + URL 可验证。
- [ ] **Visual + delivery** — 4 关键页 × 2 版 PNG spot-check；PDF 文件本体（非路径）交付。

**If any box is unchecked, go back.**

---

## Deployment & Sync

This is a **regent profile** skill. After ANY update:

```bash
# 1. Sync back from local to repo
cd ~/code/jz-skills && ./deploy/sync-back.sh

# 2. Sanitize — never blind commit (catches secrets, emails, IPs, home paths)
grep -rE '(/Users/[a-z]|gho_|sk-[0-9a-zA-Z]|192\.168|@[a-zA-Z0-9.-]+\.(com|cn))' hermes-3S6M-profiles/regent/morning-news-briefing/ \
  && echo "⚠️  SENSITIVE DATA FOUND — sanitize before commit" && exit 1 || true

# 3. Stage skill directory only, then push
git add hermes-3S6M-profiles/regent/morning-news-briefing/ \
  && git commit -m "sync: morning-news-briefing" \
  && git push
```
