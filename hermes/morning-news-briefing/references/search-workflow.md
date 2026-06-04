# 早新闻搜索工作流 v3.0 (web-research-router v3.9 对齐)

> **Read when:** 早新闻三 lane 搜索阶段。本文档定义 morning-news 如何经 web-research-router v3.9 取数。
> **依赖:** web-research-router v3.9 — `~/.hermes/skills/research/web-research-router/SKILL.md`
> **变更:** v1.0 (各 lane 单引擎) → v2.0 (SearXNG 多引擎广扫起手) → **v3.0 (对齐 WRR v3.9：SearXNG 实例已损坏降兜底；三 lane 按场景分工 Brave/Exa 双主力发现 + Exa Fetch/Tavily Extract 抓取；aihot 仅辅助兜底)**

---

## 0. 核心原则 — fail-loud（高于一切特性）

- **未成功抓取的 URL 不得进引用**；每个数字/事实必须挂在 `extracted_quotes[]` 的某条 verbatim quote 上。
- **缺源即拒发**，不产空白 PDF。
- **SearXNG 实例已损坏**（Google 失效 / Bing 降级 / DDG CAPTCHA，WRR v3.9 跨平台判定）→ **绝不作起手**，仅 WRR 内部最后兜底。
- **`web_extract` 已弃用**（环境网络策略拦截所有 HTTPS URL）→ 禁止用于抓取。

---

## 1. 工具清单（对齐 WRR v3.9 `tool-names.md`）

| 工具 | 角色 | 何时用 |
|---|---|---|
| `mcp_brave_search_brave_web_search` | **发现主力**（时效 / locale-aware / 独立索引） | 中文新闻 + 突发 + 市场快讯起手；`count` 参数 |
| `mcp_exa_web_search_exa` | **发现主力**（语义精准 / 跨语言召回） | 英文 / 国际 / 科技深度；"哪些公司宣布了 X"；`numResults` 参数 |
| `mcp_exa_web_fetch_exa` | **抓取主力** | URL → 正文（`urls: string[]` **数组**） |
| `mcp_tavily_tavily_extract` | **抓取主力**（结构化，质量完胜 SearXNG URL Read） | URL → 正文（`urls: string[]` **数组**） |
| `mcp_tavily_tavily_search` | grounding | 价格 / 数字 / 口径核对；`max_results` 参数 |
| aihot API（🔶 辅助，经 WRR，**待验证**） | 中文 AI 资讯辅助源 | Lane C 仅兜底：Brave+Exa 都失败时；详见 WRR `references/aihot-source.md`（P2 待建） |
| `mcp_searxng_web_url_read` | 抓取**备胎** | **仅** Exa Fetch + Tavily Extract 都失败时；`url: string` |

> ⚠️ **工具名修正**：v2.0 把 Brave/Exa 误写为 `mcp_brave_brave_web_search` / `mcp_exa_exa_web_search`（调不通）。以上为 WRR `tool-names.md` 的正确名。
> 🪤 **参数陷阱**：search 类用 `query: string`；fetch/extract 类用 `urls: string[]` **数组**（误传单字符串 → InputValidationError）。

---

## 2. 通用搜索流程（4 步）

```
Step 1: 发现（按 lane 选主力引擎，经 web-research-router 路由）
  → 中文     → Brave (locale-aware) 主 + Exa 语义补
  → 英文     → Exa 语义 主 + Brave 独立交叉
  → 科技/AI  → Brave 快讯 + Exa 深度（aihot 仅兜底：Brave+Exa 都不可用时，经 WRR curl pre-flight 通过后启用）
  ✗ 不调 SearXNG 起手（实例已损坏）

Step 2: query-decomposition 实体分解
  → 见 ~/.hermes/skills/research/web-research-router/references/query-decomposition.md
  → Read when: 原 query 实体密度高（人/地/时/数）
  → 按 5 类实体拆 sub-query：
     TEMPORAL    (2026-XX-XX / 今日 / 24h)
     NUMERICAL   (价格 / GDP / 涨跌幅)
     NAMES       (人名 / 公司 / 机构)
     LOCATIONS   (国家 / 城市)
     DESCRIPTORS (主题词，引用 ../references/keyword-expansion-dict.md)

Step 3: fetch-extract 抽取 verbatim quote（杠杆最高的一步）
  → 见 ~/.hermes/skills/research/web-research-router/references/fetch-extract-pattern.md
  → 每条候选 URL 跑 mcp_exa_web_fetch_exa 或 mcp_tavily_tavily_extract（urls 数组）+ extractor prompt
  → 产出 extracted_quotes[]: {text, focus, char_offset}
  → 抓取失败 → SearXNG URL Read 备胎；再失败 → 该源标 evidence_status="unread"，禁止进引用（fail-loud）

Step 4: cross-check（按需触发，不要全跑）
  → 价格/数据 claim   → Tavily grounding
  → 本地化/突发       → Brave
  → 语义精准/"哪些 X" → Exa
  → 政策双源比对      → Brave（新华社 vs 人民网 vs 路透）
```

---

## 3. 三路并行

### Lane A: 中国媒体 (zh)

**目标:** ≥15 sources；覆盖政治/经济/科技/外交/社会

```
1. 发现: Brave (locale-aware 主力，直接中文 query) + Exa 语义补
   query = "今日中国 政治 经济 科技 24小时 {date}"
   ✗ 不用 SearXNG；中文新闻发现不靠 Tavily search（实测时效差，返回旧页）

2. query-decomposition 分解 sub-query
   字典: ../references/keyword-expansion-dict.md (zh-politics / zh-economy)
   - TEMPORAL / NAMES（当日热点人物，按字典）/ LOCATIONS / DESCRIPTORS

3. 对 top-5 URL 跑 fetch-extract:
   mcp_exa_web_fetch_exa / mcp_tavily_tavily_extract → extractor prompt
   → extracted_quotes[] 入 source_map

4. Cross-check:
   - 价格/数据 claim → Tavily (mcp_tavily_tavily_search)
   - 政策声明       → Brave 双源比对 (新华社 / 人民网)
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-zh.json`

```json
{
  "date": "{date}",
  "lane": "zh",
  "engines": ["brave", "exa", "tavily"],
  "articles": [
    {
      "citation_id": "zh-001",
      "title": "...",
      "url": "...",
      "source": "新华社",
      "published_at": "...",
      "extracted_quotes": [{"text": "...", "focus": "policy", "char_offset": 1234}],
      "evidence_status": "extracted",
      "cross_checked": true
    }
  ]
}
```

> `evidence_status`: `extracted`（已抓到 quote）/ `unread`（抓取失败，禁止进引用）。

---

### Lane B: 美国 + 国际 (en)

**目标:** ≥18 sources；US domestic/economy/Congress/tech + Russia-Ukraine/Asia-Pacific/Africa/LatAm

```
1. 发现: Exa 语义 主力 + Brave 独立索引交叉
   query = "US politics economy Congress tech {date} 24h
            Russia Ukraine Asia Pacific Africa Latin America"

2. query-decomposition: 字典 en-politics / en-intl
   - TEMPORAL / NAMES（US 政客 / 国际领导人）/ LOCATIONS / DESCRIPTORS

3. 对 top-6 URL 跑 fetch-extract:
   mcp_exa_web_fetch_exa / mcp_tavily_tavily_extract → extractor prompt

4. Cross-check:
   - 战况/伤亡数字  → Tavily grounding
   - 突发/地名定位  → Brave
   - "哪些国家表态" → Exa 语义查
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-en.json`（schema 同 Lane A）

---

### Lane C: 市场 + 科技 (mixed)

**目标:** ≥8 sources；oil/equities/forex/crypto + AI/tech

```
1. 发现:
   - Brave 快讯 (mcp_brave_search_brave_web_search) — 市场广度
   - Exa 语义 (mcp_exa_web_search_exa) — 科技深度
   - 🔶 aihot API 仅兜底（Brave+Exa 双双不可达时，经 WRR curl pre-flight 通过后启用；详见 WRR aihot-source.md，P2 待建）
   query = "oil price equities forex crypto AI tech earnings {date} 24h Brent WTI S&P Nasdaq BTC ETH"

2. query-decomposition:
   - NUMERICAL（涨跌幅 / 价格区间 / market cap）/ NAMES（NVIDIA / OpenAI / 特定 token）/ DESCRIPTORS

3. 对 top-4 URL 跑 fetch-extract（市场数据强制 verbatim quote）

4. Cross-check:
   - 所有价格 claim → Tavily grounding（强制；±2% 内通过，超过标"数据冲突"取中位）
   - 突发科技发布   → Brave + Exa 双补强
```

**落盘:** `~/.hermes/workspaces/morning-news-{date}/search/lane-mixed.json`（schema 同 Lane A）

---

## 4. 降级策略（对齐 WRR v3.9）

| 故障 | 检测 | 降级 |
|---|---|---|
| 主力引擎(Brave/Exa)单家故障 | 单 lane 标错跳过 | 另一主力 + `web_search` 兜底；**最后**才 SearXNG search |
| aihot 不可达（无 SLA，未测试） | curl pre-flight 失败（预期常态） | 标 Lane C 来源缺口，靠其它 lane 填补；不阻塞（aihot 仅在 Brave+Exa 双败后才触达，回退无对象，故不回退 Brave+Exa） |
| 抓取全失败 | Exa Fetch + Tavily Extract + SearXNG URL Read 都败 | 该源标 `evidence_status="unread"`，**禁止进引用**（fail-loud） |
| 单 lane 全失败 | 三 lane 互不阻塞 | 其它 lane 继续，标注来源缺口 |
| 三 lane 全失败 | — | 中止本次奏报，写 audit log 标 `search-skip`，不产空白 PDF |

---

## 5. 与 WRR v3.9 references 交叉链接

| Router reference | 何时调用 |
|---|---|
| `tool-names.md` | 工具正确名 + 参数（`urls` 数组陷阱） |
| `research-modes.md` | 选 mode（默认 `research`，重大事件升 deep loop） |
| `query-decomposition.md` | Step 2 实体分解 |
| `fetch-extract-pattern.md` | **Step 3 verbatim quote 抽取（杠杆最高）** |
| `vertical-domains.md` | News / Chinese content 域的引擎映射 |
| `aihot-source.md` | Lane C aihot 🔶 辅助兜底（待验证+待建，P2） |
| `anti-refusal-prompt.md` | Assembly 写正文遇 hedge phrase 时改写 |
| `source-map-schema.md` | 落盘 schema 必须含 `citation_id` + `extracted_quotes[]` |

完整路径前缀: `~/.hermes/skills/research/web-research-router/references/`

---

## 6. 常见错误

- ❌ **SearXNG 起手**（实例已损坏，WRR v3.9 已判定，绝不起手）
- ❌ 直接 `web_search` 跳过 WRR（漏独立索引交叉 + 漏 verbatim quote 锚）
- ❌ **`web_extract` 抓取**（已弃用，拦截所有 HTTPS → 伪引用 → 幻觉数字）
- ❌ Brave/Exa 工具名写错（用 `tool-names.md` 正确名；fetch/extract 用 `urls: []` 数组）
- ❌ fetch-extract 跳过 → 正文里出现没 verbatim quote 锚的"分析"
- ❌ **抓取失败的源进了引用**（违反 fail-loud；必须标 `unread` 并剔除）
- ❌ Cross-check 全跑（浪费成本）：只在数据/价格/政策类 claim 触发
- ❌ 价格类 claim 未走 Tavily grounding 就入正文
- ❌ 三 lane 串行跑（必须并行 fan-out）

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
