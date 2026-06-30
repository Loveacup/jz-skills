# 三问题裁决（2026-06-16 CC 第二轮）

> 来源：Alex 对审核 Agent 设计的三点追问，CC 逐条回答

## 问题 1：去 regent 化 → 通用角色

**裁决**：删掉所有 "regent"，协议里只命名两个角色——`delegator`（委派者）和 `auditor`（审核者）。这是**角色**，不是 agent。

- `auditor` = 调用方指定，默认 = self（L1）
- `independence_level` = delegator 和 auditor 之间强制隔离的强度
- 同一 agent 兼任 = `auditor==delegator` 的特例

## 问题 2："切 auditor 身份"的机械定义

**裁决**：本质是 B（上下文裁剪），不是 A（心理暗示）。四步机械过程（L1-L3 同一套，差在第①步强度）：

1. 封掉自报证据（禁止引用"CC 说已通过"，pass/fail 必须指向此刻新取证据）
2. 客观半重跑（gate 脚本现在重新执行，不信历史运行）
3. 对 criterion 审，不对意图审
4. 产出结构化 Verdict（每条挂新证据指针）

L1 做不到物理上下文裁剪（设计讨论还在窗口里）→ 脚本 gate 必须接管高后果客观半。

## 问题 3：脚本物理落点

**裁决**：按耦合度劈两处——

| 脚本 | 耦合度 | 落点 |
|------|--------|------|
| 客观验收/危险拦截/终止计数 | 基质无关 | `cc-tmux/scripts/gate/`（独立子目录，头注零耦合） |
| 失败检测（tmux pane 读 token 冻结/崩溃） | 内在耦合 tmux | 留 `cc-tmux/scripts/`（cc-monitor/cc-finish） |

出现第 2 消费者 → gate 整组提升为独立 audit skill。
