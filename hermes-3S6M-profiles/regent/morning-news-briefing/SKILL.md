---
name: morning-news-briefing
description: "Use when producing the daily morning news briefing — multi-source parallel search via web-research-router, fused analysis format (前提→推理→结论 + 趋势 + 为什么重要), and mobile PDF delivery (430×932px, #fffdf8/#1b1a17/#b47a32). Executes in hybrid mode: delegate_task for search (fast), Kanban for assembly+render (auditable). Do NOT use for single-topic deep dives, non-news content, A4 reports, or manual article curation."
version: 3.0.0
author: Hermes Agent (v3.0 — hybrid execution + web-research-router + CSS template)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [productivity, news, briefing, mobile-pdf, daily]
    related_skills: [web-research-router, source-verification, md-to-pdf, skill-authoring]
---

# 早新闻简报 v3.0

Hybrid execution: parallel search via delegate_task + auditable assembly/render via Kanban.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll use yesterday's template, same CSS" | Style continuity gate: must auto-diff against last accepted baseline. Free-form styling = broken brand |
| "I'll just run web_search for each section" | web-research-router picks the best engine per query type. Brave for broad coverage, Exa for semantic discovery, Tavily for fact grounding. Direct web_search skips all three |
| "The analysis is thin today, I'll pad it" | Analysis format is locked: 前提→推理→结论 + 📈趋势 + 为什么重要. No hedging — grep for 一方面/另一方面/可能/或许 → auto-reject |
| "Search results are in Kanban summaries, good enough" | All search output MUST land in persistent workspace paths. Scratch GC has eaten results 3+ times |
| "I'll render as soon as assembly starts" | Render card MUST wait for assembly completion (parent dependency). Rendering before content = blank/stale PDF |

## 🔀 Decision Tree

```
"早新闻" / "morning news" triggered?
├── Step 1: Parallel search via delegate_task (3 lanes)
│   ├── Lane A: 中国媒体 (Brave news → Tavily 校验, ≥15 sources)
│   ├── Lane B: 美国+国际 (Exa discovery → Tavily grounding, ≥18 sources)
│   └── Lane C: 市场+科技 (Brave 快讯 → Exa 深度 → Tavily 价格校验)
│   Full routing spec: references/search-workflow.md
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

1. **搜索必须三路并行** — 不走单引擎。Brave 中文广撒网 + Exa 英文深度发现 + Tavily 事实校验。缺一路 = 缺信息维度。
2. **结果必须落盘持久 workspace** — 用 `~/.hermes/workspaces/morning-news-{date}/`。scratch GC 已吃掉 3+ 次搜索结果。搜索完立即写 JSON，不缓存内存。
3. **渲染必须等汇编完成** — 父子 Kanban 依赖不可跳。先渲染 = 空白/过期 PDF。
4. **CSS 必须 diff-check** — 渲染前跑 `assets/diff-check.sh` 双版验证，偏离 baseline >5% 警告。禁止自由调色/改布局。
5. **交付前必须全量审计** — 7 sentinels × 2 editions，PyMuPDF 全量提取，反骑墙 grep，源数校验。任一未过 = 不得交付。
6. **搜索失败不阻塞整路** — 单源 404/单引擎超时 = 跳过 + 标注。整路失败 = 其他路填补。三路全败 = 中止奏报，不等。
7. **Workspace 持久化卫生** — 新建 workspace `chmod 700`，含 `.gitignore`（`*` 全忽略）。保留 7 天，超期 `find -mtime +7 -delete`。

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
| `references/sources.json` | Structured source registry with locale/tier/status |
| `references/analysis-format.md` | Fused analysis format specification |
| `references/search-workflow.md` | web-research-router integration + delegate_task lanes |
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
| **盲 `git commit -am`** | `.env`/缓存/API 原始响应一并推上 GitHub。必须先 sanitize grep |
| **单引擎搜索** | 直接 `web_search` 不走三引擎路由 = 丢失深度发现(Exa)和事实校验(Tavily)两个维度 |
| **scratch workspace 丢产出** | 内存缓存被 GC 吃掉 3+ 次。搜索产物必须落盘持久 workspace |
| **先渲染后汇编** | 内容未完成就渲染 = 空白 PDF。Kanban 父子依赖不可跳过 |
| **反骑墙 grep 未跑** | "一方面/另一方面/可能/或许" 任一命中 = 骑墙分析。不检查 = 蒙混过关 |

### More Anti-Patterns

- Using free-form CSS instead of locked `assets/*-template.html`
- Hedging analysis with "on one hand… on the other…"
- Compressing news items to reduce page count
- Delivering before audit is `done`
- Rendering before assembly is complete (missing parent dependency)

## ✅ Verification Checklist (RUN BEFORE DELIVERY)

- [ ] All 7 sentinels verified via PyMuPDF full-text extraction (both editions)?
- [ ] Analysis: all items follow 前提→推理→结论 + 趋势 + 为什么重要?
- [ ] Anti-hedging: zero hits for 一方面/另一方面/可能/或许?
- [ ] CSS diff-check passed for BOTH editions (deviation <5%)?
- [ ] Source ledger: S01–SNN numbered with outlet names + verifiable URLs?
- [ ] Visual PNG spot-check on 4 key pages × 2 editions?
- [ ] PDF file delivered directly (not just path)?

**If any box is unchecked, go back.**

---

## Deployment & Sync

This is a **regent profile** skill. After ANY update:

```bash
# 1. Sync back from local to repo
cd ~/code/jz-skills && ./deploy/sync-back.sh

# 2. Sanitize — never blind commit (catches secrets, emails, IPs, home paths)
grep -rE '(/Users/[a-z]|gho_|sk-[0-9a-zA-Z]|192\.168|@foxmail)' hermes/productivity/morning-news-briefing/ \
  && echo "⚠️  SENSITIVE DATA FOUND — sanitize before commit" && exit 1 || true

# 3. Stage skill directory only, then push
git add hermes/productivity/morning-news-briefing/ \
  && git commit -m "sync: morning-news-briefing" \
  && git push
```
