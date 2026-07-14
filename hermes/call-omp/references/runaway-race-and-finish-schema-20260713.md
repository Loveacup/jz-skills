# OMP runaway kill race 与 finish evidence schema（2026-07-13）

## 适用场景

Shell async 审计 raw 超过 20MB、持续高速增长，Hermes 按熔断规则准备停止进程。

## 新发现

`kill <pid>` 与 OMP 输出最终 verdict 可能发生竞态：停止命令发出前后，OMP 可能恰好完成最后一个 assistant turn。此时紧接着运行 `omp-monitor --json`，可能得到：

- `phase=reported`
- 合法 `severity`
- 非空 `evidence`
- `stop_reason=stop`

这不是“被 kill 的失败产物”，而是已经完整落盘并通过 monitor schema 校验的 verdict。应按 verdict 内容裁决，不能因为刚执行过 kill 就机械标成工具失败。

## 正确顺序

1. raw >20MB 且无合法 verdict：停止 pid。
2. **停止后只运行一次 `omp-monitor --json`**，读取最终落盘状态。
3. 若 `reported + severity_valid + evidence_count>0 + stop_reason=stop`：保留 verdict，按 pass/concern/blocker 正常裁决。
4. 若 `rejected`、`toolUse/aborted`、空 evidence 或无合法 JSON：按审计工具失败处理，不代表代码 blocker/pass。
5. 同一 evidence bundle 不做等价重试；只有 scope、criterion 或 evidence 实质变化才允许新一轮。

## `omp-finish` 的 evidence schema 边界

本次合法 concern verdict 的 `evidence` 是字符串数组；`omp-finish --reject` 内部按对象读取 `.ref`，触发：

```text
jq: Cannot index string with string "ref"
```

处理规则：

- 不因 finish 渲染失败丢弃 monitor 已验证的 verdict。
- 不改判为 pass，也不伪造 finish 成功。
- 保留 state/raw 路径和 monitor 紧凑结果；Hermes 明确记录“verdict 合法，finish 展示层 schema 不兼容”。
- 该轮仍按实际 severity 执行 revise/人工裁决。
- 后续应给 `omp-finish.sh` 增加 evidence string/object 双形态回归测试；在脚本修复前，审计 prompt 优先要求 evidence 对象形态，例如 `[{"ref":"file:line","claim":"..."}]`。

## 反例

- kill 后不 monitor，直接宣布 OMP 无 verdict。
- monitor 已报告合法 concern，却因 finish jq 报错将其忽略。
- 为修复展示层错误而重新烧一轮相同 OMP 审计。
