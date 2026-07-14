# 审计的 diff 可用性与 scope 对齐

## 触发信号

OMP 审计返回类似“无法 inspect actual uncommitted diff”“无 git/bash 能力”或因为读取未列入 scope 的上下文文件而中止。

这不是目标代码的 blocker；是**审计证据输入不足或 scope 配置不完整**。该轮 verdict 不可 accept。

## 审计前检查清单

1. 审计者要看未提交 diff 时，二选一：
   - `independent_readonly`：确认该通道实际具备 `git diff`/bash 工具；或
   - `bundle_only`：用 `scripts/omp-bundle-code-audit.sh` 生成 evidence bundle，并把 `diff.patch`、`git-status.txt`、targeted-test 摘要作为指定证据。
2. `allowed_paths` 必须包含审计任务要求读取的**全部**文件：生产代码、测试、参考文档、以及理解 contract 所需的相邻接口。只读 scope 不要过窄。
3. 对小修复只提供 diff hunk、关键文件片段、targeted test 摘要和 `git diff --check`；避免把全量 pytest 逐行输出塞进包。
4. Prompt 明确：只基于 bundle/允许路径取证；若缺证据，输出 `concern` 并指出缺什么，**不要把工具能力缺失表述为代码 blocker**。

## 失败后的裁决

- `omp-finish --reject`，不采信 aborted/scope-violating verdict。
- Hermes 独立复跑 targeted/full tests、`git diff --check`、读取当前 diff。
- 若原审计给出了明确、可验证的 concern，先补最小回归测试或修复，再以有 diff 的 bundle 做窄范围复审；若通道仍无法取证，记录人工裁决而非伪造 OMP pass。
