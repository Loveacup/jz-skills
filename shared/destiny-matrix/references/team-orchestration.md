# Agent Team 执行流程（destiny-matrix v5）

本文是唯一流程规范：定义任务 DAG、角色输入隔离、复用、修订和发布。`SKILL.md` 只作入口与索引；角色产物字段见对应 agent 文档及 `schemas/`；16 项验收只见 [`locked-checklist.md`](locked-checklist.md)；本端工具映射只见 `runtime-omp.md` / `runtime-cc.md`。

## 1. 入口合同

### 1.1 输入冻结

S0 `intake-refiner` 将原始请求整理成 `intake_brief`。所有后续任务消费同一份冻结输入快照，不自行重问用户或改写范围。至少包含：

- `subject`：`birth_date`、`date_calendar`、必填 nullable `lunar_date:{year,month,day,is_leap_month}`、`calculation_sex`、地点等原始出生资料；公历/儒略历输入的 `lunar_date` 为 `null`，农历输入保留原年月日与闰月标记。
- `time_input`：`precision:"minute"|"range"|"branch"|"unknown"`、`start`、`end`、`branch_label`、`timezone_name`、`utc_offset_hours`、`fold`、`clock_basis:"civil"|"local_mean_solar"|"local_apparent_solar"|"unknown"`。未知项保留 `null`，不推测。
- `personality_input`：`instrument`、`version`、`test_date`、`construct:"functions8"|"subtypes16"|"neris5"|"mbti_type"|"interview"|"none"`、原始 `scores` 和量程、自述类型、观察、反例及必填字段 `transcription`；非截图输入时 `transcription:null`，截图输入时须提供完整转录对象。无资料时使用 `construct:"none"`，不合成分数。
- `scope`：`{mode:"full"|"focused",requested_topics:string[],accepted_limits:string[]}`；主题枚举为 `personality,bazi,ziwei,astrology,synthesis,timing,relationships,practice,career,wellbeing,synastry`。
- 顶层字段还包括 `known_events`、`open_gaps`、`questions_for_user`、`analysis_as_of`、`timing_request`、`privacy`、`synastry`、`age_years`、`minor_mode`、`audience`、`cost_policy`。
- `timing_request`：`{years:int[],months:[{year:int,month:int}],systems:["bazi"|"ziwei"|"astrology"]}`；只将实际计算覆盖的粒度送入对应主题。
- `synastry` 固定 `{enabled:boolean,partner:{subject,time_input,personality_input,known_events}|null}`；双方资料各自独立，不共享出生时刻或量表。`cost_policy` 可为 `null`，表示无用户设定的硬预算。
- 每份 `personality_input` 必须含 `transcription`：非截图输入必须为 `null`；截图输入必须含 `image_refs`、两份独立 `first_pass`/`second_pass`、`differences`、`status:"verified"|"needs_clarification"`。Leader 派遣新的独立转录 task 作第二遍；该 task 只接收原图和转录字段定义，不接收首遍结果、人格结论或其他个案材料。按键、分值、量程比较；分歧回到原图局部复核，无法辨认置 `null` 并问用户，不投票或取平均。确认后同案角色复用该转录，不逐席重复。

### 1.1.1 非精确时刻

- `minute` 保留输入秒用于计算，显示精度不得超过实际输入精度。
- `range` 按用户给定闭区间解析，不取中点；`branch` 用当地/声明时基下传统左闭右开两小时区间，并显式处理跨日子时。
- `unknown` 且日期已知时使用该地本地历日 `[00:00, 次日00:00)`，不含次日零点、不取正午。跨夏令时按真实存在的 23/25 小时处理，DST gap 排除不存在时刻，fold 未消歧时保留两支。
- 非精确输入按真实边界拆成候选区间并去重；列出稳定离散字段、变化字段、有效范围和限制。出生时刻非精确时不得给出确定占星本命角度、ASC/MC 或宫位。相关计算维度标 partial；未获用户接受限制前不能宣称完整报告。无出生日期时三传统计算标 missing_input/not_applicable，不补造时刻或人格结果。

S0 按用户当地分析日一次固定 `analysis_as_of`；年龄据此计算，未满 18 岁必须 `minor_mode:true`，未知年龄记 `null` 并按保守适龄措辞。默认 `audience:"subject"`；只有用户明确选择时才改为 `guardian` 或 `both`。未成年任务谈关系时限于家庭、同伴、师长和边界，事业改谈学习/兴趣；不替孩子选职业，不描写未来婚恋对象或年份，不作性化推断和健康诊断。只在 `audience` 包含 guardian 时写给家长的内容，且不能取代面向当事人的正文。

默认 `privacy.external_chart_submission:false`、`retain_case_memory:false`。外部核验需用户针对具体站点和数据字段授权；未授权时只用公共算法/匿名基准，不声称已独立验盘。原始个案不自动进入跨会话记忆。

### 1.2 主题路由

- `full` 默认主题及顺序为 `personality,bazi,ziwei,astrology,synthesis,timing,relationships,practice`；用户另请求 `career`、`wellbeing` 时按 career、wellbeing 顺序插入 relationships 与 practice 之间。`synastry` 固定写在 `relationships` 内的合盘模块，不新增重复章节。
- `focused` 只生成用户明确请求的主题。必要背景和行动收束留在请求主题内，不额外补人格、关系或实践章节。
- `personality/bazi/ziwei/astrology/synthesis/timing/relationships/career/wellbeing/practice` 分别路由到同名 section。只有确有请求并且资料适用时才生成。
- 合盘需双方各自独立输入与至少一层可用资料；请求合盘但缺伴侣数据时列出缺口，不静默改成单人分析。timing 需固定年份与实际计算粒度；`full` 未指定年份时，S0 用 `analysis_as_of` 所在公历年作为明确默认。career/wellbeing 需有对应问题。
- 缺依赖时补问输入或记录待用户接受的限制。不得因难以计算、材料不足或成本自行删主题；未接受限制的关键请求阻断发布。

## 2. Stage DAG

```text
S0 intake-refiner：冻结输入、范围、隐私及适龄边界
  ↓
S1 caster：执行请求的计算，生成 chart_bundle 与原始 artifact
  ↓
S2 external-verifier：计算/方法核验；无外部授权时不提交个案
  ↓
S4 派遣前 Leader 按 S0/S2 适用集合写入 `judge_verdicts.json.expected_judges:[{subject_id:"primary"|"partner",dimension:"jung"|"bazi"|"ziwei"|"astro"}]`
  ↓
┌──────────────────────┴──────────────────────┐
S3 各适用 analyst 独立分析             S4 各适用 judge 盲审原始数据
└──────────────────────┬──────────────────────┘
                       ↓
S4 chief-judge：逐项核对 expected_judges 对应 analyst/judge 覆盖并比较
  ↓
S4C external-verifier：核验本次引用和经验性外部声明
  ↓
S5 synthesizer：围绕读者问题的主题综合与章节提纲；Leader 登记新综合 claim
  ↓
S6 love-specialist ∥ growth-specialist：按有效主题集合派遣适用专题
  ↓
S7 chart-director：冻结 sections 与 chart_table
  ↓
S8 book-writer：单一作者统稿；需要时先过功能性样章门，缺口经 Leader 定向回提
  ↓
S8.5 reader-editor：只改措辞（guard_book prose scope），不占修订额度；guard 失败则以 S8 原稿进入 S9
  ↓
S9 book-finalizer：HTML/内容终审，写 pre 裁决
  ↓ decision=awaiting_export
S10 Leader：导出 PDF → finalizer 检视真实 PDF 并写 post 裁决
  ↓ decision=pass
released：交付哈希相符的 HTML + PDF
```

S3 与 S4 并行，二者共同依赖 S2；不等待 S3 才启动判官。chief 同时消费两边已完成的证据，不用一致票数决定真伪。每批满足上游依赖后一次派遣，等待 barrier 再进入下游。失败先按真实原因修复；计算、数据或未满足必要输入不得用文案/排版绕过。

### 2.1 各阶段责任

| 阶段 | 负责席位 | 主要输入 → 产物 |
|---|---|---|
| S0 | intake-refiner | 原始请求 → `intake_brief` |
| S1 | caster | 冻结的 intake → schema v2 `chart_bundle`、方法和原始计算 artifact |
| S2 | external-verifier | chart_bundle + 公共依据/获准的核验输入 → 计算差异、来源与限制 |
| S3 | jung/bazi/ziwei/astro analysts（仅适用维度） | 本维原始输入 + intake 中本维必要请求 → 按本维 framework 推读路径形成的领域论述素材、claims、`evidence_summary`、`evidence_limits` |
| S4 | 对应 judges（仅适用维度） | 本维原始 JSON、输入口径、公共方法合同 → 独立推读、核算问题与解释限制 |
| S4 chief | chief-judge | 本维 judge 与 analyst 产物 → 分类后的 `consistency_report`、修订责任 |
| S4C | external-verifier | 实际将使用的引用/外部声明 → 核验过的来源、支持范围与限制 |
| S5 | synthesizer | 各维 findings、chief 分类、请求 → 围绕同一读者问题的新增理解（`synthesis_claims`）、行动选项、outline，以及全书 3–5 条 `core_propositions:[{proposition_id:"CP-01",image:string\|null,statement,claim_ids:[]}]`（`statement` 是带对象/条件的判断，`claim_ids` 回链已登记的 active claim；`image` 可空，不得升级为能力/命运结论） |
| S6 | love-specialist / growth-specialist | 本专题请求、有关 findings 和计算材料 → relationships/career/wellbeing/timing/practice 专题覆盖 |
| S7 | chart-director | intake、claim/evidence、专题和 chart_bundle → 冻结 `chart_plan.sections` 与 `chart_table` |
| S8 | book-writer（全书唯一作者） | 已审事实摘录及 artifact 定位、领域论述、综合主张、`core_propositions`、专题素材、冻结计划、输出模板 → HTML |
| S8.5 | reader-editor | S8 的 `$WS/book.html`、冻结计划、`case_evidence.json`（只读）、文风合同 → 同路径改写后的 HTML 与 `$WS/reader_edit_report.json`（`{guard_ok,patterns:[{pattern,count}],notes}`） |
| S9 | book-finalizer | HTML、计划、evidence、checklist、验证器与真实浏览器证据 → `verdict-rN-pre.json`（含 `reader_takeaways`） |
| S10 | Leader + book-finalizer | 合格 pre、HTML → PDF 技术导出；finalizer 检视真实 PDF → `verdict-rN-post.json` |

阶段需重算/补充的职责边界、定稿后的完整字段形状在 `agents/*.md` 与 schema 中；不可因本表简写而改变它们。

### 2.2 S6 派遣与作者素材

- S6 按 §1.2 解析后的**有效主题集合**判定：`full` 包含默认八主题，再合并 `requested_topics` 中的额外请求；不能只检查 `requested_topics` 数组。有效集合含 `relationships` 或 `synastry` 才派 love；含 `timing/practice/career/wellbeing` 任一项才派 growth；都不含时不派空任务。完整命书默认含关系、时间与实践，不能借条件派遣省掉它们。
- S3 的领域论述、S5 的 outline、`synthesis_claims` 与 `core_propositions`、S6 的 `chapter_material` 都是给作者的素材，不是逐项照抄的成文。作者负责章节内次序、承接、意象与删重；section/topic 与图表 ID 仍服从 S7 冻结计划，计算与传统规则推算不交给作者。

## 3. 判官输入隔离与 chief 复核

- S0/S2 确定每个 `subject_id` 的适用维度集合；真正不适用的维度才省略。S4 派遣前 Leader 将完整 `(subject_id,dimension)` 对写入必填 `judge_verdicts.json.expected_judges`（`subject_id` 为 `primary|partner`，`dimension` 为 `jung|bazi|ziwei|astro`）；chief 必须逐项核对每对均有对应 analyst finding 与 judge 结果。适用席位缺失、重复或覆盖不完整均为 `blocked`；checker 对缺失项发 `missing_applicable_judge`。不得把遗漏伪装成“不适用”。仅当无适用 judge 且 `judges` 为空时 `expected_judges` 才可为空；B1 的 `quality_contracts` 校验 expected 与实际 judge 覆盖。
- 每位 judge 在独立上下文中只接收本体系原始 JSON、必要输入口径与公开方法合同。不得接收历史事件、人格概括、其他体系数据、analyst findings、成稿、通用案例工作区根目录或跨会话记忆。
- 判官载荷只由 `scripts/judge_payload.py` 生成：本维原始切片、判官合同“首读”所列合同与公共来源 ID 索引，不含其他维度、历史事件或 intake 其余字段。Leader 把载荷文本原样作为该 task 的全部正文，派给本端无文件/Shell/派遣工具的 `dm-judge` adapter（见 runtime 文件），不附加其他材料。
- Leader 记录该任务实际字段，并从脚本输出登记 `input_artifact_ids`、`input_payload_sha256`。`isolation_level:"input_only"` 仅当以 `dm-judge` 派遣、正文与该哈希对应的载荷逐字一致、且判官未返回 `input_contamination` 时成立；使用通用子代理或带文件工具的 adapter、改写或补充载荷、判官报告污染，或运行时不能限制输入时，一律标 `unavailable`，并停止“独立盲审”声称。omp 端若判官工具表含可联网的 MCP 工具，runtime_trace 该 task 另记 `egress_tools`（实际可见的工具名清单），供隐私审计复核；判官若实际调用了其中任何工具，按输入污染处理：该判官标 `unavailable`、结果不用，fresh 重派。
- judge 返回 `independent_readings`、每项的输入引用/来源/限制、`calculation_issues` 与 `interpretation_limits`；简明证据摘要，不输出隐藏思维链。不得评 analyst 或写一致性评级。
- chief 的差异按 `calculation_error|source_error|unsupported_inference|method_difference|wording_difference` 分类，严重度 `blocking|disclose|editorial`。前三类证据成立即阻断；流派方法差异披露，文字差异不强行统一。
- chief 只在有支持证据时定 `pass|revise|blocked`。若需 AB/BA 检查顺序偏好，在同一 chief 任务内交换材料；不另开判官投票。
- `consistency_report.json.correction_rounds` 必须为每个 `expected_judges` 对提供一条 `{subject_id,dimension,round:0|1|2,trigger_discrepancy_ids:[],round2_trigger_discrepancy_ids?:[]}` 记录。未纠正时 `round:0` 且触发 ID 为空；基于新证据进行的维度纠正复审记 `round:1` 和触发该复审的 discrepancy IDs。每维常规只有这一次，和 book-writer 的 `revision_round` 分开。
- **纠正轮新错可再修一次**：round-1 复审时，chief 对每条 blocking discrepancy 标 `introduced_in_round`：其阻断内容（claim 或论述原句）在 round-0 findings 中不存在、由纠正稿新写入的记 `1`，并在 evidence 中并列 round-0 与 round-1 原文为证；原有问题未修好或只部分修好的记 `0`（不能为取得第二次机会而把旧问题改记新 ID）。若该维仍有 `introduced_in_round:0` 的 blocking，verdict 必须 `blocked`。若该维剩余 blocking 全部为 `1`，chief 可判 `revise`：Leader 把这些 discrepancy 与涉及的 claim 定点交回同一维 analyst 再修一次，只改这些 claim 及其论述句，不重派判官；随后 fresh chief 复审，记 `round:2`，`trigger_discrepancy_ids` 保留 round-1 值，`round2_trigger_discrepancy_ids` 列本次触发 ID。`round:2` 后仍有任何 blocking 必须 `blocked`，没有第三次。B1 的 `quality_contracts` 校验以上状态。
- 原始输入、计算方法、依赖版本、合同和实际角色配置未变时，同案判官产物可复用。只改 analyst 文本时保留 judge 结果，只派 fresh chief 比较新文本。原始维度输入/方法改变，仅重派受影响维度及其下游依赖；不得绕开上述纠正轮上限。

## 4. 证据、artifact 与复用

Leader 是唯一 `$WS/case_evidence.json` 工作账本的写入者，并原地更新；可在写入前保存不可变 `evidence-rN.json` 快照供审计，但校验与裁决只认 `$WS/case_evidence.json`。禁止并存 `case_evidence_current.json` 或其他“current”账本副本。Leader 同时唯一写入 `runtime_trace.json`、revision manifest 和 verdict 文件；角色只返回增量。

- artifact 注册路径相对本案 `$WS`，并记录 SHA-256、claim/artifact 依赖和 `current|stale`。更正后只失效直接及传递依赖；未受影响资产保留。verdict 不自注册，须绑定证据修订和实际产物哈希。
- claims 有全案唯一 ID、subject、kind、输入引用、来源、父 claim、反证、限制和状态；输入引用含 artifact ID、文件哈希与 JSON Pointer。修正以 correction 登记，不能让旧失效 claim 继续 active。
- 角色 claim 登记：S3 analyst、S5 synthesizer、S6 specialist 只返回 claim 增量，不写账本。Leader 审查父 claim（须为 active）、来源和限制，补齐 ledger 必需的 `owner:<席位名>`、`status:"active"` 后登记到唯一 `case_evidence.json`；引入新来源时先走 S4C 核验，未核来源的主张不登记。S3 首稿若经 chief 判 revise，只登记纠正轮后经 chief 复核的 claims，首稿 findings 保留为 `stale` artifact。
- S5 新综合主张（`owner:"synthesizer"`）：S7 在相应 `sections[].claim_ids` 引用这些已登记主张，writer 段落用 `data-claim-ids` 回链。综合稿不送盲判官；终审 A3/R2 审核推论是否越级。父主张被修正时，下游综合 claim 依 corrections 置 `superseded` 或 `rejected`、相关 artifact 置 `stale`（claim 没有 `stale` 状态），再重做受影响的综合、计划与正文；父 claim 的限制与反例对子 claim 继续有效。登记综合 claim 时，Leader 把其父 claim 所受的 `changes_reading:true` 限制的 `affected_claim_ids` 扩展到该子 claim（checker：`inherited_limitation_missing`）；综合章以短从句回扣，由 S9 A3 核对。
- **限制分两层。** 审计层是 `claims[].limits`、`counterevidence` 与 judge/chief 措辞，只供评审和附录，writer 不原样渲染进正文。读者层是 `limitations[]`，每条必填 `changes_reading`（删掉它读者会不会形成具体误读，或某句结论会不会变）、`reader_text`（面向读者的正向/条件句，不含流程词）与 `required_placement`。Leader 登记时按以下规则定落点。`changes_reading` 由 Leader 判定并把理由写入 `impact`；chief 判为 `disclose` 的差异默认 `changes_reading:true`，改标 `false` 须在 `impact` 写明它不改变哪一句结论；S9 可推翻该判定（见 `locked-checklist.md` A3）。schema 以 `limitation_placement` / `reader_limitation_in_appendix` 报错：`changes_reading:false` 只能 `appendix`；`changes_reading:true` 只能 `opening` 或 `adjacent`；`opening` 只用于全书通用边界（性质、非预测、资料范围），建议全书不超过 5 条（checker 不设门禁，validator 超过时给 `review_required` 提示）。chief 的 `disclose` 差异先改写成 `reader_text` 再登记，不把回应判官的口吻带进读者层。
- S7 `sections[].limitation_ids` 只收 `adjacent` 限制，同一 ID 只进一个 section；`adjacent` 限制的 `affected_claim_ids` 与计划中任一 claim 相交时必须有落点。`quality_contracts.py chart_plan --evidence` 分别报 `section_limitation_not_reader_layer`、`section_limitation_not_adjacent`、`limitation_multiple_sections`、`adjacent_limitation_unplanned`、`dangling_limitation`。正文以可见元素的 `data-limitation-id`（可空格分隔多个）标记限制：计划限制在所属 section 恰好一次，`opening` 在必要披露恰好一次，`appendix` 不以该属性进正文；标记元素去掉编号后须写出限制本身（不少于 6 个汉字，否则 `limitation_empty`）；后文回扣用不带标记的短从句。
- 公共引文目录在 `references/sources.json`；案例证据账本记录本案使用和核验状态。任何来源不明、版本不明或未核原话均不得伪装 verified。
- **通行读法（`common_reading`）。** 找不到古籍原文核实、但确为通行的象义，以 `sources[].kind:"common_reading"` 登记：`locator` 写可定位的现代通行资料或教材表述，`status:"verified"` 表示“已确认为通行读法”，不表示古籍原文已核；`excerpt` 必须为 `null`（`common_reading_excerpt`）。引用它的 claim 只能是 `traditional_interpretation`（`common_reading_claim_kind`）。正文以“传统上常见的讲法是……”转述，不加引号、不挂古籍名/篇名/作者；`references/sources.json` 中 `kind:"common_reading"` 的条目 `quotes` 必须为空，`<q data-quote-id>` 指向通行读法来源时 validator 报 `common_reading_quoted`。冒充古籍出处仍是 `source_error`。
- 仅同案、相同规范化输入切片、上游 hash、方法/依赖版本、角色合同/schema 版本及实际 role 配置下的成功产物可复用。
- `task_fingerprint` 为以上输入切片与配置快照的 SHA-256。复用项填写 `reused_from`；新证据、合同、上游产物或已知实际模型变化使其失效。resolvedModel 未知时只允许同一次运行内复用。

## 5. 派遣与档位

每个 task 首步完整读取自己的 `agents/<seat>.md` 与其中明确要求的合同。prompt 说明目标、输出 schema、必需来源/工具、任务边界、上游 artifact ID 和验收方式；不要反复粘贴全局流程。batch 共享 context 仅放本批全员可见的中性内容，原始输入、私人字段和判官 payload 放各自 task；判官 task 不读角色文档，其正文就是 §3 的载荷全文。

| 档位 | 席位 | OMP adapter/model 顺序 | Claude Code |
|---|---|---|---|
| light | intake-refiner、caster；受限机械布局修补 | `dm-light`：`["@smol","@task"]` | 通用子代理，派遣时 `model:"haiku"` |
| research | external-verifier、四 analyst、love/growth、chart-director | `dm-research`：`["@default","@slow"]` | 通用子代理，省略 `model`（继承） |
| deep | chief-judge、synthesizer、book-writer、reader-editor、book-finalizer | `dm-deep`：`["@slow","@default"]` | 通用子代理，省略 `model`（继承） |
| deep（隔离） | 四 judge | `dm-judge`：`["@slow","@default"]`，`tools: []` | `subagent_type:"dm-judge"`，`model: inherit` |

模型档位表示任务深度，不承诺费用高低或输出质量。纯机械布局改动可由 light 执行，但原 finalizer 复核。light 能力不足最多升 research 一次；输入/文件/依赖错误要先修原因；deep/judge/终审不降档。按运行时规则尊重 thinking 后缀及 `task.agentModelOverrides`；不改全局 model roles。具体工具名和后缀语义见本端 runtime 文件。

## 6. runtime_trace 与成本暂停

Leader 每个阶段和 task 记录：

`{task_id,stage,seat,agent,requested_role,configured_model,resolvedModel,resolvedModelIsFallback,model_observation_source,started_at,finished_at,wall_ms,task_fingerprint,reused_from,retry_of,status,input_artifact_ids,output_artifact_ids,usage_events}`

`usage_events` 只收与本案 task/request 明确关联的原生事件：`{event_id,request_id,input_tokens,output_tokens,cache_read_tokens,cache_write_tokens,cost,currency,source,coverage}`。缺失即 `null`，按 event_id 去重；不靠字数、用时或邻近请求推算。并行墙钟用执行区间合并，并另报累计席位时间。遥测缺失不伪造，也不以不完整数据声称精确成本收益。

`intake_brief.cost_policy` 的 `max_elapsed_minutes`、`max_input_tokens`、`max_output_tokens` 默认为 `null`。用户明确设定的任一预算上限触达时，停止新派遣，记录断点、已完成资产、实际成本与缺口，暂停并请求用户决定是否继续。没有硬上限时仍不重复无新证据的失败；不以降低质量、删请求或少做终审省成本。

## 7. 主题与专业边界

- 以人为本，不是以某份量表结论为本：四个体系按各自 framework 的推读路径独立完整解读，再围绕同一读者问题综合。人格资料是默认阅读入口之一，不构成其他体系必须围绕的主答案，也不要求传统体系证明人格结论。综合说明各视角增加了什么、真实的并行、张力或不可比，不建置信度评分或因果公式。
- 缺测量时先给一次访谈机会；用户不接受则说明人格资料边界并给开放观察问题。16Personalities/NERIS 五维、自述类型、16 亚型和八功能分数保持原构念，不互相伪转换。
- 人生事件仅作用户给出的背景，不反向校准出生时间或计算预测命中率。出生时间更正必须有新的出生记录/原始记忆依据，并保留前后候选差异。
- 未成年约束进入所有相关席位任务，不依赖 Leader 临时提醒。健康专题仅回应用户主动提供的生活习惯、压力与求助问题，不从排盘推出疾病或生育结论；事业、关系和流年不承诺事件、收益、成功率或吉日。
- 合盘不产生匹配总分或成功概率；伴侣称谓、现实身份不由传统排盘性别参数推断。
- 缺年/月/行运等实际计算时，相关时间主题明确写缺口，不由作者补算或假称已完成。

## 8. 写作前目录、样章与内容合同

S5 输出请求覆盖、主题综合、claim 回链和章节 outline；S6 处理适用专题（派遣条件见 §2.2）。S7 冻结 `chart_plan.sections` 与 `chart_table` 后，writer 不新增/删除请求主题或图表 ID。

- `full` 默认主题及 focused 路由见 §1.2。全部主题有清楚正文落点或经用户接受的限制；资料缺失未获接受时不以空章代替完成。默认八主题是导航，不按等分篇幅或章数验收。
- 每项核心回答在正文能理解：本盘看见的结构与含义、为何这样读、改变读法的限制和现实含义。计算细节、流派/时钟/软件版本与次要来源索引放方法附录，但影响结论的分歧/时刻不确定性（`changes_reading:true`）不能只藏在附录；未采用的取法及原因集中列在附录一处，正文不宣布“未核/未采用”。
- 图表没有最低数量，也不以图数验收。每张均由真实输入、计算值或有证据的 claim 支持；不补零、不填造数值，也不为凑图复刻同一信息。正文确实解释空间/周期结构时，采用 `chart-patterns.md` 的对应结构图，而不是一律退成表格。
- HTML 采用 `references/output-template.md` 的唯一语义结构；writer 不自行重算/填写计算值，需引用 artifact JSON Pointer。截图转录只使用已确认结果。

### 8.1 功能性样章门

首次采用当前 `book-writer.md` 编辑合同、此前发生内容或风格失败、或出现新的输入构念／受众分支时开门；相同合同与同类输入不重复开门。S8 从冻结计划中选**最容易写成审计口吻的一个领域解读段**（限制多、来源多为通行读法或未采用取法多的那一段）；范围含 synthesis 时加入与之关联的一个综合段，存在适用结构图时一起输出可读 HTML 小样。非 focused 任务另加入一条行动（含回链判断的“为什么是你”），让 S5 `action_options.goal` 的缺口在样章阶段暴露。focused 任务不为样章额外增加综合或图表，按其实际任务检查解释深度。样章篇幅以完整表达该论点为止，不按字数凑数；只写人格开篇或泛泛寄语不能过门。

同一 finalizer 按 `book-finalizer.md` 的预检合同先读读者稿、再查 evidence，预检同样套用 R1 换盘测试与 D3 有效段落标准；失败项汇总一次定点纠正，仍失败按现行阻断规则留存原因，不生成整本凑交付。过门后同一 writer 继续全书；样章不取代全书 16 项终审和实际 PDF 回审。

### 8.2 作者缺口回提

写作中发现素材缺口时，writer 一次汇总具体目标判断、现有 claim/artifact ID 与缺少的支持，交 Leader 定向回派：领域问题回对应 analyst，跨维问题回 synthesizer，关系/实践问题回对应 specialist，新来源回 external-verifier（S4C）。已有 claims 的忠实解释或改写无需新评审；新的实质推论须按 §4 登记并核验后才能入稿。新增 claim 若改变 `sections[].claim_ids/required_content/limitation_ids` 或图表，S7 仅更新受影响条目并重冻结，再由同一 writer 续写。

回提是补齐依赖，不是重新包装终审失败：触及 chief 已裁定的 blocking 问题时沿 §3 的纠正轮次处理，不用回提清零；S9 之后仍严格按 §9 的一轮 fresh writer 修订。没有新证据不循环派人，也不以措辞规避阻断。

## 9. 裁决状态机、修订与发布

终审 JSON 形状见 `schemas/final_verdict.json`。每次裁决不可变保存 `verdict-rN-pre.json` 或 `verdict-rN-post.json`；`final_verdict.json` 是最新完整裁决副本。

- **S8.5 reader-editor。** S8 成稿后、S9 前，Leader 先把 S8 稿存为不可变的当轮基准稿 `$WS/book-s8-r{N}.html`（N 为 `revision_round`，fresh writer 修订后的第二次 S8.5 用新文件，不覆盖上一轮），再派 reader-editor 改写 `$WS/book.html`：只做去重、否定→条件句、主语回到人、流程词替换、删除宣告式“未核”、合并重复停止条件、审计口吻改读者口吻；不得增删 claim/限制、改数字/引文/图表或写新推论。出口由 Leader 运行 `guard_book.py --before "$WS/book-s8-r{N}.html" --after "$WS/book.html" --scope prose --targets <全部 body section_id> --plan "$WS/chart_plan.json" --json`：`ok:true` 才以改后稿进入 S9；否则把 `book-s8-r{N}.html` 恢复为 `book.html` 进入 S9，并在 runtime_trace 该 task 记 `status:"reverted"` 与 guard issue code。prose scope 允许改带 `data-claim-ids` 段落的措辞与合并段落（每节 claim ID 集合不变），数字按集合比较（可删重复出现，不可新增或改值），`data-value-ref` 与引文节点原样，图表与隐藏状态不可变，每节 `data-limitation-id` 集合不变且计划限制恰好一次。guard 输出的 `certainty_review`（声源/条件标记减少的 section 及改前/改后计数）与 `reader_edit_report.json` 一并交 S9 对照。S8.5 不占 fresh writer 修订额度，也不开新的修订轮；S9 可因 S8.5 引入的退步（确定程度升高、声源标签被删、限制条件被削）判回退，由 Leader 把当轮基准稿恢复为 `book.html`，回退不计修订轮；回退后由 fresh finalizer 对恢复稿重做 pre 裁决，原裁决保留为不可变记录。S8.5 结束（含回退）后，Leader 按实际文件更新 `book.html` 的 artifact 哈希；`book-s8-r{N}.html` 另行登记或不登记，不得以 current 与正文并存。
- `pre_export` 检查 HTML。所有适用非 PDF 项通过且 P1–P3 标 `deferred` 才能是 `awaiting_export`。此阶段不允许 `pass`；deferred 仅可用于 P1–P3。D1 必须基于 `validate_book.py "$WS/book.html" --plan "$WS/chart_plan.json" --evidence "$WS/case_evidence.json" --json` 的 `ok:true` 输出，并在 D1 evidence 附该次 stdout JSON 的哈希；若怀疑 validator 误报，只能 `blocked` 并报告工具缺陷，不得豁免为 pass。
- S10 只接受与当前 HTML 哈希相符、decision 为 `awaiting_export` 的 pre verdict。导出后 finalizer 亲自核验真实 PDF；post 必须有 HTML/PDF 哈希、实际视觉证据、16 项齐全且均通过或合法 `na` 才能为 `pass` / released。
- 最终 decision 仅 `awaiting_export|revise|blocked|pass`。内容错误、来源错误、请求未回答、缺少实际 PDF、未验证真实 PDF、哈希不匹配或任何阻断项失败均不得放行。
- 每项 revision instruction 为 `{check_id,fix_type,owner,claim_ids,section_ids,problem,acceptance}`；`fix_type` 是 `calculation|source|analysis|prose|layout`。上游 calculation/source/analysis 更正先使相关 artifact 失效并重跑必要下游；writer 不可用措辞掩盖计算错误。
- 终审只读读者稿后写 `reader_takeaways`（3–5 句“读者能带走什么”）；写不出时给空数组，且 R1 与 D3 同时 `fail`（checker：`reader_takeaways_missing`；1–2 句报 `reader_takeaways_count`）。
- 最多一轮 fresh writer 内容修订；定点内容修补也计入该轮。fresh writer 修订后先再过一次 S8.5（`--targets` 为全部 body section，同样不占额度），再进入 S9。纯 CSS/layout 交 light 在 guard 指定范围内修补，由原 finalizer复核，不重写全文；每轮成书最多两次 layout 修补，第二次只能把 `output-template.md` 已有的规则套进本书唯一 `<style>`，不新写 CSS 手法。修订 writer 只拿 prepare-revision 生成的干净目录、未受影响内容和纠正素材，不接收被拒正文或内部审稿日志。
- 任意 HTML、CSS、数据或正文变更使旧 PDF、P1–P3 结果和 post verdict 失效，必须重新导出并复核。内容修订或第二次 layout 修补后仍有必过项 fail 即 `blocked`，不降级交付；第一次 layout 修补后仅剩 layout 类 fail 时，finalizer 判 `revise` 并给出第二次修补指令。
- `guard_book.py` 按 `prose|layout|citations|charts|content` 及 targets 约束差异；计算、来源或分析纠错须具备已接受的 revision 与更新 evidence。越界改动拒绝。

## 10. 脚本与最终 CLI 合同

所有 Python 脚本以 `doctor.py --json` 返回的 `$DM_PY` 执行。CLI 退出码：0=ok/partial（必须读取 JSON status）；1=计算、依赖、导出或契约失败；2=输入、参数或文件错误。错误 JSON 到 stdout，诊断到 stderr，不裸抛 traceback。

```text
cast_chart.py --intake <intake_brief.json> [--subject primary|partner] [--zi-hour-rule midnight|zi_start] [--house-system placidus|whole_sign]
cast_chart.py DATE TIME m|f|- CITY [--lat=<deg> --lon=<deg> --tz=<offset>|--tz-name=<IANA>] [--zi-hour-rule midnight|zi_start] [--house-system placidus|whole_sign]
bazi_calc.py --intake <file> [--subject ..] [--zi-hour-rule ..]
ziwei_calc.py --intake <file> [--subject ..]
astro_calc.py DATE TIME LAT LON --tz=<UTC偏移小时>|--tz-name=<IANA> [--house-system placidus|whole_sign] [--mean-node] [--orbs=<JSON对象>]
jung_calc.py --scores <JSON> --scale <max> | --scores16 <JSON> --scale <max> | --type <XXXX>
synastry_calc.py --a <chart_bundle A> --b <chart_bundle B> [--a-jung <jung.json>] [--b-jung <jung.json>] [--orbs <JSON>]
chart_data.py {radar,wheel,timeline,arc,dumbbell}
chart_data.py wheel --cusps <12个互异有限且位于[0,360)的宫始黄经> --asc <[0,360)度> [--planets <K=位于[0,360)度的黄经,...>]
chart_data.py dumbbell --pairs <JSON数组> --min 0 --max <scale>
quality_contracts.py <kind> <json_path> [--evidence <case_evidence.json>] [--json]
validate_book.py <html> --plan <chart_plan.json> --evidence <case_evidence.json> [--sources <references/sources.json 默认技能内>] --json
export_pdf.py <html> <pdf> --verdict <verdict-rN-pre.json> --json
guard_book.py --before <html> --after <html> --scope prose|layout|citations|charts|content --targets <id,...> [--plan <chart_plan.json>] [--revision <instructions.json> --evidence <case_evidence.json>] --json
guard_book.py --prepare-revision --before <html> --revision <instructions.json> --evidence <case_evidence.json> --output <new_dir> --json
judge_payload.py --dimension jung|bazi|ziwei|astro --subject primary|partner [--input <chart_bundle.json | jung_calc 结果>] [--intake <intake_brief.json>] [--evidence <case_evidence.json>] [--ws <dir>] [--dm <dir>] [--output <payload.txt>]
```

`astro_calc.py` 的 `--tz` 与 `--tz-name` 必须且只能给一个；没有时区时不默认 UTC+8。
`validate_book.py` 的 `review_required` 只作人工复核提示，不进 `issues`、不影响 `ok`：`forbidden_term`（硬禁词）、`process_term`（流程词词表，扫必要披露与正文，不扫附录）、`opening_negation` / `opening_method`（正文段首否定或方法句）、`opening_limitation_count`（必要披露中 opening 限制超过 5 条）。词表是 `validate_book.py` 顶部的模块常量。
`guard_book.py --plan` 只作用于 prose scope：给出时每个改动 section 的计划 `limitation_ids` 须恰好出现一次（`prose_limitation_count`）；不给时仍检查每节 `data-limitation-id` 集合不变（`prose_limitation_changed`）。prose scope 另拒绝把限制标记删到只剩编号（`prose_limitation_emptied`），并在输出中给 `certainty_review:[{section,before,after,before_total,after_total}]`：声源/条件标记（“在…的读法里”“传统上”“常见的讲法”“如果”“可能”“倾向”“多半”“例如”）减少的 section，只作 S9 对照提示，不影响 `ok`。
`judge_payload.py` 返回 `{ok,status,dimension,subject_id,input_payload_sha256,input_artifact_ids,artifact_id_source:"case_evidence"|"content_hash",included,payload_bytes,payload_path|payload}`；三传统维度必须给该 subject 的 chart_bundle，且该维 status 为 ok/partial，否则 exit 1 `dimension_unavailable`。jung 取 `jung_calc` 结果和/或 intake 的 `personality_input` 白名单字段（访谈构念才带观察与反例），两者构念不一致即 exit 1。`--intake` 只贡献年龄/受众口径与 jung 切片；给 `--evidence` 时按文件 SHA-256 取 current artifact_id，未登记即 exit 1。哈希为载荷 UTF-8 字节的 SHA-256，同输入逐字节确定。
`jung_calc.py --scores` 返回 `{construct:"functions8",raw_scores,scale,normalized_scores,ranked_tiers:[{functions,raw_score,normalized_score}],reflection_prompts:[{theory_basis,question,needs_observation:true}],interpretation_limits}`；并列分数放入同一 tier。`--scores16` 返回 `{construct:"subtypes16",raw_scores,scale,pairs:[{function,left_key,right_key,left,right,delta}],derived_functions:null,reflection_prompts,interpretation_limits}`；T/F 的 delta=H−A、N/S 的 delta=B−O。`--type` 返回 `{construct:"mbti_type",self_reported_type,theory_mapping:{basis,stack:[{position,function,role}×8]},reflection_prompts,interpretation_limits}`。三种模式互斥，不输出主导类型/未校准置信度。
`synastry_calc.py` 返回 `{schema_version:1,status:"ok"|"partial",aspect_profile:"standard-v1",orbs,dimensions:{jung,bazi,ziwei,astrology},communication_options:[{action,trigger,review_question,adapt_or_stop}],limitations}`。每层为 `{status:"available"|"unavailable",input_refs,observations,limits}`；关联 chart_bundle 维度 `data:null` 时映为 `unavailable`。
Jung 的 functions8/subtypes16 observation 为 `{kind:"construct_snapshot",person,construct,raw_scores,scale}`；`mbti_type` 为 `{kind:"theory_mapping",person,self_reported_type,stack}`。Bazi 为 `{kind:"traditional_calculation",calculation_method:"day_stem_element_relations",day_stems,elements,element_relation,direction,ten_stem_combination_element}`；Zi Wei 按共同宫位为 `{calculation_method:"traditional_palace_configuration",palace,a:{main_stars,mutagens},b:{main_stars,mutagens}}`。
Astrology 使用实际返回的 `computed_aspect` / `aspect_scan`；相位字段含 `a_point,b_point,aspect,angle,orb_used,exact_diff,profile`。扫描 checked/matched 仅为覆盖统计，不是关系评分。Bazi/Zi Wei 只报告规则计算或盘面字段，不冒称来源已核的个体关系解释。
`chart_data.py wheel` 返回 `{type,cx,cy,r,asc,cusps,planets,cusp_lines:[{house,longitude,offset_deg,x1,y1,x2,y2}]}`。`--cusps` 必须恰好 12 个互异有限黄经且每个在 `[0,360)`；`--asc` 与行星黄经也须在 `[0,360)`。非法输入 exit 2 并输出结构化 JSON；不生成 30° fallback。`timeline` 点 status 为 `inside_range|outside_range`，越界点 `x:null`；`dumbbell` 返回 `pairs` 原始端点、坐标、`delta` 和 status，缺端点标 `missing_endpoint` 且不输出 delta/line。缺失值不补造。

`quality_contracts.py` kind 为 `intake_brief|chart_bundle|sources|case_evidence|judge_verdicts|consistency_report|chart_plan|final_verdict|runtime_trace`；Python API：
CLI 输出 `{ok,kind,issues:[{path,code,message}]}`；退出码 0=通过、1=契约失败、2=参数/文件错误。
`quality_contracts.check(kind:str, data:dict, *, evidence:dict|None=None, base_dir:str|None=None) -> list[dict]`。

共用 Python 接口由 A1 的 `scripts/_common.py` 提供并由 A2 消费：

```python
normalize_birth_time(subject: dict, time_input: dict, *, as_of: str | None = None) -> dict
ASPECT_PROFILES = {"standard-v1": {"conjunction": 8, "opposition": 8, "trine": 7, "square": 7, "sextile": 5}}
resolve_orbs(custom: dict | None) -> tuple[str, dict]
match_aspect(lon_a: float, lon_b: float, orbs: dict) -> dict | None
```

时刻规范化返回统一 `time_context`；输入错误为 `InputError(code,path,message)`，计算错误为 `CalcError(code,path,message)`。`match_aspect` 用未四舍五入角距，边界 `≤orb` 成立。其余 chart bundle 外层字段、维度状态和错误行形状遵守 `schemas/chart_bundle.json`。
`chart_bundle` 外壳为 `{schema_version:2,status:"ok"|"partial"|"error",time_context,methods,dimensions:{bazi,ziwei,astrology},errors:[{code,path,message}],limitations:[]}`。每个维度为 `{status:"ok"|"partial"|"missing_input"|"not_applicable"|"error",data,candidates,limitations,methods?}`；失败不能伪装成空数组或数值 0。

## 11. 完成条件

只有所有已接受请求有真实回答或明确适用限制，依赖与 evidence 当前、HTML 通过结构/内容核验、S9 非 PDF 项完成、S10 导出并经真实 PDF 复核、pre/post/HTML/PDF 哈希一致且 `decision:"pass"`，状态才为 released。机器导出成功、阶段任务完成、格式整齐或没有报告错误都不能单独代表完成。
