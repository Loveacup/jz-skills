# Multi-Round Codex Planning-Discussion Pattern

> 2026-06-30 · v1.40.0 实战验证 · 适用于"需要设计讨论、不直接写代码"的场景

## 模式

当任务涉及**设计修正**而非纯实现时，不要让 Codex 一 round 出 plan 就直接执行。拉它做多轮只读 planning-only 讨论：

### Round 1：诊断 + 初版方向

```bash
codex exec --sandbox read-only 'Planning-only. Do not edit files.
Read <brief>. Inspect relevant code. Produce analysis and initial direction.
Do NOT produce implementation plan yet.'
```

Codex 输出：分析 + 初始方向建议。

### Round 2：自我批判 + 收紧

```bash
codex exec --sandbox read-only 'Round 2 critique. Do not edit files.
Critique your own round 1 proposal for weaknesses: scope creep, unnecessary
state files, over-engineering. Find the leanest path.'
```

Codex 输出：自我批判（如"ledger 太重，不该引入第二套状态源"），收敛到更精简的方案。

### Round 3：最终 plan

```bash
codex exec --sandbox read-only 'Final planning round. Do not edit files.
Produce the FINAL concrete implementation plan. Include exact file changes,
test cases, exit codes, docs, migration notes.'
```

Codex 输出：可执行的最终 plan。

## 为什么有效

- **避免草率落地**：第一轮方向通常不够好，直接执行会在实现中反复修改
- **Codex 自我批判**比 Hermes 批判更有效——它了解自己方案的弱点
- **最终 plan 是锚**：三轮后拿到的方案基本上可以直接执行，不用在实现阶段再争论

## 本轮实战

v1.40.0 CC 补全感知的全链路：

- Round 1：Codex 提 "last_sent ledger + timing + hook evidence"，方向对但太重
- Round 2：Codex 自我批判，收敛到"不加 ledger，收修复窗口 + additive signals"
- Round 3：Codex 出最终 plan（`cc-send-robust` 收紧 repair 窗口 + `cc-wait-decision` schema v2）
- 执行：Hermes 按 plan 实现 → 测试 → push → OB 回写

## 不适用场景

- 纯实现任务（直接 `codex exec` one-shot）
- 简单 bug fix
- 用户已明确指定方案

## 与 OMP 的配合

这个模式之后通常接 **OMP 独立审计**（另一条轨，不在此模式内）。Codex plan → Hermes 实现 → OMP 审计 → 修正 → 再审计。
