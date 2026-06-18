# Deep-Research Loop SOP · 多轮深度研究流程

> **Read when:** 单轮 `research` mode 出来的 source map 覆盖度不够；议题 broad 且 multi-faceted；
> 或者用户明确要求"深挖" / "出报告" / "deep research"。这是现有 5 个 mode 的**可选升级路径**，
> **不替换** discovery / grounding / research / academic / recovery 的默认流程。
> **Source:** `~/research-tmp/odr/` (open_deep_research, legacy graph) + `~/research-tmp/gptr/` (gpt-researcher multi_agents) +
> `~/research-tmp/ldr-circuit/` (focused-iteration 8×5)。
>
> **🆕 v3.4 (2026-05-28)**: 基于好伴AI案例 RCA，Step 2/3/4 重构 + 新增 Step 5（颗粒度强制）。
> 核心思想转变：**deep loop 不是"加长版的回答"，而是"研究"**——必须有独立的事实层、独立的验证回路、独立的补搜机制。
> "独立"是关键词：独立的中间产物（facts.jsonl）、独立的 LLM call（CoV）、独立的检索（补搜回路）。

## 关系映射：deep loop 与现有 5 mode

Deep loop 不是第 6 个 mode；它是 `research` mode 的可选升级层（兼容 `academic` 用于综述类）。
`discovery` / `grounding` / `recovery` 仍走单轮，**不应升级**——它们是定向任务，深 loop 会浪费 budget。

**触发深 loop 的判定标准（任一满足即可考虑）：**

1. 议题维度 ≥ 3（多 facet：技术 + 商业 + 政策 等）
2. 用户显式 ask：「深挖」「出报告」「全面分析」「deep research」
3. `CROSS_CHECK_DEPTH ≥ 2` 且未指定 mode
4. 单轮 research 后估算 source map 命中率 < 70%（关键 facet 缺失）

否则降级回 `research` mode 单轮。

## 标准流程 SOP（v3.4 5-step）

```
Step 1 PLAN → Step 2 SECTION (fetch → facts.jsonl → write) → Step 3 CoV (claim → independent verify)
            → Step 4 MERGE (盲区检视 → 反向假设 → 补搜 → compile) → Step 5 颗粒度强制
```

### Step 1: PLAN（议题分解 → sections）

- **触发：** 通过上面判定标准。
- **输入：** 用户原议题（可能含模糊词）+ 可选 user feedback。
- **操作：**
  - LLM 把议题拆成 N 个 `Section`。直接复用 `~/research-tmp/odr/src/legacy/state.py:5-22` 的 schema：
    `Section{name, description, research: bool, content}` 装在 `Sections{sections: List[Section]}`。
  - `research=True` 的 section 走 Step 2；`research=False` 的（intro / conclusion）只读其它 section 结果，留到 Step 4 合成。
  - **🆕 必须同时产出"反向假设清单"**（meta hypothesis list）：列出 PLAN 框架**外**可能遗漏的维度，例如：
    - "如果这个领域有重要的国际玩家，他们最近做了什么？"
    - "如果有跨语言信源（英文/日文/韩文），我们漏了什么？"
    - "如果有反方/对手 PR，他们怎么说？"
    - 这份清单留到 Step 4 补搜环节用，**不在 Step 2 内消耗**。
  - 设定 budget（见下方表格）。
- **输出：** `plan = Sections(sections=[...])` + `meta_hypotheses: List[str]`。
- **终止条件：** plan ≥ 1 section 且 meta_hypotheses ≥ 2 条；否则降级走单轮 `research` mode。

**节点签名参考：** `~/research-tmp/odr/src/legacy/graph.py:43 generate_report_plan` + `:142 human_feedback`（人工 review plan，**可选**保留）。

### Step 2: SECTION RESEARCH（每 section 独立小图，fetch ⊥ write 解耦）★ 重构

> ⚠️ **核心改动：fetch 与 write 解耦**——这是 2026-05-28 案例诊断出的 80% 偏差根因。
> 旧流程 `generate_queries → search_web → write_section` 让营销话术直接叙事化；
> 新流程 **强制插入 `extract_to_facts.jsonl` 中间层**，write_section 只能读 facts.jsonl，不能读原始页面。

- **触发：** 每个 `research=True` section 进入。
- **输入：** `SectionState{topic, section, search_iterations=0, search_queries, source_str, facts: List[Fact], ...}`。
- **操作（4 阶段，顺序不可换）：**

  **2.1 `generate_queries`** —— 基于 section.description 生成 `Queries{queries: List[SearchQuery]}`，数量 = `number_of_queries`（默认 2）。

  **2.2 `search_web`** —— 用 Exa + Brave 双主力广扫候选（web_search 兜底；SearXNG 仅命中 <3 条时兜底）→ 每个候选走 **fetch-extract-pattern**（详见 `./fetch-extract-pattern.md`，抓取主力 Exa Fetch / Tavily Extract），抽取 verbatim quotes，section 内本地编号引用。

  **2.2+ 🆕 不稳定高质量源补充（pre-flight 必检）** —— 主链路搜索完成后，对 §不稳定高质量源 做 pre-flight check：
  - `which claude && claude --version` → 可用则 `scripts/claude-web-search.sh` 追加搜索，结果合并入候选池
  - `which codex && codex login status` → 可用则同理（预留，需认证）
  - **规则：** 失败静默跳过；返回空视为额度耗尽，该 section 内不再重试；结果与主链路结果统一走 2.3 extract_to_facts.jsonl
  - **成本意识：** Claude Code ~$0.30-0.66/query，仅在 section 为 `research=True` 且 `search_iterations ≤ 1` 时启用（首轮用一次，后续轮次不重复）

  **2.2g 🆕 实体接地闸（ENTITY_MISS gate）★ v3.11** —— 在 2.2 抽 quote、进 2.3 原子化**之前**插一道闸。偷自 last30days `rerank.py` 的 `ENTITY_MISS_PENALTY`，但换形为 WRR 的**二元门控**（非连续打分）：
  - **接地基准：** SKILL.md **Step 0.6** 解析出的核心实体（官方名 / repo / handle）；Step 0.6 未跑时退化为本 section 的核心 **NAMES** 实体（`query-decomposition.md`）。
  - **判定：** 逐候选页/quote 检查**是否提及核心实体**。整页**完全不含**核心实体（含别名/缩写/官方域）→ 标 `entity_miss: true`。
  - **行动：** `entity_miss` 的候选**不进 facts.jsonl**（不原子化），除非该 section 明确就是研究"关联但未命名"的侧面（须显式复核理由）。
  - **为什么：** 堵 **Exa 语义漂移**（SKILL.md pitfall #8：「React release date」召回 GTA 6）——一个全程不提实体的页面，几乎必是漂移/噪声，放进 facts 就是给后续合成喂错前提。
  - **与 CoV 互补：** 本闸防"主题跑偏的源混入"；Step 3 CoV 防"主题正确但 claim 错误"。两者正交，都要跑。

  **2.3 `extract_to_facts.jsonl`** —— ★ **新增强制步骤**。把 2.2 抽出的 verbatim quotes（**已过 2.2g 实体接地闸**）进一步原子化为事实卡片：

  ```jsonl
  {"id":"f001","section":"竞争格局","claim":"蚂蚁阿福用户突破1亿","metric_type":"用户数","scope":"⚠️未指明(累计/MAU/DAU?)","value":"1亿","value_unit":"用户","time":"2026.1 PR稿","source_url":"https://...","source_tier":"C(蚂蚁PR稿)","confidence":"低-单源","extracted_at":"2026-05-28T...","verify_status":"unverified"}
  {"id":"f002","section":"竞争格局","claim":"好伴AI注册用户1000万","metric_type":"用户数","scope":"⚠️未指明(累计/MAU?)","value":"1000万","time":"2026.4 官网","source_tier":"C(官网)","confidence":"低-单源","verify_status":"unverified"}
  ```

  **字段强制要求：**
  - `metric_type`：必须分类（用户数 / 收入 / 估值 / benchmark分数 / 政策项目数 / 时间点）
  - `scope`：**口径**。涉及"用户/规模"必须标注（累计/MAU/DAU/注册量/付费），不明确时**显式写"⚠️未指明"**，禁止留空
  - `source_tier`：A(独立第三方评测) / B(权威媒体) / C(公司PR/官网) / D(自媒体) / E(口头声称)
  - `confidence`：高/中/低/单源（C 及以下默认"低-单源"）
  - `verify_status`：unverified / verified / contradicted / cross-checked

  **2.4 `write_section(from=facts.jsonl)`** —— 只能引用 facts.jsonl 里**已有的 fact_id**，禁止"自由发挥"引述原始页面。
  - 引用规范：每个数据点必须带 `[f001]` 标记
  - 涉及"⚠️未指明"口径的 fact 必须在文中标注（例："蚂蚁阿福用户1亿[f001，口径未明]"）而非直接说"蚂蚁阿福已有1亿用户"
  - 触发 Step 3 的 CoV grader。

- **输出：** `SectionOutputState{completed_sections, source_str, facts_jsonl_path}`。
- **终止条件：** Step 3 CoV pass，或 `search_iterations >= max_search_depth`（`~/research-tmp/odr/src/legacy/graph.py:342`）。

**节点签名参考：** `~/research-tmp/odr/src/legacy/graph.py:474-482`（section_builder：原 `generate_queries → search_web → write_section`，v3.4 改造为 `generate_queries → search_web → extract_to_facts → write_section`）。

### Step 3: CoV（Claim 抽取 + 独立检索 + 正交比对）★ 替换 REFLECT

> ⚠️ **核心改动：REFLECT 改造为 CoV**——同 Agent 自审无法发现 prior 错误。
> 旧 REFLECT 用 `Feedback{grade, follow_up_queries}` 让同一 Agent 在同一上下文中自审；
> 新 CoV 在 **独立 LLM call / 新上下文** 中抽 claim → 独立 search → 正交比对。

- **触发：** 每次 `write_section` 之后。
- **输入：** 当前 section 草稿 + facts.jsonl + 已收集的 source_str。
- **操作（3 步）：**

  **3.1 Claim 抽取（独立 call）** —— 扫描 section 草稿，自动捕获以下高风险句：
  - 含关键词：`第一` / `最` / `独家` / `突破` / `领先` / `超过` / `首家` / `首个` / `全球` / `行业`
  - 含数字规模声明：用户数、金额、增长率、benchmark 分数
  - 含政策引用：法规名称、生效日期、覆盖范围
  - 含排名结论：榜单名称、排名位置

  产出 `claims_to_verify = [{text, type, source_fact_id, confidence}]`，按 `confidence=低/单源` 优先排序。

  **3.2 独立 search（每 claim 独立 call）** —— 对每个 claim 发起**全新**的 web search：
  - **不复用** Step 2 的 fetch 结果，不与 Step 2 上下文共享
  - **跨信源**：PR 稿/官网 claim → 强制搜第三方报道、benchmark 原始榜单、竞争对手 PR
  - **跨语言**：中文 claim 至少做 1 次英文搜索（e.g. "WiseDiag benchmark independent ranking"）
  - **跨时间**：搜更新的版本（e.g. HealthBench 2025/2026 latest）

  **3.3 正交比对** —— 新检索结果 vs 原 claim，按下表处理：

  | 比对结果 | 行动 | facts.jsonl 更新 |
  |---------|------|----------------|
  | 独立信源支撑 | 标注 `verified[source]` | `verify_status: verified` + `verify_sources: [...]` |
  | 无独立信源 | 保留但降权 + 文中加 `[单源未独立验证]` | `verify_status: single-source` |
  | 有矛盾信号 | 用新证据修正 claim，原文附 `[已修正：原 X，新证据 Y]` | `verify_status: contradicted` + `corrected_value: ...` |
  | 完全推翻 | 删除原 claim，替换为新证据结论 | `verify_status: refuted` |

  **3.4 grade（仅最后）** —— 基于 verify 结果决定 grade：
  - 所有"含关键词"句子都 `verified` 或 `corrected` → `grade=pass`
  - 剩余 `single-source` 句子 ≤ 1 且非核心 → `grade=pass-with-caveat`
  - 否则 → `grade=fail`，回到 Step 2.2 用 `follow_up_queries` 补 search

- **gpt-researcher 启发的 None 习惯：** reviewer 若判定"差不多够了"应允许返回 `None` 立即终止，避免计数器一刀切。
  参见 `~/research-tmp/gptr/multi_agents/agents/reviewer.py:34` 和 `:59-60`。

- **REFLECT vs CoV 对照：**

  | | 旧 REFLECT | 新 CoV |
  |---|---|---|
  | 执行者 | 同一 Agent | 独立 LLM call（新上下文） |
  | 上下文 | 复用 SECTION 的 fetch 结果 | 全新独立 search |
  | 发现什么 | 段落间逻辑矛盾 | prior 本身的错误 |
  | 案例 | "第3段说的增长率与第5段矛盾" | "整个讨论基于错误的用户数口径" |

详见 `./deep-loop-verification-pattern.md`。

### Step 4: MERGE（合并 sections + 补搜回路 + 最终综合）★ 增加补搜

> ⚠️ **核心改动：MERGE 前插入"盲区检视 → 反向假设 → 跨语言补搜"**。
> 旧流程 `gather → write_intro/conclusion → compile` 让 PLAN 阶段的框架成为天花板——框架外的事实（如 Anthropic Claude for Healthcare）系统性遗漏。

- **触发：** 所有 `research=True` section 完结。
- **输入：** `completed_sections` + `report_sections_from_research` + 所有 section 的 `facts.jsonl` + Step 1 产出的 `meta_hypotheses`。
- **操作（5 阶段，顺序不可换）：**

  **4.1 `gather_completed_sections`** —— 汇集（`~/research-tmp/odr/src/legacy/graph.py:396`）。

  **4.2 ★ 盲区检视（blind spot review）** —— 由 Leader / 独立 LLM call 做 meta 审视：
  - 把 PLAN 的 section names + meta_hypotheses 拿出来对照
  - 问："已写的 6 段覆盖了什么？没覆盖什么？meta_hypotheses 里哪些 hypothesis 还没被任何 section 触碰？"
  - 产出 `blind_spots: List[str]`（应 ≥ Step 1 meta_hypotheses 中"未被覆盖"的部分 + 新发现的盲点）。

  **4.3 ★ 反向假设搜索（reverse hypothesis search）** —— 对 blind_spots 每条发起补搜：
  - 强制至少 1 次**跨语言查询**（中文议题 → 至少 1 次英文 query；英文议题 → 至少 1 次中文 query）
  - 强制至少 1 次**反向 framing**（e.g. 议题是"国内 player 竞争"，补搜"国际玩家在该领域的最近动作"）
  - 强制至少 1 次**对手视角**（e.g. 议题是"X 公司机会"，补搜"X 公司当前的最大风险"）
  - 命中的新事实进入新 fact（`section: 补遗`）并走完整 Step 2.3 → Step 3 CoV

  **4.4 `write_final_sections`** —— 处理 `research=False` 的 intro/conclusion（`:356`），引用必须可映射到 facts.jsonl。

  **4.5 `compile_final_report`** —— 时**统一 renumber 全文 inline citation**——各 section 原本是 section-local 编号，merge 时拍平为 `[1]..[N]` 全局序号。
  - 输出最终 source map（schema 见 `./source-map-schema.md`），每条断言带 global `citation_id` + `verify_status` + `source_tier`。

- **终止条件：** 输出完成；调用方仍需**自行二次核验**——deep loop 不宣布"我对了"。

### Step 5: 颗粒度强制（granularity gate）★ 新增

> ⚠️ **核心改动：政策/数据/排名类 claim 必须列原始项目名/数字/日期/信源等级，禁止笼统措辞**。
> 这是为了堵住"颗粒度坍缩"——"医保红利"等笼统词把"12个项目全是影像类"这种 critical detail 抹平。

在 compile_final_report **之前**插入一道闸门，逐条扫描全文，对以下三类 claim 强制 enforce：

| Claim 类型 | 触发关键词 | 必须包含 | 缺一则 fail |
|-----------|----------|---------|-----------|
| **数字类** | "用户"/"MAU"/"DAU"/"GMV"/"收入"/"估值"/"增长率"/"\d+万"/"\d+亿" | (a) 数值 (b) 口径（累计/MAU/DAU/注册/付费）(c) 时间点 (d) 信源 tier | **fail** |
| **政策类** | "政策"/"医保"/"法规"/"补贴"/"红利"/"扶持"/"试点" | (a) 政策原文名 (b) 生效日期 (c) **覆盖项目/范围的清单**（数量+至少 2 个具体名称）(d) 信源 tier | **fail** |
| **排名/Benchmark 类** | "第一"/"领先"/"突破"/"全球"/"行业"/"\w+Bench" | (a) **榜单/benchmark 原始名** (b) **测评机构**（独立/官方/PR）(c) 横向对手 ≥ 2 (d) 信源 tier (e) **是否唯一信源标注** | **fail** |

**Fail 处理：**
- 回到 Step 3 重新做 CoV 补 search 拿细节
- 拿不到 → 文中强制加 `[颗粒度不足，仅笼统数据]` 警示并降低该段权重
- 禁止"政策红利"/"市场领先"/"用户增长迅猛"等无原始项目名/数字/对手的笼统措辞通过 Gate

**输出：** `granularity_check: {pass: N, fail: M, fail_details: [...]}` 附于最终 source map。

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
| `token_budget` | 30k | 60k | （硬上限）| 整轮 deep loop token 预算 |
| `cov_max_claims_per_section` | 5 | 10 | （v3.4 新增）| Step 3 每 section 最多 CoV 验证的 claim 数 |
| `blind_spot_search_count` | 3 | 6 | （v3.4 新增）| Step 4 反向假设补搜次数 |
| `aux_source_max_calls` | 1 | 3 | （v3.8 新增）| 不稳定高质量源（Claude Code）每 session 最大调用次数。首轮 section 用 1 次，后续不再重复 |

**衰减规则（gpt-researcher 启发）：** breadth 越深越窄。每深一层 section，`number_of_queries ÷ 2`、`max_search_depth - 1`。

## 终止条件清单（任一命中即停）

1. **Reviewer 返回 None** —— "够了"判断完全交给 LLM（gpt-researcher 习惯）
2. 所有 section CoV `grade = pass` 或 `pass-with-caveat`，**且 Step 5 颗粒度 Gate 全通过**
3. `search_iterations >= max_search_depth`（单 section）或 `max_iterations` 用完（整轮）
4. `token_budget` 用尽 → 强制 merge，全文标注 `budget-exhausted`
5. 连续 2 轮无新增 verbatim quote / 新 fact（无进展信号）

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
- ❌ **Step 2.2g 实体接地闸被跳过** ★ → Exa 语义漂移结果（整页不提核心实体）混进 facts.jsonl，给后续合成喂错前提（pitfall #8）。
- ❌ **Step 2.3 跳过 facts.jsonl 直接写散文** ★ → fetch-write 耦合复发，所有改造作废。营销话术再次直接叙事化。
- ❌ **Step 3 CoV 复用 Step 2 上下文** ★ → 失去"独立"性，退化为 REFLECT 自审。必须新 LLM call、新搜索。
- ❌ **Step 4 跳过盲区检视/反向假设** ★ → 跨语言/跨地域召回失败复发。
- ❌ **Step 5 颗粒度 Gate 被绕过** ★ → "政策红利"等笼统措辞再次通过。
- ❌ Merge 阶段没 renumber citation → 全文引用错位（参考 `compile_final_report` 必须重编号）。
- ❌ Reflect 完全不接受 `None` → 永远跑满 `max_search_depth`，浪费 token。
- ❌ Plan 阶段不给 section `research: bool` 标志 → 所有 intro/conclusion 都去搜网，结果一堆冗余引用。
- ❌ Plan 阶段不产 `meta_hypotheses` → Step 4 没有反向假设可用，盲区检视沦为空操作。

## ⚠️ 质量缺陷预警（2026-05-28 好伴AI案例 RCA）

> **核心发现**：deep loop 的单 Agent 串行架构存在系统性质量缺陷。在开放性研究任务中，它倾向于产生"叙事一致"而非"事实正交"的输出。以下 5 个失败模式来自同一案例，指向架构级问题而非 prompt 级问题。
> v3.4 通过 Step 2.3 (facts.jsonl)、Step 3 (CoV)、Step 4 (盲区补搜)、Step 5 (颗粒度 Gate) 四道闸门系统性堵漏。

| 失败模式 | 机制 | v3.4 阻止机制 |
|---------|------|--------------|
| **fetch-write 耦合** | fetch 后直接写散文，无事实卡片中间层。营销话术一旦叙事化，REFLECT 无法回头推翻 | **Step 2.3** 强制 facts.jsonl；write_section 只能引 fact_id |
| **REFLECT 自审天花板** | 同一 Agent + 同一上下文自审 = 在同一个先验下 check，无法发现 prior 错误 | **Step 3** CoV 用独立 LLM call + 新 search，正交验证 |
| **单 Agent 上下文压缩** | 6 sections × 多源 → 100k+ tokens → 必须压缩 → 口径细节丢失 | **Step 2.3** facts.jsonl 把口径独立物化，不再依赖上下文记忆；P1 进一步用多 Worker 并行 |
| **跨语言召回失败** | 中文搜索词 + 无补搜回路 → 英文源永不被召回 | **Step 4.3** 强制跨语言 + 反向假设补搜 |
| **Benchmark 樱桃挑选** | PR 稿选有利 benchmark，deep loop 单源采信不交叉验证 | **Step 3** CoV 强制对"第一/领先"类 claim 跨信源验证 + **Step 5** 颗粒度 Gate 强制列原始榜单与对手 |
| **颗粒度坍缩** | "政策红利"抹平"12个项目全是影像类" | **Step 5** 颗粒度 Gate 强制列原始项目名+数量+日期 |
| **口径混淆（累计/MAU/DAU）** | PR 稿写"用户1亿"被写成"已有1亿用户" | **Step 2.3** facts.jsonl 强制 `scope` 字段；不明则 `⚠️未指明`；**Step 5** Gate 不让"⚠️未指明"句通过 |

> ⚠️ 这些不是 prompt 能修的问题——已经升级为流程级强制动作。详见 `references/deep-loop-verification-pattern.md`。

## 对照 5 偏差案例的自检（v3.4 改造效果）

| # | 案例 | 旧流程偏差 | v3.4 阻止点 |
|---|------|-----------|-----------|
| 1 | 蚂蚁阿福"1亿用户" | 直接写入散文 | **Step 2.3** scope 必须标注 → 实际 PR 未指明 → `⚠️未指明(累计/MAU?)` + Step 3 CoV 独立搜 → 命中 "MAU 3000万" → `contradicted` → Step 5 Gate 拦截 "1亿用户" 笼统措辞 |
| 2 | "WiseDiag 全球第一" | 单源采信 | **Step 3** 强制"第一/全球" claim 独立 search → 命中 HealthBench 百川 M3 → `corrected_value: "DoctorBench 单源领先，HealthBench 上百川 M3 65.1 > 该模型"` + **Step 5** 必须列对手 ≥ 2 |
| 3 | "医保政策红利" | 颗粒度坍缩 | **Step 5** 政策类必须列 (a) 原文名 (b) 日期 (c) **12个项目清单**（影像/筛查具体名） → fail → 回 Step 3 补 search → 修正为"政策覆盖影像/筛查 12 项，未覆盖全科咨询/数字分身" |
| 4 | "1亿 vs 1000万 = 10x" | 派生指标错误 | 修复 #1 后，f001 已修正为"MAU 3000万"，f002 仍为"注册1000万"，**Step 5** Gate 检查口径不一致 → 文中必须明确"MAU vs 注册量不可直接比" |
| 5 | Anthropic Healthcare 遗漏 | 跨语言盲区 | **Step 1** meta_hypotheses 含"国际玩家最近做了什么" → **Step 4.2** 盲区检视命中 → **Step 4.3** 反向假设搜索（英文 query "Anthropic healthcare 2026"）→ 召回 → 进入补遗 section |

**结论：5 个偏差案例**全部被 v3.4 流程阻止**。**
