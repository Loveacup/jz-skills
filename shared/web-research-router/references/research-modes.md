# Research Modes

Detailed mode instructions for web-research-router. Loaded on-demand from SKILL.md.

## Mode Selection

**Auto-detect vs. ask:** Deterministic scenarios → auto-select. Uncertain scenarios → ask the user.

**When to ask (8 scenarios):**

| Scenario | Ask |
|----------|-----|
| Intent is ambiguous (quick overview vs. deep research?) | "是要快速了解还是深度调研？" |
| Topic is too broad with no specific need | "你关注哪个维度？" |
| Multi-engine results contradict each other | "结果有矛盾，要深挖吗？" |
| Search terms have multiple meanings | "你指的是哪种含义？" |
| Answer likely already in local knowledge (Hindsight/qmd) | "本地好像有，要先查本地吗？" |
| Not clear if user wants full-text fetch vs. summary | "要抓原文细读还是先看摘要？" |
| Academic search scope unclear (time range, include preprints?) | "时间范围和是否包含预印本？" |
| GitHub exploration depth unclear (L1 quick look vs. L4 full analysis) | "快速看实现还是全面分析？" |

---

## `discovery` — find high-signal sources

Use when the user asks for background, landscape, competitors, examples, docs, projects, or "有没有相关资料/项目".

Default path:
1. Exa for semantic discovery.
2. Brave if broad/public coverage matters or Exa looks narrow.
3. Fetch 1–3 canonical sources only.

Good sources: official docs, GitHub repos, maintainer posts, primary reports, credible practitioner analysis.

---

## `grounding` — verify claims

Use when the task depends on dates, numbers, prices, authorship, identity, legal/regulatory facts, current news, or financial/investment claims.

Default path:
1. Tavily or Brave for current factual lookup.
2. Cross-check with the other engine when the claim matters.
3. Fetch/read the primary source before asserting.

Output must separate confirmed facts, inference, conflicts, and gaps.

---

## `research` — build a source-backed brief

Use when the user wants a substantive answer, source map, decision memo, market scan, technical recommendation, or long-form research.

Default path:
1. Start with Exa for source discovery or Tavily research when factual synthesis is the goal.
2. Add Brave for mainstream/current coverage and cross-checking.
3. Fetch only the highest-signal URLs.
4. Hand off to `source-reader`, `content-source-workflow`, `source-verification`, or a domain skill when the source map is built.

---

## `academic` — papers, citations, and research genealogy

Use when the user asks for papers, literature reviews, arXiv, citations, references, SOTA, surveys, academic sources, DOI/venue metadata, author profiles, research lineage.

**Full academic lane policy: `references/academic-lane.md`**

Quick default paths by domain:
1. **AI/ML/CS/math/physics:** load `arxiv` → Semantic Scholar for citations → Exa/Brave for project pages and web context.
2. **Biomedical/clinical:** PubMed/Europe PMC first → Semantic Scholar/OpenAlex → journal full text.
3. **Published metadata / DOI:** OpenAlex or Crossref → publisher page → Semantic Scholar.
4. **Reproducibility:** Papers with Code, GitHub, Hugging Face after canonical paper identified.

Output should distinguish: seminal / survey / SOTA / implementation / critique.

---

## `recovery` — recover missing, moved, or hard-to-find material

Use when a URL is dead, a source moved, a title is known but the link is missing.

Default path:
1. Brave with exact title/URL fragments and `site:` operators.
2. Exa for semantically similar pages or remembered titles.
3. Tavily extract/fetch if candidate URLs are found.
4. Report whether the recovered source is canonical, mirrored, archived, or uncertain.

---

## Cost / Noise Discipline

- Do not use all engines by default.
- Start with 5–8 results.
- Fetch/extract sparingly.
- Prefer one strong primary source over five weak summaries.
- For recurring monitoring, use silent cron/script watchdogs; notify only on meaningful deltas.
- If a query can be answered from local KB/code/session memory, avoid paid/public APIs.
