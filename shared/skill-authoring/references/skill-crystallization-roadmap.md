# Skill 自动结晶路线 — Obsidian 文档索引

> 2026-06-05，基于 16 篇论文（Library Drift、SkillX、SkillOS、SkillOps、A-MAC 等）的系统研究。

## 核心文档（Obsidian `02-Plan&CQI/`）

- `Hermes Skill 计数自动结晶 研究简报_20260605.md` — 16 篇论文全文综述 + 路线重排
- `Hermes Skill 计数自动结晶 路线图_20260605.md` — 五阶段路线图（阶段 0–4）+ 三方决策定案
- `Hermes Skill 自动结晶 四模块架构草案_20260605.md` — 计量/审计/检索/结晶四模块 v2 架构（~2,000 行）

## 可运行系统

- `~/.hermes/scripts/skill-metering.py` — 阶段 0 计量脚本（每日 cron `b305c6e941eb`）
- `~/.hermes/skills/_lifecycle/` — 数据总线：metrics/ + reports/ + scripts/
- 164 skill 已标注 `type: routine`（待手动标 `critical`）

## 四条路线概要

| 路线 | 定位 | 状态 |
|:-----|:-----|:-----|
| A 计量+减法 | 防 Library Drift 静默退化 | 阶段 0 已上线 |
| B3 健康审计 | A 的减法引擎 | 与 A 并列 |
| D 按需检索 | token 数量级解法 | 评估阶段 |
| C 全自动结晶 | 终极闭环 | 暂缓 |

## 关键发现

- **Library Drift**: 无界 skill 积累让性能低于无 skill 基线；LLM 自生成 skill 净提升≈+0.0pp
- **A-MAC Type Prior**: rare-but-critical 技能保护的最佳现成解
- **并行设计语义漂移**: agent team 并行写架构后必须做跨模块语义对账

## 三方决策

1. 路线 D：只做评估报告
2. 删除闸：永远人工确认
3. 孵化期：90 天 + 贡献分≥0 + 人工确认
