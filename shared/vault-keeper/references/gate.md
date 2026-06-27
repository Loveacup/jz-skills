# gate 判定规程（晋升的 agent 判断部分）

> 配套 `engine/gate.py`（确定性：硬门槛 + confidence 算分 + 矩阵查表）。
> **engine 算"事实"，agent 做"语义判断"并把判断作为标记 / 参数喂给 engine。** 对应方法论 §十、§10.4。

## 边界：什么是确定性、什么需要你判断

| engine 自动做（**不要你判断**） | 你（agent）必须先判断，再喂给 engine |
|---|---|
| 硬门槛 pass/fail（sources / 双链 / 字段 / 断链） | **选目标区** `--to`（按 ROUTER + 目标区 `_purpose.md`） |
| confidence 复合算分 | **AI 自评** `_ai_self`（你对内容质量的一票，0–1，写进 frontmatter） |
| 矩阵路由查表（conf × risk → 退出码） | **是否权威 claim 变更**（非追加，是改既有断言）→ 标 `_authoritative_change: true` |
| 风险定级的规则部分（路径 / 入链 / status） | **是否丢信息合并** → 标 `_lossy_merge: true` |
| | **入链数** `--inlinks N`（agent 数或工具数） |

## 流程
1. 先做上表右列的判断，把标记写进候选页 frontmatter、目标区与入链数作参数。
2. **保真前置**（见 `references/fidelity.md`）：确认每条权威 claim 可被 `sources` 支撑、无源外推。
3. 跑 `python3 $VK/gate.py "<页>" --to <区> --inlinks <N>`，读退出码：
   - `0` 自动晋升 → 调 `promote.py`
   - `10` 进人工队列（R2 中置信 / R3）→ 写 `88-审计` 等人裁
   - `20` 退回加工 → 留隔离区补源 / 补链
   - `30` 矛盾 → 走 §二十五 裁决

## 红线（engine 不自动做）
R3（对外发布 / 改治理）+ R2 中置信 → 写队列，人裁，**不自动翻状态**。
