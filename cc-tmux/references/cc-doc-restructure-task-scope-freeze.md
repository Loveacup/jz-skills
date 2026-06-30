# CC 文档重构任务冻结：任务 scope 与模型行为

> 2026-06-27 实发：Opus 4.8 high effort 在「完全重构模型配置文档」任务上思考 12+ 分钟无输出。

## 症状

- CC `cc-send` 后开始思考，`cc-monitor` 显示 `THINKING`
- "Considering… (N min · almost done thinking with high effort)" 持续 >8 分钟
- 无工具调用、无文件写入、无 token 增量显示
- 配置数据已收集（命令产出文件已写盘），但 CC 在规划阶段卡住

## 根因

**任务 scope 过宽 + Opus 4.8 high effort 的"全面规划"倾向**：

- "完完整整重构这份文档" = 一个巨型任务：读文档 → 收集配置 → 分析差异 → 设计方案 → 写三套方案 → 附具体命令
- Opus 4.8 在 high effort 下会把所有子任务一次性规划完再动手，而不是边做边改
- 10+ 个配置段 × 3 Profile × 3 方案 = 大量决策点在思考阶段同时展开 → 分析瘫痪

## 正确做法

**把大任务拆成小任务，逐步迭代**：

```
❌ 错误：「完完整整重构这份文档」
✅ 正确：
  1. 先让 CC 读文档 + 收集配置 → 汇报发现
  2. 再让 CC 更新"可用模型清单" section
  3. 再让 CC 补"三方案配置" section
  4. 最后让 CC 校对 + 润色
```

**拆分原则**：
- 每个子任务 ≤1 个"写"操作（改一个 section）
- 子任务间留讨论空间（Hermes 审核 + 纠偏再派下一个）
- 不要让 CC 同时规划"分析 + 设计 + 实现 + 校验"

## 与已有 Pitfall 的关系

- **Pitfall #14** 针对 xhigh effort + 工程实现，本案例是 **high effort + 文档重构**
- **`cc-overthinking-writing-tasks.md`** 针对 xhigh 写作任务，本案例扩展了 effort 范围
- **Pitfall #27** 针对工作流顺序（Hermes 先写文档再调 CC），本案例是 CC 自身的 task scope 问题

## 恢复方法

若已卡死：
1. `C-c` 中断 CC
2. 收窄任务 → 重新 `cc-send`
3. 或降 effort → `cc-start --effort high`（若已是 high 则维持）

## 预防

- CC 任务的 context 里明确写：**"按顺序执行，每完成一步先汇报再继续"**
- 重构类任务优先用 Agent Team（拆关注点并行）
- 首轮只用 CC 做**只读分析 + 汇报发现**，确认方向后再派写入
