# Verify 证据纪律

本页定义 ④Verify 的证据、BLOCKED、timeout 与 single-writer 语义。

## 证据阶梯

| 层级 | 名称 | 可用机制 | 证明什么 |
|---|---|---|---|
| ① parse | 静态/格式 | schema validate、编译器/LSP（若 runtime 提供） | 文件可解析、类型/配置格式成立 |
| ② resolve | 引用完整性 | references、依赖解析、`grep` 旧符号归零 | 调用方和依赖已迁移 |
| ③ live | 运行时实证 | 实际命令 exit code、`browser`、`debug`、真实状态 | 用户可观察行为成立 |

L1 使用足以覆盖改动的最小相关证据；L2 至少覆盖引用/影响面；L3/high-risk 尽可能使用 live 证据并启用 claimcheck。不要为了流程重复已经成立且没有新变更、失败或未决风险的验证。

## Verdict 与锚

每条验收项必须给出：

```yaml
verdict: PASS | FAIL | BLOCKED
anchor: <file:line | exit code | log line | agent://id>
blocks: <依赖项/acceptance/release>
```

- 无锚、锚不可达或证据不覆盖论断 → BLOCKED，不得 PASS。
- 无人值守整轮不可锚率 >40% → 整轮作废；计入 regen。
- `scripts/gates.mjs` 的现有 API 是 `verifyArtifact`、`verifyTest`、`scanDanger`、`bumpCounter`。

## 夹逼证据

终态暂不可直接观察时，可记录配置端与运行端代理证据，但只能降格为“未终验”。任何依赖最终行为成立的 Acceptance、合并、发布或交付保持 BLOCKED。夹逼不是 inference-based approval。

## 失败语义

| 情况 | 相关项 | 下游 |
|---|---|---|
| 证据不足/验证崩溃/部分产出/timeout | BLOCKED | 无依赖 slice 可继续；依赖的 Build、Acceptance、merge、release、delivery 停止 |
| 明确反例 | FAIL | 回 Build 或 Accept；计入相应 counter |
| regen 达 3 / slice 达 2 | BLOCKED + 升级人工 | 停止自动循环 |

软失败不是低置信度放行。它可以不阻塞独立工作，但绝不能让依赖该证据的结论或发布通过。

## Timeout 与 writer 终止

- timeout、沉默或缺少 turn-done 只证明未收到完成证据。
- 它们不证明 executor、进程或远端 writer 已停止。
- 可接受的 stop proof 包括：明确 stop acknowledgement、受监督进程退出、锁/lease/ownership 的可定位释放证据。
- stop proof 前不得把同一文件/worktree/状态重派给新 writer；保持 single-writer，冻结依赖链并升级人工。
- 不重叠且无依赖的 slice 可以继续。

心跳只用于发现异常，不是终止证明。运行时 hard timeout 也必须取得可观察的退出/释放结果后才能重派。

## 计数器

```bash
node scripts/gates.mjs counter --key <task> --kind regen --max 3 --incr
node scripts/gates.mjs counter --key <task> --kind slice --max 2 --incr
```

计数器命令的 exit code 和输出应作为证据保存；满硬顶停止，不自动重试。
