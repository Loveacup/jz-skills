# 引擎质量实测报告（2026-05-28）

> 5 引擎全量对比测试，3 组 query × 5 引擎 = 15 次搜索。

## 测试环境

- Hermes regent profile, MCP 5 服务器全 online
- Query 1 (事实): "React 19 release date December 2024"
- Query 2 (发现): "best open source AI agent framework 2026 comparison"
- Query 3 (研究): "SearXNG vs Exa vs Brave vs Tavily search engine comparison"

## 引擎排名

| 排名 | 引擎 | 可用性 | 相关性 | 信噪比 | 特点 |
|:--:|------|:--:|:--:|:--:|------|
| 🥇 | **web_search** | 3/3 | 15/15 100% | 极高 | 全能主力，事实/发现/研究均满分 |
| 🥈 | **Exa** | 3/3 | 7/9 78% | 高 | 研究类 3/3 全中，偶有语义漂移 |
| 🥉 | **SearXNG MCP** | 3/3 | ~6/9 67% | ⚠️ 极低 | 140+条但大量spam/词典/钓鱼 |
| 4 | **Brave** | 0/3 | — | — | `SUBSCRIPTION_TOKEN_INVALID` |
| 5 | **Tavily** | 0/3 | — | — | `Invalid API key` |

## 引擎特点

### web_search — 主力引擎
- 100% 可靠，15/15 满分
- 返回 5 条高质量结果，无垃圾
- 三类 query（事实/发现/研究）全部精准命中

### Exa — 语义补强
- 研究/对比类最优（Q3 3/3 全中）
- 限制 3 条结果/次
- 偶尔语义漂移（Q1 跑偏到 GTA 6）
- 适合补强而非主力

### SearXNG MCP — 广撒网后备
- 功能可用但信噪比极低
- 140+ 结果含大量垃圾——词典释义、"Best Buy"商城、钓鱼域名、无关条目
- 仅作最后补充，需人工/脚本二次过滤

### Brave / Tavily — 不可用
- Brave: API subscription token 过期，需重新申请
- Tavily: API key 未配置或失效

## 专项功能测试

| 功能 | 工具 | 结果 |
|------|------|:--:|
| URL→Markdown | `mcp_searxng_web_url_read` | ✅ |
| GitHub 抓取 | `mcp_exa_web_fetch_exa` | ✅ |
| Tavily Extract | `mcp_tavily_tavily_extract` | ❌ key |
| Brave Local | `mcp_brave_search_brave_local_search` | ❌ token |
| Tavily Research | `mcp_tavily_tavily_research` | ❌ key |

## 建议路由策略

```
事实查询 (grounding)  → web_search 起手，Exa 交叉验证
发现查询 (discovery)  → web_search 起手，Exa 语义补强
研究查询 (research)   → web_search + Exa 双引擎，SearXNG 后备
学术查询 (academic)   → Exa + SearXNG arxiv
恢复查询 (recovery)   → web_search + SearXNG URL Read + Exa Fetch
GitHub 源码          → Exa Fetch 直抓
```

> 与 v3.4 测试对比：新增 SearXNG MCP（替代 HTTP curl）、Brave/Tavily 从「未配置」升级到「已配但 key 失效」。
