---
name: news-assembly
description: |
  Use when assembling multi-source search results into a structured, deduplicated, importance-ranked briefing skeleton. Does: dedup + cross-source event-merge, continuity detection vs prior briefing, importance scoring + top-k, configurable section structuring, citation anchoring (fail-loud). 通用「简报编辑大脑」,被 morning-news-briefing 等简报 skill 复用。
  Triggers: assemble briefing, 简报汇编, 去重合并, 事件归并, 简报骨架.
  DO NOT use for: 搜索(用 web-research-router)、渲染 PDF(见 references/playwright-pdf-rendering.md)、分析层/前提推理结论格式化(调用方处理)、事实验证(用 source-verification)。
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
| 重要性打分 + 每板块 top-k | 渲染 PDF(见 `references/playwright-pdf-rendering.md`) |
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
      "continuity": null, "tier": "analysis" }
  ], "briefs": [
    { "title": "...", "summary": "1-2 句摘要",
      "citation_ids": ["zh-007"], "sources": ["财新"],
      "tier": "brief" }
  ]}
]}
```
- `events[]`: 高分段(top_k 内),供调用方套深度分析层
- `briefs[]`: 低于 top_k 但非空的剩余事件,**必须保留**为摘要条目(title + 1-2 句 + citation)。调用方渲染时摘要层先行(15-20 条简报),分析层后置(5-8 条深度)。没有 briefs 层 = 新闻数量腰斩 = 调用方成品看起来"新闻不够"
- `tier`: `"analysis"` | `"brief"` — 调用方据此决定渲染深度
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

### 4. 重要性打分 + top-k + brief 保留
对每个 event 轻量打分(0-10):多源印证数(citation_ids 越多越重) + 时效(published_at 越新越高) + 板块相关性 + 是否连续性热点。每板块按分降序:
- **取 `config.top_k` 个** → `tier: "analysis"`,进入 `events[]`
- **剩余非空事件** → `tier: "brief"`,进入 `briefs[]`,保留 title + 1-2 句摘要 + citation
- **完全重复/无信息增量** → 丢弃,写日志
- **briefs 为空但 events 不足 top_k** → 日志标注"搜索产出不足,非截断"

### 5. 板块结构化 + 双层输出
按 `config.sections` 的 `match_hints` 把 event 归入板块。写 `assembled-{date}.json`:
- `events[]`: 高分段(top_k),供调用方套深度分析层。每个必须:挂 ≥1 citation_id;summary 可逐句追溯。
- `briefs[]`: 低分段,保留为摘要条目。每个必须:挂 ≥1 citation_id;title + 1-2 句 summary。
- 两层合计 = 搜索入库总数,调用方可据此校验"是否有新闻被吃掉"。

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
- ❌ **top-k 截断后事件消失** —— 低于 top_k 的事件必须在输出中保留为**摘要条目**(title + 1-2 句,挂 citation),不得静默消失。否则搜索 20+ 篇入库,成品只剩 10 条深度分析,新闻数量腰斩。调用方渲染时:摘要层先(15-20 条简报),分析层后(5-8 条深度)。两者皆来自 assembly 输出,不是调用方凭空生成。

## References

| File | Use |
|---|---|
| `references/playwright-pdf-rendering.md` | Dual-format PDF rendering (mobile 430×932 + A4) from bilingual markdown via Playwright. Covers CSS templates, cover page setup, font loading, and pitfalls. |
| `scripts/render-dual-pdf.py` | 🆕 Production-ready CLI script: `python3 render-dual-pdf.py <path/to/briefing.md>`. Converts news briefing markdown → mobile PDF + A4 PDF in one run. Includes md_to_html converter with blockquote/summary-list/table handling, Google Fonts @import + networkidle wait, and all CSS variables from the reference doc. Proven in morning-news-briefing v5.1.1 pipeline. |

## ⚠️ Pitfalls (操作陷阱)

| 陷阱 | 症状 | 修复 |
|------|------|------|
| **cron-worker workspace 路径偏移** | `execute_code` 写的文件落在 `~/.hermes/profiles/cron-worker/home/.hermes/workspaces/...` 而非用户 home 的 `~/.hermes/workspaces/...` | 写完后 `find ~/.hermes -name "lane-*.json"` 定位 → `cp` 到正确路径。或在 execute_code 中硬编码绝对路径 |
| **delegate_task 被 kanban gate 拦截** | cron-worker profile 无权生成子 Agent | 所有搜索必须由主 Agent 亲自执行。并行化策略：同轮次批量发起 web_search + Exa + Brave 调用（它们之间无依赖），减少总轮次 |

## 与调用方协作(以 morning-news-briefing 为例)
1. 早新闻搜索 → `lane-*.json`(经 web-research-router)
2. **调 news-assembly** → `assembled-{date}.json`(本 skill)
3. 早新闻在骨架上**套分析层**(`analysis-format`:🔍 前提→推理→结论)+ banned-phrases 门禁
4. 渲染(Playwright PDF — 见 `references/playwright-pdf-rendering.md`)+ 验证(`source-verification`)
