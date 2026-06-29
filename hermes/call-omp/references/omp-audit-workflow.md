# ACP Audit-Driven Design Workflow

> 用 OMP 的 ACP 通道做架构审计，而非直接跳进实现。
> 一次成功的实战：`--watch 模式` 方案被 OMP 审出 blocker → 大改设计 → 落地。

## 流程

```
Hermes 设计方案（口头描述/文字）
  ↓
call-omp: omp-start --mode audit → omp-send --channel acp
  ↓
OMP ACP (delegate_task) 审计方案
  ↓ verdict: blocker/concern/nit/pass
Hermes 阅读审计报告，决策：
  ├─ blocker → 修改方案，不回退直接实现
  ├─ concern → 评估取舍
  ├─ nit → 接受并记录
  └─ pass → 直接实现
  ↓
按 accept findings 后的方案实现
```

## 关键决策点

- **blocker ≠ 放弃**：OMP 给 blocker 是告诉你"这样有问题"，不是"别做了"。
  本次 `--watch 模式` 被标 blocker（ACP --await 不可行），修正后方案从"新建 80 行脚本"改为"扩展 omp-monitor +20 行"——方案更优。
- **ACP 审计比找 bugs 更划算**：一次审计发现 6 个维度的问题，避免按错方案投入数小时实现再重写。

## 本次实例

| 阶段 | 动作 |
|------|------|
| Hermes 提出 | `--watch 模式` 独立进程 + ACP --await + 📡 监控 |
| OMP 审计 | ACP delegate → verdict: blocker（ACP --await 架构不可行）|
| 证据 | `omp-monitor.sh:57-86` 已实现轮询逻辑 · `omp-send.sh:245-255` ACP= pending_acp 非 running |
| 修正 | 扩展 `omp-monitor.sh` + --watch（+88行），ACP 走回调 |
| 结果 | v0.4.0 落地，55/55 测试 + smoke test 通过 |

## 触发条件

- 设计方案涉及通道/协议/安全/竞态等复杂交互
- 想在写代码前让独立审计者过一遍架构
- 与 cc-tmux 配合：cc-tmux 做实现，OMP 做审计
