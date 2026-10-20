# P6-A Atomic Claim Evidence Gate（2026-07-10）

## 目标

P6-A 为 claim-first pipeline 增加**证据指针完整性**发布门：正式报告中的 claim 必须能唯一回到其产生章节的 evidence candidate。它不改变 writer 输出的 `[E#]` 格式，也不做 LLM 语义蕴含判定。

## 根因

`evidence_ids` 是给 writer 使用的章节内编号，`E1` 在 §3 与 §4 中可以同时存在。此前若把裸 `E1` 当全局 ID，发布前审计会把不同章节的正确证据误判为同一来源，或无法可靠阻断错指针。

## 合同

- `Claim.evidence_ids` 保持原样，例如 `E1`：公开 writer/prompt 协议，向后兼容。
- `Claim.evidence_locations` 新增内部 canonical pointer，例如 `3:E1`、`4:E1`。
- `claim_bundle_to_dict()` 写入 `evidence_contract_version: 1`。
- `evaluate_claim_evidence_gate(report)` 只审 §1/§3/§4：
  - canonical location 可解析且非 audience signal → `supported` / `1.0`；
  - comment/danmaku/audience → `partial` / `0.5`，不能成为事实性支持；
  - 空 location 或 `3:E99` 等不可解析 location → `unsupported` / `0.0`，versioned bundle fail-closed；
  - 无版本号的旧 bundle → `skipped=True`，保证历史 payload 兼容。
- `verify_publishable_report.evaluate(markdown)` 继续是 Markdown-only API。
- `evaluate_publishable_report(markdown, report)` 才合并 `P0_CLAIM_EVIDENCE_SCORE`。
- `generate_report.py` 只在正式 `B站笔记_*.md` 或正式视频笔记目录路径调用组合 gate；debug/tmp 不受影响。

## 质量边界

这个 gate 证明的是 **pointer integrity**，而不是“claim 文本已被证据在语义上完全蕴含”。后者需要 P6-B 的视频专属 QA（coverage / factuality / temporal coherence）或受校准的人类审查，不能把本轮的索引解析冒充成事实核验。

## 验收

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_claim_first_pipeline.py tests/test_generate_report_publishable_guard.py
PYTHONPATH=scripts pytest -q tests
PYTHONPATH=scripts python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json
```

关键回归：

1. `§3:E1` 与 `§4:E1` 同时存在，仍能唯一解析；
2. versioned bundle 的空 location 与不可解析 location 都拒绝正式发布；
3. legacy bundle 跳过，不误伤历史 payload；
4. audience signal 只作 partial，不能充当事实性支持；
5. 原 `[E#]` writer 协议不改变。
