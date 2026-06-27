# CQI Plan Template（持续质量改进计划模板）

> Use when creating a CQI plan for any skill. Dual-track structure: self-improvement + assist-others.

## Document Structure

```markdown
---
status: 树苗
type: 方法论
priority: 重要
aliases: [<Skill> CQI Plan]
tags: [hermes/<skill>, devops/quality]
created: YYYY-MM-DD HH:MM
modified: YYYY-MM-DD HH:MM
---

# <Skill> 持续质量改进计划（CQI Plan）

> [!abstract] TL;DR
> 双轨并行：**上轨 ⇢ 自我改进**；**下轨 ⇢ 协助改进**。

---

# 上轨：自我改进

> <skill>自身的合规性、问题修复、进化轨迹。

## §A1. 问题日志
### A1.1 已知缺陷
| ID | 分类 | 问题 | 发现日期 | 状态 |

### A1.2 自审盲区
| 步骤 | 对其他 skill | 对自身的盲区 |

## §A2. 更新日志
| Version | Date | Changes |
### 规划版本
| Target | 核心变更 | 解决 |

## §A3. 自我改进路线
- [ ] 任务列表

---

# 下轨：协助改进

> 提升<skill>审查/服务其他 skill 的能力。

## §B1. 诊断能力升级
| 维度 | 当前 | 目标 |

## §B2. 跨 Skill 缺陷模式库
| 模式 ID | 模式名 | 来源 | 临床表现 | 根因 |

## §B3. 自动化验证/服务 Pipeline
(架构图 + 门禁指标 + 实施路线)

## §B4. 学术与开源吸收计划
| 优先级 | 来源 | 吸收内容 | 目标版本 |

## §B5. 实施路线图
(Week-by-week)

## §B6. 成功标准
| 指标 | 现状 | 目标 | 测量 |

## §B7. 风险
| 风险 | 影响 | 缓解 |

---

## 附录：理论基石索引
| 论文/项目 | ID/URL | 核心方法 | 状态 |

## 关联
- → 关联的其他 CQI 计划
- → 关联的 skill 文件
```

## Key Principles

1. **Dual-track is mandatory** — every CQI plan must cover both self-improvement (上轨) and assist-others (下轨)
2. **Issue log must have IDs + classification** — use EmbodiSkill's 4-type system: 🔍 DISCOVERY / ⚡ OPTIMIZATION / 🐛 DEFECT / 🏃 EXECUTION LAPSE
3. **Update log must cover past AND planned** — show version history AND target versions with what each solves
4. **Cross-skill patterns** — extract recurring failure modes from other skills' CQI plans and feed them back
5. **Success criteria must be measurable** — no subjective goals; every target has a measurement method
6. **Risk table is mandatory** — for each risk: what, impact, mitigation

## Common Pitfalls When Writing CQI Plans

| Trap | Consequence |
|------|-------------|
| Single-track (only self-improvement, no assist-others) | Misses half the value — the skill's impact on others |
| No issue IDs | Can't trace which fixes resolved which problems |
| Subjective success criteria | Can't tell if the plan worked |
| Skipping the risk table | Blind spots uncovered too late |
| Writing as one-shot document | CQI plans evolve; version the plan itself |
