---
name: news-assembly
description: |
  Use when assembling multi-source search results into a structured, deduplicated, importance-ranked briefing skeleton. Does: dedup + cross-source event-merge, continuity detection vs prior briefing, importance scoring + top-k, configurable section structuring, citation anchoring (fail-loud). 通用「简报编辑大脑」,被 morning-news-briefing 等简报 skill 复用。
  Triggers: assemble briefing, 简报汇编, 去重合并, 事件归并, 简报骨架.
  DO NOT use for: 搜索(用 web-research-router)、渲染 PDF(用 pdf)、分析层/前提推理结论格式化(调用方处理)、事实验证(用 source-verification)。
version: 0.1.0
author: Hermes Agent (v0.1 — 从 morning-news-briefing 抽出的通用编辑大脑)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [briefing, assembly, dedup, continuity, scoring, citation, reusable]
    related_skills: [web-research-router, morning-news-briefing, source-verification, pdf]
---

# News Assembly v0.1 — 简报编辑大脑

把多源搜索产出(带 citation + verbatim quote)加工成**结构化、去重、按重要性排序、按板块组织**的简报骨架。**纯机械编辑** —— 不做搜索、不做分析判断、不做渲染、不做验证。被 morning-news-briefing 等简报 skill 复用。

## 🔀 何时用 / 不用

| ✅ 做 | ❌ 不做(谁做) |
|---|---|
| 去重 + 跨源事件合并 | 搜索(`web-research-router`) |
| 连续性检测(vs 昨日成品) | 分析层 🔍 前提→推理→结论(调用方,如早新闻 `analysis-format`) |
| 重要性打分 + 每板块 top-k | 渲染 PDF(`pdf` skill) |
| 板块结构化(参数化) | 事实验证(`source-verification`) |
| citation 锚定 + fail-loud | 去 AI 味(`de-slop`) |

> **核心原则**:assembly 只**组织事实**,不**判断事实**。判断(分析层)是调用方的护城河,留给调用方。

## 输入契约

**搜索产物** — `search/lane-*.json`(web-research-router / 调用方 search-workflow 产出):
```json
{ "lane": "zh", "engines": ["brave","exa"], "articles": [
  { "citation_id": "zh-001", "title": "...", "url": "...", "source": "新华社",
    "published_at": "ISO8601", "extracted_quotes": [{"text":"...","focus":"..."}],
    "evidence_status": "extracted" }
]}
```

**config**(调用方传):
- `sections`: `[{key, name, match_hints[]}]` — 参数化板块(早新闻传 头条/美国/中国/国际/市场 5 个)
- `top_k`: 每板块最多事件数
- `prior_brief_path`: 昨日简报成品路径(连续性用,可空)

## 输出契约

`assembled-{date}.json`:
```json
{ "date": "...", "sections": [
  { "key": "headline", "name": "🔥 头条/中东", "events": [
    { "title": "...", "summary": "只复述 quote,不脑补",
      "citation_ids": ["zh-001","en-003"], "sources": ["新华社","Reuters"],
      "importance": 8.5, "published_at": "...",
      "continuity": null }
  ]}
]}
```
- `continuity`: `null` | `{ "prior_date": "...", "delta": "较昨日新增/进展描述" }`

## 执行步骤(5 能力,顺序执行)

### 1. 加载 + fail-loud 过滤
读所有 `lane-*.json`。**只保留 `evidence_status="extracted"` 且 `extracted_quotes[]` 非空的 article**。其余丢弃并计数(日志)。无任何合格 article → 中止,返回 `{error: "no extracted evidence"}`,不产空骨架。

### 2. 去重 + 事件合并
跨 lane 识别**同一事件**的多条报道(标题/实体/时间相近)→ 合并为一个 `event`。合并时:
- `citation_ids[]` = 所有来源的 citation_id(多源印证)
- `sources[]` = 去重的 outlet 名
- `summary` = 综合各源 extracted_quotes,**只复述不脑补**

### 3. 连续性检测(喂昨日存档,非 RAG)
若 `prior_brief_path` 存在,读昨日成品 → 对每个 event 检查是否昨日已报:
- 是 → `continuity = {prior_date, delta: "较昨日:X 进展"}`,summary 聚焦**增量**而非重复
- 否 → `continuity = null`
- 无昨日存档 → 跳过此步(全 null)

### 4. 重要性打分 + top-k
对每个 event 轻量打分(0-10):多源印证数(citation_ids 越多越重) + 时效(published_at 越新越高) + 板块相关性 + 是否连续性热点。每板块按分降序取 `config.top_k`,其余降级或丢弃 —— **丢弃的写日志,不静默截断**。

### 5. 板块结构化 + 输出
按 `config.sections` 的 `match_hints` 把 event 归入板块。写 `assembled-{date}.json`。每个 event 必须:挂 ≥1 citation_id(否则第 1 步已丢弃);summary 可逐句追溯到某 extracted_quote。

## fail-loud 铁律
- 无 extracted_quote 锚的 event **绝不进骨架**(数字/事实必须可追溯)
- summary **只复述 quote**,出现 quote 外的具体数字/人名/日期 = 脑补 = 违规
- top-k 丢弃的事件**写日志**,不静默截断(否则"看似覆盖全部"实则没有)

## 反模式
- ❌ 在 assembly 做分析判断(前提→推理→结论)—— 那是调用方的事
- ❌ summary 脑补 extracted_quotes 之外的内容
- ❌ 硬编码板块(必须参数化,否则不通用)
- ❌ 连续性引入向量库/RAG(读昨日成品即可)
- ❌ 静默丢弃低分事件(必须日志)

## 与调用方协作(以 morning-news-briefing 为例)
1. 早新闻搜索 → `lane-*.json`(经 web-research-router)
2. **调 news-assembly** → `assembled-{date}.json`(本 skill)
3. 早新闻在骨架上**套分析层**(`analysis-format`:🔍 前提→推理→结论)+ banned-phrases 门禁
4. 渲染(`pdf` skill)+ 验证(`source-verification`)
