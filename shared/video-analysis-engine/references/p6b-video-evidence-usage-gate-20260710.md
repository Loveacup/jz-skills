# P6-B1 Video Evidence Usage Gate（2026-07-10）

## 目标

P6-B1 检查最终报告正文是否**实际使用**可解析的本节视频转录证据。它补足 P6-A：P6-A 验证 claim bundle 的内部 pointer；P6-B1 验证最终 Markdown 的 `[E#]` 没有脱离该节 evidence map。

## 范围与边界

- 仅检查最终 Markdown 的 §3「核心洞察」和 §4「深度拆解」。
- `[E#]` 是章节内展示语法；P6-B1 在解析时转换为本节 canonical location，例如 §3 的 `[E1]` → `3:E1`。
- 若该节拥有 transcript candidate，至少必须实际引用一条可解析的 transcript candidate。
- 任意本节未解析引用（如 `[E99]`）会失败，即使同节另有有效 `[E1]`。
- fenced code block 中的 `[E#]` 是示例，不计入正文 evidence usage。
- candidate `start` 倒序只产生 `temporal_order_warning`；没有时间字段也不失败。引用顺序不是叙事因果或事实蕴含的可靠代理。
- legacy/unversioned claim bundle 兼容跳过；debug/tmp 仅保留 metadata，不会被 P6-B1 阻断。

## 正式发布接线

`verify_publishable_report.evaluate_publishable_report(markdown, report)` 在 report 为 versioned bundle 时追加：

```text
P0_VIDEO_EVIDENCE_USAGE
```

正式 `B站笔记_*.md` 需同时通过既有 Markdown gate、P6-A `P0_CLAIM_EVIDENCE_SCORE` 与 P6-B1。非正式路径由 `generate_report.check_formal_output_publishable()` 原样跳过。

`generate_report.report_markdown()` 还将诊断结果放到 `report["video_evidence_usage"]`，供 debug/CI 观察，不嵌入 Markdown，也不改变 debug 退出码。

## 明确不验证

P6-B1 不是 factuality / entailment / 事实核验：

- 不从最终 Markdown 抽取 reader-facing claim；
- 不判断 claim 是否被转录文本蕴含；
- 不验证外部 URL、视频真实性、采集完整性；
- 不调用 LLM、外部服务或新增依赖。

这些属于未来 P6-B2：先建立“最终 claim span → canonical evidence pointer → 原文证据”的数据契约，再选择可校准的语义 judge 与人评集。

## 验收

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_verify_publishable_report.py \
  tests/test_generate_report_publishable_guard.py \
  tests/test_generate_report_writer_provider.py
PYTHONPATH=scripts pytest -q tests
PYTHONPATH=scripts python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json
```

关键回归：跨 section 的 `E1` 消歧、有效引用混入 `E99`、audience-only 引用、fenced 示例、时间倒序 warning、legacy skip 与正式路径 P0 接线。
