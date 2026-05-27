# Vertical Domain → Engine Mapping · 垂直领域引擎映射

Inspired by AnySearch's 23 vertical search domains. When a query clearly belongs to a specific domain, route to the best engine instead of generic web search.

| Domain | Sub-domain | Best Engine | Query Tip |
|:---|:---|:---|:---|
| **Finance** | US stock, crypto, forex | Brave (coverage) or Tavily (facts) | Include ticker + metric wanted |
| **Academic** | Papers, citations, SOTA | arXiv / Semantic Scholar | Use academic lane (`references/academic-lane.md`) |
| **Code** | Implementation, API usage | `github-code-explorer` skill | Route before touching web search |
| **Security** | CVE, vulnerability, exploit | Tavily (grounding) | Include CVE ID if known |
| **Legal** | Case law, regulation, patent | Tavily (grounding) | Cross-check with Brave |
| **Health** | Drug, condition, clinical trial | Tavily → PubMed if biomedical | Require cross-check; label study type |
| **News** | Breaking, trending, current events | Brave (broad) or Tavily (deep) | Set `freshness=day` or `week` |
| **Travel** | Flight, hotel, IATA code | Brave (local) | Use `mcp_brave_search_brave_local_search` |
| **Geo** | Map, location, coordinates | Brave (local) | Use local search variant |
| **Science** | Experiment, dataset, methodology | Exa (discovery) → fetch | Cross-check with Semantic Scholar |
| **Product** | Company, tool, comparison | Exa (discovery) | Category search: `category:company` |
| **People** | Biography, profile, background | Exa (discovery) | Category search: `category:people` |
| **Image** | Visual search, diagram, photo | Web search → `vision_analyze` | Search for image URL, then analyze |
| **Video** | YouTube, Bilibili, tutorial | Web search → extract | Use `youtube-content` or `bilibili-video-analyzer` |
| **Audio** | Podcast, sound, music | Web search | Consider `spotify` skill for music |
| **Data** | Statistics, dataset, CSV | Exa (discovery) → fetch | Prefer official sources (.gov, .edu, .org) |
| **Document** | PDF, report, whitepaper | Exa (discovery) | Use `filetype:pdf` in query |
| **API** | Endpoint, SDK, integration | `github-code-explorer` or Exa | Search GitHub for examples |
| **DevOps** | Config, Docker, k8s, CI/CD | Exa → fetch docs | Prefer official docs over blog posts |
| **AI/ML** | Model, benchmark, paper | arXiv / Semantic Scholar | Use academic lane; cross-check with Papers with Code |
| **Game** | Walkthrough, mod, strategy | Web search (Exa) | No domain-specific engine; general web |
| **Shopping** | Price, review, product spec | Brave (coverage) | Cross-check multiple sources |
| **Weather** | Forecast, climate data | Web search (Tavily) | Prefer official weather service sites |

## When to use this table

- Query contains a domain-specific identifier (stock ticker, CVE ID, DOI, IATA code, patent number)
- User explicitly names a domain ("找篇论文", "查一下这个CVE", "有什么开源项目")
- Generic web search returns noisy results that a vertical engine would filter

## When NOT to use

- Cross-domain queries → use `research` mode with Exa + Tavily
- Simple factual questions ("巴黎几点了") → `grounding` mode with Tavily
- "Best X for Y" comparisons → `discovery` mode with Exa
