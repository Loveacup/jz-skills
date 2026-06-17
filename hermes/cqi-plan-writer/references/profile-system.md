# Profile: System CQI（系统质量改进）

> 适用于架构/系统/基础设施的质量改进。吸收自 Varietyz/Disciplined-AI-Software-Development 的验证门 + PAG 形式化约束，以及 muratcankoylan 的 skill health 机制。

## 触发条件

写 CQI 时，目标对象是：
- 软件架构质量改进
- 系统可靠性/性能改进
- 基础设施升级
- 代码库健康度改进
- 平台/框架迁移

## 特有元素

| 元素 | 说明 |
|------|------|
| **ALWAYS/NEVER 规则** | 形式化约束。`ALWAYS: 文件不超过 150 行`；`NEVER: 跳过 CI 直接合入 main`。比自然语言约束更明确。 |
| **VALIDATION GATE 块** | 每个改进阶段末尾的显式通过/失败标准。格式：`✅ 标准 — 验证方式` |
| **架构合规检查** | 改进后是否仍满足架构约束？（如模块边界、依赖方向、接口契约） |
| **健康评分持续追踪** | 每次改进后重算健康分，形成趋势线。 |

## 文档结构

```markdown
---
status: active
type: cqi-system
priority: P0/P1
aliases: [系统名 CQI]
tags: [cqi, system, architecture]
created: YYYY-MM-DD
modified: YYYY-MM-DD
health_score: 0.72
health_trend: [0.68, 0.70, 0.72]  # 最近 3 次评分
---

# <系统名> 系统质量改进计划

> [!abstract] TL;DR
> 当前健康分 0.72，趋势 ↑。核心问题：3 个 P0 + 5 个 P1。

## 一、ALWAYS/NEVER 规则（系统宪法）

| 规则 | 类型 | 当前合规？ |
|------|------|----------|
| 文件不超过 150 行 | ALWAYS | ❌ 12 个文件超标 |
| 禁止跳过 CI 合入 main | NEVER | ✅ |
| ... | | |

## 二、现状诊断 — 健康评分明细

| 维度 | 当前分 | 目标分 |
|------|--------|--------|
| 功能完整性 | 0.60 | 0.85 |
| 代码质量 | 0.70 | 0.85 |
| 架构合规 | 0.75 | 0.90 |
| 可维护性 | 0.80 | 0.85 |
| 加权总分 | **0.72** | **0.86** |

## 三、问题线程（8 元素 + 置信度）

## 四、分阶段实施方案

### Phase 1：P0 清零
| Issue | Fix | VALIDATION GATE |
|-------|-----|-----------------|
| #1 | ... | ✅ 所有 P0 issue After 标准达成 |

### Phase 2：P1 治理

## 五、架构影响评估

每个改动对架构的影响：
- 模块边界是否变化？
- 依赖方向是否保持？
- 接口契约是否兼容？

## 六、成功标准

- 健康分从 0.72 → 0.86
- P0 issue 清零
- 所有 ALWAYS 规则合规

## 七、关联

---
*CQI Plan Writer v2.0 · Profile: System*
```

## 健康评分维度（System 特化）

| 维度 | 权重 | 测量方式 |
|------|------|---------|
| 功能完整性 | 25% | 核心功能是否正常？P0 数量？ |
| 代码质量 | 25% | Lint/typecheck 通过率？测试覆盖率？ |
| 架构合规 | 20% | ALWAYS/NEVER 规则合规率？模块边界违规数？ |
| 可维护性 | 15% | 文件大小分布？TODO/FIXME 数量？ |
| 文档完整度 | 15% | 架构文档是否存在？是否最新？ |

## 验证门格式

每个 Phase 末尾写 VALIDATION GATE：

```markdown
### VALIDATION GATE: Phase 1 Complete
- ✅ P0 issue 全部 closed — 3/3
- ✅ 健康分 ≥ 0.80 — 当前 0.82
- ✅ 所有 ALWAYS 规则合规 — 12/12
- ❌ 测试覆盖率 ≥ 85% — 当前 78%，延期到 Phase 2
```
