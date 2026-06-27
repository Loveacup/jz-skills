# Regent 3S6M v0.1 Templates — Reference

> Session reference: 2026-05-18, v0.1 implementation completed via Kanban tasks T1-T6.

## Template files

All templates live under `~/.hermes/skills/devops/kanban-orchestrator/templates/`:

| Template | File | Purpose | Lines |
|---|---|---|---|
| Task Brief | `task-brief.yaml` | 19-field YAML schema for every Kanban task; embeddable in body or A2A payload | 71 |
| Audit Checklist | `audit-checklist.md` | 御史台 5维度×5项=25检查点; includes self-check template and kanban_complete metadata integration | 130 |
| Archive Workflow | `archive-workflow.md` | 史馆 standard flow: trigger conditions, Obsidian paths, qmd commands, 11-point checklist | 213 |
| External Expert Spec | `external-expert-spec.md` | 将作监 spec: call timing, 4 modes (tmux/print/MCP/Codex), task brief, output requirements, audit, MCP check script | 425 |

## How they were created

- T2 (t_1a0ba9ea): task-brief.yaml + 3 examples (research/engineering/audit) in workspace
- T3 (t_9717df80): audit-checklist.md
- T4 (t_88fc3d57): archive-workflow.md
- T5 (t_73d0e636): external-expert-spec.md
- T6 (t_17fd0285): v0.1 README at `~/.hermes/notes/regent-3s6m-v0.1-readme.md`

## Integration with kanban-orchestrator SKILL.md

The orchestrator skill's appendix ("3S6M v0.1 模板速查") references these files. When updating templates, also update the appendix table in SKILL.md if fields or filenames change.

## v0.2 roadmap (from v0.1 README)

| Task | Priority | Status |
|---|---|---|
| Profile 启动脚本 | P1 | Not started |
| Profile 健康检查 | P1 | Not started |
| A2A Agent Card 设计 | P2 | Not started |
| A2A 消息 schema | P2 | Not started |
| 六部细分 profile | P2 | Not started |
| Codex CLI 修复 | P2 | Not started |
| 自动化审计 | P2 | Not started |
| 自动化归档 | P2 | Not started |
