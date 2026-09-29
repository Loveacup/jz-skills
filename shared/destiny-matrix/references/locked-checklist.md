# 发布验收清单（destiny-matrix v5）

本文件是 book-finalizer 唯一清单。每份 `final_verdict` 必须对 I1–I3、A1–A3、R1–R3、D1–D4、P1–P3 各记录一次，合计 16 项。状态机与修订分流以 [`team-orchestration.md`](team-orchestration.md) 为准；字段结构以 `schemas/final_verdict.json` 为准。

## 逐项判定

| ID | 必须通过的行为 | 主要证据 |
|---|---|---|
| I1 | 用户请求、来源和受众清楚；scope 中每个请求均有成品落点或用户接受的限制。 | intake、问题清单、chart_plan section 与成品位置 |
| I2 | 日期、出生时刻精度、时区/历法、方法口径和数据完整性如实记录；关键不确定性出现在适当位置。 | `time_context`、计算方法、限制披露及相关正文 |
| I3 | 隐私、外部提交授权、年龄、minor_mode 与 audience 均遵守；未知值未被猜定，未成年隐私没有因受众默认外泄。minor_mode 下正文不把盘面、类型、分数或功能位置贴成能力缺陷、风险标签或人生限制，不为当事人编写未提供的亲历场景，关系/事业内容限于 `character-inference-workflow.md` §5 的适龄范围。 | intake 快照与外部任务输入、正文受众及相关限制、未成年人正文原句 |
| A1 | 正文、表格、图表与计算 artifact 的值、单位、精度和方法一致；精确数字可追溯到有效输入或计算结果。 | artifact hash/JSON Pointer、HTML 绑定、可见读者文本 |
| A2 | 直接引文与来源目录逐条匹配，定位和译文类型正确，来源实际支持相邻声明；无伪署名或无法追溯的事实性外部声明。 | `sources.json` quote/source ID、原文/译文及正文位置 |
| A3 | 用户事实、计算事实、传统解释、心理假说和行动建议没有越级；重要反例、方法分歧、误差及边界保留；无诊断或事件保证。 | claim/evidence 回链、judge/chief 结果、正文原句和限制 |
| R1 | 每个已接受的用户问题及各体系的核心问题（本盘结构是什么、为何这样读、对读者意味着什么）均得到实质回答；没有以空章节、术语表、免责声明或“详见附录”替代正文回答。 | intake 请求 → chart_plan → 正文位置的逐项覆盖；读者可复述的领域判断 |
| R2 | 具体盘面、分数或自述如何进入解释可定位；综合章给出各视角分别增加的理解与合并后的新增理解，而不只是四份摘要或“相互呼应”；个体心理判断有合适的自述/观察支持，并在该层说明可改变判断的观察或缺口。计算事实按输入与方法、传统解释按取法条件审查，不要求每段追加反例或“尚无法检验”。 | claims 与父 claim、反例/限制、成品中逐条可定位的论述及综合段 |
| R3 | 现实建议采用 `{goal,claim_ids,small_action,frequency_or_trigger,review_question,adapt_or_stop}`，低风险、可开始、可复核且可调整；不是空泛劝说或预测依赖项。 | 对应行动选项与正文实施说明 |
| D1 | 正文主题、必要披露、附录、顺序、IDs 与冻结 plan 一致；details 仅位于附录并有唯一 ID，必要限制不隐藏。必须核对本次 `validate_book.py "$WS/book.html" --plan "$WS/chart_plan.json" --evidence "$WS/case_evidence.json" --json` 为 `ok:true`，并将其确切输出 JSON 哈希附入 D1 evidence。怀疑误报只能 blocked 并报告工具缺陷，不能自行豁免。 | 冻结 plan、语义 DOM，以及本次 validator `ok:true` JSON 输出与 SHA-256 |
| D2 | 每个图表有核准计划、有效数据/claim 来源、正确单位与尺度；缺值未补零，坐标和实际显示数值准确。正文解释空间/周期结构时，图确实表达该结构（如十二宫地支格位、周期分面与单位），而不是可复述不出结构的装饰或把全部结构退成无关表格。图数本身不是标准。 | chart_plan 与 `planning_rationale`、HTML figure、SVG/表格和可见数值、正文与图的互指 |
| D3 | 首现术语可理解，术语负担与重复可控；篇章回答清晰、连贯并保有自然文气；每章先讲看见的结构与含义，免责声明不替代解读；流程词、数据字段、审计记录不作为叙事主线；同一信息没有为配额重复堆叠。 | 定位的正文段落、章节承接与读者任务 |
| D4 | 在实际浏览器桌面与 320–430px 窄视口阅读；键盘/链接可用，普通文字对比度至少 4.5:1、关键信息图形至少 3:1；文字和图表在最终渲染中可读（逐图确认字号，不只看 CSS 值）、可重排或局部滚动，无整页横移、裁切、遮挡、隐匿或颜色单独承载信息。正文内 `<details>`、隐藏元素、夹带内容的 HTML 注释任一存在即 D4 fail。 | 实际 viewport、对比度/设备宽度、可见性逐项检查、图表与内容块位置的视觉证据 |
| P1 | PDF 可解析且保留正文、必要披露、附录、表格单元格、引文、首尾和纯矢量图页内容；无丢块/未分类折叠内容。 | exporter JSON、文本提取清单、疑似/不确定页码 |
| P2 | 实际 PDF 分页、图表、长表、字体、书签和阅读顺序可读；正文不低于 12pt、表格信息不低于 9.5pt、图内信息不低于 9pt；无裁切、孤立标题或不能判定的块冒充通过。 | 真实 PDF 逐页/图表视觉检查、实测字号证据与书签导航 |
| P3 | 本次 PDF 与正在审核的 HTML、verdict 和导出记录哈希一致；产物路径和版本对应本次交付。 | HTML/PDF SHA-256、pre/post verdict 与 export JSON |

## 状态规则

- 每项 `verdict` 为 `pass|fail|na|deferred`，并记录 `evidence:{artifact,location,quote}` 与 `reason`。证据必须能让另一位终审者复定位，不用“整体良好”替代。
- `na` 仅用于该项确实不适用，并写出条件依据。D2 无图时，只有已批准的 focused 计划无合适图且核心数据表达完整，才可 `na`；不得因成品漏图而判不适用。无引文时 A2 仍需检查伪署名、来源需求和外部声明，不能直接 `na`。
- `deferred` 仅能用于 `pre_export` 阶段的 P1、P2、P3。其他缺少证据的项不得 defer 或视为 pass。
- `pre_export` 所有适用非 PDF 项通过且 P 组 deferred，decision 才能是 `awaiting_export`；此阶段不得是 `pass`。
- `post_export` 必须复核真实 PDF，P 组不得 deferred。只有 16 项全部 pass 或有依据的合法 na、无 blocker 且 HTML/PDF 哈希匹配时 decision 才能是 `pass`。
- 读者先行：R1/R2/D3 先只读读者稿，记录能够复述的领域判断、推读依据、综合增加的理解及图揭示的结构，再看 evidence 核对。复述不出回答、综合只是四份摘要、或免责声明替代解读，分别按 R1/R2/D3 fail；“每段都有反例/边界句”不是通过理由。A3 仍独立检查虚构、诊断、确定性和越级推断，文学性不能抵消 A3/I3 失败。

## 阻断条件

以下情况至少对应一项 `fail`，并阻断发布：事实/计算错误；假引文或来源不支持声明；请求实质遗漏；未披露且会改变判断的资料/方法限制；隐藏关键披露；从盘面推断疾病、生育、确定事件、能力缺陷或关系成功率；缺失或裁切的正文/PDF内容；HTML/PDF 或 verdict 哈希不匹配；未做实际 PDF 视觉检查。

普通可选美化可列在 `recommendations`，但不得把 16 项中已失败的必过项移到建议、降级或用其他 pass 抵消。不存在加权总分或降级交付。

## 修订归因

每个 fail 均提供 `revision_instructions`：`{check_id,fix_type,owner,claim_ids,section_ids,problem,acceptance}`。`fix_type` 为 `calculation|source|analysis|prose|layout`；上游事实/来源/分析纠错先修证据再更新派生内容。最多一轮 fresh writer 内容修订；layout 受限补丁不重写正文，仍由原 finalizer 复核。完整状态机见 `team-orchestration.md`。
