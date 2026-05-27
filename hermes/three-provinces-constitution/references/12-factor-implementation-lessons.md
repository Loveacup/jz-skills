# 12-Factor Agents 三件套实施教训

> 会话：2026-05-26，基于 humanlayer/12-factor-agents 原文审计 → 实施 EmpireThread + context_tags + human_input_tool
> 状态：全部完成（3 模块 1,209 行代码，86/86 测试全绿，零 Core 侵入）

---

## 实施模式：跳过中书门下直接执行链

### 背景
Phase 1 经历了两次失败：
- v1：中书(planner)产出放 scratch workspace → GC 清除 → 门下 reviewer 报"审查标的物灭失"
- v2：中书再次产出，handoff 摘要声称文件已写入，但实际磁盘为空 → 门下仍然 APPROVE（基于摘要而非文件验证）

### 根因
planner 和 reviewer profile 擅长**文本级分析判断**，但不擅长**文件系统操作**。要求 planner "将设计文档写入磁盘"超出了其有效能力边界。

### 教训
对于**需要代码/文件产出的实施任务**，跳过 planner-reviewer 设计阶段，直接走执行链：

```
❌ planner → reviewer → SHANGSHU → engineer（两轮返修，产物灭失）
✅ SHANGSHU → engineer → auditor → archivist → reviewer（一轮通过）
```

**适用条件**：
1. 方案已在对话中充分讨论（有明确验收标准）
2. 产出是代码/文件而非纯设计文档
3. 之前同类任务的 planner-reviewer 链已证明低效

### 此模式下的角色重定位
- **SHANGSHU**：从"协调已批准方案"变为"确认工部就绪 + 派发"
- **engineer**：承担了部分设计责任（从对话摘要中提取需求直接实现）
- **auditor**：稽核覆盖了原 reviewer 的部分职责（设计合理性判断）
- **reviewer**：退到链尾做终复，不做前置审批

---

## Scratch Workspace GC 陷阱（已知，本次再证）

planner 产出的 artifact 必须写入**持久路径**（`~/.hermes/workspaces/<slug>/`），不能依赖 scratch workspace。
即使任务 body 明确要求持久路径，planner 仍可能只在 handoff 摘要中描述产出而不实际写入文件。

**验证方法**：reviewer 封驳时必须 `ls` 验证文件存在，不能仅读 handoff 摘要。

---

## EmpireThread 集成模式

三模块的依赖关系：
```
empire_thread.py (523行) → 事件流存储 + API
    ↓
context_tags.py (299行) → XML 标签渲染 + to_prompt()
    ↓  
human_input_tool.py (387行) → 人类交互 tool call + EmpireThread 事件写入
```

所有模块均为 regent profile 层实现，不修改 Hermes 核心源码。
集成点：kanban-gate pre_tool_call hook 拦截工具调用自动写入 EmpireThread。

---

## 知识库同步

实施过程中产出的文档已同步至 Obsidian：
- `30-审计/12-factor-agents-原文审计-Hermes对照-20260526.md`
- `10-制度/12-factor-三件套实施方案-20260526.md`
- `10-制度/EmpireThread-*` (4 份)
- `10-制度/request_human_input_*` (2 份)
- `20-实施/context_tags-v1.0-实施记录-20260526.md`
- `20-实施/request_human_input_v1.0_实施记录_20260526.md`

---

## 与 12-factor 原文的最终合规度

```
审计前：~78%（7✅ 5🟡 0❌）
实施后：~95%（F3/F5/F7 三条 🟡 → ✅）
```

最大护城河（F8+F6）：Kanban block/unblock + 门下封驳 = 审批可中断在工具选择与执行之间。
