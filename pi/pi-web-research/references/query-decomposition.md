# Query Decomposition · 子查询拆解

> **Read when:** SearXNG 多引擎广扫返回结果分散、噪声多；议题含多个实体 / 时间维度 / 对比对象；
> 需要把一个 broad query 拆成 sub-query 喂给后续 fetch-extract 循环。
> **Source:** `~/research-tmp/ldr-circuit/` (entity-decomposition + focused-iteration 8×5) +
> `~/research-tmp/perplexica/` (one-shot classifier，一次 LLM call 多布尔)
> **Sibling refs:** `fetch-extract-pattern.md` (拆出 sub-query 后的下一步) · `deep-research-loop.md` (整体研究循环位置)

---

## 拆解时机

SearXNG 本身就是聚合搜索（一次拉 N 个引擎），所以"广扫一次"≠"拆解"。**拆解的真正动机是给后续 fetch-extract 提供多个聚焦视角**。判断口径：

- ✅ 拆：议题含 ≥2 个独立维度（时间 × 实体 × 对比）；top-20 标题落在 ≥3 个不相关子主题
- ✅ 拆：fact-recall 类题但 query 是模糊自然语言（"那家做 X 的公司在 2025 大概多少估值"）
- ❌ 不拆：单实体单维度（"Redis 默认端口"）；SearXNG 首页 top-5 已收敛到同一答案

---

## 五类实体分解（local-deep-research 原文）

来源：`~/research-tmp/ldr-circuit/src/local_deep_research/advanced_search_system/questions/browsecomp_question.py:73-94`

| 类别 | 提取目标 | 示例（原文） |
|---|---|---|
| **TEMPORAL** | All years, dates, time periods | `"2018"`, `"between 1995 and 2006"`, `"2023"` |
| **NUMERICAL** | All numbers, statistics, counts | `"300"`, `"more than 3"`, `"4-3"`, `"84.5%"` |
| **NAMES** | Partial names, name hints, proper nouns | `"Dartmouth"`, `"EMNLP"`, `"Plastic Man"` |
| **LOCATIONS** | Places, institutions, geographic features | `"Pennsylvania"`, `"Grand Canyon"` |
| **DESCRIPTORS** | Key descriptive terms | `"fourth wall"`, `"ascetics"`, `"decider game"` |

> 注：源码里另有一套 `ConstraintType`（PROPERTY/NAME_PATTERN/EVENT/STATISTIC/TEMPORAL/LOCATION/COMPARISON/EXISTENCE），见 `advanced_search_system/constraints/base_constraint.py:10-20`，那套用于"答案核验约束"，不是用于"搜索 query 拆解"。本文件采用前者（搜索面用法）。

### 提取 prompt（verbatim, browsecomp_question.py:75-94）

```
Extract ALL concrete, searchable entities from this query:

Query: {query}

Extract:
1. TEMPORAL: All years, dates, time periods (e.g., "2018", "between 1995 and 2006", "2023")
2. NUMERICAL: All numbers, statistics, counts (e.g., "300", "more than 3", "4-3", "84.5%")
3. NAMES: Partial names, name hints, proper nouns (e.g., "Dartmouth", "EMNLP", "Plastic Man")
4. LOCATIONS: Places, institutions, geographic features (e.g., "Pennsylvania", "Grand Canyon")
5. DESCRIPTORS: Key descriptive terms (e.g., "fourth wall", "ascetics", "decider game")

For TEMPORAL entities, if there's a range (e.g., "between 2018-2023"), list EACH individual year.

Format your response as:
TEMPORAL: [entity1], [entity2], ...
NUMERICAL: [entity1], [entity2], ...
NAMES: [entity1], [entity2], ...
LOCATIONS: [entity1], [entity2], ...
DESCRIPTORS: [entity1], [entity2], ...
```

---

## focused-iteration: 8×5 是什么

来源：`~/research-tmp/ldr-circuit/src/local_deep_research/advanced_search_system/strategies/focused_iteration_strategy.py:1-7, 53-70`

注释原文（line 2-7）：
```
PROVEN HIGH-PERFORMANCE STRATEGY FOR SIMPLEQA
- SimpleQA Accuracy: 96.51% (CONFIRMED HIGH PERFORMER)
- Optimal Configuration: 8 iterations, 5 questions/iteration, GPT-4.1 Mini
```

- `max_iterations: int = 8`（line 59）— 最多 8 轮迭代
- `questions_per_iteration: int = 5`（line 60）— 每轮拆 5 条 sub-query
- 每轮 sub-query → SearXNG → top-K fetch → extractor 收 verbatim quote → 喂给下一轮
- 终止：实体覆盖率 ≥ 阈值（`coverage_ratio >= 0.8` line 458）或 reviewer 返回 None（参考 gptr 模式）
- **与 deep-research-loop.md 衔接**：deep loop "section research" 这一步可选启用 focused-iteration 作为更密集策略；普通模式 1-2 轮 5×sub-query 即可

---

## Perplexica classifier：一次过多布尔

来源：`~/research-tmp/perplexica/src/lib/prompts/search/classifier.ts:1-64`

不分多轮判定，一次 LLM call 同时返回多个布尔：

```json
{
  "classification": {
    "skipSearch": boolean,        // 一般知识即可，跳过搜索
    "personalSearch": boolean,    // 走用户上传文档
    "academicSearch": boolean,    // 走学术库
    "discussionSearch": boolean,  // 走论坛/社区
    "showWeatherWidget": boolean,
    "showStockWidget": boolean,
    "showCalculationWidget": boolean
  },
  "standaloneFollowUp": string    // 上下文无关的独立改写
}
```

**节省 round-trip**：适合做"先看议题画像、再选 mode/lane"的预筛。对应到 web-research-router，可在 mode 路由前先跑一次 classifier，决定 academic-lane / discussion / fact-recall / skip。

---

## 与 SearXNG 多引擎广扫的协同

1. 先用原 query SearXNG 广扫一次 → 看 top-20 landscape（标题足以判断维度数）
2. landscape 收敛（≥80% 标题指向同一答案）→ 直接 fetch-extract，不拆
3. landscape 发散（≥3 子主题、各自独立）→ 进入 decomposition
4. 拆出 sub-query 列表（5 条上限）→ 各自再 SearXNG → 各自 fetch-extract → 汇总到 source map
5. **拆出 sub-query 后不要回头再用原 broad query 重跑**，避免重复结果 / 拖慢 RRF

---

## 中文场景特别说明

- **NAMES** 类对中文极有效，`"准确人名/公司名"` 加引号在 Bing 中文 / Bilibili / Zhihu 都更准
- **TEMPORAL** 中文议题常含相对时间词（"最近"/"近期"/"前阵子"），decomp 时强制 LLM 替换成具体年份（基于 currentDate）
- **DESCRIPTORS** 中文易模糊（"做这个怎么样"），需 LLM 在 decomp 时挑出明确 concept term
- 中文 NUMERICAL 含中文计量（"百万"/"亿"），生成 sub-query 时同时发英文/数字版（`"10 million"` + `"1000万"`）

---

## 使用示例

### 示例 1：英文对比题
**Query:** "Compare LangGraph and LlamaIndex agent patterns"
**拆解：**
- NAMES: `"LangGraph" agent pattern`, `"LlamaIndex" agent pattern`
- DESCRIPTORS: `agent architecture comparison framework`
- TEMPORAL: 补 `2025 2026`
- → 4-5 条 sub-query 一轮 SearXNG → fetch-extract → merge

### 示例 2：fact-recall 数字题
**Query:** "Anthropic 2025 年 Series D 估值多少"
**拆解：**
- NAMES: `Anthropic Series D`
- TEMPORAL: `2025`
- NUMERICAL: `valuation`
- → 合成 sub-query `Anthropic Series D 2025 valuation`（quoted "Series D"）+ 中文版 `Anthropic 2025 D轮 估值`
- → 进入 fact-recall / forced-answer 路径（见 `anti-refusal-prompt.md`）

### 示例 3：中文模糊议题
**Query:** "上海最近那家做具身智能的初创公司怎么样"
**拆解：**
- LOCATIONS: `上海`
- DESCRIPTORS: `具身智能 / embodied AI` + `初创公司`
- TEMPORAL: 把"最近"具化为 `2025 2026`
- NAMES: 空 → 第一步广扫拿候选名 → 第二轮把名字补成 NAMES 重跑
- → Bing 中文 + Bilibili 路径优先（中文议题 lane，见 `query-patterns.md`）

---

## 常见误用

- ❌ 任何 query 都先拆 → 单实体问题（"端口号"）不需要拆
- ❌ 拆完 sub-query 后又把原 query 再跑一遍 → 浪费 + 重复污染 RRF
- ❌ 5 类标签全堆给同一 query → 选最显著的 1-2 类即可，其余空着
- ❌ 拆出的 sub-query 含义重叠（`"X 用法"` + `"X 怎么用"`）→ RRF 前先手工 dedup
- ❌ 没经过 landscape 判断直接进 8×5 焦点迭代 → 简单题被过度搜索，反而拉高噪声
