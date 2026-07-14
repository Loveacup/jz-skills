# Bundle-only runaway stop policy

用于 `call-omp` 的 evidence-only / bundle-only 审计。目标不是记录某次任务，而是提供可复用的体积熔断与降级裁决模板。

## 1. 何时启动熔断

OMP shell async 启动后，除 `omp-monitor --watch` 外，每 10–15 秒采样：

- raw bytes
- raw lines
- process alive
- state phase
- 是否已有合法 `{severity,evidence,summary}` 候选

满足任一条件即停止等待：

1. raw > 20MB 且没有合法 verdict；
2. 连续 3 个采样窗口 raw 高速增长，但 verdict/evidence 数仍为 0；
3. `stopReason=toolUse/aborted` 且进程已退出；
4. watch timeout。

不要因为 bundle 很小、prompt 写了“不要调用工具”就取消体积熔断。

## 2. 停止后的固定顺序

1. 停止 OMP 进程（若仍存活）。
2. 单次运行 `omp-monitor.sh --state <state>`。
3. 查看 compact debug；必要时只提取最后 assistant turn，不把完整 raw 注入上下文。
4. 若存在合法 JSON verdict：按正常 blocker / concern / pass 流程。
5. 若无合法 verdict、`evidence=0`：`omp-finish.sh --reject`。

## 3. 裁决语义

| 观测 | 语义 |
|---|---|
| 合法 blocker + evidence | 代码/方案 blocker，必须 reject → revise → re-audit |
| 合法 concern + evidence | 处理 actionable item 后缩小范围复审 |
| 合法 pass + evidence | 可 accept |
| aborted/toolUse + 无 JSON + 0 evidence | 审计工具失败；不是 blocker，也不是 pass |

## 4. 何时允许重试

只在以下任一项发生实质变化后重试：

- scope / allowed paths 修正；
- evidence bundle 补了原始命令输出、untracked 文件或关键源码；
- criterion 明显收窄；
- 通道能力发生变化。

以下不算实质修订：

- 单纯延长 timeout；
- 原包原 prompt 再跑一遍；
- 只把“ONLY JSON”写得更大声。

## 5. 降级审查链

同包等价重试禁止后，用两类独立证据闭环：

### 客观证据（Hermes 亲自运行）

- targeted tests + exit code
- full baseline + exit code
- CLI / handler smoke
- `git diff --check`
- diff name-only / redline diff
- protected-file hash parity（若工作区已有未提交成果）

### 主观独立审查

- 独立 read-only reviewer（如 Codex）读取当前 diff；
- reviewer 的自报测试不能替代 Hermes 命令证据；
- 最终记录明确写：`OMP 未产出合法 verdict，已 reject；最终依据为 Hermes 原始证据 + independent read-only review`。

## 6. 推荐验收措辞

```text
OMP 本轮 stopReason=aborted/toolUse，未产出合法 JSON，evidence=0，已正式 reject。
该结果仅表示审计工具失败，不构成代码 blocker 或 pass。
最终验收依据：Hermes 原始测试/smoke/diff 证据 + 独立 read-only 源码审查。
```
