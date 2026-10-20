# bilibili-video-analyzer v2.3.1 质量衰退修复执行记录（2026-07-09）

## 触发

用户要求按 2026-07-09 简报启动质量衰退修复。选择 A：按 CC/Codex 合并方案执行 P0-P4。

## 方案

- **P0**：默认 `depth_profile` 从 `standard` 切回 `v24-full`
- **P1**：补强 `WRITER_PROMPTS_STANDARD` 的 §3/§4 结构要求（核心观点、证据展开、边界说明/批判审视、证据汇总行）
- **P2**：恢复 §7 弹幕共识度分析表，数据稀疏时强制输出框架
- **P3**：注入个人知识库双链到 §6，从 `~/Documents/Obsidian/AlexCai/知识库MOC.md` 读取概念并匹配转录内容
- **P4**：修复 §2/§2.5 数据稀疏时章节消失问题，改为始终保留框架并标注“数据不足”

## 执行

1. **拆分任务包**：为每个 P 编写独立 `/tmp/cc-tasks/cc-p{N}-task.md`，再合并为 `/tmp/cc-tasks/cc-all-p-task.md`。
2. **CC 执行**：复用既有 tmux session `cc-bili-regression`，发送完整任务包。CC 按 P0→P4 顺序执行，约 40 分钟完成代码修改 + fixture 测试 + 真实样片生成。
3. **Hermes 独立验收**：
   - `git diff` 审查两个改动文件
   - `pytest tests/ -q --ignore=tests/test_asr_config.py --ignore=tests/test_draft_report_knowledge_graph.py` → 224 passed
   - `python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json --writer-provider fixture` → PASS
   - fixture 真实样片 `BV1QcQfB7EtH` → 结构完整（§0–§8），约 29KB
4. **P3 优化**：CC 实现只取 wikilink 文件名，命中率低；改为同时保留文件名和别名（`[[文件名|别名]]`）作为匹配候选。
5. **内部一致性修复**：`video_analysis_engine.py` 中 6 个函数默认 `depth_profile="standard"` 与 `generate_report.py` 新默认值不一致；统一改为 `"v24-full"`。
6. **OMP 审核**：通过 `delegate_task` 派发 OMP 审计，返回 approved=true，但列出 6 条风险；其中内部默认不一致被立即修复，其余风险被记录。
7. **发布**：
   - commit `abf9891`：P0-P4 修复 + 内部一致性修复
   - push main
   - tag `v2.3.1`
   - 新增 `CHANGELOG.md`
   - 更新 OB 项目总览 `00_项目总览.md`

## 未竞项

- 真实 LLM writer（`--writer-provider cli`）端到端验证因本地 `omp` 调用超时未完成；P1/P2/P3 的 prompt 效果需待环境恢复后补跑。
- YouTube 评论抓取依赖问题保持现状，未在本次修复。

## 关键教训

- CC 产物不可采信：即使 CC 写了 `done.txt` 和最终总结，Hermes 必须独立 `git diff` + 跑测试 + 检查样片。
- 默认配置一致性：`generate_report.py` 改了默认值后，必须同步检查 `video_analysis_engine.py` 内部函数的默认值，避免入口与引擎行为分叉。
- 双链匹配策略：MOC 中的 `[[文件名|别名]]` 应同时用文件名和别名做候选，否则转录中的常用概念（别名）会漏匹配。
- 稀疏数据：删除章节比“数据不足”占位更隐蔽，因为 verify_report 仍可能通过，但 reader 会误判维度缺失。

## 相关

- `references/report-quality-regression-analysis-20260709.md`
- `references/v2-3-sampling-real-video-testing-workflow-20260708.md`
- `CHANGELOG.md`（仓库内）
