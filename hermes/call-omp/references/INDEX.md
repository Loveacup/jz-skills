# call-omp References Index

> 按任务加载；不要把全部 reference 注入同一轮。

## 当前操作合同

- `omp-rpc-acp-notes.md` — RPC/Shell/ACP 通道现状与协议差异。
- `omp-audit-workflow.md` — 审计四步闭环与 verdict 处理。
- `omp-audit-package-json-minimal-example.md` — 最小合法委派包。
- `audit-scope-real-path-contract.md` — scope 必须使用真实路径。
- `preimplementation-audit-contracts.md` — 实现前审计合同。
- `evidence-only-code-audit-contract.md` — evidence-only 审计边界。

## Bundle-only 与 runaway

- `bundle-only-audit-gates.md` — bundle-only 快速 gate。
- `bundle-only-preexisting-evidence-coverage.md` — 未改动证据覆盖。
- `bundle-only-scope-and-termination.md` — scope 与终止。
- `bundle-only-runaway-stop-policy.md` — raw 熔断与降级。
- `bundle-only-unchanged-evidence-and-raw-fuse.md` — unchanged evidence 与 raw fuse。
- `medium-bundle-runaway-criterion-excerpts.md` — 中型 bundle 拆 criterion 摘录。
- `runaway-race-and-finish-schema-20260713.md` — kill/落盘竞态与 finish schema。

## 失败案例与裁决

- `audit-diff-availability.md` — 审计者看不到 diff 时的处理。
- `omp-audit-iteration-pattern.md` — concern/blocker 迭代。
- `omp-audit-blocker-concern-raw-pass-20260705.md` — 大 diff 审计案例。
- `omp-bundle-only-scope-creep-20260707.md` — bundle scope creep。
- `omp-shell-scope-creep-hn-fix-20260708.md` — Shell scope creep。
- `omp-hn-unit-fix-r5-override-20260708.md` — monitor 误拒后的人工取证。
- `omp-extract-markdown-wrapped-verdict-20260706.md` — fenced verdict 提取。
- `omp-small-fix-audit-raw-bloat-20260708.md` — 小修复证据包精简。

## 平台与 ACP 探针

- `platform-adapters.md` — 平台适配总览。
- `claude-code-call-omp.md` — Claude Code 调用视图。
- `omp-self-call.md` — OMP self-call 递归护栏。
- `OD-OMP-1-acp-smoke.md` — ACP initialize smoke。
- `OD-OMP-2-acp-client.md` — ACP 方言探针。
- `omp-shell-smoke-test.md` — 真 token Shell smoke，手动运行。
- `watch-acceptance-checklist.md` — watch 验收。

## 安全救援

- `sandbox-escape-gateway-rescue-20260629.md` — gateway 救援、安全边界和误归因订正。
- `hermes-gateway-plist-env-fix.md` — launchd plist 环境变量诊断。

## 应用集成与历史

- `application-cli-writer-vs-omp-audit.md` — writer 与独立 auditor 分治。
- `historical-operations-and-pitfalls.md` — v0.7.x 以前完整历史说明；非当前操作合同。
