# GitHub prior art for web research routing

Last searched: 2026-05-26

Use this as comparative prior art for Hermes `web-research-router`: we currently keep Exa, Tavily, and Brave as separate MCP servers and use this skill as the routing/policy layer. These projects show alternative designs if we later want a dedicated broker MCP.

## Most relevant projects

### spences10/mcp-omnisearch

- URL: https://github.com/spences10/mcp-omnisearch
- Shape: TypeScript MCP server with four consolidated tools: `web_search`, `ai_search`, `github_search`, `web_extract`.
- Providers: Tavily, Brave, Kagi, Exa, GitHub, Linkup, Firecrawl.
- Interesting ideas:
  - Unified interface while still exposing provider choice.
  - Explicit `large_result_mode` for oversized extraction responses.
  - GitHub search as a first-class research surface.
  - Operator translation: Brave/Kagi query operators pass through, Tavily domain/date operators are converted to API params.
- Caveat: More wrapper complexity; may duplicate tools Hermes already has.

### Khamel83/argus

- URL: https://github.com/Khamel83/argus
- Shape: Python search broker, HTTP/CLI/MCP/Python import.
- Providers: SearXNG, Brave, Serper, Tavily, Exa; extraction via trafilatura + Jina; SQLite state.
- Interesting ideas:
  - Search modes: `discovery`, `recovery`, `grounding`, `research` with different provider chains.
  - RRF ranking, dedup, health tracking, budget enforcement.
  - Multi-turn session memory for follow-up searches.
  - Budget/health inspection tools (`search_health`, `search_budgets`, `test_provider`).
- Caveat: Very low adoption at search time, but architecture maps closely to what Hermes might want.

### ykq007/mcp-nexus

- URL: https://github.com/ykq007/mcp-nexus
- Shape: Tavily + Brave MCP bridge with Admin UI, key rotation, usage monitoring, client auth.
- Providers: Tavily and Brave.
- Interesting ideas:
  - Multiple upstream API keys with round-robin/random key selection.
  - `SEARCH_SOURCE_MODE`: `tavily_only`, `brave_only`, `combined`, `brave_prefer_tavily_fallback`.
  - Query logging privacy modes: none/hash/preview/full.
  - Rate limits and queue overflow fallback behavior.
- Caveat: Operationally heavier than needed for a single-user Hermes profile unless API-key pooling becomes important.

### BjornMelin/mcp-search-hub

- URL: https://github.com/BjornMelin/mcp-search-hub
- Shape: Python/FastMCP intelligent multi-provider search aggregation server.
- Providers: Linkup, Exa, Perplexity, Tavily, Firecrawl.
- Interesting ideas:
  - Provider routing by query class and advertised provider strengths.
  - Result merger, caching, and provider info tools.
  - Embedding official provider MCP servers rather than reimplementing every provider.
- Caveat: Low adoption; includes providers not currently configured in Hermes.

### minpeter/opensearch-mcp

- URL: https://github.com/minpeter/opensearch-mcp
- Shape: TypeScript zero-config web search/fetch MCP.
- Providers: Brave → Exa hosted MCP → Exa API → DuckDuckGo → Bing; Google scraping opt-in.
- Interesting ideas:
  - Free-tier-first fallback, especially trying hosted Exa before consuming local Exa API quota.
  - Text-first result rendering compatible with simple MCP clients.
  - `web_fetch` fallback chain: Exa hosted fetch → Exa contents API → local Readability/PDF → Jina.
- Caveat: Narrower than our Exa/Tavily/Brave stack; less policy nuance.

### robbyczgw-cla/web-search-plus-mcp

- URL: https://github.com/robbyczgw-cla/web-search-plus-mcp
- Shape: Python MCP server with intelligent auto-routing.
- Providers: Serper, Tavily, Querit, Exa, Perplexity, You.com, SearXNG.
- Interesting ideas:
  - Simple `provider: auto` API.
  - Intent examples: shopping → Serper, explanation/research → Tavily, discovery → Exa, direct answer → Perplexity.
- Caveat: Low adoption; no Brave in the listed provider set.

### guptabhishek/multi-search-mcp

- URL: https://github.com/guptabhishek/multi-search-mcp
- Shape: TypeScript MCP server with one `search` tool and provider fallback.
- Providers: Google Custom Search, Tavily, DuckDuckGo, Brave.
- Interesting ideas:
  - Minimal standard result schema.
  - Configurable provider priority / random strategy.
- Caveat: No Exa; mainly fallback rather than semantic routing.

### JonusNattapong/MCPSearch

- URL: https://github.com/JonusNattapong/MCPSearch
- Shape: Python self-hosted research/crawling stack with MCP tools.
- Providers/surfaces: DuckDuckGo, Google, Bing, HTTP/browser/stealth crawling, Reddit, X/Twitter, YouTube, GitHub.
- Interesting ideas:
  - Unified `mcpsearch` and `mcpsearch_multi` action interface.
  - Higher-level workflows: `investigate`, `compare`, `trending`.
  - Separate fast/hybrid/stealth crawl modes.
- Caveat: Crawling/social stack is a broader and riskier scope than current Hermes search routing.

### exa-labs/exa-mcp-server

- URL: https://github.com/exa-labs/exa-mcp-server
- Shape: Official Exa MCP server.
- Interesting ideas:
  - Official hosted MCP option.
  - Built-in Claude Skill examples for company, code, people, financial reports, research papers, personal sites.
  - Strong category/filter caveats documented in skill text.
- Caveat: Single-provider; best used as a tactical provider skill rather than the router itself.

## Design implications for Hermes

1. Keep the current skill-router model for now. It avoids duplicating official MCP tools and keeps provider-specific features available.
2. Borrow from Argus: search modes, budget/health checks, RRF/dedup if we build a broker later.
3. Borrow from mcp-omnisearch: large-result handling, GitHub search as a first-class source, operator translation notes.
4. Borrow from mcp-nexus only if multi-key rotation or usage accounting becomes necessary.
5. Avoid installing a wrapper MCP immediately; each wrapper adds another abstraction layer and may hide provider-specific strengths.

## Candidate future Hermes enhancements

- Add router examples for `discovery`, `grounding`, `research`, and `recovery` modes.
- Add a `source map` schema that records provider, URL, source tier, claim supported, and conflict status.
- Add optional result dedup/RRF script for multi-engine searches when the same query is sent to multiple engines.
- Consider GitHub search integration as its own research surface, especially for implementation pattern discovery.
- Add budget/health inspection conventions after Tavily/Brave/Exa expose usage signals reliably.
