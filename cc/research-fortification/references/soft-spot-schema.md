# 软处 Schema（14 字段）+ point-by-point 台账

> 从 Insight Units 提取 N 个「软处」(Soft-Spot)。每个软处是一条贯穿 P1→P5 的可追溯记录，字段随阶段递进填充。**`sid` 是全程追溯键。**
> 提取数量 N（质量重于数量）：Quick 6-10 / Standard 10-18 / Deep 18-30。**N 是上限预算 + 相关性阈值，不是填够的配额**——软处数随基底承重断言数自然定：短稿/承重断言少时少于下限是合规的，别为凑数稀释承重相关性。超量只留承重相关性最高的前 N，低优先 corrective 合并批处理。

## 字段定义表

| 字段 | 含义 | 取值 | 填充阶段 |
|---|---|---|---|
| `sid` | 软处唯一 ID，全程追溯键 | `SS-01`…`SS-N` | P1 |
| `load_bearing_claim` | 所在的**承重论点**（塌了全文结论就动摇的关键 claim） | 一句承重断言 | P1 |
| `base_anchor` | 软处在基底文档的物理定位 | 段落/行号/小标题 | P1 |
| `softness_type` | 软处性质 | {论证断层, 证据缺位, 反例未防御, warrant缺失, backing缺失, 口径过强, 结构错位, 措辞含糊} | P1 |
| `fw_surface_meaning` | Faigley-Witte 纵轴 | {表层, 意义} | P2 |
| `fw_micro_macro` | Faigley-Witte 横轴 | {微观命题, 宏观论旨} | P2 |
| `revision_polarity` | 加固投入性质 | {additive, corrective} | P2 |
| `evidence_anchor` | 加固依据的证据 | 基底引文 / 洞察引文 / 外部 URL / 运行日志 | P3 |
| `claimcheck_status` | 反幻觉：该批评点本身在基底是否有据 | {grounded, hallucinated→剔除, needs-external} | P3 |
| `escalation` | 审定门分流：本软处是 Hermes 自核还是上报用户（gate-prep 判据见 team-orchestration.md §3） | {auto, user}（拿不准归 user） | P3 |
| `weld_strategy` | 焊接策略（见 weld-strategy.md） | {整章注入, 措辞纠偏, 口径降格} | P3 |
| `target_position` | 焊回基底的落地位置 | 段落 / 「新增于 X 后」 / 「替换 Y」 | P3/P4 |
| `weld_result` | 焊接后实际写入的文本引用 | 终稿引文/锚点 | P4 |
| `critique_utility` | 落地验证：洞察是否真改善文档 | {injected, partial, not-landed→回流} | P5 |
| `macro_consistency` | 焊回后是否破坏宏观一致性 | {consistent, conflict→复焊} | P5 |

> **填充阶段在 2-run / 合并档下的对齐**：RUN-1（P0-P3）填 `sid … escalation` + `weld_strategy` + `target_position` 初值；**P4/P5 字段 `weld_result`/`critique_utility`/`macro_consistency` 在 RUN-1 留 `PENDING`**，由 RUN-2 welder/verifier 补。Quick 档把 P2+P3 合一个 agent 时，这些字段**一次性填**，「填充阶段」列只标语义归属、不要求分步。

> **softness_type 允许复合标注**：一处软处可跨类型（如「形态联想」= `口径过强 + warrant缺失`），用 `主+次` 记全（尤其 N=1 单 lens 命中跨类型软处时，把另一 lens 域的类型也记上，别漏命名）。**主导类型决定 weld_strategy**（按 weld-strategy 决策树用主导 type 选策略）。

## warrant缺失 vs backing缺失（预算分野，必分清）

- **warrant缺失**：数据与结论都在，独缺那座「凭什么由此及彼」的隐含推理桥（如 X 像 Y ⇒ X 能照搬 Y）。桥没说出口而已——**补出隐含许可一句话/一两段即可**，多为微观、便宜。
- **backing缺失**：推理桥*说了*，但桥本身（「这类现象由这类根因导致」这条规则）没有机制、先例或理论背书——桥墩悬空。**必须成段成章把背书层建起来**，天然宏观、昂贵，走整章注入。

> 混判即误投：warrant缺失被过投会浪费整章注入额度；backing缺失被欠投则桥墩仍悬空。

## 单软处填充示例（通用模板）

| 字段 | 取值示例 |
|---|---|
| `sid` | SS-01 |
| `load_bearing_claim` | 「某通道是业务触达的骨干」——整篇承重前提 |
| `softness_type` | 证据缺位 + 口径含糊 |
| `fw_surface_meaning` / `fw_micro_macro` | 意义层 / 宏观论旨 |
| `revision_polarity` | additive |
| `claimcheck_status` | grounded |
| `weld_strategy` | 整章注入 |
| `critique_utility` / `macro_consistency` | injected / consistent |

## point-by-point 台账格式（= 焊接质检单 = Response-to-Reviewers 回复信）

每行一个 `sid`，列：
```
sid | W编号 | [已落地/未落地/调整] | 载入位置(章节/行号) | weld_strategy | claimcheck_status | critique_utility | macro_consistency
```
终稿附此台账即可被 G2 逐点核验。
