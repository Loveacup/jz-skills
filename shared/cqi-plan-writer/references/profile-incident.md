# Profile: Incident CQI（事故复盘）

> 适用于事故/故障/安全事件的事后复盘。吸收自 Google SRE postmortem 模板（dastergon/postmortem-templates）和 danluu/post-mortems 收集的 200+ 真实案例。

## 触发条件

写 CQI 时，目标对象是：
- 系统故障/宕机
- 安全事故/数据泄露
- 服务降级/性能崩溃
- 任何「发生了不该发生的事」

## 特有元素

| 元素 | 说明 |
|------|------|
| **Timeline 驱动叙事** | 以时间线为核心叙事结构，精确到分钟。所有 issue 按时间线组织。 |
| **Detection** | 怎么发现的？监控告警？用户报告？偶然发现？——这是改进监控的关键输入。 |
| **Blameless 文化** | 不追究个人责任，追究系统缺陷。不说"XX 操作失误"，说"系统允许 XX 操作在没有二次确认的情况下执行"。 |
| **What went well / wrong / lucky** | 三类经验教训，分别记录。 |
| **Impact 量化** | 持续时间、影响用户数、经济损失、数据丢失量。 |

## 文档结构

```markdown
---
status: closed  # 事故复盘通常是一次性的
type: cqi-incident
severity: P0/P1
aliases: [YYYY-MM-DD 事故名]
tags: [cqi, incident, 系统名]
created: YYYY-MM-DD
modified: YYYY-MM-DD
health_score: N/A  # 事故复盘通常不适用持续健康分
---

# 事故复盘：<标题>（Incident #XXX）

> [!abstract] TL;DR
> 时间、影响、根因一句话

## 一、Timeline（精确到分钟）

| 时间 (UTC) | 事件 |
|-----------|------|
| 14:01 | 部署了配置变更 X |
| 14:03 | 监控告警触发 |
| 14:05 | On-call 确认问题 |
| 14:07 | 开始回滚 |
| 14:12 | 服务恢复 |

## 二、Impact
- **持续时间**：XX 分钟
- **影响范围**：XX 用户 / XX 区域
- **业务影响**：XX

## 三、Root Cause（5 Whys）

1. 直接原因：
2. 为什么？（一层）
3. 为什么？（二层）
4. 为什么？（三层）
5. 为什么？（四层）
6. 根本原因：

## 四、Detection
- 怎么发现的？
- 为什么没有更早发现？
- 监控缺口是什么？

## 五、Resolution
- 怎么恢复的？
- 回滚了什么？
- 有没有副作用？

## 六、Action Items（8 元素格式）

| # | Signal | Impact | Root Cause | Fix | Verify | Before | After | Lessons | Conf. |
|---|--------|--------|-----------|-----|--------|--------|-------|---------|-------|

## 七、Lessons Learned

### What went well
- 

### What went wrong
- 

### Where we got lucky
- 

## 八、关联
- 相关 CQI 计划
- 相关监控变更
- 相关 on-call 手册更新

---
*CQI Plan Writer v2.0 · Profile: Incident*
```

## 核心原则

1. **时间线是第一公民**。读者应该能从时间线理解事故全貌。
2. **5 Whys 挖到系统根因**。不说"操作失误"，说"为什么操作失误没有被拦截"。
3. **Action Items 可验证**。每条 fix 必须有 verify 方式。
4. **Blameless**。复盘不是为了找人背锅，是为了让同类事故不再发生。
