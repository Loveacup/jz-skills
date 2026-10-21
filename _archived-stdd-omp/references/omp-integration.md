# STDD-OMP 与 OMP 机制映射

本页只在首次接入、新 session、版本变化、集成报错，或 L2/L3 需要可执行隔离/异步/auditor 时读取。简单 L1 不需要 preflight。

OMP 原语、agent 名和配置键会随 runtime 漂移；当前 tool schema、agent roster 与 `omp --help` 是事实源，本文示例不是能力保证。

## 稳定语义与 runtime 绑定

| STDD 语义 | 需要的能力 | 绑定规则 |
|---|---|---|
| L1 Build/Verify | 当前主 agent 的读写与相关验证能力 | 内联，不强制 subagent |
| L2 evaluator | fresh context + 只读被审对象 | 从当前 roster 按能力选择 |
| L3 auditor | fresh context + 只读 + 高风险模型/视角独立或实态补偿 | 从当前 roster 按能力选择；不可用则 BLOCKED |
| 客观 gate | 可运行 JS/CLI | `scripts/gates.mjs` 的已导出 API |
| single-writer | ownership/lock/隔离 | 同一状态不并发写；重派前要 stop proof |
| danger | 明确授权 + scan/hook | hook 可选，不等于授权 |

不要假定 `reviewer`、`oracle`、`explore`、`quick_task`、`irc`、`parallel()` 或任何 modelRole 一定存在。只有 runtime 当前列出的名称可写入 Plan/梁3/GOAL。

## Acceptance 与用户授权

- L1 直接在对话中记录 checklist。
- L2/L3 可使用当前 runtime 支持的 Plan 工件/审批机制。
- 用户已经授权且 scope 无歧义时，不重复请求确认 checklist。
- 只有 scope 分叉、不可逆动作或新权限需求才请求决定。

## Gates

`scripts/gates.mjs` 的当前导出：

```js
const {
  verifyArtifact,
  verifyTest,
  scanDanger,
  bumpCounter,
} = await import('./scripts/gates.mjs');
```

CLI counter：

```bash
node scripts/gates.mjs counter --key <task> --kind regen --max 3 --incr
node scripts/gates.mjs counter --key <task> --kind slice --max 2 --incr
```

不要把 gate 当作通用测试替代物；选择能直接证明 Acceptance 的实际表面。没有新变更、失败或未决风险时不重复跑同一验证。

## Artifact 与独立审计

若 runtime 提供 `agent://<id>`、history 或等价 artifact，auditor 直接读取产物和证据，不要求 executor 重述。若这些机制不可用，将等价可定位工件路径写进 verdict。

L2 需要独立上下文 evaluator；L3 需要独立 auditor。实际 agent 名在 dispatch 前从 runtime roster 决定并记录。

## 异步、等待与 timeout

使用 runtime 当前提供的消息/等待/监督进程能力。timeout 只表示没有完成证据：

1. 将相关验收项标为 BLOCKED；
2. 不把 timeout 当作 writer 已退出；
3. 取得 stop acknowledgement、进程退出或锁/lease 释放证据后，才可重派同一所有权；
4. 无依赖且不重叠的 slice 可以继续。

## 隔离

L2/L3 可在 runtime 确认支持时启用 worktree/COW/isolated execution。隔离能力不可用不应被伪装为已启用；若它是验收或风险前提，则 BLOCKED。

## 可选能力

- LSP/编译器：parse 与引用证据；
- browser：Web 用户路径实态；
- debug：运行时变量与线程状态；
- Advisor/WATCHDOG：回合级审查；
- hook：危险 tool call 的额外拦截；
- memory：经验回写。

这些都是按需能力，不是简单 L1 的启动税。安装、启用、改配置或认证均需对应明确授权。

## Full-auto 边界

runtime 的 yolo、async、isolated 或 approval 设置都不扩大用户授权。Full-auto 不能隐含执行 commit/push/publish/deploy、安装/升级、runtime config/repoint、登录/认证/凭据/权限或删除。

## 版本校准

发生以下任一情况时才跑只读 preflight：

- 新 session/首次接入且需要上述可执行集成；
- OMP 或 skill 版本变化；
- agent、gate、hook、Advisor、artifact 或路径报错。

命令：`node scripts/orchestrate.mjs --text`。检测结果不自动触发安装、升级或配置变更。
