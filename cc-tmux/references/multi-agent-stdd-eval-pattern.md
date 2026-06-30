# Multi-Agent STDD Evaluation Pipeline

> 五阶段跨 agent 评估-规划-执行-审计-验证模式。
> WRR v5.1 (2026-06-29) 全程验证：Phase 1-5 全绿，187/187 tests。

## 五阶段设计

| Phase | Agent | 输入 | 产出 |
|-------|-------|------|------|
| **P1 并行评估** | CC + Codex | eval brief | 独立评估报告 |
| **P2 统一规划** | Codex | 两份评估 + codebase | 实现计划 |
| **P3 执行落地** | CC | 计划 + codebase | commits + tests |
| **P4 独立审计** | OMP | 交付物 | verdict (nit/concern/blocker) |
| **P5 交叉验证** | Hermes | 全量交付 | accept/reject |

## 关键设计原则

1. **P1 并行不是竞速**：CC 和 Codex 各自独立评估，不强求答案一致。分歧在 P2 由 Codex 综合裁决。
2. **P2 裁决分歧**：计划文档必须显式列出 CC vs Codex 的分歧点 + 最终裁决理由。
3. **P3 逐阶段提交**：CC 实现时按 P0→P1 两个独立 commit，每阶段跑全量测试。
4. **P4 红线**：OMP 的 blocker → 必须修复后再 accept。concern/nit → 可 accept 后 fix。
5. **P5 实跑 CLI**：不只跑 pytest，还要 `wrr-cli.py doctor` 实跑看人类可读输出。

## CC 执行边界（P3 约束）

- 不改现有测试行为（baseline 全绿）
- API 引擎只做 key-check，不 live call
- evidence 不裸打印密钥（redaction）
- 修复处方具体（export/install 命令）
- 用 `PYTHONPATH=.` 跑测试

## P4 OMP 审计 checklist

```
criterion: 故障隔离（单引擎 crash 不拖垮全局）
criterion: evidence redaction（不裸打印密钥）
criterion: 修复处方具体可操作
criterion: 测试覆盖边界情况
```

## 本 session 实测数据

- P1: Codex 810行 + CC 1129行（并行约 15min）
- P2: Codex 605行（约 3min，综合两方后裁决 3 项分歧）
- P3: CC 3 commits（P0 1100行 + P1 701行 + fix 1行），~25min
- P4: OMP 43MB raw，4/4 PASS，1 concern → 已修复
- P5: 187/187 tests + CLI 实跑 7/7 OK

总计：~2.5h 端到端（含 OMP 审计等待）。
