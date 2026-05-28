# Deep-Research Loop SOP · 多轮深度研究流程

> **Read when:** 单轮 `research` mode 出来的 source map 覆盖度不够；议题 broad 且 multi-faceted；
> 或者用户明确要求"深挖" / "出报告" / "deep research"。这是现有 5 个 mode 的**可选升级路径**，
> **不替换** discovery / grounding / research / academic / recovery 的默认流程。
> **Source:** `~/research-tmp/odr/` (open_deep_research, legacy graph) + `~/research-tmp/gptr/` (gpt-researcher multi_agents) +
> `~/research-tmp/ldr-circuit/` (focused-iteration 8×5)。

## 关系映射：deep loop 与现有 5 mode

Deep loop 不是第 6 个 mode；它是 `research` mode 的可选升级层（兼容 `academic` 用于综述类）。
`discovery` / `grounding` / `recovery` 仍走单轮，**不应升级**——它们是定向任务，深 loop 会浪费 budget。

**触发深 loop 的判定标准（任一满足即可考虑）：**

1. 议题维度 ≥ 3（多 facet：技术 + 商业 + 政策 等）
2. 用户显式 ask：「深挖」「出报告」「全面分析」「deep research」
3. `CROSS_CHECK_DEPTH ≥ 2` 且未指定 mode
4. 单轮 research 后估算 source map 命中率 < 70%（关键 facet 缺失）

否则降级回 `research` mode 单轮。

## 标准流程 SOP

### Step 1: PLAN（议题分解 → sections）

- **触发：** 通过上面判定标准。
- **输入：** 用户原议题（可能含模糊词）+ 可选 user feedback。
- **操作：**
  - LLM 把议题拆成 N 个 `Section`。直接复用 `~/research-tmp/odr/src/legacy/state.py:5-22` 的 schema：
    `Section{name, description, research: bool, content}` 装在 `Sections{sections: List[Section]}`。
  - `research=True` 的 section 走 Step 2；`research=False` 的（intro / conclusion）只读其它 section 结果，留到 Step 4 合成。
  - 设定 budget（见下方表格）。
- **输出：** `plan = Sections(sections=[...])`。
- **终止条件：** plan ≥ 1 section；否则降级走单轮 `research` mode。

**节点签名参考：** `~/research-tmp/odr/src/legacy/graph.py:43 generate_report_plan` + `:142 human_feedback`（人工 review plan，**可选**保留）。

### Step 2: SECTION RESEARCH（每 section 独立小图）

- **触发：** 每个 `research=True` section 进入。
- **输入：** `SectionState{topic, section, search_iterations=0, search_queries, source_str, ...}`（`~/research-tmp/odr/src/legacy/state.py:60-67`）。
- **操作：**
  1. `generate_queries`：基于 section.description 生成 `Queries{queries: List[SearchQuery]}`，数量 = `number_of_queries`（默认 2）。
  2. `search_web`：用 SearXNG 广扫候选 → 每个候选走 **fetch-extract-pattern**（详见 `./fetch-extract-pattern.md`），抽取 verbatim quotes，section 内本地编号引用。
  3. `write_section`：尝试给该 section 出稿，触发 Step 3 的 grader。
- **输出：** `SectionOutputState{completed_sections, source_str}`。
- **终止条件：** grader pass，或 `search_iterations >= max_search_depth`（`~/research-tmp/odr/src/legacy/graph.py:342`）。

**节点签名参考：** `~/research-tmp/odr/src/legacy/graph.py:474-482`（section_builder：`generate_queries → search_web → write_section`）。

### Step 3: REFLECT（grader 自我审视）

- **触发：** 每次 `write_section` 之后。
- **输入：** 当前 section 草稿 + 已收集的 source_str。
- **操作：** 用结构化输出 `Feedback{grade: Literal["pass","fail"], follow_up_queries: List[SearchQuery]}`（**verbatim from** `~/research-tmp/odr/src/legacy/state.py:32-38`）。
  - `grade=pass` → 该 section 完结，归并到 `completed_sections`。
  - `grade=fail` 且 `search_iterations < max_search_depth` → `follow_up_queries` 进入下一轮 `search_web`。
  - `search_iterations >= max_search_depth` → **强制 pass**，标注 `budget-exhausted`（即 `~/research-tmp/odr/src/legacy/graph.py:342` 的 `or` 分支）。
- **gpt-researcher 启发的 None 习惯：** reviewer 若判定"差不多够了"应允许返回 `None`，立即终止。
  参见 `~/research-tmp/gptr/multi_agents/agents/reviewer.py:34` (`"please aim to return None"`) 和 `:59-60`（`if "None" in response: return None`）。
  **★ 关键：放手让 LLM 自评，避免计数器一刀切。**

### Step 4: MERGE（合并 sections + 最终综合）

- **触发：** 所有 `research=True` section 完结。
- **输入：** `completed_sections` + `report_sections_from_research`。
- **操作：**
  - `gather_completed_sections` 汇集（`~/research-tmp/odr/src/legacy/graph.py:396`）。
  - `write_final_sections` 处理 `research=False` 的 intro/conclusion（`:356`）。
  - `compile_final_report` 时**统一 renumber 全文 inline citation**——各 section 原本是 section-local 编号，merge 时拍平为 `[1]..[N]` 全局序号。
  - 输出最终 source map（schema 见 `./source-map-schema.md`），每条断言带 global `citation_id`。
- **终止条件：** 输出完成；调用方仍需**自行二次核验**——deep loop 不宣布"我对了"。

## Budget 控制（旋钮即权威配置名）

| 旋钮 | 默认 | 上限 | 来源 | 说明 |
|---|---|---|---|---|
| `number_of_queries` | 2 | 5 | `odr/legacy/configuration.py:45,81` | 每 section / 每轮生成几条 query |
| `max_search_depth` | 2 | 3 | `odr/legacy/configuration.py:46` | 单 section 的 grader 重试上限 |
| `max_concurrent_research_units` | 5 | 10 | `odr/open_deep_research/configuration.py:64` | section 并发数 |
| `max_react_tool_calls` | 10 | 20 | `odr/open_deep_research/configuration.py:107` | 单 section 内工具调用上限 |
| `max_structured_output_retries` | 3 | 5 | `odr/open_deep_research/configuration.py:42` | grader 结构化输出失败重试 |
| `max_iterations` | 8 | 12 | `ldr-circuit/.../focused_iteration_strategy.py:59` | focused-iteration 整轮上限（8×5 SimpleQA 96.51%）|
| `questions_per_iteration` | 5 | 8 | `ldr-circuit/.../focused_iteration_strategy.py:60` | 每轮问题数 |
| `token_budget` | 30k | 60k | （新增硬上限）| 整轮 deep loop token 预算 |

**衰减规则（gpt-researcher 启发）：** breadth 越深越窄。每深一层 section，`number_of_queries ÷ 2`、`max_search_depth - 1`。

## 终止条件清单（任一命中即停）

1. **Reviewer 返回 None** —— "够了"判断完全交给 LLM（gpt-researcher 习惯）
2. 所有 section grader = `pass`
3. `search_iterations >= max_search_depth`（单 section）或 `max_iterations` 用完（整轮）
4. `token_budget` 用尽 → 强制 merge，全文标注 `budget-exhausted`
5. 连续 2 轮无新增 verbatim quote（无进展信号）

## 与现有 5 mode 的搭配

| 既有 mode | 是否升级到 deep loop | 触发场景 |
|---|---|---|
| `discovery` | ❌ 否 | 单轮 SearXNG 候选清单即够 |
| `grounding` | ⚠️ 视情况 | 议题事实有冲突且 facet 多 → 限定 2 sections |
| `research` | ✅ **典型升级路径** | 多维度、需可引用结构化报告 |
| `academic` | ⚠️ 视情况 | 综述类（多篇 paper 横向综合） |
| `recovery` | ❌ 否 | recovery 是定位单 source，反向操作 |

## 常见误用

- ❌ 把 `grounding` 简单查询硬升 deep loop → 浪费 budget。
- ❌ 不设 `token_budget` → LLM 自己开心循环（实际是无限）。
- ❌ Section research 跳过 `fetch-extract-pattern` → 幻觉风险回归。
- ❌ Merge 阶段没 renumber citation → 全文引用错位（参考 `compile_final_report` 必须重编号）。
- ❌ Reflect 完全不接受 `None` → 永远跑满 `max_search_depth`，浪费 token。
- ❌ Plan 阶段不给 section `research: bool` 标志 → 所有 intro/conclusion 都去搜网，结果一堆冗余引用。
