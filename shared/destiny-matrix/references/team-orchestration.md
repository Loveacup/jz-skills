# Agent Team 执行流规范（destiny-matrix v4 orchestration）

> v4 核心架构文档，参照 strategic-insight-longform 同名规范改写。本 skill 以 **Leader + 多 teammate + Stage DAG（S0-S10）** 运行：Leader 只路由不代笔，数据走 task I/O 不落盘中间件。各 agent 详细契约见 `agents/*.md`。
>
> **v4.1 · harness 中立**：本文只用中立编排动词（`dispatch / barrier / collect / message / fresh_spawn / ask_user / teardown`）与能力词（§9）。落到具体工具的映射只在 `runtime-omp.md` / `runtime-cc.md` 各出现一次；Leader 第 0 步按自身工具表判定运行时（§10）。

---

## 0. 三条铁律

1. **数据走 task I/O，不走盘**：teammate 产出结构化结果 → Leader 读取 → 注入下游 prompt。落盘文件只有三类：最终 `{命主名}_命书.html`（book-writer 唯一写）、PDF（Leader 跑 `scripts/export_pdf.py`）、跨会话 `memory/analysis-sessions/`（归档单独收口）。
2. **依赖全显式**：按 Stage 分批 `dispatch`，本批 `barrier` 全部送达后才派下游；下游派遣 prompt 只注入已 `collect` 的上游产物，无隐式顺序。
3. **写盘所有权单一**：只有 book-writer 写 HTML、Leader 跑 PDF 脚本、memory 归档单独收口。其他 teammate 一律不写盘（`$WS/<席位>/` 临时输入文件除外，§10），杜绝抢写。

## 1. 判官隔离铁律（v4 防叙事传染的结构性保证）

- S4 四位判官（judge-jung/bazi/ziwei/astro）在**全新上下文**运行，**只接收对应排盘原始 JSON，严禁给 S3 成稿/素材**。
- 判官只出独立推论；**判官产出与 analyst 成稿的分歧对比只在 chief-judge 处发生**。
- Leader 派遣判官时的 prompt 里不得引用、转述、摘要任何 analyst 文本；判官发现输入混入叙事成稿必须中止上报污染。
- chief-judge 一致性评级 ≤ ★★ → 打回对应 analyst 修订，该维判官流程重跑。
- v3 靠自觉，v4 靠上下文隔离——这是本条存在的全部理由。
- **v4.1 · 数据层与通道层隔离**（2026-08-13 三位判官报出的三条污染路径逐条封堵）：
  1. 脚本层：排盘脚本默认不再输出 `性格映射提示`（需显式 `--hints`，判官链路永不加）；caster 交付前核验 JSON 中无该字段。
  2. 任务层：「本案历史归档是否被污染」这类核查派给 external-verifier（第四方），不得派给判官；判官输入不含 `memory/analysis-sessions/`。
  3. 通道层：判官各自的 JSON 写在**本席位的 task 正文**里；批次共享背景（omp 的 batch `context` 会注入同批每个子代理）只放四位判官都可见的中性材料（locked-checklist 相关条款、禁词表、时刻口径说明），不放任何一维 JSON、不放任何成稿。判官不拿 `$WS` 以外的共享目录路径（§10）。
  4. **污染分级处置（唯一规则源；judge-*.md 与 omp 的 dm-deep 均按此执行）**：🔴 一级——输入混入叙事成稿/他席产出 → 判官中止并上报，Leader 清洗输入后重派；🟡 二级——JSON 含 `性格映射提示` 字段或本案历史归档 → 判官不读该内容、在 `confidence_notes` 首条披露后继续。两级都「主动披露不扣分、隐瞒才扣分」。

## 2. fresh-writer 修订流（v4 修订铁律）

S9 book-finalizer 出现 🔴 级 fail（M/C 组任一）→ `decision: revise`：

1. finalizer 产出 `revision_instructions`（逐条「问题—位置—改法」+ 优先级）。
2. **Leader 派全新 book-writer 实例**（干净上下文），注入：① revision_instructions ② 相关素材切片（各 findings / chart_plan）③ 未受影响章节全文（含被拒章节的前后邻章，作衔接锚定）。
3. **不注入被拒章节原文**——失败稿留在上下文会让重写结构性继承原错误；被拒章节从素材从零重写。
4. 修订稿回 finalizer 复审。**max 1 轮**；仍不过 → 降级交付 + `defect_disclosure` 显式披露缺陷清单。
5. 不 `message` 给原 writer 原地改——原 writer 带着被拒稿上下文；修订一律 `fresh_spawn`。

## 3. 委派五要素（每条派遣 prompt 必须齐备）

模糊短指令是多 agent 头号失败模式。每条派遣 prompt 显式包含：

1. **目标**：本 agent 要回答的问题（一句话）；
2. **输出 schema**：结构化返回的字段与键序（引用对应 `agents/{name}.md` 契约）；
3. **工具与来源指引**：用什么工具/脚本/references，来源优先级；
4. **任务边界**：明确**不做什么**（如「不做印证矩阵，那是 S5 的事」）；
5. **努力度区间**：预期工具调用次数（见 §6），超界须在输出中说明理由。

派遣统一走 `dispatch`：每个席位一个独立 task，任务名 `Dm<席位CamelCase>`（如 `DmJudgeBazi`），档位按 §11 分档表；席位契约 `agents/{name}.md` 全文注入 task 正文。agent `.md` 里的「工具」段是能力声明（§9），实际通道以 preflight 生成的 capability_map 为准。能给结构化 schema 的席位（`schemas/*.json`，§12）派遣时一并挂上，由 harness 强校验。

## 4. Stage DAG 与并行

```
S0 → S1 → S2 → S3[4并行] → S4[4判官并行 → chief-judge] → S5 → S6[2并行] → S7 → S8 → S9 → S10
```

- 并行 stage 一次性 `dispatch` 全部，`barrier` 等本批全部送达，不 busy-loop 死轮询。
- 串行 stage：dispatch → 等 completed → 读输出 → dispatch 下一个。
- 某 teammate 失败 → 标 failed → 能降级则降级（如外部某比对源不可达换备源），不卡整条流水线；不可降级的 Gate 缺口（如 G1 四柱缺失）→ 停线报用户。
- task 输出过大 → teammate 只返回结构化摘要，大块留各自上下文。

## 5. 数据契约表（S0-S10）

所有中间产物均为 **task 输出的结构化结果**（非落盘 JSON）。✦ = 真文件。**键序铁律：推理/证据字段一律排在判断/结论字段之前**（结论键在前会诱发跳过推理直接作答）；分析型 agent（S3/S5/S6/S7/S9）一律 **NL-to-Format**：先自然语言完成推理，最后一步才组装结构块。

| Stage | Teammate | 消费（输入） | 产出（结构化返回） | Gate |
|---|---|---|---|---|
| S0 输入核验 | intake-refiner | 用户输入 + memory 历史匹配 | `intake_brief`{template_check, tier_routing, subject, known_events, focus_weights, synastry, open_gaps} | — |
| S1 排盘 | caster | intake_brief | `chart_bundle`{commands_run, known_issue_checks, bazi/ziwei/astro/jung_json, g1_checklist, boundary_warnings} | **G1** 数据齐备 |
| S2 外部验盘 | external-verifier | chart_bundle + known_events | `verification_report`{sources_used, comparison_table(7点), boundary_alerts, event_backcheck, hour_verdict三档, disclosure_for_book} | **G2** 三档明示 |
| S3 分维 ‖ | jung-analyst | jung_json + intake_brief | `jung_findings`{八功能, Beebe八原型, Grip, Fi, 发展阶段, **character_signature**, chapter_material} | **G2.0** 签名齐备 |
| S3 ‖ | bazi-analyst | bazi_json + signature + disclosure | `bazi_findings`{四柱/五行/十神/格局/喜用调候/神煞/感情星/大运流年, signature_echoes, **explanatory_rating**, chapter_material} | **G2.x** 评级齐备 |
| S3 ‖ | ziwei-analyst | ziwei_json + signature + disclosure | `ziwei_findings`{主星亮度/四化/全辅星/杂耀/五宫/格局/大限, signature_echoes, **explanatory_rating**, chapter_material} | 同上 |
| S3 ‖ | astro-analyst | astro_json + signature + verification | `astro_findings`{三轴/十行星/宫主/相位/世代/关系模式/行运, signature_echoes, **explanatory_rating**, chapter_material} | 同上 |
| S4 ‖ | judge-jung/bazi/ziwei/astro | **仅对应原始 JSON**（隔离铁律） | `judge_*_verdicts`{reasoning_trace, independent_inferences(json_evidence在前), confidence_notes} | — |
| S4 | chief-judge | 4 judge_verdicts + 4 findings | `consistency_report`{comparison_log, discrepancies, **consistency_rating**, verdict, revise_targets, disclosure_for_book} | **G4** ≤★★ 打回 |
| S5 综合 | synthesizer | 4 findings + consistency_report | `synthesis`{三维印证矩阵, 印证度四档, 命运密码3-5(公式显性), 终极课题(必出自劣势/阴影), 双轨时间线, chapter_material} | **G3/G5** |
| S6 ‖ | love-specialist | findings 切片 + synthesis + intake | `love_findings`{荣格动力学(含Beebe Child+Inferior), 三维应期, 给予/需要, 已发生阶段明判, 演化预测, chapter_material} | **Gate 5** 四要件 |
| S6 ‖ | growth-specialist | synthesis + findings 切片 | `growth_findings`{5条可塑路径(功能原型+行为练习+应期窗口), health_section按需, chapter_material} | **G6** |
| S7 图表规划 | chart-director | 全部 S3-S6 素材 + chart_bundle | `chart_plan`{planning_rationale, chart_table(逐行契约), quota_check, anchor_six_check, total≥26} | **G7** 配额+六锚点 |
| S8 成文 | book-writer | 全部素材 + chart_plan + 两份 disclosure | ✦ `{命主名}_命书.html`（唯一写盘）+ writing_report | — |
| S9 终审 | book-finalizer | ✦ html + chart_plan + locked-checklist | `final_verdict`{checklist_results(M/C/W/E/P 逐项+引证), validator_output, visual_qa, decision, revision_instructions} | **G9** 🔴→修订流 |
| S10 交付 | Leader | ✦ html | `$DM_PY $DM/scripts/export_pdf.py` → ✦ PDF；P 组核验回填 → 双产物交付 → 会话存档 memory/ | **P 组** |

v3 Phase ↔ v4 Stage 映射：Phase 1→S1，1.5→S2，2.0-2.3→S3，3.5→S4，3+4→S5，5→S6，6→S7-S10。Gate 内容全部保留并指向 `references/locked-checklist.md` 的固定 ID。

## 6. 努力度基线表（V4_PLAN §7 基线）

| Agent | 预期外部工具调用 | 说明 |
|---|---|---|
| external-verifier | **5-12 次检索/抓取** | 前段唯一联网角色；7 校验点 × 每体系 2-3 源 |
| jung/bazi/ziwei/astro-analyst 各 | **0-3 次典籍核查性检索** | 仅核对引文出处，不外扩论断 |
| judges（4+chief）/ book-writer / book-finalizer | **0 次联网** | 只消费上游产物；证据缺口标「待定」上报，不自行补搜 |
| intake-refiner | 0 次联网；【问用户】由 Leader 代问 0-3 问 | 能推断则不问；缺口写进 `questions_for_user` |
| caster | 0 次联网；脚本 2-6 次 | 含失败重试 |
| synthesizer / love / growth / chart-director | 0 次联网 | 纯消费上游 |

> 区间是**自我校准锚**不是熔断器：超界继续做（质量优先），但必须写明理由——用于事后归因。

## 7. 反模式清单

| 反模式 | 症状 | 修复 |
|---|---|---|
| Leader 代笔成文 | 素材被压成概要、章节权重崩 | S8 必派 book-writer 独立成文 |
| 判官读到成稿 | 判官措辞出现 analyst 比喻 | 派遣 prompt 只含原始 JSON；污染即重派 |
| 原 writer 原地改被拒稿 | 修订稿继承原错误 | fresh-writer 修订流（§2） |
| 中间产物落盘 | stale 文件/路径漂移/上下文污染 | task I/O；临时文件只进 `$WS/<席位>/` |
| 跳过 barrier | 排盘没完就有人开写 | 按 Stage 分批派遣，本批送达才派下游 |
| finalizer 凭感觉打分 | 无引证 pass/fail | locked-checklist 逐项二元 + 强制引证 |
| 忘记 teardown | 残留子任务/后台作业 | cleanup 固定在 S10 归档之后 |
| 共享通道混入判官输入 | 判官措辞出现 analyst 比喻 / 知道他维结论 | 判官 JSON 只进本席位 task 正文；批次共享背景只放中性材料（§1.3） |
| 用 PATH 上的 python3 跑脚本 | 缺依赖报错、S10 PDF 断 | 一律 `$DM_PY`（§10），preflight 核验 |

## 8. 成熟度检验（每次升级编排后自检）

- [ ] 每个 teammate 产出字段固定（§5），推理/证据键排在结论键之前
- [ ] 每条派遣 prompt 含委派五要素
- [ ] 判官 prompt 零成稿泄漏；分歧对比只在 chief-judge
- [ ] 所有下游 Stage 均在上游 barrier 之后派遣
- [ ] 无 teammate 越权写盘（仅 book-writer / Leader-PDF / memory 归档）
- [ ] 🔴 fail 走 fresh-writer 修订流且 max 1 轮
- [ ] Gate 全部指向 locked-checklist 固定 ID
- [ ] teardown 在最后，无残留
- [ ] 判官输入无 `性格映射提示`、无成稿、无历史归档；批次共享背景只含中性材料
- [ ] trace 记录每席位实际模型与是否 fallback（§11）

## 9. 能力词（agent 契约只写能力，不写工具名）

| 能力词 | 含义 | 主要使用者 |
|---|---|---|
| 【读文件】 | 读 skill 内 references / agents / memory 与脚本输出 | 全部 |
| 【跑脚本】 | 以 `$DM_PY $DM/scripts/<脚本>.py` 运行计算与校验脚本 | caster、book-writer（chart_data）、book-finalizer（validate_book）、Leader（export_pdf） |
| 【写成书】 | 写 `{命主名}_命书.html`（唯一写盘席位） | book-writer |
| 【写临时】 | 写 `$WS/<席位>/` 下临时输入文件 | caster、book-finalizer |
| 【网页检索】 | 通用 web 检索 | external-verifier；analyst 典籍核查（0-3 次） |
| 【抓网页】 | 读取服务端渲染页面正文 | external-verifier |
| 【真实浏览器】 | 需 JS 渲染 / 表单提交的在线排盘源；截屏 | external-verifier、book-finalizer 视觉 QA |
| 【问用户】 | 向用户提问；**只有 Leader 可用**，teammate 把问题写进结果由 Leader 代问 | intake-refiner（经 Leader） |

某能力在本端不可用 → 结果写「降级：<能力词>→<实际通道>」或「无法核验」，不静默替换；S2 源全不可达按 SKILL.md 规则标注不阻断。

## 10. 运行环境与工作区（第 0 步 preflight）

1. **判定运行时**（按工具表能力，不看版本）：有 `task` 子代理工具且可用 `write agent://<id>` 发消息 → omp，读 `runtime-omp.md`；有 `Agent` 工具 → cc，读 `runtime-cc.md`；都不像 → 报告后停止。
2. **跑 doctor**：`<任意 python3> $DM/scripts/doctor.py --json`。它输出 `dm_root`（即 `$DM`）、`dm_py`（即 `$DM_PY`，依赖齐备的解释器）、依赖、playwright 浏览器、判官隔离自检、回归结果与 omp 适配件状态；🔴 项非 0 退出 → 停线报用户，不降级运行。
3. **工作区**：`$WS=/tmp/dm-<命主拼音或slug>-<yyyymmdd>/`，每席位一个子目录 `$WS/<席位>/`；只把本席位子目录路径交给该席位。**不用 omp 的 `local://`**——同一会话所有子代理共享同一 `local://` 根，等于把判官放回共享黑板（known-issues「harness 文件推送」同类路径）。
4. Leader 在每批派遣正文里注入：`$DM`、`$DM_PY`、本席位 `$WS/<席位>/`、capability_map、委派五要素。

## 11. 模型分档（只引用 harness 自带角色，不写模型 ID）

| 档 | 席位 | omp agent（frontmatter model） | cc |
|---|---|---|---|
| deep | judge-jung/bazi/ziwei/astro、chief-judge、synthesizer、book-writer（含 fresh-writer）、book-finalizer | `dm-deep`（`@slow` → `@default`） | `inherit` |
| research | external-verifier、jung/bazi/ziwei/astro-analyst、love-specialist、growth-specialist、chart-director | `dm-research`（`@default` → `@slow`） | `inherit` |
| light | intake-refiner、caster | `dm-light`（`@smol` → `@task`）；失败用 `dm-research` 重跑 | 家族别名（如 `sonnet`） |

- 换模型只改 harness 的角色映射（omp `/model` → Roles；cc `/model`），skill 与 agent 文件不动。只调某一档用 omp `task.agentModelOverrides`（值仍写角色）。
- 每席位 collect 时记录实际模型与是否 fallback，写进会话归档 `runtime_trace`；工具未返回实际模型时记「缺失」，不从计划档位推断。
- 判官 4 席必须同档：分档不同会把「模型差异」混进「一致性评级」。

## 12. 结构化契约（schemas/）

`schemas/` 收录可机器强校验的席位产出 JSON Schema：`judge_verdicts.json`（四判官共用）、`consistency_report.json`（chief-judge）、`chart_plan.json`（chart-director）、`final_verdict.json`（book-finalizer）。字段与键序以 `agents/*.md` 为准，schema 只把它变成可校验的形状；改契约时两处同步。`chart_plan` 同时是 `validate_book.py --plan` 的输入。
