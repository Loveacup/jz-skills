# 尚书省强制插入规则（2026-05-25）

## 背景

尚书省 profile（shangshu, kimi-k2.6）已通过 Phase1-3 全量部署：L1 智能派发、L2 主动协调、L3 汇总呈报。但多次实战测试中未调用——全板仅 2 个 shangshu done 任务。

## 根因

1. 监国太子建 Kanban 链时默认模式为 `planner → review → engineer → auditor → archivist`，从未自动插入尚书省
2. `morning-news-briefing` 和 `kanban-orchestrator` skill 的"通路 C 跳过部门盘点"被泛化为"跳过尚书省"
3. 尚书省不只是"部门盘点"，它是执行总枢

## 强制规则

**任何多步骤 Kanban 链，门下封驳通过后必须插入尚书省协调卡。**

标准链：`planner → reviewer → SHANGSHU → [engineer, auditor, archivist] → final reviewer`

不得以"固定链路/通路 C 简径"为由绕过。跳过的是 pre-planning 部门盘点，不是尚书省在 execution chain 中的协调位置。

## 尚书省 card body 模板

```markdown
【尚书省协调】上游：门下封驳 <tid> 通过后接手调度。

L1 派发：确认工部/御史/史馆的 assignee 与工具正确，如有 mismatch 则 reassign。
L2 协调：跟踪进度，blocked/running超时主动恢复(≤2次)，超限建 decision card 请太子裁。
L3 汇总：全部完成时合成 final-results，呈太子复命。

约束：不改代码、不改 core、不亲操工部/御史/史馆的具体执行。
summary 必含 delivery_required=yes fan_in_status=...
```

## 已修补文件

- `morning-news-briefing/SKILL.md` — 通路 C "跳过"→"简径" + 警告
- `kanban-orchestrator/SKILL.md` — 强制插入规则 + pipeline 更新
- `three-provinces-constitution/SKILL.md` — 尚书省段强制插入规则
