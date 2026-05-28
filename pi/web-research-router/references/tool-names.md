# MCP Tool Names

Tool names available in this profile. Loaded on-demand.

After gateway restart / new Hermes session:

- **SearXNG**（本地实例 `http://127.0.0.1:32080`，聚合 6+ 引擎，覆盖最广，**默认起手**）：
  - `mcp_searxng_searxng_web_search` — 多引擎并发搜索；一次拿到 Bing/Brave/Qwant/Mwmbl/DuckDuckGo/Startpage（通用） + arXiv/Semantic Scholar/Crossref（学术） + GitHub/StackOverflow（代码） + Bilibili（中文视频） + Wikipedia/Wikidata（百科）的结果。英文查询 ~124 条、中文 ~88 条、学术 ~40 条、代码 ~35 条。
  - `mcp_searxng_web_url_read` — 把任意 URL 抓成 markdown，含 GitHub/raw.githubusercontent.com 页面（绕过 `web_extract` 的内网误判）。
- **Exa:**
  - `mcp_exa_web_search_exa`
  - `mcp_exa_web_fetch_exa`
- **Tavily:**
  - `mcp_tavily_tavily_search`
  - `mcp_tavily_tavily_extract`
  - `mcp_tavily_tavily_map`
  - `mcp_tavily_tavily_crawl`
  - `mcp_tavily_tavily_research`
- **Brave:**
  - `mcp_brave_search_brave_web_search`
  - `mcp_brave_search_brave_local_search`

If a tool is not visible in the current session, verify with `hermes mcp test <server>` and restart/new-session before relying on it.
