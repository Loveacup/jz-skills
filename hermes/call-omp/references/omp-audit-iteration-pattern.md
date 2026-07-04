# OMP 最终审计迭代模式

> Package C 实战（2026-07-03）：OMP final audit 跑了 4 轮才拿到 pass。
> 这不是 OMP 不可靠，而是 OMP 在多轮审查中逐层揭示问题。

## 迭代序列

| 轮次 | OMP verdict | 实际问题 | Hermes 动作 |
|---|---|---|---|
| v1 | concern | criterion 过窄：我们写了 "only parse/validation failures"，但实现覆盖了所有 rejected non-execute。OMP 正确指出 mismatch。 | 收紧 criterion 为 "rejected non-execute failures"，重新委派 |
| v2 | concern | 文档字段表漂移：`omp-audit-workflow.md` 缺了 `no_final_text/no_candidate/invalid_inner`。test 断言正确但文档没同步。 | 补齐 field table，重新委派 |
| v3 | nit | 测试缺口：16c 只断言 `final_text_bytes=0`，没断言 `failure_stage=no_final_text`。代码正确但测试不完整。 | 补断言 + 1 assertion，重新委派 |
| v4 | pass | — | accept |

## 模式

OMP 审查是逐层深入的：第一轮抓 criterion/contract mismatch，第二轮抓 doc drift，第三轮抓 test gap，第四轮通过。这不是重复浪费——每轮的真实问题都不同，且在前一轮修复后才被揭示。

## 建议流程

1. **第一次 OMP audit 预期至少 1 个 concern/nit**——不是质量标准差，是 OMP 审查密度高。
2. 每次 OMP 给出 concern/nit 时，先读 verdict 的 `issues[]` 和 `reject_instruction`，不要直接跳去做。
3. 修一个问题后重跑 source/runtime tests，然后重新委派同 task（换 task_id）。
4. 如果三轮后仍 concern，停下来检查是否 criterion 有歧义或实现和文档有根本性 mismatch。
5. `call-omp-package-c-final-audit-v4` 证明 pass 是可以拿到的，只是需要逐层收敛。

## 反模式（不要做）

- **不要在 OMP 返回 concern 时直接 accept**——monitor/finish 虽然不物理阻止，但这会绕过审查价值。
- **不要把 concern 当 blocker**——concern 是可接受的偏差，不需要 reject + 重新从头开始，只需要收窄修复后重新委派。
- **不要因为问题小就跳过重新委派**——测试缺口（缺 1 个 chk 行）足够让 OMP 给 nit，而这些 nit 修完后往往下一轮 pass。
