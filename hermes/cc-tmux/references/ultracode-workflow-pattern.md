# Ultracode Dynamic Workflow 模式

> 2026-06-16 首次成功使用。用 CC 原生 `ultracode` / dynamic workflow 做深度调研，13 个 subagent 并行产出 29k 字符 synthesis + 785 行整合方案。

## 什么是 Ultracode

CC v2.1.154+ 的 Dynamic Workflows 功能。CC 写一段 JS 编排脚本，独立 runtime 在后台执行，协调最多 16 个并发 subagent、总计 1000 个 agent。

## 触发方式

- **手动**：prompt 中含 `ultracode` 关键词，或自然语言 "use a workflow"
- **自动**：`/effort ultracode` → 每个实质性任务自动规划 workflow
- **适用模型**：Opus 4.8（Pro/Max/Team/API 均可）

## 何时用 vs 不用

| 用 workflow | 用 cc-tmux agent team |
|---|---|
| 宽而同质 fan-out（≥8 独立单元：批量迁移/全库审查/多源交叉研究） | 需持久第二工程师（跨多轮存活/可中途 steer/须外部 gate+人审） |
| 不需中途转向、不需人审签字 | 任务中途需人/agent 拍板转向 |
| 产物不需要 survive CC 退出 | 产物/进度须 survive CC 退出 + 须外部脚本独立 gate |

**两个一票否决**（命中即排除 workflow）：
- 任务中途需人/agent 拍板转向 → workflow 禁（无 mid-run input）
- 产物须 survive CC 退出 / 须外部脚本独立 gate → workflow 禁（退出即重跑）

## 本次实测数据

| 指标 | 值 |
|---|---|
| 任务 | cc-tmux skill 深度优化调研 |
| agent 数 | 13（1 Ground + 6 Analyze + 6 Verify）+ 1 补 D4 |
| 编排结构 | Ground → Analyze(6 维并行) → Verify(对抗核验) → Synthesize(整合) |
| 耗时 | ~25min workflow + ~10min leader 整合 |
| token 消耗 | ~913k |
| 产出 | 29k 字符 synthesis + 785 行整合方案 |
| 失败 | 1 agent（D4 stream timeout，后单独补回）|

## 编排设计原则

1. **Ground 先行**：一个 agent 核实外部事实地基（API 能力、当前状态），给后续分析提供事实约束
2. **Analyze + Verify 配对**：每个分析维度配一个对抗核验 agent，核验只判 sound/flawed/uncertain/violates
3. **Synthesize 只纳核验通过的提案**：被标 violates 的剔除，flawed/uncertain 的标修正
4. **Leader 补盲**：workflow 中失败的维度由 leader 单独补 subagent 或实读脚本填补

## 成本意识

- 913k tokens 的单次深度调研 ≈ $0.90（Opus 4.8）
- workflow 运行时 CC leader 的 context 持续增长
- 建议：调研类 workflow 后立刻 `/clear` 或新 session 继续落地

## 监控

- CC pane 底部显示 `◯ workflow-name  N/M agents done · failed · time · tokens`
- `/workflows` 进入 TUI 监控界面（↑↓ 选 agent、Enter 看详情、p 暂停、x 停止、s 保存）
- 注意：workflow 跑完后 CC 需要额外时间整合（"✽ Hashing…" 等状态），不是卡死

## 嵌套使用

CC 长会话里可 launch workflow 跑 mass-parallel 子步（如审 200 文件），外层保留 "可 steer 持久 peer"：
- Context 强制 CC 在 workflow 各阶段 echo 进度到 `/tmp/cc-progress-*`
- Monitor 以磁盘文件为准而非 pane
- 外层 team 在内层 workflow 运行时不再起并行 CC
