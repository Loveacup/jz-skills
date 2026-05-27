# 早新闻搜索工作流 v1.0

web-research-router 集成规范。早新闻搜索必须经此路由，不得直接调用单一引擎。

---

## 工具清单 (当前环境)

| 引擎 | 工具名 | 核心能力 | 最佳场景 |
|------|--------|---------|---------|
| **Exa** | `mcp_exa_web_search_exa` | 语义发现、英文高质量源 | 美国/国际/科技深度 |
| **Exa Fetch** | `mcp_exa_web_fetch_exa` | 全文提取 | 长文逐字引用 |
| **Tavily** | `mcp_tavily_tavily_search` | 实时 grounding、事实校验 | 价格/数据/声明验证 |
| **Brave** | `mcp_brave_search_brave_web_search` | 广覆盖、新闻快讯 | 中文源/突发新闻/市场快讯 |

> 三引擎全覆盖。Tavily 用于 grounding（事实确认），Brave 用于 coverage（广撒网），Exa 用于 discovery（深度发现）。

---

## 三路并行搜索 (delegate_task)

### Lane A: 中国媒体 (zh)

```
主引擎: Brave Search (broad coverage + locale-aware)
校验: Tavily (grounding on key claims)

查询模板 (Brave):
  1. "{今日中国政治要闻}" → max_results=8
  2. "{中国经济政策最新}" → max_results=6
  3. "{中国科技外交社会}" → max_results=6
  总目标 ≥15 源

校验 (Tavily):
  对价格/数据类声明 → Tavily 二次确认
  对重大政策声明 → 双源比对 (Brave + 人民网/新华社)

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json
结构: { date, engine_used: ["brave","tavily"], articles: [{title, url, source, snippet, category, cross_checked}] }
```

### Lane B: 美国+国际 (en)

```
主引擎: Exa (discovery mode — semantic, high-quality)
校验: Tavily (grounding on dates/numbers/claims)
补充: Brave (breaking news catch-up)

查询模板 (Exa):
  1. "US politics and economy news today {date}" → category:news, 8 results
  2. "international relations Ukraine Middle East today {date}" → 5 results
  3. "global technology and markets today {date}" → 5 results
  总目标 ≥18 源

提取: mcp_exa_web_fetch_exa 取 5-8 篇高信号正文
校验: Tavily search 验证关键数据点（GDP/就业/军费/制裁）

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-en.json
```

### Lane C: 市场+科技

```
主引擎: Brave (市场快讯 + 科技头条, 实时性优先)
深度: Exa (科技深度分析)
校验: Tavily (价格/数据 grounding)

查询模板 (Brave):
  1. "原油价格 黄金 美元指数 今日" → 3 results
  2. "美股 港股 A股 期货 最新行情" → 3 results
  3. "加密货币 bitcoin ethereum 价格" → 2 results
  4. "AI 人工智能 科技 最新突破" → 3 results

深度 (Exa):
  "technology breakthrough innovation today" → 3 results

校验 (Tavily):
  价格数据三引擎交叉比对: Brave → Exa → Tavily
  ±2% 以内 → 通过; 超过 → 标注 "数据冲突"
  加密货币价格取三源平均值

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-market.json
```

---

## delegate_task 调用示例

```
delegate_task(
  tasks=[
    {
      goal: "搜索中国媒体今日要闻，覆盖政治/经济/科技/外交/社会",
      context: "主引擎: Brave Search (mcp_brave_search_brave_web_search)
                校验: Tavily (mcp_tavily_tavily_search)
                Brave 查询模板见 references/search-workflow.md Lane A
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json
                结构: { date, engine_used, articles: [{title, url, source, snippet, category, cross_checked}] }
                ≥15 articles, 每篇含 source 字段",
      toolsets: ["web", "file", "terminal"]
    },
    {
      goal: "搜索英文主流媒体今日要闻，覆盖美国政治/经济/国际/科技",
      context: "主引擎: Exa (mcp_exa_web_search_exa discovery mode)
                校验: Tavily (mcp_tavily_tavily_search grounding)
                提取: mcp_exa_web_fetch_exa 5-8篇
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-en.json
                ≥18 articles, 结构同上",
      toolsets: ["web", "file", "terminal"]
    },
    {
      goal: "搜索市场数据（油价/美股/外汇/加密货币）+ 科技头条",
      context: "主引擎: Brave (mcp_brave_search_brave_web_search 快讯)
                深度: Exa (mcp_exa_web_search_exa 科技深度)
                校验: Tavily (mcp_tavily_tavily_search 价格三源比对)
                价格交叉: ±2%以内通过, 超过标冲突
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-market.json
                ≥8 articles + 市场数据段",
      toolsets: ["web", "file", "terminal"]
    }
  ]
)
```

---

## 三引擎分工矩阵

| 场景 | Brave | Exa | Tavily |
|------|-------|-----|--------|
| 中文政治新闻 | **主** (locale) | — | 校验 |
| 中文经济政策 | **主** | — | 数据校验 |
| 美国政治 | — | **主** (FT/WSJ) | 事实校验 |
| 国际地缘 | 快讯 | **主** (Reuters/AP) | 声明校验 |
| 科技深度 | — | **主** (MIT TR/Nature) | — |
| 油价/黄金 | 快讯 | 趋势分析 | **价格校验** |
| 美股/港股 | 快讯 | 分析 | **数据校验** |
| 加密货币 | 快讯 | — | **价格校验** |
| 突发新闻 | **主** (时效) | 补充 | 确认 |

---

## 持久化规则

| 规则 | 值 |
|------|-----|
| Workspace 根 | `~/.hermes/workspaces/morning-news-{YYYYMMDD}/` |
| 搜索产物 | `search/lane-{zh,en,market}.json` |
| 汇编产物 | `morning-news-{date}.md` |
| 渲染产物 | `output/morning-news-{date}.html` |
| PDF 产物 | `output/morning-news-{date}.pdf` |
| 昨日缓存 | `cache/{YYYYMMDD}/` |
| 目录权限 | `chmod 700`（仅 owner 可读写） |
| `.gitignore` | `*`（全部忽略，防止 secrets 入仓） |
| 保留策略 | 7 天 TTL，超期 `find ~/.hermes/workspaces/morning-news-* -mtime +7 -type d -exec rm -rf {} +` |

**严禁 scratch workspace**。

---

## 错误处理 & 重试矩阵

### 引擎级重试策略

| 引擎 | 最大重试 | 退避策略 | 单次超时 | 熔断条件 |
|------|---------|---------|---------|---------|
| Brave | 2 | 指数: 2s → 4s | 15s | 连续 3 次 429/5xx → 标记不可用 |
| Exa (search) | 2 | 指数: 3s → 6s | 20s | 连续 2 次超时 → 降级到 Brave |
| Exa (fetch) | 1 | 固定 2s | 30s | 单次超时 → 跳过该 URL，继续下一篇 |
| Tavily | 2 | 指数: 1s → 2s | 10s | 连续 5 次 429 → 标记不可用 |

### 场景级降级

| 场景 | 降级路径 |
|------|---------|
| 中文新闻 (Brave 故障) | Tavily 兜底 → Lane A 标注 "Brave 不可用，Tavily 单源" |
| 英文深度 (Exa 故障) | Brave + Tavily 并联 → Lane B 标注 "Exa 不可用" |
| 价格校验 (Tavily 故障) | Brave + Exa 双源比对 → Lane C 标注，不取均价 |
| 三路全败 | 中止，奏报父皇，不产出空白 PDF |

### 源级容错

| 错误 | 处理 |
|------|------|
| 单引擎故障 | 剩余引擎补偿，标注 "Brave/Exa/Tavily 不可用" |
| 单源 404 | 跳过，不阻塞整路 |
| 整路搜索失败 | 其他路填补，标注来源 |
| 三路全失败 | 中止，报告父皇 |
| 源数不达标 | <80% 目标 → 警告继续；<50% → 中止 |
| 价格三源冲突 (>2%) | 标注冲突，取中位值 |
