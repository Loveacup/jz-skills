# MCP Tool Names (v3.7 · 2026-05-29)

> 5 引擎全矩阵，跨平台（regent macOS + pi Windows）交叉验证后的可用性快照。
> Replaces references/tool-names.md v3.6.

**Status legend**
- ✅ 主力可用 / 满分或近满分
- ⚠️ 可用但有限制（高噪声 / 截断 / 仅特定场景）
- 🔧 实例已损坏 / API 失效 / 仅保留特定通道

---

## 5 引擎可用性矩阵

- **Exa** ✅ 🥇 主力 #1
  - 评分: 9/9 perfect (regent + pi 双平台)
  - 角色: 语义精准搜索、技术/研究/对比类最优、跨语言召回强
  - 真实可用性: API key 已配置，跨平台稳定

- **Brave** ✅ 🥇 主力 #2
  - 评分: 9/9 perfect
  - 角色: 独立索引交叉验证、新闻/时效类首选、绕开 Google 重排
  - 真实可用性: API key 已修复（v3.6→v3.7 升级关键），免费 2000 次/月

- **Tavily** ✅ 🥈 深度调研
  - 评分: 8/9
  - 角色: 结构化输出、deep loop facts.jsonl 抽取、数字/口径核对
  - 真实可用性: API key 已修复，免费 1000 次/月
  - 特别说明: `tavily_extract` 在抓取质量上**完胜** SearXNG URL Read

- **web_search** ✅ 🥉 广扫兜底
  - 评分: 13/15
  - 角色: Hermes 内置、通用 broad scan、Exa/Brave 命中不足时补盲
  - 真实可用性: 100% 在线，无需 API key

- **SearXNG** 🔧 ⚠️ 实例损坏，仅保留抓取通道
  - 评分: 9/9* 名义满分，但 30% 导航噪声 + 5000 字符截断
  - 实例根因: Google 完全失效 / Bing 严重降级 / DDG CAPTCHA（pi-report RCA）
  - 跨平台确认: **换 MCP 客户端无效，根因在 SearXNG 实例本身**
  - 当前定位: search 通道**不再**作为默认；URL Read 仅作 Exa Fetch 失败时的备胎

---

## 工具清单（按推荐顺序）

### 搜索类工具（参数 = `query: string`）

- **`mcp_exa_web_search_exa`** ✅
  - 签名: `query: string, numResults?: number=3`
  - 状态: 主力 #1，9/9 perfect
  - 用法: `mcp_exa_web_search_exa({ query: "...", numResults: 5 })`

- **`mcp_brave_search_brave_web_search`** ✅
  - 签名: `query: string, count?: number=5`
  - 状态: 主力 #2，9/9 perfect
  - 用法: `mcp_brave_search_brave_web_search({ query: "...", count: 10 })`

- **`mcp_tavily_tavily_search`** ✅
  - 签名: `query: string, max_results?: number=5`
  - 状态: 深度调研，8/9
  - 用法: `mcp_tavily_tavily_search({ query: "...", max_results: 10 })`

- **`web_search`** ✅
  - 签名: `query: string, limit?: number=5`
  - 状态: Hermes 内置，广扫兜底
  - 用法: `web_search({ query: "...", limit: 5 })`

- **`mcp_searxng_searxng_web_search`** 🔧 ⛔ **仅兜底，不默认调用**
  - 签名: `query: string, language?: string='en'`
  - 状态: 实例 Google 失效 / Bing 降级 / DDG CAPTCHA
  - 启用条件: 前 4 家全部命中 <3 条 → 才考虑启用；必须人工过滤前 5-10 条
  - 警告: **不作为起手引擎**；v3.7 从「默认起手」降级为「最后兜底」

- **`mcp_brave_search_brave_local_search`** ✅
  - 签名: `query: string`
  - 状态: Brave 本地化搜索（POI / 地理）
  - 用法: 仅地理位置/本地商家相关 query

### 抓取 / 抽取类工具（参数 = `urls: string[]` **数组**）

- **`mcp_exa_web_fetch_exa`** ✅ 抓取主力
  - 签名: `urls: string[]`（⚠️ **数组**！非 `url: string`）
  - 状态: 唯一可靠 GitHub / HTTPS 抓取通道
  - 用法: `mcp_exa_web_fetch_exa({ urls: ["https://..."] })`
  - 🪤 **常见错误**: 误传 `url: "..."`（单字符串）→ InputValidationError

- **`mcp_tavily_tavily_extract`** ✅ 结构化抽取
  - 签名: `urls: string[]`（⚠️ **数组**！）
  - 状态: 抓取质量**完胜** SearXNG URL Read（pi-report 结论）
  - 用法: `mcp_tavily_tavily_extract({ urls: ["https://..."] })`
  - 用于: deep loop SECTION 阶段 facts.jsonl 抽取

- **`mcp_tavily_tavily_research`** ✅
  - 签名: 见 Tavily MCP schema
  - 状态: 深度研究专用，API key 已配置

- **`mcp_searxng_web_url_read`** ⚠️ 仅抓取通道
  - 签名: `url: string`（单字符串，与抓取类工具不同）
  - 状态: 可用但 5000 字符截断 + 30% 导航噪声
  - 启用条件: Exa Fetch / Tavily Extract 全部失败时的备胎
  - **保留价值**: SearXNG 实例的唯一可用功能

- **`web_extract`** ❌
  - 状态: 全局网络策略拦截所有 HTTPS URL
  - 替代: 用 `mcp_exa_web_fetch_exa` 或 `mcp_tavily_tavily_extract`

---

## 参数陷阱速查（pi-report 教训 + 跨平台吸收）

- 🪤 **search vs fetch 签名差异**:
  - search 工具 = `query: string`（单字符串）
  - fetch / extract 工具 = `urls: string[]`（**数组**）
  - 唯一例外: `mcp_searxng_web_url_read` 用 `url: string`（单字符串）

- 🪤 **数组陷阱**:
  - `mcp_exa_web_fetch_exa` → `urls: ["https://..."]` ✅，**不是** `url: "..."`
  - `mcp_tavily_tavily_extract` → `urls: ["https://..."]` ✅，**不是** `url: "..."`

- 🪤 **结果数量参数命名不统一**:
  - Exa: `numResults`
  - Brave: `count`
  - Tavily: `max_results`
  - web_search: `limit`
  - 记错就报 schema error

- 🪤 **language 参数**:
  - SearXNG MCP 用 `language: 'en' | 'zh-CN' | ...`
  - 其它引擎多数自动识别，无需显式传

---

## API key 修复指引（v3.7 更新）

```bash
# Exa (主力 #1): https://exa.ai
export EXA_API_KEY="your-key"

# Brave (主力 #2, 免费 2000次/月): https://brave.com/search/api/
export BRAVE_API_KEY="your-key"

# Tavily (深度调研, 免费 1000次/月): https://tavily.com/
export TAVILY_API_KEY="your-key"

# SearXNG (自建实例，仅保留抓取通道): http://127.0.0.1:32080
export SEARXNG_URL="http://127.0.0.1:32080"

# 配置后重启 MCP gateway
hermes gateway restart
```

### 验证 key 是否生效

```bash
# 查看 MCP 服务器在线状态
hermes mcp list

# 单点测试 Brave
hermes mcp call brave_search brave_web_search '{"query":"test","count":1}'

# 单点测试 Tavily
hermes mcp call tavily tavily_search '{"query":"test","max_results":1}'

# 检查 SearXNG 实例健康
curl http://127.0.0.1:32080/healthz
```

---

## SearXNG 特别说明（v3.7 关键变更）

- **search 通道 `mcp_searxng_searxng_web_search`** 🔧
  - 跨平台测试确认实例本身已损坏：Google dead / Bing degraded / DDG CAPTCHA
  - 换 MCP 客户端无效——根因在 SearXNG 实例配置
  - **v3.7 决定**: 从「默认起手」降级为「最后兜底」，仅在前 4 家全部命中 <3 条时启用

- **URL Read 通道 `mcp_searxng_web_url_read`** ⚠️
  - 实例的唯一保留价值
  - 仅作 Exa Fetch / Tavily Extract 失败时的备胎抓取通道
  - **不**用于搜索；**不**作为默认抓取首选

- **修复建议**（未来）:
  - 排查自建 SearXNG 实例的 engine 配置文件
  - 重置 Google / Bing engine token
  - 配置 captcha solver 或更换上游 engine 组合
  - 修复后可重新评估，但 v3.7 阶段以 Exa+Brave+Tavily 为主力

---

## 与 v3.6 对比

- ⬆️ Brave: 🔧 → ✅（API key 修复，升为主力 #2）
- ⬆️ Tavily: 🔧 → ✅（API key 修复，深度调研专用）
- ⬇️ SearXNG search: ⚠️ → 🔧（从「可用高噪声」降级为「实例损坏，仅兜底」）
- ↔️ SearXNG URL Read: ✅ → ⚠️（保留抓取通道，但优先级落后于 Exa Fetch / Tavily Extract）
- ↔️ Exa / web_search: ✅ → ✅（持续主力）
- 🆕 参数陷阱速查（pi-report 吸收：`urls: string[]` 数组格式）
- 🆕 验证方法（`hermes mcp list` + `curl healthz`）
