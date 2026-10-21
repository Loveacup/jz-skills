---
source_l1: ""
source_l2: ""
status: active   # active | paused | blocked | done | failed
---

# 梁3 agent 执行层

## GOAL

<一句话目标>

## AUTHORIZED_SCOPE

- <允许的文件/系统/动作>

## ACCEPT

- [ ] <可证伪项 1；verifier；threshold>
- [ ] <可证伪项 2；verifier；threshold>

## REJECT_IF

- <失败条件 1>

## FORBIDDEN_UNLESS_SEPARATELY_AUTHORIZED

- commit / push / publish / deploy / external send
- install / upgrade / runtime config or repoint
- login / auth / credential / privilege change
- delete / overwrite / destructive rollback

## STOP_AFTER

- regen: 3
- slice: 2

## 角色与所有权

| 角色 | 当前 runtime agent | capability / independence | ownership | 状态 |
|---|---|---|---|---|
| executor | <按 roster 选择，不填历史示例名> | write | <唯一文件/worktree/state> | |
| auditor | <按 roster 选择> | read-only; fresh context; high-risk model/view | <只读审计> | |

L2 使用 fresh-context evaluator；L3 使用独立 auditor。agent 名必须来自当前 runtime roster。

## 计数器

- regen: <count>
- slice: <count>

## Verdict

| acceptance id | PASS / FAIL / BLOCKED | evidence anchor | blocks | next action |
|---|---|---|---|---|
| | | | | |

## Timeout / writer stop proof

- timeout 只表示未收到完成证据，不表示 writer 已停止。
- stop acknowledgement / process exit / lock or lease release: <anchor or BLOCKED>
- 缺少 stop proof 时不得重派同一 ownership；独立 slice 可继续。

### 计划校准事件（复用此执行日志）

每个四步阶段或独立工作单元结束/失败/阻塞后，及新指令/事实/授权/所有权风险到达时，记录：

| time | phase/unit | observation + evidence anchor | contract ref | plan revision | affected work/owner | decision + next action |
|---|---|---|---|---|---|---|
| <time> | <phase/unit> | <new fact or no-change basis + anchor> | <contract> | <plan revision> | <affected task/ownership> | continue / delta / replan candidate / BLOCKED / escalate; <next> |

计划版本、契约版本、产物/证据版本分开；无变化时记原计划及依据。未获 stop proof 不得重派所有权。细则见 `references/dynamic-plan.md`。

## 执行日志

<!-- 每次 loop 记录：时间、动作、证据、结果、ownership、下一步 -->
