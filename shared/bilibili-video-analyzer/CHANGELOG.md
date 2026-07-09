# bilibili-video-analyzer Changelog

## v2.3.1 - 2026-07-09

### 质量衰退修复（P0-P4）

- **P0**: 默认 `depth_profile` 从 `standard` 切换回 `v24-full`，恢复 v2.4 七步推理链 + Toulmin 结构化报告。
- **P1**: 补强 `WRITER_PROMPTS_STANDARD` 的 §3/§4 结构要求：每个洞察/模块必须包含核心观点、证据展开、边界说明/批判审视，以及 `证据：@[E1] @[E2]` 汇总行。
- **P2**: 恢复 §7 弹幕共识度分析表；数据稀疏时也必须输出表格框架并标注“数据不足”。
- **P3**: 注入个人知识库双链到 §6：从 `~/Documents/Obsidian/AlexCai/知识库MOC.md` 读取概念，命中后输出 `[[概念]]` 双链格式；未命中时保持原文；提供 fallback 术语列表。
- **P4**: 修复 §2/§2.5 在数据稀疏时章节消失问题：改为始终保留章节框架并标注“数据不足”，不注水。
- **内部一致性**: 统一 `video_analysis_engine.py` 中所有 `depth_profile` 函数默认值为 `v24-full`，避免与 `generate_report.py` 默认值不一致。

### 验证

- `pytest tests/ -q --ignore=tests/test_asr_config.py --ignore=tests/test_draft_report_knowledge_graph.py`: 224 passed
- `python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json --writer-provider fixture`: PASS
- fixture 真实样片 `BV1QcQfB7EtH`: 结构完整（§0-§8），约 29KB

### 已知限制

- 真实 LLM writer（`--writer-provider cli`）端到端验证因本地 `omp` 调用超时未完成，需待环境恢复后补跑。
- P3 双链、P1 证据汇总行、P2 弹幕共识度表格内容需真实 LLM writer 才能完整验证输出效果。

## v2.3.0 - 2026-07-09

### 采样量扩量与 Bug 修复（第二轮测试）

- 修复 `fetch_all.py` 参数透传 bug：`--writer-provider` 误传给子脚本。
- 修复 `generate_report.py` 弹幕键兼容 bug：支持 `danmaku` 和 `data` 双键。
- 全量测试：228 passed。
- 真实视频样片 `BV1QcQfB7EtH` 成功生成报告，约 26K 字符，3 个洞察。
- 提交：`446200b`

### 已知问题

- 默认 `depth_profile` 被切换为 `standard`，导致结构化报告质量衰退（已在 v2.3.1 修复）。
- YouTube 评论抓取依赖 `youtube-comment-downloader` 不可用，yt-dlp GitHub API 调用失败；暂保持现状，可通过 mock input 绕过。

---

_格式：Keep a Changelog 简化版。关键决策和 CQI 记录详见 Obsidian 项目目录。_
