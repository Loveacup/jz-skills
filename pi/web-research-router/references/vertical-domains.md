# Vertical Domain → Engine Mapping · 垂直领域引擎映射

Inspired by AnySearch's 23 vertical search domains. When a query clearly belongs to a specific domain, route to the best engine instead of generic web search.

> 🌐 **通用前置：** 任何垂直域查询都可以先用 **SearXNG**（`mcp_searxng_searxng_web_search`）做一次广扫
> ——它聚合了 Bing + Brave + Qwant + Mwmbl + DuckDuckGo + Startpage + arXiv + Semantic Scholar +
> Crossref + GitHub + StackOverflow + Bilibili + Wikipedia/Wikidata。下表中标 ⭐ 的域 SearXNG 表现尤其好。

| Domain | Sub-domain | Best Engine | Query Tip |
|:---|:---|:---|:---|
| **Finance** | US stock, crypto, forex | Brave (coverage) or Tavily (facts) | Include ticker + metric wanted |
| ⭐ **Academic** | Papers, citations, SOTA | **SearXNG**（一次拿 arXiv+SS+Crossref，约 40 条）→ arXiv / Semantic Scholar 深刷 | Use academic lane (`references/academic-lane.md`) |
| ⭐ **Code** | Implementation, API usage | **SearXNG**（一次拿 GitHub+SO，约 35 条）→ `github` skill 深挖 | Route before touching web search |
| **Security** | CVE, vulnerability, exploit | Tavily (grounding) | Include CVE ID if known |
| **Legal** | Case law, regulation, patent | Tavily (grounding) | Cross-check with Brave |
| **Health** | Drug, condition, clinical trial | Tavily → PubMed if biomedical | Require cross-check; label study type |
| ⭐ **News** | Breaking, trending, current events | **SearXNG**（6 引擎同步覆盖当下报道）→ Tavily 深核 / Brave 补强 | Set `freshness=day` or `week` |
| **Travel** | Flight, hotel, IATA code | Brave (local) | Use `mcp_brave_search_brave_local_search` |
| **Geo** | Map, location, coordinates | Brave (local) | Use local search variant |
| **Science** | Experiment, dataset, methodology | SearXNG → Exa (discovery) → fetch | Cross-check with Semantic Scholar |
| **Product** | Company, tool, comparison | SearXNG → Exa (discovery) | Category search: `category:company` |
| **People** | Biography, profile, background | SearXNG → Exa (discovery) | Category search: `category:people` |
| **Image** | Visual search, diagram, photo | Web search → `vision_analyze` | Search for image URL, then analyze |
| ⭐ **Video** | YouTube, Bilibili, tutorial | **SearXNG**（含 Bilibili 引擎）→ extract | Use `youtube-content` or `bilibili-video-analyzer` |
| **Audio** | Podcast, sound, music | Web search | Consider `spotify` skill for music |
| **Data** | Statistics, dataset, CSV | Exa (discovery) → fetch | Prefer official sources (.gov, .edu, .org) |
| **Document** | PDF, report, whitepaper | Exa (discovery) | Use `filetype:pdf` in query |
| **API** | Endpoint, SDK, integration | SearXNG → `github` or Exa | Search GitHub for examples |
| **DevOps** | Config, Docker, k8s, CI/CD | Exa → fetch docs | Prefer official docs over blog posts |
| ⭐ **AI/ML** | Model, benchmark, paper | **SearXNG**（arXiv+SS+Crossref+GitHub 一次拿到，跨学术+实现）→ arXiv 深刷 → Papers with Code | Use academic lane; cross-check with Papers with Code |
| **Game** | Walkthrough, mod, strategy | Web search (Exa) | No domain-specific engine; general web |
| **Shopping** | Price, review, product spec | Brave (coverage) | Cross-check multiple sources |
| **Weather** | Forecast, climate data | Web search (Tavily) | Prefer official weather service sites |
| ⭐ **Chinese content** | 中文资料、Bilibili、知乎、博客 | **SearXNG**（Bing 中文 + Bilibili，约 88 条/次） | 直接用中文 query，无需翻译 |

## When to use this table

- Query contains a domain-specific identifier (stock ticker, CVE ID, DOI, IATA code, patent number)
- User explicitly names a domain ("找篇论文", "查一下这个CVE", "有什么开源项目")
- Generic web search returns noisy results that a vertical engine would filter

## When NOT to use

- Cross-domain queries → use `research` mode with Exa + Tavily
- Simple factual questions ("巴黎几点了") → `grounding` mode with Tavily
- "Best X for Y" comparisons → `discovery` mode with Exa
