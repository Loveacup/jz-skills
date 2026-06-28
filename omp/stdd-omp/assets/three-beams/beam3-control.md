---
source_l1: ""
source_l2: ""
status: active   # active | paused | done | failed
---

# 梁3 agent 执行层

## GOAL

<一句话目标>

## ACCEPT

- [ ] <可证伪项 1>
- [ ] <可证伪项 2>

## REJECT_IF

- <失败条件 1>

## STOP_AFTER

- regen: 3
- slice: 2

## 审计链

| 角色 | agent | 状态 |
|---|---|---|
| executor | task / oracle | |
| auditor | reviewer / oracle（默认）；可选 stdd-auditor | |

## 计数器

- regen: <count>
- slice: <count>

## 执行日志

<!-- 每次 loop 记录：时间、动作、结果、下一步 -->
