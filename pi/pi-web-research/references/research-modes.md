# Research Modes

Detailed mode instructions for web-research-router. Loaded on-demand from SKILL.md.

## Mode Selection

> 🌐 **跨模式默认起手：SearXNG。** 五种模式都从 `mcp_searxng_searxng_web_search` 广扫开始；
> 看清 landscape 后再按下表选模式、按各模式 Default path 决定精深方向。
> 这不是省钱省 token——是因为单引擎遗漏太常见，先广扫再精挖比从一开始就走窄漏斗更可靠。

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
1. **SearXNG 广扫**（`mcp_searxng_searxng_web_search`）—— 一次拿到 6+ 通用引擎结果，看清整个 landscape。
2. Exa 做语义精准——基于 SearXNG 的初探结果定义更精确的语义查询。
3. Brave if Exa looks narrow or 需要本地化 / 新闻补强。
4. Fetch 1–3 canonical sources only.

Good sources: official docs, GitHub repos, maintainer posts, primary reports, credible practitioner analysis.

---

## `grounding` — verify claims

Use when the task depends on dates, numbers, prices, authorship, identity, legal/regulatory facts, current news, or financial/investment claims.

Default path:
1. **SearXNG 多引擎交叉**（`mcp_searxng_searxng_web_search`）—— 6 个通用引擎同时返回，一致 → 高置信；分歧 → 进入深核流程。
2. Tavily 深核——仅当 SearXNG 引擎间出现分歧、或目标是最新动态 / 抽取原文时调用。
3. Brave 作为 Tavily 的补充交叉源。
4. Fetch/read the primary source before asserting.

Output must separate confirmed facts, inference, conflicts, and gaps.

---

## `research` — build a source-backed brief

Use when the user wants a substantive answer, source map, decision memo, market scan, technical recommendation, or long-form research.

Default path:
1. **SearXNG landscape scan**（`mcp_searxng_searxng_web_search`）—— 先把全景拉满：通用 + 学术 + 代码 + 中文，得到 100+ 候选源。
2. Exa 做语义精准——挑出 SearXNG 没覆盖到的 high-signal 角度（公司、产品对比、深度博文）。
3. Tavily 做事实核验 / 抽取原文。
4. Brave 仅在需要 mainstream / 新闻视角时叠加。
5. Fetch only the highest-signal URLs（`mcp_searxng_web_url_read` 适合 GitHub 页面；其余用 Tavily extract）。
6. Hand off to `source-reader`, `content-source-workflow`, `source-verification`, or a domain skill when the source map is built.

---

## `academic` — papers, citations, and research genealogy

Use when the user asks for papers, literature reviews, arXiv, citations, references, SOTA, surveys, academic sources, DOI/venue metadata, author profiles, research lineage.

**Full academic lane policy: `references/academic-lane.md`**

> 🎓 **SearXNG 学术模式：** `mcp_searxng_searxng_web_search` 已开 arXiv + Semantic Scholar + Crossref（约 40 条/次），
> 一次调用即可拿到三个学术源的合并结果。**适合：** 快速看 landscape、跨源交叉、术语未定时的探路。
> **不适合：** 引用图谱、作者档案、PubMed 生物医学专项——这些仍需 Semantic Scholar / OpenAlex / PubMed 单刷。

Quick default paths by domain:
1. **AI/ML/CS/math/physics:** SearXNG（一次拿 arXiv+SS+Crossref）→ load `arxiv` 深刷预印本 → Semantic Scholar 拉引用图谱 → Exa/Brave 找 project pages 与 blog 上下文。
2. **Biomedical/clinical:** PubMed/Europe PMC first → Semantic Scholar/OpenAlex → journal full text。SearXNG 不覆盖 PubMed，跳过。
3. **Published metadata / DOI:** SearXNG（Crossref 已包含）→ OpenAlex/Crossref 单刷补全 → publisher page → Semantic Scholar.
4. **Reproducibility:** Papers with Code, GitHub, Hugging Face after canonical paper identified.

Output should distinguish: seminal / survey / SOTA / implementation / critique.

---

## `recovery` — recover missing, moved, or hard-to-find material

Use when a URL is dead, a source moved, a title is known but the link is missing.

Default path:
1. **SearXNG 起手**（`mcp_searxng_searxng_web_search`）—— 6 引擎并发，命中概率最高。某一引擎漏掉的快照，另一引擎可能还留着。
2. Brave with exact title/URL fragments and `site:` operators——SearXNG 没找到时的兜底。
3. Exa for semantically similar pages or remembered titles（标题模糊时尤其有用）。
4. Tavily extract/fetch（或 `mcp_searxng_web_url_read` 对付 GitHub 页面）if candidate URLs are found.
5. Report whether the recovered source is canonical, mirrored, archived, or uncertain.

---

## Cost / Noise Discipline

- Do not use all engines by default.
- Start with 5–8 results.
- Fetch/extract sparingly.
- Prefer one strong primary source over five weak summaries.
- For recurring monitoring, use silent cron/script watchdogs; notify only on meaningful deltas.
- If a query can be answered from local KB/code/session memory, avoid paid/public APIs.
