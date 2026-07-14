# 实施前 OMP 审计：合同设计

## 适用场景

当实现尚未开始、需要 OMP 审查最小方案或数据契约时，审计对象是**设计可行性**，不是仓库当前是否已经具备目标功能。

## 常见误判

若 criterion 写成“`X` 必须存在 / 当前 formal gate 必须 fail-closed”，OMP 会正确地发现尚未实现并给出 `blocker`。这对实施前审计没有决策价值，只是把待办事项复述一遍。

## 正确的实施前 criterion

将条件改写为可裁决的设计问题：

- proposed canonical reference 是否消除旧 ID 的歧义，同时保留公开协议；
- 新旧数据如何用 schema/version 区分，避免兼容分支掩盖新数据缺陷；
- gate 应放在哪个边界，哪些 debug/legacy 路径不应受影响；
- 哪些最小 RED 测试能证明设计处理了冲突、缺失和降级。

Prompt 明确说明：**不要以“当前还未实现”作为 blocker；仅当方案本身会破坏兼容性、无法满足 criterion、或范围越界时才报 blocker。**

## 实施后审计

实现完成后再单独起一个 audit task，并把 criterion 改回实际合同：检查 diff、独立运行 targeted tests、确认 gate 路径/版本标记/边界行为。不要复用实施前的 state-audit 结论。

## 视频分析器 P6-A 示例

对 section-local `E1` 需要保持 writer 的 `[E#]` 文本协议时，使用内部 canonical location（如 `3:E1`）加版本化 bundle。正式 gate 读取 canonical pointer；legacy 未版本化 bundle 可以 skip，而 versioned bundle 缺失或无法解析 pointer 必须 fail closed。语义蕴含验证属于后续 QA 层，不要把 pointer-integrity gate 表述成 entailment proof。
