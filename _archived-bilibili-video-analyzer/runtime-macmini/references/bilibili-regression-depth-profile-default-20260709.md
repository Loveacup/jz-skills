# bilibili-video-analyzer 质量衰退与修复实录（2026-07-09）

## 事故

2026-07-09 审计发现：`generate_report.py` 默认 `depth_profile="standard"` 导致报告从旧版 v2.4 八段式深度结构退化到“通过 verify_report.py 的最小集”。
- §3 洞察只剩标题+正文，无“定义/深度解析/弹幕反馈/边界条件”子结构
- §4 模块只剩标题+正文，无“核心论点+Mermaid+用户栈关联+批判审视”
- §6 个人知识库双链未注入
- §7 弹幕共识度分析表消失
- 数据稀疏（0 弹幕/1 评论）时 §2/§2.5 章节被整体跳过

## 根因

`standard` depth profile 是向后兼容的精简版，但被误设为默认。旧版深度报告实际对应 `v24-full` profile（含七步推理链 + Toulmin 结构）。

## 修复动作（P0-P4）

| P | 改动 | 文件 | 验证 |
|---|---|---|---|
| P0 | 默认 `depth_profile` 从 `standard` 改回 `v24-full` | `scripts/generate_report.py` | `pytest` 224 passed；`run_quality_gate.py` PASS |
| P1 | 在 `WRITER_PROMPTS_STANDARD` 的 §3/§4 追加结构约束（核心观点、证据展开、边界说明、证据汇总行） | `scripts/video_analysis_engine.py` | 结构完整性检查 |
| P2 | §7 弹幕共识度分析从“可选”改为“必须输出”，稀疏数据也输出框架 | `scripts/video_analysis_engine.py` | 0 弹幕样例标题存在 |
| P3 | 注入个人知识库双链：读取 `~/Documents/Obsidian/AlexCai/知识库MOC.md`，同时匹配原名和别名，fallback 硬编码高频术语 | `scripts/video_analysis_engine.py` | MOC 105 个概念命中 |
| P4 | §2/§2.5 从 `allowed=has_social` 改为 `allowed=True`，配合 prompt 输出“数据不足”说明 | `scripts/video_analysis_engine.py` | 0 弹幕/0 评论样例章节保留 |

## 关键教训

1. **默认档位即质量承诺**：默认参数不是“向后兼容”的代名词，而是用户拿到手的第一份质量。向后兼容应通过显式 `--depth-profile standard` 保留，而不是把精简版设默认。
2. **verify_report.py 只保证结构下限，不保证内容深度**：报告可以通过所有 gate 但失去增值结构。深度质量需要人工样片对比 + publishable gate。
3. **MOC 匹配要同时考虑原名和别名**：Obsidian 中大量 `[[文件名|显示别名]]`，只匹配文件名会导致显示别名无法命中。应同时保留两者作为候选。
4. **fixture/quality gate 是 LLM 验证不可用时的好 fallback**：当 `omp` 或 `cli` writer 在当前环境无输出/超时时，先用 `--writer-provider fixture` 验证结构和 prompt 注入，真实 LLM 效果择机补测。

## 仍未验证项

- 真实 LLM writer（`--writer-provider cli|deepseek`）对 §3/§4/§7 新 prompt 的实际输出效果
- 不同视频类型下 §6 双链命中率
- 稀疏数据场景的 LLM 实际降级说明质量

## 参考命令

```bash
# 默认 v24-full 结构验证
python3 scripts/generate_report.py --bvid BV1QcQfB7EtH --writer-provider fixture --output /tmp/regression_fixture.md

# 真实 LLM 验证（需可用 writer 环境）
python3 scripts/generate_report.py --bvid BV1QcQfB7EtH --writer-provider cli --output /tmp/regression_llm.md

# 全量回归
pytest tests/ -q --ignore=tests/test_asr_config.py --ignore=tests/test_draft_report_knowledge_graph.py
python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json --writer-provider fixture
```
