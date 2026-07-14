# Bundle-only 审计：把未改动的既有证据显式装箱

## 适用场景

小型代码审计只改 1–3 个文件，但某项验收依赖 **HEAD 中已存在、此次 diff 未触碰** 的测试、契约或安全断言。典型例子：新 fallback 复用旧 adapter 脱敏测试；diff 只增加 fallback 测试，旧 stderr 泄漏测试仍承担 criterion。

## 失败模式

`omp-bundle-code-audit.sh` 的 `diff.patch` 主要突出变化。OMP 若只盯 diff，可能得出“缺少测试/证据”的假 concern，即使 scope snapshot 或仓库中早已有对应测试。大 raw/tool-loop 会进一步放大这个问题：auditor 花大量 token 探索，却错过最短的旧证据。

## 装箱规则

1. **按 criterion 做证据矩阵**，不要只按 changed files 打包：
   - changed implementation
   - changed tests
   - unchanged pre-existing tests/contracts that still prove the criterion
   - Hermes command result/exit code
2. 对每个 unchanged evidence，额外写一份精简摘要，明确：
   - `file:line-range`
   - 测试名 / symbol
   - 输入中的敏感或负向条件
   - 穿过的生产调用链
   - 关键断言
3. 若 auditor 是 `bundle_only`，把上述旧文件或 source excerpt 加入 bundle/allowed paths；不要假设它会从 diff 自动发现。
4. prompt 明确区分：
   - “new coverage in diff”
   - “pre-existing coverage retained in HEAD/current tree”
5. 验证摘要只保留命令、exit code、pass count、关键 live-smoke 状态；不要塞完整 pytest 日志。

## 假 concern 处理

当 OMP 声称“缺少测试”，Hermes 必须先直接核对它指向的 criterion：

- 若测试确实不存在：accept concern，最小补测后复审。
- 若测试已存在且调用链/断言精确覆盖：`omp-finish --reject`，记录 auditor 漏读；不要为了迎合 verdict 重复写等价测试。
- 用 Hermes 原始测试证据 + 独立 read-only reviewer 复核。若 OMP 同一 bundle 已出现 >20MB tool-loop，不做第二次等价重试；只有 evidence 内容实质修订后才允许新一轮。

## 最小证据摘要模板

```text
Criterion: sensitive CLI stderr does not leak
Pre-existing evidence: tests/test_provider.py:87-103
Path: failing runner(stderr="cookie=secret") -> Provider -> Adapter.collect
Assertions: status=unavailable; "secret" not in safe_message; bundle validates
Hermes run: targeted exit 0; full exit 0; release exit 0
```

## 核心原则

**审计输入的单位是 criterion，不是 diff。** Diff 说明“改了什么”，但 unchanged tests/contracts 说明“为什么仍然安全”。二者缺一不可。
