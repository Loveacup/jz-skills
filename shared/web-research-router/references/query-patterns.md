# Query Patterns

Common search query patterns. Loaded on-demand from SKILL.md.

## 双主力广扫（默认起手）· Dual-primary broad search

> ⚠️ **v3.9：SearXNG 实例已损坏（Google 失效 / Bing 降级 / DDG CAPTCHA），从「默认起手」降为「最后兜底」（前几家命中 <3 条才用）。** 默认起手 = Exa + Brave 双主力。

Primary: **Exa**（`mcp_exa_web_search_exa`，语义精准）+ **Brave**（`mcp_brave_search_brave_web_search`，独立索引交叉）双引擎并行。
覆盖神经索引 + 独立爬虫两套互补盲区，看清 landscape 后再决定走哪个垂直精挖路径。

```
<topic> 2026  →  Exa（语义精准候选）+ Brave（独立索引交叉）
                 → 命中 <3 条再补 web_search 广扫 / SearXNG 兜底
                 → 按结果分布判断后续路径：
                   - 学术多 → arXiv / Semantic Scholar 深刷
                   - 代码多 → github skill / gh CLI
                   - 主流报道多 → Tavily 深核
                   - 全是 blog/discovery 类 → Exa 已覆盖语义精准
```

适合：议题不熟、术语未定、不知道从哪个垂直入口下手时的探路。
不适合：已知精确 DOI / arxiv_id / 仓库名 → 直接走对应垂直工具，不绕路。

## Current factual lookup

Primary: Exa + Brave 双引擎交叉（独立索引看是否一致）→ Tavily 深核抽数字 / web_search 兜底补充。一致 → 高置信；分歧 → cross-check。

```
<entity/topic> latest official announcement pricing release date 2026
```

Output: concise answer + citations + uncertainty if sources disagree.

## Semantic source discovery

Primary: Exa 语义精准起手 → Brave 独立索引补种子。Exa 擅长基于"已有种子页"找语义相邻源；Brave 帮你先拿到独立爬虫覆盖的种子。

```
high signal sources about <topic> official docs reports practitioner analysis 2026
```

Output: source map, not a raw result dump.

## Company / market scan

Primary: Exa + Brave 双主力（语义精准 + 独立索引看主流报道/官网/对手覆盖范围）→ Tavily extract for selected pages；web_search 广扫补盲区。

```
<company/category> competitors pricing product positioning enterprise adoption 2026 official pages
```

Prefer official sites, docs, pricing, changelogs, investor materials, credible interviews.

## Technical docs / API lookup

Primary: Exa（语义召回官方文档 + GitHub + StackOverflow 代码源）+ Brave 独立交叉 → fetch 官方文档（Exa Fetch / Tavily Extract）。Use CodeGraph first for local repo behavior.

```
<language/framework/package version> <API/error> official docs examples issue
```

## Academic paper / literature lookup

Primary: Exa + arXiv skill 做 landscape（Brave 学术域名独立交叉）；
再用 arXiv 深刷预印本 / Semantic Scholar 拉引用图谱。SearXNG **不**推荐——学术信源被实例噪声淹没（见 `academic-lane.md`）。

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
