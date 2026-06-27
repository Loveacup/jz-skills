# CC Overthinking on Document Writing Tasks

## 症状
CC 以 xhigh effort 执行纯文档写作任务时，可能陷入 5min+ 思考循环，token 完全冻结，持续显示「almost done thinking」但不产出任何内容。

## 根本原因
xhigh effort 的深度推理引擎在纯文档任务上没有足够的「工程复杂度」来消耗算力，反而陷入过度规划。文档任务的结构是线性的（标题→段落→代码块），不需要 xhigh 级别的多路径搜索和交叉验证。

## 恢复方法
1. **Ctrl+C 中断**思考循环
2. **简短重定向**：发一行「简短回复：直接写入文件。」（不是新任务描述）
3. CC 在中断后会压缩上下文、跳过过度规划，通常在 1min 内完成

## 预防
- 文档写作、指令格式化等线性任务用 `--effort high`（不是 xhigh）
- xhigh/max 保留给架构设计、多文件重构、根因调试等需要深度推理的任务
- 规则：**复杂度不明确时用 high，确认复杂再升 xhigh**

## 复现记录
- 2026-06-16：CC xhigh 写 63 行 Obsidian 笔记，思考 5min+ token 冻结，Ctrl+C→重定向后 51s 完成
- 2026-06-17：CC xhigh cc-monitor TDD 实现，**49 分钟 stuck 在 `✽ Inferring… (46m 28s · thinking some more)` 状态**。token 和屏显完全冻结，但 CC 不报错、不崩溃。Ctrl+C → `/effort high` +「缩小范围，不要过度工程，直接产出代码」→ 恢复产出。**教训：xhigh + 工程实现类任务极度易冻结；发现 stuck >5min 立刻 Ctrl+C 降 effort 缩小范围，不要等。**
