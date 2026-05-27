---
name: web-research-router
description: "Searches the web, finds papers, explores GitHub source code, and verifies facts using Exa/Tavily/Brave plus local knowledge (Hindsight/qmd/Obsidian/CodeGraph). Use when the user needs to 搜索, 检索, 查找, 调研, 核实, 找资料, 找项目, search, research, find, look up, or verify information — even if they don't explicitly say 'search'. Routes GitHub source code tasks to github-code-explorer (看看源码, 找实现, 搜用法). Do NOT use for reading local files, editing code, running terminal commands, or tasks not involving external or knowledge-base retrieval."
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [search, research, router, exa, tavily, brave, academic, papers, citations, sources, mcp]
    related_skills: [source-search, exa-research, source-reader, source-verification, content-source-workflow, qmd, obsidian, arxiv, native-mcp, github-code-explorer]
---

# Web Research Router v3.0

**Progressive-disclosure search routing.** This file is ~150 lines. Detailed mode descriptions, query patterns, academic lane policy, and schema live in `references/` — loaded only when needed.

---

## 🚨 Red Flags: DO NOT SKIP THIS ROUTER

Before calling ANY search tool, check this table. If any excuse below sounds familiar, **STOP — you are about to violate the decision tree.**

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is a simple query, I'll just use `web_search`" | `web_search` is a generic fallback. The router picks the best engine per query type. Even "simple" factual queries should go through Tavily (grounding) or Brave (coverage). |
| "I already know the answer" | Training data is stale. Current facts need current search. |
| "I already loaded the skill, that's enough" | Loading ≠ following. Loading tells you WHAT to do; you still need to DO it. |
| "The decision tree is too complicated for this" | It's 4 branches. Pick one. Takes 5 seconds. |
| "I'll cross-check later" | Cross-checking after the fact is twice the work. Do it in the right order now. |

**If you caught yourself thinking any of these → re-read the decision tree below and start over.**

---

## 🔀 Routing Decision Tree (ALWAYS RUN THIS FIRST)

### Step 0: Local knowledge first
Before ANY public search, check: Hindsight (cross-session) → session_search (this session) → qmd/Obsidian (knowledge base) → CodeGraph (local code). Only go public if local is exhausted or needs validation.

### Step 1: Is this a GitHub source code task?
- `github.com` / `raw.githubusercontent.com` / `gist.github.com` URL → **⚠️ Skip `web_extract`** (it blocks GitHub as "internal network"). Load `github-code-explorer` → L1 Exa/gh api → L2 gh search → L3 browser → L4 clone+CodeGraph.
- "看看 X 项目源码" / "这个函数怎么实现" → load `github-code-explorer`.

### Step 2: Pick the search mode and engine

| Task type | Mode | Primary engine | Cross-check |
|-----------|------|---------------|-------------|
| Background, landscape, "有没有相关项目" | `discovery` | Exa | Brave if narrow |
| Dates, numbers, prices, claims, news | `grounding` | Tavily or Brave | The other engine |
| Substantive brief, decision memo, market scan | `research` | Exa → fetch → Tavily/Brave | If claim-dependent |
| Papers, citations, SOTA, arXiv, DOI | `academic` | arXiv/Semantic Scholar | See `references/academic-lane.md` |
| Dead URL, moved source, missing material | `recovery` | Brave `site:` → Exa → Tavily | Report certainty |

Detailed mode instructions: `references/research-modes.md`

### Step 3: Cross-check only when warranted
Cross-check when: numbers, dates, prices, legal claims, attribution, SOTA claims, financial decisions, fast-changing news, suspicious claims.

### Step 4: Fetch discipline
Search first, fetch second. Fetch 1–3 high-signal URLs only. Prefer primary/official sources.

---

## 🧭 Quick Reference: Which Engine When

| Engine | Best for | Tool name |
|--------|----------|-----------|
| **Exa** | Semantic discovery, company/product scans, high-signal sources | `mcp_exa_web_search_exa` |
| **Tavily** | Current facts, extraction, site crawl, research | `mcp_tavily_tavily_search` |
| **Brave** | Broad coverage, news, local queries, cross-checking | `mcp_brave_search_brave_web_search` |
| **Exa Fetch** | Full page content (esp. GitHub raw URLs) | `mcp_exa_web_fetch_exa` |
| **arXiv** | CS/AI/ML/math/physics preprints | `arxiv` skill |
| **Semantic Scholar** | Citations, references, author profiles | MCP tools |
| **gh CLI** | GitHub code search, API, issues | `terminal` → `gh search code` |

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

## ⚠️ Common Pitfalls (Top 5)

1. **Search-engine maximalism.** More engines ≠ better. Pick the smallest set.
2. **Skipping local truth.** Check Hindsight/qmd/CodeGraph before public web.
3. **Conflating discovery with evidence.** Search results are candidates; fetched sources are evidence.
4. **GitHub `web_extract` trap.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` as "internal network." Use `mcp_exa_web_fetch_exa` or `gh api` instead.
5. **Cron job model pinning.** Always pin model explicitly in cron jobs — default model may be rate-limited.

Full pitfalls (13 items): `references/common-pitfalls.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I check local knowledge first (Hindsight/session/qmd/CodeGraph)?
- [ ] Did I pick a research mode (discovery/grounding/research/academic/recovery)?
- [ ] Did I use the right primary engine for that mode?
- [ ] Did I cross-check important claims with a second source?
- [ ] Did I fetch ≤3 high-signal URLs, not bulk-dump?
- [ ] Did I separate confirmed facts from inference?
- [ ] For GitHub URLs: did I skip `web_extract` and use Exa/gh instead?

**If any box is unchecked, go back.**

---

> 🔄 Deployment & Sync: `references/deployment.md`
