---
name: web-research-router
description: "Searches the web, finds papers, explores GitHub source code, and verifies facts using SearXNG（多引擎聚合，覆盖最广）/Exa/Tavily/Brave plus local knowledge (Hindsight/qmd/Obsidian/CodeGraph). Use when the user needs to 搜索, 检索, 查找, 调研, 核实, 找资料, 找项目, search, research, find, look up, or verify information — even if they don't explicitly say 'search'. Routes GitHub source code tasks to github (references/code-explorer.md — 看看源码, 找实现, 搜用法). Do NOT use for reading local files, editing code, running terminal commands, or tasks not involving external or knowledge-base retrieval."
version: 3.1.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [search, research, router, searxng, exa, tavily, brave, academic, papers, citations, sources, mcp]
    related_skills: [source-search, exa-research, source-reader, source-verification, content-source-workflow, qmd, obsidian, arxiv, native-mcp, github]
---

# Web Research Router v3.1

**Progressive-disclosure search routing.** This file is ~130 lines. Detailed mode descriptions, query patterns, academic lane policy, and schema live in `references/` — loaded only when needed.

> ⚙️ **Tuning:** `CROSS_CHECK_DEPTH=1` (fast, single-source) to `3` (thorough, triple-verify). Default: `2`.

---

## 🚨 Red Flags: DO NOT SKIP THIS ROUTER

Before calling ANY search tool, check this table. If any excuse below sounds familiar, **STOP — you are about to violate the decision tree.**

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is a simple query, I'll just use `web_search`" | `web_search` is a generic fallback. The router picks the best engine per query type. Even "simple" factual queries should start with SearXNG 广扫 then Tavily/Brave 深核。 |
| "I already know the answer" | Training data is stale. Current facts need current search. |
| "I already loaded the skill, that's enough" | Loading ≠ following. Loading tells you WHAT to do; you still need to DO it. |
| "The decision tree is too complicated for this" | It's 4 branches. Pick one. Takes 5 seconds. |
| "I'll cross-check later" | Cross-checking after the fact is twice the work. Do it in the right order now. |
| "我直接 Exa/Tavily 单引擎一次到位" | 单引擎容易遗漏（Bing 收录的 Brave 漏，反之亦然）。SearXNG 一次聚合 6+ 引擎，先用它扫一遍再决定是否精准深挖。 |

**If you caught yourself thinking any of these → re-read the decision tree below and start over.**

---

## 🔀 Routing Decision Tree (ALWAYS RUN THIS FIRST)

### Step 0: Local knowledge first
Before ANY public search, check: Hindsight (cross-session) → session_search (this session) → qmd/Obsidian (knowledge base) → CodeGraph (local code). Only go public if local is exhausted or needs validation.

### Step 1: Is this a GitHub source code task?
- `github.com` / `raw.githubusercontent.com` / `gist.github.com` URL → **⚠️ Skip `web_extract`** (it blocks GitHub as "internal network"). Load `github` (references/code-explorer.md) → L1 Exa/gh api → L2 gh search → L3 browser → L4 clone+CodeGraph.
- "看看 X 项目源码" / "这个函数怎么实现" → load `github`.

### Step 2: Pick the search mode and engine

> 🌐 **默认从 SearXNG 起手：** SearXNG（`mcp_searxng_searxng_web_search`）一次调用聚合 6+ 引擎
> （Bing / Brave / Qwant / Mwmbl / DuckDuckGo / Startpage + 学术 arXiv/SS/Crossref + 代码 GitHub/SO + 中文 Bilibili），
> 覆盖面最广。先 SearXNG 扫一遍，再用 Exa 做语义精准、Tavily 做事实核验、Brave 做特定补强。

| Task type | Mode | Primary engine | Cross-check |
|-----------|------|---------------|-------------|
| Background, landscape, "有没有相关项目" | `discovery` | SearXNG（广扫）→ Exa（语义精准） | Brave if narrow |
| Dates, numbers, prices, claims, news | `grounding` | SearXNG（多引擎交叉）→ Tavily（深核） | Brave / 另一引擎 |
| Substantive brief, decision memo, market scan | `research` | SearXNG（landscape）→ Exa → Tavily | If claim-dependent |
| Papers, citations, SOTA, arXiv, DOI | `academic` | SearXNG（arXiv+SS+Crossref 一次） / arXiv 单刷 | See `references/academic-lane.md` |
| Dead URL, moved source, missing material | `recovery` | SearXNG（6 引擎覆盖率最高）→ Brave `site:` → Exa | Report certainty |

Detailed mode instructions: `references/research-modes.md`

### Step 3: Cross-check only when warranted (respect `CROSS_CHECK_DEPTH`)
Cross-check when: numbers, dates, prices, legal claims, attribution, SOTA claims, financial decisions, fast-changing news, suspicious claims. At depth 1, skip cross-check. At depth 2 (default), cross-check one source. At depth 3, triple-verify.

### Step 4: Fetch discipline
Search first, fetch second. Fetch 1–3 high-signal URLs only. Prefer primary/official sources.

---

## 🧭 Quick Reference: Which Engine When

| Engine | Best for | Tool name |
|--------|----------|-----------|
| **SearXNG** | 多引擎聚合广扫（Bing+Brave+Qwant+Mwmbl+DDG+Startpage + arXiv+SS+Crossref + GitHub+SO + Bilibili），覆盖最广 | `mcp_searxng_searxng_web_search` |
| **SearXNG URL Read** | 把任意 URL 抓成 markdown（含 GitHub 页面）| `mcp_searxng_web_url_read` |
| **Exa** | Semantic discovery, company/product scans, high-signal sources | `mcp_exa_web_search_exa` |
| **Tavily** | Current facts, extraction, site crawl, research | `mcp_tavily_tavily_search` |
| **Brave** | Broad coverage, news, local queries, cross-checking | `mcp_brave_search_brave_web_search` |
| **Exa Fetch** | Full page content (esp. GitHub raw URLs) | `mcp_exa_web_fetch_exa` |
| **arXiv** | CS/AI/ML/math/physics preprints | `arxiv` skill |
| **Semantic Scholar** | Citations, references, author profiles | MCP tools |
| **gh CLI** | GitHub code search, API, issues | `terminal` → `gh search code` |

**选型口诀：** SearXNG 扫广度（一次拿到 6+ 引擎结果）→ Exa 拣精度（语义匹配）→
Tavily 核事实（最新动态、抽取）→ Brave 补特定（本地、新闻）→ gh/arxiv 走垂直深井。

Full tool list: `references/tool-names.md`

---

## 📋 Output Contract

For Telegram, avoid tables. Use compact bullets:

- **结论:** one or two lines.
- **模式:** `discovery` / `grounding` / `research` / `recovery` / `academic`.
- **来源:** title/domain + why it matters + URL.
- **已确认 / 推断 / 冲突缺口:** separate facts from judgment.

Full Source Map Schema: `references/source-map-schema.md`

---

## 📦 Progressive Disclosure Reference Map

| When you need... | Read... |
|-----------------|---------|
| Detailed mode instructions (default paths, examples) | `references/research-modes.md` |
| Query patterns for common tasks | `references/query-patterns.md` |
| Academic lane policy (arXiv, Semantic Scholar, PubMed, etc.) | `references/academic-lane.md` |
| Vertical domain → engine mapping (finance, security, health, etc.) | `references/vertical-domains.md` |
| Full Source Map Schema JSON | `references/source-map-schema.md` |
| MCP tool names by profile | `references/tool-names.md` |
| Deployment & Sync instructions | `references/deployment.md` |

---

## ⚠️ Common Pitfalls (Top 6)

1. **Search-engine maximalism.** 引擎多 ≠ 好。SearXNG 已聚合 6+ 引擎，一次广扫足够，无须叠 Exa/Tavily/Brave 并发。
2. **单引擎依赖症。** 直接用 Exa 或 Tavily 单刷而跳过 SearXNG，容易漏掉某些引擎独家收录的页面。先 SearXNG 广扫，再决定深挖。
3. **Skipping local truth.** Check Hindsight/qmd/CodeGraph before public web.
4. **Conflating discovery with evidence.** Search results are candidates; fetched sources are evidence.
5. **GitHub `web_extract` trap.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` as "internal network." Use `mcp_searxng_web_url_read`、`mcp_exa_web_fetch_exa`、或 `gh api` instead.
6. **Cron job model pinning.** Always pin model explicitly in cron jobs — default model may be rate-limited.

Full pitfalls (15 items): `references/common-pitfalls.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] CHECK: Local knowledge first (Hindsight/session/qmd/CodeGraph)?
- [ ] CHECK: Picked a research mode (discovery/grounding/research/academic/recovery)?
- [ ] CHECK: Used the right primary engine for that mode?
- [ ] CHECK: Cross-checked important claims at the right depth (CROSS_CHECK_DEPTH)?
- [ ] CHECK: Fetched ≤3 high-signal URLs, not bulk-dump?
- [ ] CHECK: Separated confirmed facts from inference?
- [ ] CHECK: For GitHub URLs — skipped `web_extract`, used `mcp_searxng_web_url_read`/Exa Fetch/gh api instead?

**Every box must honestly pass before returning results. If unchecked, go back.**

---

> 🔄 Deployment & Sync: `references/deployment.md`
