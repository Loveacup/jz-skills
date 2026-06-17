# Profile: Process CQI（流程改进）

> 适用于业务流程/工作流的持续改进。基于 PDCA（Plan-Do-Check-Act）循环。

## 触发条件

写 CQI 时，目标对象是：
- 业务流程优化（开发流程、发布流程、审批流程）
- 工作流改进（on-call 轮值、code review 流程、CI/CD pipeline）
- 组织流程变更
- SOP（标准操作流程）改进

## 特有元素

| 元素 | 说明 |
|------|------|
| **PDCA 映射** | 每个 issue 标注处于 PDCA 哪个阶段。 |
| **Before/After 指标对比表** | 核心输出：一张表对比改进前后的关键指标。 |
| **利益相关者分析** | 谁受这个流程影响？谁需要批准？ |
| **SOP 更新检查** | 流程改了之后，对应的文档/SOP 是否同步更新了？ |

## 文档结构

```markdown
---
status: active
type: cqi-process
priority: P1
aliases: [流程名 改进]
tags: [cqi, process, pdca]
created: YYYY-MM-DD
modified: YYYY-MM-DD
health_score: 0.78
---

# <流程名> 流程改进计划

> [!abstract] TL;DR
> 一句话 + 核心指标对比

## 一、流程现状（As-Is）

- 流程图（Mermaid flowchart）
- 当前痛点
- 利益相关者列表

## 二、问题线程（8 元素 + PDCA 阶段 + 置信度）

| # | Signal | Impact | Root Cause | Fix | PDCA 阶段 | Before | After | Verify | Lessons | Conf. |
|---|--------|--------|-----------|-----|----------|--------|-------|--------|---------|-------|
| 1 | PR review 平均等待 4h | 发布延迟 1 天 | reviewer 不明确 | 自动分配 reviewer | Plan | 4h avg | <1h avg | 3 周数据 | ... | 0.85 |

## 三、Before/After 指标对比表

| 指标 | 改进前 | 目标 | 测量方式 |
|------|--------|------|---------|
| PR review 等待时间 | 4h avg | <1h avg | GitHub API |
| 发布频率 | 2/week | 5/week | CI 日志 |
| 回滚率 | 15% | <5% | 部署日志 |

## 四、实施方案（PDCA 循环）

### Plan（计划）
### Do（执行）
### Check（检查）
### Act（标准化）

## 五、SOP 更新清单

- [ ] SOP-001 已更新
- [ ] On-call 手册已更新
- [ ] 新人 onboarding 文档已更新

## 六、关联

---
*CQI Plan Writer v2.0 · Profile: Process*
```

## 健康评分维度（Process 特化）

| 维度 | 权重 | 测量方式 |
|------|------|---------|
| 流程效率 | 30% | 端到端耗时？瓶颈在哪里？ |
| 质量产出 | 30% | 缺陷率？回滚率？返工率？ |
| 合规性 | 20% | SOP 是否被遵守？审计发现？ |
| 可重复性 | 20% | 流程是否文档化？新人能否独立执行？ |

## 核心原则

1. **指标驱动**。流程改进必须有 Before/After 数字。
2. **SOP 同步**。流程改了但文档没改 = 没改。
3. **利益相关者参与**。流程不是一个人的事，谁受影响谁有发言权。
