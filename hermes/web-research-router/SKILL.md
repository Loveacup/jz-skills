---
name: web-research-router
description: "Searches the web, finds papers, explores GitHub source code, verifies facts, and runs multi-step deep-research loops using SearXNG（多引擎聚合，覆盖最广）/Exa/Tavily/Brave plus local knowledge (Hindsight/qmd/Obsidian/CodeGraph). Includes verbatim-quote extraction (anti-hallucination), query decomposition, and forced-answer fact-recall. Use when the user needs to 搜索, 检索, 查找, 调研, 核实, 深挖, 出报告, 找资料, 找项目, search, research, deep-research, find, look up, or verify information — even if they don't explicitly say 'search'. Routes GitHub source code tasks to github (references/code-explorer.md — 看看源码, 找实现, 搜用法). Do NOT use for reading local files, editing code, running terminal commands, or tasks not involving external or knowledge-base retrieval."
version: 3.4.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [search, research, router, searxng, exa, tavily, brave, academic, papers, citations, sources, mcp, deep-research, verbatim-quote, anti-refusal]
    related_skills: [source-search, exa-research, source-reader, source-verification, content-source-workflow, qmd, obsidian, arxiv, native-mcp, github]
---

# Web Research Router v3.4

**Progressive-disclosure search routing.** This file is ~150 lines. Detailed mode descriptions, query patterns, academic lane policy, and schema live in `references/` — loaded only when needed.

> 🆕 **v3.4 (2026-05-28)**: 基于好伴AI深度研究案例 RCA，新增 3 条 deep loop Red Flag 与 4 条质量验证清单（事实解耦/Claim 溯源/补搜回路/口径确认）。详见 `references/deep-research-loop.md` 与 `references/deep-loop-verification-pattern.md`。

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
| "我不会 deep research / 单轮就够了" | 议题维度 ≥3、需可引用报告、单轮 source map 覆盖 <70% → 升级 deep loop（`references/deep-research-loop.md`）。不升级 ≠ 答得对；只是把幻觉藏起来。 |
| "fetch 完直接综合答案就行，省一步" | fetch + 综合答案放一次 LLM call → 幻觉高发。正确：fetch → extractor（verbatim quotes only） → 独立 call 综合。详见 `references/fetch-extract-pattern.md`。 |
| "section 写完就行，facts.jsonl 太麻烦" ★ | **fetch-write 耦合是 deep loop 80% 偏差的根因。** 营销话术一旦被叙事化（"已有1亿用户、竞争压力巨大"），REFLECT 看到的是流畅叙事而非原子事实卡片，无法回头推翻。SECTION 阶段必须先产 `facts.jsonl`（指标/口径/来源/可信度/原始URL），write 读卡片不读原始页面。详见 `references/deep-research-loop.md` Step 2。 |
| "REFLECT 过一遍就够了，不用再做 Claim 溯源" ★ | REFLECT 是同一 Agent 在相同上下文做自审 → 只能发现"段落间逻辑矛盾"，无法发现"整个上下文 based on 一个错误前提"。含"第一/最/突破/领先/超过/首家"或带规模数字的 claim **必须独立 search 溯源**，由独立 LLM call 在新上下文中验证。详见 `references/deep-loop-verification-pattern.md`。 |
| "中文搜索词够了，议题是国内的" ★ | 跨语言盲区是**系统性**的——中文 query 几乎召不回英文公告（Anthropic Claude for Healthcare 案例）。MERGE 前必须有"盲区检视 → 反向假设（'国际玩家最近做了什么'）→ 跨语言补搜"回路。详见 `references/deep-research-loop.md` Step 4。 |

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

> 🔁 **何时升级到 deep-research loop？** 议题维度 ≥ 3 / 需可引用结构化报告 / 单轮 source map 命中 <70% / 用户显式说"深挖" → 进入
> `references/deep-research-loop.md` 的 plan → section research（含 `fetch-extract-pattern.md` extractor） → reflect → merge 循环。
> Deep loop **不替换**上表 5 mode；它是 `research` mode 的可选升级路径。

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
| Full Source Map Schema JSON（含 `citation_id` / `extracted_quotes` / `budget` 字段） | `references/source-map-schema.md` |
| MCP tool names by profile | `references/tool-names.md` |
| Deployment & Sync instructions | `references/deployment.md` |
| **抓页面后如何抽 verbatim quote**（防幻觉最大杠杆）★ | `references/fetch-extract-pattern.md` |
| **多轮 deep research loop SOP v3.4**（plan → section(facts.jsonl) → CoV验证 → merge(盲区补搜) → 颗粒度Gate） | `references/deep-research-loop.md` |
| **Deep loop 质量缺陷 + CoV 验证模式**（fetch-write耦合、REFLECT天花板、跨语言盲区 — 2026-05-28 案例RCA） | `references/deep-loop-verification-pattern.md` |
| **broad 议题如何拆 sub-query**（TEMPORAL/NUMERICAL/NAMES/ENTITY/CONCEPTUAL 五类） | `references/query-decomposition.md` |
| **产品/公司深度评估快速模式**（并行抓取→补刀→综合，比 formal deep loop 省 50%+ token） | `references/product-evaluation-pattern.md` |
| **fact-recall 时 LLM 死活不答如何破**（8 hedge phrase + forced-answer prompt） | `references/anti-refusal-prompt.md` |

---

## ⚠️ Common Pitfalls (Top 7)

1. **Search-engine maximalism.** 引擎多 ≠ 好。SearXNG 已聚合 6+ 引擎，一次广扫足够，无须叠 Exa/Tavily/Brave 并发。
2. **单引擎依赖症。** 直接用 Exa 或 Tavily 单刷而跳过 SearXNG，容易漏掉某些引擎独家收录的页面。先 SearXNG 广扫，再决定深挖。
3. **Extractor 当 answerer 用** ★ 同一次 LLM call 既 fetch 又综合答案 → 幻觉高发。fetch → verbatim quote 抽取 → 后续独立 call 综合。详见 `references/fetch-extract-pattern.md`。
4. **Skipping local truth.** Check Hindsight/qmd/CodeGraph before public web.
5. **Conflating discovery with evidence.** Search results are candidates; fetched/extracted sources are evidence.
6. **GitHub `web_extract` trap.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` as "internal network." Use `mcp_searxng_web_url_read`、`mcp_exa_web_fetch_exa`、或 `gh api` instead.
7. **Cron job model pinning.** Always pin model explicitly in cron jobs — default model may be rate-limited.

Full pitfalls (33 items, 含 v3.4 新增 deep loop 质量 8 项): `references/common-pitfalls.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] **Local first?** Hindsight/session/qmd/CodeGraph 都查过再上公网。
- [ ] **Mode + engine?** 选定 discovery/grounding/research/academic/recovery，或升级 deep loop；按表用对 primary engine（默认 SearXNG 起手）。
- [ ] **Extractor not answerer?** 每个 fetched 页面跑过 extractor、verbatim quote 入 source map，**不是**让单次 LLM call 又 fetch 又综合答案。
- [ ] **Citation 用 `citation_id`?** 综合答案中 inline citation 写 `[s3]`，不写裸 URL；`confirmed[i].citation_ids` 全部映得回 source map。
- [ ] **Cross-check + budget?** 重要 claim 按 `CROSS_CHECK_DEPTH` 交叉；走 deep loop 时 `max_iter` / `token_budget` / `stop_reason` 都有值。
- [ ] **Fetch discipline?** Fetched ≤3 high-signal URLs；GitHub URL 用 `mcp_searxng_web_url_read` / Exa Fetch / gh api（**不**用 `web_extract`）。
- [ ] **Confirmed vs inference 分开?** 报告中事实与判断必须分栏，conflicts/gaps 单列。

### Deep-loop 专属（如果用了 deep-research loop，以下 4 条必须勾过）★

- [ ] **事实解耦？** deep loop 的 SECTION 阶段 fetch 后是否先产 `facts.jsonl`（字段：指标/口径/来源/可信度/原始URL）再 write_section？— 防止 fetch-write 耦合（80% 偏差根因）。
- [ ] **Claim 溯源？** 含 `"第一/最/独家/突破/领先/超过/首家/首个"` 或带数字规模/benchmark/排名 的 claim，是否每条都做了独立 search 验证（新上下文、跨信源、跨语言）？— 防 REFLECT 自审天花板。
- [ ] **补搜回路？** MERGE 前是否做了"盲区检视 → 反向假设（'国际玩家/跨语言信源遗漏什么？'）→ 跨语言补搜"？— 防跨地域/跨语种召回失败。
- [ ] **口径确认？** 涉及数字（用户量/MAU/DAU/累计/GMV）是否区分了"累计 vs 月活 vs 日活 vs 截至某月"？涉及政策/排名是否标注了原始项目名/数量/信源等级？— 防颗粒度坍缩与营销口径误读。

**Every box must honestly pass before returning results. If unchecked, go back.**

---

> 🔄 Deployment & Sync: `references/deployment.md`
