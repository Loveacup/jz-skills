# Engine Test Results v3.6 (2026-05-28)

第二轮全量测试：5 MCP servers 全在线，3 query × 5 engines = 15 次搜索。

## 引擎对比

| Query | web_search | Exa | SearXNG MCP | Brave | Tavily |
|-------|:---:|:---:|:---:|:---:|:---:|
| "React 19 release date" (事实) | ✅ 5/5 | ✅ 2/3* | ⚠️ ~2/3 高噪声 | ❌ key | ❌ key |
| "best AI agent framework 2026" (发现) | ✅ 5/5 | ✅ 2/3 | ⚠️ ~2/3 高噪声 | ❌ key | ❌ key |
| "SearXNG vs Exa vs Brave vs Tavily" (研究) | ✅ 5/5 | ✅ 3/3 | ⚠️ ~2/3 高噪声 | ❌ key | ❌ key |
| **总分** | **15/15** | **7/9** | **~6/9** | **0** | **0** |

*Exa Q1 #2 漂移到 GTA 6。

## 专项功能

| # | 测试项 | 结果 |
|---|--------|:--:|
| 1 | SearXNG URL Read (obsidian.md/cli) | ✅ |
| 2 | Exa Fetch (github.com/torvalds/linux) | ✅ |
| 3 | Tavily Extract | ❌ Invalid API key |
| 4 | Brave Local Search | ❌ SUBSCRIPTION_TOKEN_INVALID |
| 5 | Tavily Research | ❌ Invalid API key |
| 6 | SearXNG Resources (list + read) | ✅ |

## SearXNG MCP 身份

- 包: `ihor-sokoliuk/mcp-searxng` v1.0.5
- SearXNG 地址: `http://127.0.0.1:32080`
- 暴露工具: `searxng_web_search` + `web_url_read`
- 每次返回 140+ 条结果，含大量 spam/钓鱼/词典/无关条目

## API Key 状态

| 引擎 | Key 变量 | 状态 | 修复 |
|------|---------|:--:|------|
| Brave | `BRAVE_API_KEY` | 🔧 失效 | [brave.com/search/api](https://brave.com/search/api/) 免费 2000/月 |
| Tavily | `TAVILY_API_KEY` | 🔧 未设 | [tavily.com](https://tavily.com/) 免费 1000/月 |
