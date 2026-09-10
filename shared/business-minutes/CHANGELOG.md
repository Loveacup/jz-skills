# Changelog

## v1.0.0 (2026-09-10)

- First release. Fusion of `voice-to-markdown-workflow` v6.0 pipeline, the vault minutes SOP, and `video-analysis-engine`-style gates.
- `scripts/verify_minutes.py`: G1 frontmatter · G2 参会表 · G3 执行摘要 · G4 决策四要素+ID · G5 行动项责任人+节点+证据 · G6 原话引用 · G7 外部依据 · G8 订正表 · G9 字数下限 · G10 占位符/倾倒. Exit 1 on any FAIL.
- Templates for 商务拓展纪要 / 需求交流纪要 / 周例会纪要.
- Relay task-pack template and Leader rules from the 2026-09-08 惠登 run (narrow reads, one wait loop, settle-from-receipt).
- Origin incident: 惠登需求交流 minutes came out at 69 lines against a 922-line exemplar because minutes were a side product; this skill makes them a gated deliverable.
