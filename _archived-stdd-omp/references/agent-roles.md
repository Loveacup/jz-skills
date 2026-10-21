# STDD-OMP 角色与独立性

本页定义角色能力，不承诺任何固定 agent 名称。实际名称必须来自当前 runtime/tool 暴露的可用 agent 列表。

## 分级要求

| 档位 | 执行与评估 |
|---|---|
| L0 | 默认不启用 STDD。 |
| L1 | 主 agent 内联 Spec/Accept/Build/Verify；允许自检，不强制委派。 |
| L2 | executor 与 evaluator 使用独立上下文（fresh session/subagent）；evaluator 只读复核验收与证据。 |
| L3 | executor 与独立 auditor 分离；高风险判定还必须叠不同 modelRole/provider/模型视角，或用更强的 P3 实态证据补偿。 |

同模型 fresh subagent 只提供上下文独立，不提供模型独立。核心状态权威、并发安全、发布/权限或会静默崩塌的判定属于高风险。

## Capability-first 选择

需要委派时按以下顺序：

1. 读取本次 runtime 的 agent roster、spawn policy、工具权限和隔离能力；
2. 按任务选择：只读研究、写入执行、动态测试、静态审计或领域专项；
3. evaluator/auditor 必须能读取契约和证据，且不得写入被审对象；
4. 将实际选择的 agent 名、上下文/模型独立性和工具权限记录到梁3/GOAL；
5. 所需能力不可用时标记 BLOCKED，不猜测 `reviewer`、`oracle`、`explore`、`quick_task` 等名字存在。

文档、模板或示例中的名字只表示历史示例；runtime roster 才是当前事实。

## 最小角色

| 角色 | 职责 | 能力要求 |
|---|---|---|
| coordinator | 定档、分配不重叠所有权、汇总 verdict、收口 | 当前主 session；不越过 auditor 改判 |
| executor | 在单一所有权内 Build 并上抛证据 | 写入能力；遵守 scope 与 single-writer |
| tester | 运行相关场景并记录 exit/log/state | 对目标表面有真实运行能力 |
| evaluator | L2 独立上下文复算验收 | fresh context；只读被审对象 |
| auditor | L3 独立裁决；逐项 PASS/FAIL/BLOCKED | 只读、上下文独立；高风险时再叠模型/视角独立 |
| publisher | 执行已单独授权的 commit/push/publish/deploy | 不属于 full-auto 默认能力 |

L1 不因“角色表存在”而委派。L2/L3 只起完成验收所需的最小角色组。

## Single-writer 与 timeout

- 同一文件、worktree 或不可分割状态同时只有一个 writer。
- 并行 executor 必须有不重叠的明确所有权。
- timeout/无心跳只证明“未收到完成证据”，不证明 writer 停止。
- 重派 writer 前必须有 stop acknowledgement、进程退出、锁/租约释放或其他可定位的终止证据。
- 没有 stop proof 时，保持该所有权冻结并升级人工；独立且无依赖的 slice 可以继续。

## Evidence 与裁决

evaluator/auditor 只根据 Acceptance contract 与可定位证据裁决，不把 executor 自报当成实态。每项输出：

```yaml
id: <acceptance-id>
verdict: PASS | FAIL | BLOCKED
anchor: <file:line | exit code | log line | agent://id>
blocks: <依赖项/acceptance/release>
next_action: continue | rebuild | revise-contract | escalate
```

证据不足、验证崩溃、部分产出或 timeout → 相关项 BLOCKED。无依赖工作可继续；依赖该项的合并、Acceptance、发布或交付不能继续。

## Full-auto 权限边界

Full-auto 只覆盖 GOAL 中已授权的可逆操作。以下动作需要各自明确授权，不能由 full-auto、yolo 或已有普通任务授权推导：

- commit/push/publish/deploy/对外发送；
- install/upgrade/runtime repoint/config 修改；
- 登录、认证、密钥/凭据、权限提升；
- 删除、覆盖、破坏性回滚。

## 并发与硬顶

- regen max=3；slice max=2。
- 并发上限、递归深度、运行时上限只使用当前 runtime 确认存在的控制项；不要把旧版本配置键当成事实。
- 达到硬顶停止自动循环并升级人工。

## 启动对齐清单

L2/L3 开始前确认：

1. Spec 与 Acceptance 是否可证伪；
2. 每个 slice 的 writer 所有权是否唯一；
3. evaluator/auditor 的实际 runtime 名称和只读能力；
4. 上下文独立；L3 高风险时模型/视角独立或实态补偿；
5. 证据动作、regen/slice 硬顶和 danger 边界；
6. 哪些 scope 已授权，哪些动作仍需单独授权。

能从仓库、runtime roster 或现有授权自答的，不重复询问用户。
