# Profile: Skill CQI

> 适用于 Hermes / agent skill 的持续质量改进。继承自 v1.2，适配 v2.0 通用骨架。

## 触发条件

写 CQI 时，目标对象是：
- Hermes skill（SKILL.md + 关联脚本）
- Claude Code / Codex / Cursor skill
- 任何 agent skill 文件

## 特有元素

| 元素 | 说明 |
|------|------|
| **重构回写模式** | 每次回写 = 全文重构，已完成项→附录表。禁止 patch 追加。 |
| **Obsidian 双链规范** | 同 vault 用 `[[笔记名]]`；研究产物用 `[[40-Archives/10_Projects_Archive/项目名/文件]]`。禁止 `/tmp/` 路径。 |
| **重大决策前置协议** | 多方案选型/架构变更时：写背景文件 → CC agent team + 太子并行评估 → 调和分歧 → 写入 CQI → 归档研究产物 → 创建索引笔记。 |
| **CC audit 验证** | 修复后由独立 CC agent audit 验证，不自审。 |
| **版本附录表** | `| 日期 | 版本 | 类别 | 改进项 | 说明 |`，来源：SKILL.md version headers + CHANGELOG。 |
| **Mermaid 图** | 架构决策用 `flowchart TD` + subgraph，Python `open().write()` 直写避免行号污染。 |
| **obsidian-md-ac 美化** | 写完必须加载：emoji 标题、callout 选型、YAML 五维元数据、双链+关系符号。 |

## 文档结构

```markdown
---
status: active
type: cqi
priority: P0/P1
aliases: [skill名 CQI]
tags: [cqi, skill名, governance]
created: YYYY-MM-DD
modified: YYYY-MM-DD
health_score: 0.85
---

# <Skill 名> 持续质量改进计划

> [!abstract] TL;DR
> 一句话总结 + 当前健康分

## 一、背景与驱动力
## 二、现状诊断 — 硬证据驱动
## 三、架构决策 / 核心架构设计（如有）
## 四～N、线程或问题分组（8 元素 + 置信度）
## N+1、分阶段实施方案
## N+2、成功标准
## N+3、风险
## N+4、关联 — Obsidian wikilinks
## N+5、历史已完成 CQI 项（附录）

---
*CQI Plan Writer v2.0 · Profile: Skill*
```

## 健康评分维度（Skill 特化）

| 维度 | 权重 | 测量方式 |
|------|------|---------|
| 功能完整性 | 30% | 核心能力是否正常？有多少 P0 issue？ |
| 证据锚定度 | 25% | issue 中有多少含实测数字？ |
| 历史负债率 | 20% | P0/P1 issue 存续时间（天） |
| 可验证性 | 15% | 多少 fix 有 verify 命令？ |
| 文档完整度 | 10% | SKILL.md 是否有 red flags/decision tree/pitfalls？ |

## 信号采集（Skill 特化）

额外信号源：
- `search_files` 搜 `TODO|FIXME|HACK|workaround` 在 skill 目录
- SKILL.md 中的 `common-pitfalls` 条目是否对应 issue
- Cron job 输出中与该 skill 相关的 ERROR
- 用户在使用该 skill 时的纠错消息（"不应该这样"、"你错了"）

## Workflow Integration

`cqi-plan-writer`（写 CQI）→ `skill-authoring`（改 SKILL.md）→ CC audit（验证修复）
