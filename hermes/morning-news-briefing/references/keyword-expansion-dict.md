# Keyword Expansion Dictionary v1.0 (morning-news-briefing v4.0)

> **Read when:** 三 lane (zh / en+intl / market+tech) 跑搜索前，Step 2 query-decomposition 需展开 DESCRIPTORS 实体。每个 lane 引一份对应字典。
> **Source:** `~/research-tmp/news-aggregator-skill/scripts/daily_briefing.py` (profile keywords, verbatim) + `~/.hermes/skills/research/web-research-router/references/query-decomposition.md` (五类实体框架)
> **Sibling refs:** `./search-workflow.md` (查询主流程) · `./sources.json` (信源清单)

---

## 一、五类实体框架（与 router query-decomposition 对齐）

源自 `ldr-circuit/src/local_deep_research/advanced_search_system/questions/browsecomp_question.py:73-94`：

- **TEMPORAL**: 时间维度（`"2026-05-28"` / `"今日"` / `"24小时"` / `"近一周"`）
- **NUMERICAL**: 数字 / 阈值（价格、版本号、tokens、百分比）
- **NAMES**: 命名实体（人名、公司、产品；中文要 quoted）
- **LOCATIONS**: 地理（北京 / 上海 / Washington D.C. / Taiwan Strait）
- **DESCRIPTORS**: 抽象描述符（**本字典核心：每 lane 一组**）

本字典只填 DESCRIPTORS；TEMPORAL/NAMES/LOCATIONS 由每日动态生成（执行时由当日素材拼装）。

---

## 二、Lane 字典

### Lane A: 中国媒体 (zh) — DESCRIPTORS 字典

#### zh-politics（中国政治要闻）
```
关键词: 习近平,李强,政治局,中央,部署,会议,政策,法规,改革,反腐
sub-query 模板:
  - "{今日} {keyword} {LOCATIONS}"        e.g., "今日 政治局 北京"
  - "{TEMPORAL} 中国政府 {keyword}"
触发: 中文政治 / 政府 / 外交新闻搜索
```

#### zh-economy（中国经济）
```
关键词: GDP,CPI,PPI,人民币,汇率,股市,A股,深证,沪指,房地产,出口,进口,贸易,关税,基建,新基建,财报,营收,上市,IPO,基金,投资
sub-query 模板:
  - "{TEMPORAL} 中国 {keyword}"
  - "中国 {keyword} {NUMERICAL}"          e.g., "中国 GDP 2026"
触发: 中文经济 / 金融 / 贸易新闻搜索
备注: 后半段 "财报,营收,上市,IPO,基金,投资" 直接抄自 cclank daily_briefing.py:53 (fetch_36kr finance profile)
```

#### zh-tech（中国科技）
```
关键词: 国产芯片,AI大模型,DeepSeek,通义,文心,智谱,新能源车,光伏,氢能,机器人,数字人民币,融资,首发,独角兽,创投
sub-query 模板:
  - "{NAMES} {TEMPORAL}"                  e.g., "DeepSeek 2026"
  - "中国 {keyword} 新闻"
触发: 中文科技 / AI / 产业 / 创投新闻搜索
备注: "融资,首发,独角兽,创投" 抄自 cclank daily_briefing.py:84 (startups profile)
```

#### zh-society（中国社会）
```
关键词: 民生,教育,医疗,养老,人口,生育,婚姻,房价,就业,延迟退休
sub-query 模板:
  - "{TEMPORAL} 中国 {keyword}"
  - "{LOCATIONS} {keyword}"
触发: 中文社会民生新闻搜索
```

---

### Lane B: 美国 + 国际 (en+intl) — DESCRIPTORS 字典

#### us-politics
```
关键词: Trump,Biden,Congress,Senate,House,Supreme Court,executive order,bill,nomination,impeachment,subpoena
sub-query 模板:
  - "{NAMES} {TEMPORAL}"
  - "U.S. {keyword} today"
触发: U.S. domestic / Congress / White House 新闻
```

#### us-economy
```
关键词: Economy,Inflation,Fed,Stock,Finance,FOMC,interest rate,CPI,jobs report,GDP,Treasury,dollar,tariff,trade deficit
sub-query 模板:
  - "{NAMES} {TEMPORAL}"                  e.g., "Fed FOMC 2026-05"
  - "U.S. {keyword} {NUMERICAL}"
触发: U.S. economy / Fed / market-adjacent 新闻
备注: 前半段 "Economy,Inflation,Fed,Stock,Finance" 抄自 cclank daily_briefing.py:47 (finance market_overview)
```

#### us-tech
```
关键词: AI,LLM,GPT,DeepSeek,Github Copilot,Claude,OpenAI,Anthropic,Google DeepMind,Meta,NVIDIA,chip,semiconductor,Transformer,Diffusion,Model,RAG
sub-query 模板:
  - "{NAMES} {TEMPORAL}"                  e.g., "Anthropic 2026-05"
  - "{keyword} benchmark {NUMERICAL}"
触发: AI / tech / chip / model release 新闻
备注: "AI,LLM,GPT,DeepSeek,Github Copilot,Claude,OpenAI" 抄自 cclank daily_briefing.py:33 (hn_ai profile);
       "AI,LLM,Transformer,Diffusion,Model,RAG" 抄自 cclank daily_briefing.py:71 (ai_frontier profile)
```

#### intl-conflict
```
关键词: Ukraine,Russia,Iran,Israel,Gaza,Hormuz,Red Sea,Taiwan,South China Sea,North Korea
sub-query 模板:
  - "{LOCATIONS} {TEMPORAL}"
  - "{LOCATIONS} conflict {NUMERICAL}"
触发: 国际冲突 / 地缘新闻
```

#### intl-economy
```
关键词: ECB,BoE,BoJ,euro,yen,pound,emerging markets,sovereign debt,IMF,World Bank,WTO
sub-query 模板:
  - "{NAMES} {TEMPORAL}"
  - "{LOCATIONS} {keyword}"
触发: 国际经济 / 央行 / 跨境贸易新闻
```

---

### Lane C: 市场 + 科技 (mixed) — DESCRIPTORS 字典

#### market-equities
```
关键词: S&P 500,Nasdaq,Dow,NYSE,SSE,HKEX,Nikkei,FTSE,DAX,earnings,IPO,buyback
sub-query 模板:
  - "{NAMES} earnings {TEMPORAL}"
  - "{LOCATIONS} stock market {NUMERICAL}"
触发: 股票 / 市场 / earnings 新闻
```

#### market-crypto
```
关键词: Bitcoin,BTC,Ethereum,ETH,Crypto,Blockchain,Web3,DeFi,stablecoin,USDT,USDC,ETF,比特币,加密货币
sub-query 模板:
  - "{NAMES} {NUMERICAL} {TEMPORAL}"      e.g., "Bitcoin 100000 2026"
  - "{keyword} ETF {LOCATIONS}"
触发: 加密 / 区块链 / on-chain 新闻
备注: "Bitcoin,Crypto,Ethereum,Blockchain,Web3,DeFi" 抄自 cclank daily_briefing.py:60 (crypto profile);
       "比特币,加密货币" 抄自 daily_briefing.py:61 (wallstreetcn crypto)
```

#### market-commodities
```
关键词: oil,Brent,WTI,gold,silver,copper,lithium,nickel,rare earth,LNG,natural gas
sub-query 模板:
  - "{keyword} price {TEMPORAL}"
  - "{LOCATIONS} {keyword} output"
触发: 大宗商品 / 能源新闻
```

#### market-forex
```
关键词: USD,EUR,JPY,CNY,GBP,AUD,DXY,carry trade,intervention,SAFE
sub-query 模板:
  - "{keyword} {NUMERICAL} {TEMPORAL}"
  - "{LOCATIONS} central bank {keyword}"
触发: 外汇 / 央行干预 / 跨境资本流动新闻
```

---

## 三、Sub-query 生成示例（端到端）

**示例 1 (Lane A / zh-economy):**
- broad query: "今日 A股"
- DESCRIPTORS: `A股,沪指,深证`
- 当日 NAMES: `央行,证监会` · TEMPORAL: `2026-05-28`
- sub-queries: `"2026-05-28 中国 A股"`, `"中国 沪指 央行"`, `"中国 证监会 IPO"`

**示例 2 (Lane B / us-tech):**
- broad query: "AI breakthroughs today"
- DESCRIPTORS: `AI,LLM,Claude,Anthropic`
- 当日 NAMES: `Anthropic` · TEMPORAL: `2026-05`
- sub-queries: `"Anthropic 2026-05"`, `"Claude benchmark 2026"`, `"LLM model release 2026-05-28"`

**示例 3 (Lane B / intl-conflict):**
- broad query: "Middle East update"
- DESCRIPTORS: `Iran,Israel,Gaza,Hormuz`
- 当日 LOCATIONS: `Gaza` · TEMPORAL: `2026-05-28`
- sub-queries: `"Gaza 2026-05-28"`, `"Iran Israel conflict"`, `"Hormuz strait shipping"`

**示例 4 (Lane C / market-crypto):**
- broad query: "BTC moves"
- DESCRIPTORS: `Bitcoin,BTC,ETF`
- 当日 NUMERICAL: `100000` · TEMPORAL: `近24小时`
- sub-queries: `"Bitcoin 100000 2026"`, `"BTC ETF inflow 2026-05"`, `"比特币 加密货币 监管"`

**示例 5 (Lane A / zh-tech):**
- broad query: "国产 AI 进展"
- DESCRIPTORS: `DeepSeek,通义,文心,AI大模型`
- 当日 NAMES: `DeepSeek` · TEMPORAL: `2026-05`
- sub-queries: `"DeepSeek 2026"`, `"中国 AI大模型 新闻"`, `"通义 文心 发布"`

---

## 四、字典维护规则

- 每月 review 一次；新增 keyword 必须 audit step 跑一周 dry-run 回归
- 不超过 lane 4 个 DESCRIPTORS 字典；中英字典分开（`zh-*` 与 `us-*`/`intl-*`/`market-*`）不混
- 含空格的 keyword 拼 query 时必须双引号包裹（参考 cclank fetch_news.py:110 `quoted_keywords`）
