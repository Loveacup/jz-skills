# mattpocock/skills → 三省六部 完整映射 v0.7

> 来源：Claude Code agent team 分析产出
> 日期：2026-05-18
> 产出路径：~/.hermes/kanban/workspaces/t_29e41f24/mattpocock-skills-三省六部-完整映射-v0.7.md

## 总览

17 个 skill 评估完毕，分四级：

- ⭐⭐⭐ 直接嵌入 (6): grill-with-docs→planner, diagnose→engineer+auditor, to-prd→planner, to-issues→dispatcher, handoff→archivist, tdd→engineer
- ⭐⭐ 改造嵌入 (6): triage→reviewer, zoom-out→auditor, prototype→engineer, improve-codebase-architecture→engineer, grill-me→planner, git-guardrails→security
- ⭐ 启发参考 (4): caveman, setup-matt-pocock-skills, setup-pre-commit, write-a-skill
- ✗ 不适用 (1): migrate-to-shoehorn

## 关键映射

| Skill | 目标 Agent | 嵌入方式 |
|-------|-----------|---------|
| grill-with-docs | planner | prompt 增强：拟制前逐一提问，等反馈再继续 |
| diagnose | engineer + auditor | 新 skill 文档：5步调试法 |
| triage | reviewer | 流程改造：封驳状态机 |
| tdd | engineer | prompt 增强：红-绿-重构 |
| to-prd | planner | 新 skill 文档：需求→PRD |
| zoom-out | auditor | prompt 增强：全局架构审视 |
| handoff | archivist | 新 skill 文档：交接规范 |

## 实施优先级

1. grill-with-docs → planner prompt（影响最大，对齐 grilling session）
2. diagnose → engineer + auditor（减少"为什么出错"类问题）
3. triage → reviewer（封驳流程标准化）
4. to-prd / to-issues（需求分解标准化）
