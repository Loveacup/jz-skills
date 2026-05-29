# Query Patterns

Common search query patterns. Loaded on-demand from SKILL.md.

## 多引擎广扫（默认起手）· Multi-engine broad search

Primary: **SearXNG**（`mcp_searxng_searxng_web_search`）。一次调用聚合 6+ 引擎
（Bing/Brave/Qwant/Mwmbl/DuckDuckGo/Startpage + arXiv/Semantic Scholar/Crossref + GitHub/StackOverflow + Bilibili），
覆盖最广，看清 landscape 后再决定走哪个垂直精挖路径。

```
<topic> 2026  →  SearXNG（拿到 100+ 候选源、跨学术+代码+中文）
                 → 按结果分布判断后续路径：
                   - 学术多 → arXiv / Semantic Scholar 深刷
                   - 代码多 → github skill / gh CLI
                   - 主流报道多 → Tavily / Brave 深核
                   - 全是 blog/discovery 类 → Exa 做语义精准
```

适合：议题不熟、术语未定、不知道从哪个垂直入口下手时的探路。
不适合：已知精确 DOI / arxiv_id / 仓库名 → 直接走对应垂直工具，不绕路。

## Current factual lookup

Primary: SearXNG 多引擎交叉（先看 6 引擎是否一致）→ Tavily 深核 / Brave 补充。一致 → 高置信；分歧 → cross-check。

```
<entity/topic> latest official announcement pricing release date 2026
```

Output: concise answer + citations + uncertainty if sources disagree.

## Semantic source discovery

Primary: SearXNG 广扫 → Exa 拣语义精准。Exa 擅长基于"已有种子页"找语义相邻源；SearXNG 帮你先拿到种子。

```
high signal sources about <topic> official docs reports practitioner analysis 2026
```

Output: source map, not a raw result dump.

## Company / market scan

Primary: SearXNG（先看主流报道+官网+对手覆盖范围）→ Exa for semantic 拣选；Brave for coverage 补强；Tavily extract for selected pages.

```
<company/category> competitors pricing product positioning enterprise adoption 2026 official pages
```

Prefer official sites, docs, pricing, changelogs, investor materials, credible interviews.

## Technical docs / API lookup

Primary: SearXNG（一次拿到 GitHub + StackOverflow + 官方文档，约 35+ 条代码源）→ Exa for discovery 补充；fetch 官方文档。Use CodeGraph first for local repo behavior.

```
<language/framework/package version> <API/error> official docs examples issue
```

## Academic paper / literature lookup

Primary: SearXNG（一次聚合 arXiv + Semantic Scholar + Crossref，约 40 条）做 landscape；
再用 arXiv 深刷预印本 / Semantic Scholar 拉引用图谱。

```
<topic/method> recent papers survey related work SOTA citations code benchmark 2024 2025 2026
```

Output: paper map grouped by role: seminal / survey / SOTA / implementation / critique.

## Citation and research genealogy

Primary: Semantic Scholar; supplement with OpenAlex/Crossref for metadata.

```
paper: <arxiv_id|doi|title> citations references influential citations related papers
```

Output: predecessor works, descendant works, citation count, influential citation count.

## Paper-to-code / reproducibility lookup

Primary: Papers with Code, GitHub, Hugging Face, project pages.

```
<title or arxiv_id> code github project page benchmark dataset huggingface
```

Output: canonical code URL, third-party implementations labeled, datasets/models/benchmarks.

## Biomedical literature

Primary: PubMed, then Semantic Scholar/OpenAlex, then journal/PMC/full text.

```
<condition/intervention/biomarker> systematic review randomized trial PubMed 2024 2025 2026
```

Output: publication type, human/animal/in-vitro distinction, journal/source, clinical caveats.

## Website structure / docs crawl

Primary: Tavily map/crawl.

Use when the task is "what pages exist under this docs/site/pricing area?" or when a single page is insufficient.
