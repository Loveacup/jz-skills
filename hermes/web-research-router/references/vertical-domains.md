# Vertical Domain → Engine Mapping · 垂直领域引擎映射

Inspired by AnySearch's 23 vertical search domains. When a query clearly belongs to a specific domain, route to the best engine instead of generic web search.

> 🌐 **通用前置（v3.9 对齐主 SKILL.md）：** 任何垂直域查询默认用 **Exa**（`mcp_exa_web_search_exa`，语义精准）+ **Brave**（`mcp_brave_search_brave_web_search`，独立索引交叉）双主力起手；
> `web_search` 广扫补盲，**Tavily** 深研 / grounding（`tavily_extract` 抽事实卡）。
> ⛔ **SearXNG 实例已损坏**（Google 失效 / Bing 降级 / DDG CAPTCHA，跨平台系统性缺陷）——`mcp_searxng_searxng_web_search` 仅作**最后兜底**（前几家命中 <3 条才用），`mcp_searxng_web_url_read` 仅作抓取备胎。下表中标 ⭐ 的域为该垂直引擎表现尤其突出者。

| Domain | Sub-domain | Best Engine | Query Tip |
|:---|:---|:---|:---|
| **Finance** | US stock, crypto, forex | Brave (coverage) or Tavily (facts) | Include ticker + metric wanted |
| ⭐ **Academic** | Papers, citations, SOTA | **Exa**（语义精准）+ **arXiv** skill 深刷 → Semantic Scholar 交叉（SearXNG **不**推荐，学术信源被实例噪声淹没） | Use academic lane (`references/academic-lane.md`) |
| ⭐ **Code** | Implementation, API usage | **Exa** + **Brave** 起手 → `github` skill / `gh search code` 深挖 | Route before touching web search |
| **Security** | CVE, vulnerability, exploit | Tavily (grounding) | Include CVE ID if known |
| **Legal** | Case law, regulation, patent | Tavily (grounding) | Cross-check with Brave |
| **Health** | Drug, condition, clinical trial | Tavily → PubMed if biomedical | Require cross-check; label study type |
| ⭐ **News** | Breaking, trending, current events | **Brave**（时效 / locale-aware 主力）+ **Exa**（语义补）→ **Tavily** 抓取 / grounding 深核 | Set `freshness=day` or `week` |
| **Travel** | Flight, hotel, IATA code | Brave (local) | Use `mcp_brave_search_brave_local_search` |
| **Geo** | Map, location, coordinates | Brave (local) | Use local search variant |
| **Science** | Experiment, dataset, methodology | Exa + Brave (discovery) → fetch | Cross-check with Semantic Scholar |
| **Product** | Company, tool, comparison | Exa + Brave (discovery) | Cross-check multiple sources |
| **People** | Biography, profile, background | Exa + Brave (discovery) | Cross-check multiple sources |
| **Image** | Visual search, diagram, photo | Web search → `vision_analyze` | Search for image URL, then analyze |
| **Video** | YouTube, Bilibili, tutorial | Exa + Brave 起手 → extract | Use `youtube-content` or `bilibili-video-analyzer` |
| **Audio** | Podcast, sound, music | Web search | Consider `spotify` skill for music |
| **Data** | Statistics, dataset, CSV | Exa (discovery) → fetch | Prefer official sources (.gov, .edu, .org) |
| **Document** | PDF, report, whitepaper | Exa (discovery) | Use `filetype:pdf` in query |
| **API** | Endpoint, SDK, integration | Exa + Brave → `github` skill | Search GitHub for examples |
| **DevOps** | Config, Docker, k8s, CI/CD | Exa → fetch docs | Prefer official docs over blog posts |
| ⭐ **AI/ML** | Model, benchmark, paper | **Exa** + **arXiv** skill 深刷 → Papers with Code（SearXNG **不**推荐） | Use academic lane; cross-check with Papers with Code |
| **Game** | Walkthrough, mod, strategy | Web search (Exa) | No domain-specific engine; general web |
| **Shopping** | Price, review, product spec | Brave (coverage) | Cross-check multiple sources |
| **Weather** | Forecast, climate data | Web search (Tavily) | Prefer official weather service sites |
| ⭐ **Chinese content** | 中文资料、Bilibili、知乎、博客 | **Brave**（locale-aware 主力，直接中文 query）+ **Exa**（语义补）；Tavily 仅抓取 / grounding，**不**靠 SearXNG / Tavily search 发现 | 直接用中文 query，无需翻译 |

## When to use this table

- Query contains a domain-specific identifier (stock ticker, CVE ID, DOI, IATA code, patent number)
- User explicitly names a domain ("找篇论文", "查一下这个CVE", "有什么开源项目")
- Generic web search returns noisy results that a vertical engine would filter

## When NOT to use

- Cross-domain queries → use `research` mode with Exa + Tavily
- Simple factual questions ("巴黎几点了") → `grounding` mode with Tavily
- "Best X for Y" comparisons → `discovery` mode with Exa
