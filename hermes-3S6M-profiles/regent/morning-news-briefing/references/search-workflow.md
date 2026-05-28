# 早新闻搜索工作流 v2.0 (web-research-router v3.2.0 对齐)

> **Read when:** 早新闻三 lane 搜索阶段。本文档定义 morning-news 如何与 web-research-router v3.2.0 整合。
> **依赖:** web-research-router v3.2.0 — `~/.hermes/skills/research/web-research-router/SKILL.md`
> **变更:** v1.0 (Brave/Exa/Tavily 各 lane 单引擎) → v2.0 (SearXNG 多引擎广扫为默认起手，Brave/Exa/Tavily 降为 cross-check 补强)

---

## 1. 工具清单

| 工具 | 角色 | 何时用 |
|---|---|---|
| `mcp_searxng_searxng_web_search` | **广扫（默认起手）** | Step 1，所有 lane 起手；单次拿到 6+ 通用引擎 + 学术 + 代码 + 中文 (Bilibili) |
| `mcp_searxng_web_url_read` | **verbatim 抽取** | Step 3，对 top-N 候选 URL 拉正文 |
| `mcp_brave_brave_web_search` | cross-check 补强 | 本地化/突发/政策双源比对 |
| `mcp_exa_exa_web_search` | cross-check 补强 | 语义精准（"哪些公司宣布了 X"） |
| `mcp_tavily_tavily_search` | cross-check 补强 | 价格/数据 grounding |

---

## 2. 通用搜索流程（4 步）

```
Step 1: SearXNG 广扫（默认起手）
  → mcp_searxng_searxng_web_search(query, categories=["general","news"])
  → 单次返回 6+ 引擎结果

Step 2: query-decomposition 实体分解
  → 见 ~/.hermes/skills/research/web-research-router/references/query-decomposition.md
  → Read when: 原 query 实体密度高（人/地/时/数）
  → 按 5 类实体拆 sub-query：
     TEMPORAL    (2026-05-28 / 今日 / 24h)
     NUMERICAL   (价格 / GDP / 涨跌幅)
     NAMES       (人名 / 公司 / 机构)
     LOCATIONS   (国家 / 城市)
     DESCRIPTORS (主题词，引用 ../references/keyword-expansion-dict.md)

Step 3: fetch-extract 抽取 verbatim quote
  → 见 ~/.hermes/skills/research/web-research-router/references/fetch-extract-pattern.md
  → Read when: 拿到 top-N 候选 URL，准备入 source_map（杠杆最高的一步）
  → 每条候选 URL 跑 mcp_searxng_web_url_read + extractor prompt
  → 产出 extracted_quotes[]: {text, focus, char_offset}

Step 4: cross-check（按需触发，不要全跑）
  → 价格/数据 claim → Tavily grounding
  → 本地化/突发     → Brave
  → 语义精准       → Exa
  → 政策双源比对   → Brave（新华社 vs 人民网 vs 路透）
```

---

## 3. 三路并行

### Lane A: 中国媒体 (zh)

**目标:** ≥15 sources；覆盖政治/经济/科技/外交/社会

**主流程 (v2.0):**

```
1. SearXNG 广扫:
   query = "今日中国 政治 经济 科技 24小时 2026-05-28"
   categories = ["general","news"], language = "zh"
   —— 多引擎 + Bilibili 中文覆盖

2. query-decomposition 分解 sub-query
   字典: ../references/keyword-expansion-dict.md (zh-politics / zh-economy)
   - TEMPORAL:    "2026-05-28" / "今日" / "24小时"
   - NAMES:       当日热点人物（习近平 / 李强 / 何立峰，按字典）
   - LOCATIONS:   北京 / 上海 / 深圳 / 香港
   - DESCRIPTORS: zh-politics + zh-economy 字典关键词

3. 对 top-5 URL 跑 fetch-extract:
   mcp_searxng_web_url_read → extractor prompt
   → extracted_quotes[] 入 source_map

4. Cross-check 触发:
   - 价格/数据 claim → Tavily (mcp_tavily_tavily_search)
   - 政策声明       → Brave 双源比对 (新华社 / 人民网)
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json`

```json
{
  "date": "2026-05-28",
  "lane": "zh",
  "engines": ["searxng", "tavily"],
  "articles": [
    {
      "citation_id": "zh-001",
      "title": "...",
      "url": "...",
      "source": "新华社",
      "extracted_quotes": [{"text": "...", "focus": "policy", "char_offset": 1234}],
      "evidence_status": "extracted",
      "cross_checked": true
    }
  ]
}
```

---

### Lane B: 美国 + 国际 (en)

**目标:** ≥18 sources；US domestic/economy/Congress/tech + Russia-Ukraine/Asia-Pacific/Africa/LatAm

**主流程 (v2.0):**

```
1. SearXNG 广扫:
   query = "US politics economy Congress tech 2026-05-28 24h
            Russia Ukraine Asia Pacific Africa Latin America"
   categories = ["general","news"], language = "en"

2. query-decomposition 分解 sub-query
   字典: ../references/keyword-expansion-dict.md (en-politics / en-intl)
   - TEMPORAL:    "2026-05-28" / "today" / "past 24 hours"
   - NAMES:       当日 US 政客 / 国际领导人（按字典）
   - LOCATIONS:   Washington / Kyiv / Taipei / Brussels / Lagos
   - DESCRIPTORS: Congress / sanctions / election / coup / ceasefire

3. 对 top-6 URL 跑 fetch-extract:
   mcp_searxng_web_url_read → extractor prompt
   → extracted_quotes[]

4. Cross-check 触发:
   - 战况/伤亡数字  → Tavily grounding
   - 突发/地名定位  → Brave
   - "哪些国家表态" → Exa 语义查
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-en.json`（schema 同 Lane A）

---

### Lane C: 市场 + 科技 (mixed)

**目标:** ≥8 sources；oil/equities/forex/crypto + AI/tech

**主流程 (v2.0):**

```
1. SearXNG 广扫:
   query = "oil price equities forex crypto AI tech earnings
            2026-05-28 24h Brent WTI S&P Nasdaq BTC ETH"
   categories = ["general","news","science"]

2. query-decomposition:
   - NUMERICAL:   涨跌幅 / 价格区间 / market cap
   - NAMES:       NVIDIA / OpenAI / Tesla / Apple / 特定 token
   - DESCRIPTORS: earnings / IPO / model release / regulation

3. 对 top-4 URL 跑 fetch-extract（市场数据强制 verbatim）

4. Cross-check 触发:
   - 所有价格 claim → Tavily grounding（强制）
   - 突发科技发布   → Brave + Exa 双补强
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-mixed.json`（schema 同 Lane A）

---

## 4. SearXNG 不可达降级策略

| 故障 | 检测 | 降级 |
|---|---|---|
| SearXNG 不可达 | `curl --max-time 3 http://127.0.0.1:32080/` 失败 | 三 lane 各回退到 v1.0 单引擎链：A→Brave；B→Exa；C→Brave + Tavily |
| 单引擎超时 | 单 lane 标错跳过 | 其它两 lane 不阻塞，继续 |
| 全 SearXNG + 全补强引擎都败 | 三 lane 全 failed | 中止本次奏报，写入 audit log 标 `search-skip` |

---

## 5. 与 router v3.2 references 交叉链接

| Router reference | 何时调用 |
|---|---|
| `research-modes.md` | 选 mode（默认 `research`，重大事件升 `deep`） |
| `query-decomposition.md` | Step 2 实体分解 |
| `fetch-extract-pattern.md` | **Step 3 verbatim quote 抽取（杠杆最高）** |
| `anti-refusal-prompt.md` | Assembly 阶段写正文遇 hedge phrase 时改写 |
| `source-map-schema.md` | 落盘 schema 必须含 `citation_id` + `extracted_quotes[]` |

完整路径前缀: `~/.hermes/skills/research/web-research-router/references/`

---

## 6. 常见错误

- ❌ 直接 `web_search` 跳过 router（违反 v3.2 强制路由）
- ❌ 单引擎一刀切（SearXNG 默认起手原则被违反）
- ❌ fetch-extract 跳过 → 正文里出现没 verbatim quote 锚的"分析"
- ❌ Cross-check 全跑（浪费成本）：**只在数据/价格/政策类 claim 触发**
- ❌ extract 出的 quote 不入 `source_map.extracted_quotes[]`
- ❌ 三 lane 串行跑（必须并行 fan-out）
- ❌ 价格类 claim 未走 Tavily grounding 就入正文

---

## 7. 持久化路径

```
~/.hermes/workspaces/morning-news-{date}/
├── search/
│   ├── lane-zh.json       # Lane A 输出
│   ├── lane-en.json       # Lane B 输出
│   └── lane-mixed.json    # Lane C 输出
└── audit/
    └── search-trace.log   # 引擎调用 + 降级事件
```
