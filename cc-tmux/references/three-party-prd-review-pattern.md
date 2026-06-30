# Three-Party PRD Review Pattern (Hermes + CC + Codex)

> 2026-06-28 实发：MATT Skills Fork PRD 审阅。用户要求"拉起 Codex 和 CC，你们三方讨论"。

## Pattern

当用户要求多方 agent 共同审阅/讨论文档时：

1. **Hermes (小黄)** = 协调者 + 汇总者
   - 准备统一的 context 文件（任务目标、背景、待讨论问题清单）
   - 启动 CC（审阅深度分析）
   - 启动 Codex（规划/架构分析）
   - 监控各方状态，汇总结果
   - 产出统一汇报

2. **CC (Claude Code)** = 深度审阅者
   - 读取文档，逐条分析
   - 产出结构化审阅意见（分级：P0/P1/P2）
   - 识别方向性问题和返工风险

3. **Codex** = 规划/架构分析者
   - 分析技术可行性
   - 评估工作量假设
   - 识别架构风险

## Workflow

```
Hermes 准备 context → 启动 CC + 启动 Codex（并行）
  ↓
CC 审阅文档 → 产出审阅意见
Codex 分析架构 → 产出分析报告
  ↓
Hermes 汇总两方结果 → 统一汇报给用户
  ↓
用户决策 → 进入执行阶段
```

## Key Lessons from 2026-06-28 Session

1. **Context 文件必须包含正确的文件路径**——CC 第一次尝试的路径 `/Users/alexcai/code/agent-hub/matt-skills/docs/PRD_MATT-Skills-Fork.md` 是错误的，实际在 Obsidian vault。应在 context 中显式写明正确路径。

2. **CC 可能弹出 AskUserQuestion**——当任务不明确时，CC 会弹出交互式选择。Hermes 需要及时响应（选择选项 + 提供补充信息）。

3. **Codex delegate_task 是后台异步的**——结果自动注入对话，不需要 process 轮询。

4. **先规划后执行**——用户明确要求"先别动手，先把技术文档的规划做好"。这是 workflow 纠正：讨论/规划阶段不执行任何文件修改。

## Pitfall: 急于执行 vs 先规划

**症状**：用户给出一个任务（如"改造 skill"），Hermes 立即开始修改文件。
**原因**：误解了"讨论"和"执行"的边界。
**修复**：
- 用户说"讨论/审阅/规划"→ 只读分析，不修改文件
- 用户说"执行/动手/改"→ 才进入执行阶段
- 不确定时，先问"这是讨论还是执行？"

## Context Template for Three-Party Review

```markdown
# <Topic> 三方讨论任务

## 目标
<明确讨论目标>

## 背景
<关键背景信息>

## 待审阅文档
- 路径：<绝对路径>
- 版本：<版本号>

## 需要讨论的问题
1. <问题1>
2. <问题2>
...

## 交付物
<预期的产出>

## 约束
- 只读分析，不修改任何文件
- 输出到 /tmp/cc-output-<topic>/
```
