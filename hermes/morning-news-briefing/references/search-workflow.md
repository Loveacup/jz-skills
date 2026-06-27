# 早新闻搜索工作流 v2.0

web-research-router 集成规范。早新闻搜索必须经此路由，不得直接调用单一引擎。

**v2.0 变更**：Lane 命名与实际执行对齐。原 Lane C (市场+科技) 拆为 **Lane Mixed (市场)** 与 **Lane Tech (科技)** 两路，共四路并行。实际产物：`lane-zh.json`、`lane-en.json`、`lane-mixed.json`、`lane-tech.json` → `assembled-{date}.json`。

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

## 四路并行搜索 (delegate_task)

四路并行，每路独立落盘。来源目标：**各路 12-15 源，总计 50+**（与 SKILL.md Source Requirements ≥50 对齐）。

| Lane | 主题 | 主引擎 | 校验/补充 | 落盘 | 目标源数 |
|------|------|--------|-----------|------|---------|
| **zh** | 中国媒体 | Brave | Tavily | `lane-zh.json` | ≥12 |
| **en** | 美国+国际 | Exa | Tavily + Brave | `lane-en.json` | ≥15 |
| **mixed** | 市场数据 | Brave | Exa + Tavily | `lane-mixed.json` | ≥12 |
| **tech** | 科技新闻 | Exa | Brave + Tavily | `lane-tech.json` | ≥12 |

### Lane ZH: 中国媒体 (zh)

```
主引擎: Brave Search (broad coverage + locale-aware)
校验: Tavily (grounding on key claims)

查询模板 (Brave):
  1. "{今日中国政治要闻}" → max_results=6
  2. "{中国经济政策最新}" → max_results=5
  3. "{中国科技外交社会}" → max_results=5
  总目标 ≥12 源

校验 (Tavily):
  对价格/数据类声明 → Tavily 二次确认
  对重大政策声明 → 双源比对 (Brave + 人民网/新华社)

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json
结构: { date, lane: "zh", engine_used: ["brave","tavily"], articles: [{title, url, source, snippet, category, cross_checked}] }
```

### Lane EN: 美国+国际 (en)

```
主引擎: Exa (discovery mode — semantic, high-quality)
校验: Tavily (grounding on dates/numbers/claims)
补充: Brave (breaking news catch-up)

查询模板 (Exa):
  1. "US politics and economy news today {date}" → category:news, 6 results
  2. "international relations Ukraine Middle East today {date}" → 5 results
  3. "global affairs Asia-Pacific Africa LatAm today {date}" → 4 results
  总目标 ≥15 源

提取: mcp_exa_web_fetch_exa 取 5-8 篇高信号正文
校验: Tavily search 验证关键数据点（GDP/就业/军费/制裁）

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-en.json
结构: { date, lane: "en", engine_used: ["exa","tavily","brave"], articles: [...] }
```

### Lane MIXED: 市场数据 (mixed)

```
主引擎: Brave (市场快讯, 实时性优先)
深度: Exa (市场趋势分析)
校验: Tavily (价格/数据 grounding)

查询模板 (Brave):
  1. "原油价格 黄金 美元指数 今日" → 3 results
  2. "美股 港股 A股 期货 最新行情" → 4 results
  3. "加密货币 bitcoin ethereum 价格 今日" → 3 results
  总目标 ≥12 源

深度 (Exa):
  "global markets outlook oil equities forex today {date}" → 2 results

校验 (Tavily):
  价格数据三引擎交叉比对: Brave → Exa → Tavily
  ±2% 以内 → 通过; 超过 → 标注 "数据冲突", 取中位值
  加密货币价格取三源平均值

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-mixed.json
结构: { date, lane: "mixed", engine_used: ["brave","exa","tavily"], articles: [...], market_data: [{instrument, value, source, cross_checked}] }
```

### Lane TECH: 科技新闻 (tech)

```
主引擎: Exa (科技深度发现 — AI/芯片/互联网)
补充: Brave (科技快讯/产品发布)
校验: Tavily (技术声明/数据校验)

查询模板 (Exa):
  1. "AI artificial intelligence breakthrough today {date}" → category:news, 4 results
  2. "semiconductor chip industry news today {date}" → 4 results
  3. "big tech internet platform news today {date}" → 4 results
  总目标 ≥12 源

补充 (Brave):
  "AI 人工智能 芯片 科技 最新突破" → 3 results（中文科技源补充）

校验 (Tavily):
  对融资额/性能指标/发布日期类声明 → Tavily 二次确认

落盘: ~/.hermes/workspaces/morning-news-{date}/search/lane-tech.json
结构: { date, lane: "tech", engine_used: ["exa","brave","tavily"], articles: [...] }
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
                Brave 查询模板见 references/search-workflow.md Lane ZH
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json
                结构: { date, lane: 'zh', engine_used, articles: [{title, url, source, snippet, category, cross_checked}] }
                ≥12 articles, 每篇含 source 字段",
      toolsets: ["web", "file", "terminal"]
    },
    {
      goal: "搜索英文主流媒体今日要闻，覆盖美国政治/经济/国际地缘",
      context: "主引擎: Exa (mcp_exa_web_search_exa discovery mode)
                校验: Tavily (mcp_tavily_tavily_search grounding)
                补充: Brave (breaking news)
                提取: mcp_exa_web_fetch_exa 5-8篇
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-en.json
                ≥15 articles, 结构同上 (lane: 'en')",
      toolsets: ["web", "file", "terminal"]
    },
    {
      goal: "搜索市场数据（油价/美股/外汇/加密货币）",
      context: "主引擎: Brave (mcp_brave_search_brave_web_search 快讯)
                深度: Exa (mcp_exa_web_search_exa 市场趋势)
                校验: Tavily (mcp_tavily_tavily_search 价格三源比对)
                价格交叉: ±2%以内通过, 超过标冲突取中位值; 加密货币取三源均值
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-mixed.json
                ≥12 articles + market_data 数组 (lane: 'mixed')",
      toolsets: ["web", "file", "terminal"]
    },
    {
      goal: "搜索科技新闻（AI/芯片/互联网）",
      context: "主引擎: Exa (mcp_exa_web_search_exa 科技深度发现)
                补充: Brave (mcp_brave_search_brave_web_search 科技快讯 + 中文科技源)
                校验: Tavily (mcp_tavily_tavily_search 融资额/性能/发布日期校验)
                结果写入 ~/.hermes/workspaces/morning-news-{date}/search/lane-tech.json
                ≥12 articles, 结构同上 (lane: 'tech')",
      toolsets: ["web", "file", "terminal"]
    }
  ]
)
```

> Cron 模式下没有 gateway dispatcher，`delegate_task` 不可用 → 用 shell background jobs 替代（见 SKILL.md Mode A）。Interactive 模式下四路可由 `delegate_task` 或 Kanban Swarm 四 worker 承载（见 `references/kanban-swarm-workflow.md`）。

---

## 三引擎分工矩阵

| 场景 | Brave | Exa | Tavily | Lane |
|------|-------|-----|--------|------|
| 中文政治新闻 | **主** (locale) | — | 校验 | zh |
| 中文经济政策 | **主** | — | 数据校验 | zh |
| 美国政治 | 补充 | **主** (FT/WSJ) | 事实校验 | en |
| 国际地缘 | 快讯 | **主** (Reuters/AP) | 声明校验 | en |
| 油价/黄金 | 快讯 | 趋势分析 | **价格校验** | mixed |
| 美股/港股 | 快讯 | 分析 | **数据校验** | mixed |
| 加密货币 | 快讯 | — | **价格校验** | mixed |
| AI/人工智能 | 快讯 | **主** (MIT TR/Nature) | 数据校验 | tech |
| 芯片/半导体 | 快讯 | **主** | 数据校验 | tech |
| 互联网/平台 | 快讯 | **主** | — | tech |
| 突发新闻 | **主** (时效) | 补充 | 确认 | 各路 |

---

## 持久化规则

| 规则 | 值 |
|------|-----|
| Workspace 根 | `~/.hermes/workspaces/morning-news-{YYYYMMDD}/` |
| 搜索产物 | `search/lane-{zh,en,mixed,tech}.json` |
| 汇编中间产物 | `search/assembled-{date}.json`（四路去重合并） |
| 汇编产物 | `morning-news-{date}.md` |
| 渲染产物 | `output/morning-news-{date}.html` |
| PDF 产物 | `output/morning-news-{date}.pdf`（mobile + A4） |
| 音频产物 | `output/morning-news-{date}.mp3`（TTS, 见 tts-script-spec.md） |
| 昨日缓存 | `cache/{YYYYMMDD}/` |
| 目录权限 | `chmod 700`（仅 owner 可读写） |
| `.gitignore` | `*`（全部忽略，防止 secrets 入仓） |
| 保留策略 | 7 天 TTL，超期 `find ~/.hermes/workspaces/morning-news-* -mtime +7 -type d -exec rm -rf {} +` |

**严禁 scratch workspace**。

---

## 汇编去重 (assembled-{date}.json)

四路落盘后，汇编层读取全部 lane JSON → 去重 → 写 `assembled-{date}.json`。

| 规则 | 说明 |
|------|------|
| **去重键** | URL 规范化（去 query/fragment）+ 标题语义近似 |
| **跨语言同事件** | zh/en 报道同一事件 → 合并为一个 event，保留双源 [sN] |
| **保留独立性** | ⚠️ 去重 ≠ 折叠新闻数。同事件的多源合并为一条 event，但**不同事件不得 fusion**。📰 今日要闻须保留 ≥15 独立条目（见 SKILL.md Sentinel #2） |
| **源编号** | 去重后统一编号 S01–SNN，回填到 markdown `📰 来源清单` |

> 历史教训：50 源搜索 → 汇编去重到 15 event → 渲染滤到 8 条。去重必须保留独立事件，渲染层不得二次截断 📰 今日要闻。

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
| 中文新闻 (Brave 故障) | Tavily 兜底 → Lane ZH 标注 "Brave 不可用，Tavily 单源" |
| 英文深度 (Exa 故障) | Brave + Tavily 并联 → Lane EN 标注 "Exa 不可用" |
| 市场价格 (Tavily 故障) | Brave + Exa 双源比对 → Lane MIXED 标注，不取均价 |
| 科技深度 (Exa 故障) | Brave + Tavily 并联 → Lane TECH 标注 "Exa 不可用" |
| 单路全败 | 其他三路填补，标注缺失维度 |
| 三路及以上全败 | 中止，奏报父皇，不产出空白 PDF |

### 源级容错

| 错误 | 处理 |
|------|------|
| 单引擎故障 | 剩余引擎补偿，标注 "Brave/Exa/Tavily 不可用" |
| 单源 404 | 跳过，不阻塞整路 |
| 整路搜索失败 | 其他路填补，标注来源 |
| 三路及以上全失败 | 中止，报告父皇 |
| 源数不达标 | 单路 <80% 目标 → 警告继续；总计 <50% 目标(即 <25 源) → 中止 |
| 价格三源冲突 (>2%) | 标注冲突，取中位值 |
