# GitHub CQI Skill 全景搜索 — Gap Analysis

> 2026-06-17，搜索目标：找通用 CQI 写作方法论 skill。
> 结论：**GitHub 上没有现成的「通用 CQI 写作 skill」。** 我们的 `cqi-plan-writer` 反而是独特的。

## 搜索方法论

- 策略：`gh search repos --sort stars` + `gh api` REST + `exa fetch` 三层
- Query 组：15+ 组（CQI / quality improvement / skill governance / quality gates / PDCA / DMAIC / postmortem / CAPA / retrospective / improvement kata 等）
- 过滤：stars > 10, updated within 6 months, description 相关性人工筛选

## 搜索结果：7 个高度相关仓库

| # | 仓库 | ⭐ | 核心机制 | CQI 关联 | 可直接用？ |
|---|------|-----|---------|---------|----------|
| 1 | `muratcankoylan/Agent-Skills-for-Context-Engineering` | 16,590 | `skill_health.py` 量化评分、Researcher OS 状态机、Claim 溯源、Novelty 检测 | ⭐⭐⭐⭐⭐ | ❌ 方法论框架 |
| 2 | `tanweai/pua` | 18,293 | PIP 三级升级、7 点系统排查清单 | ⭐⭐⭐⭐ | ❌ Claude Code/Codex 插件 |
| 3 | `BayramAnnakov/claude-reflect` | 1,063 | 纠错捕获→技能回写、模式发现→命令生成、置信度评分 | ⭐⭐⭐⭐ | ❌ Claude Code plugin |
| 4 | `Varietyz/Disciplined-AI-Software-Development` | 402 | PAG 形式化验证门、ALWAYS/NEVER 规则 | ⭐⭐⭐ | ❌ 软件工程方法论 |
| 5 | `dastergon/postmortem-templates` | 1,437 | SRE postmortem 模板结构（Title→Impact→Root Cause→Timeline→Action Items→Lessons Learned） | ⭐⭐⭐⭐ | ❌ 模板集合 |
| 6 | `addyosmani/agent-skills` | 61,549 | DEFINE→REVIEW→SHIP 生命周期质量门 | ⭐⭐ | ❌ 工程 skill 集合 |
| 7 | `ucsandman/DashClaw` | 275 | Guard→Record→Verify 治理循环、Assumption recording | ⭐⭐ | ❌ Node.js SDK |

## GitHub 上实际存在的东西（三类）

| 类型 | 代表 | 与通用 CQI skill 的差距 |
|------|------|----------------------|
| **事后复盘模板** | `dastergon/postmortem-templates` | 只有结构骨架，无方法论；只针对事故 |
| **Agent skill 质量改进闭环** | `claude-reflect`, `muratcankoylan` | 实践系统，非教学 skill；耦合在 agent 场景 |
| **软件工程质量门框架** | `Varietyz`, `addyosmani` | 面向代码开发，非通用质量改进写作 |

## 三大可吸收机制（优先级排序）

### P0：吸收 SRE Postmortem 模板结构 → 通用化

```markdown
Title → Date → Authors → Status → Summary → Impact
→ Root Causes → Trigger → Resolution → Detection
→ Action Items → Lessons Learned (what went well/wrong/lucky)
→ Timeline → Supporting Information
```

**价值**：这是最成熟的"问题→改进"文档结构，经过 Google SRE 验证。把 `Trigger`、`Detection`、`Lessons Learned` 加入 cqi-plan-writer 的 Issue Format。

### P0：吸收 claude-reflect 的「自动信号采集」

- 从 Supermemory / session 历史 / 用户纠错 → 自动发现 CQI issue 信号
- Confidence scoring (0.60-0.95) → 每个 issue 带可信度
- Skill improvement routing → 纠错自动回写到 skill 文件

**价值**：让 CQI 从"纯手写文档"变成"半自动信号驱动的改进引擎"。

### P1：吸收 muratcankoylan 的量化健康评分

- `skill_health.py`：确定性 0-1 评分，非 checklist pass/fail
- Run state machine：`initialized → retrieved → evaluated → proposed → validated → closed`

**价值**：让 CQI 的 Quality Gates 从二元 check 变成可追踪的数值。

## SRE Postmortem 模板原始格式

（来源：Google SRE book，经 `dastergon/postmortem-templates` 收录）

```markdown
# Title (incident #)
### Date
### Authors
### Status
### Summary
### Impact
### Root Causes
### Trigger
### Resolution
### Detection
## Action Items
## Lessons Learned
### What went well
### What went wrong
### Where we got lucky
## Timeline
## Supporting information
```

## 与 cqi-plan-writer v1.2 的对照

| 我们的已有 | SRE 模板对应 | claude-reflect 对应 | 缺失 |
|----------|------------|-------------------|------|
| Signal → Root Cause (6-element) | Root Causes + Trigger + Detection | 纠错捕获 + queue | Timeline + What went well/wrong/lucky |
| Priority Tiers (P0/P1/P2) | Action Items | — | 自动信号采集 + confidence |
| Quality Gates checklist | — | — | 量化评分 (0-1) |
| 重构回写模式 | — | Skill improvement routing | Run state machine |
| 重大决策协议 | — | — | Assumption recording |
| Obsidian 双链 | — | — | — |

## 关键发现

1. **我们的 cqi-plan-writer 是独特的**：GitHub 上没有竞品
2. **通用 CQI 方法论在 GitHub 上以"模板"而非"skill"形式存在**：postmortem templates 是最接近的东西
3. **Agent skill 质量改进系统比通用 CQI 更发达**：claude-reflect 和 muratcankoylan 的闭环比大多数企业 CQI 流程更自动化
4. **CQI 知识主要分布在书籍/论文/企业内部文档**：PDCA、DMAIC、A3、8D 等方法论极少以 GitHub repo 形式出现
