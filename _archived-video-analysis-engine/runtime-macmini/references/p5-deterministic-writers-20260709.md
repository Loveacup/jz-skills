---
title: bilibili-video-analyzer P5 确定性 writer 实现记录
created: 2026-07-09
type: reference
tags: [type/修复记录, src/工程, topic/bilibili-video-analyzer]
---

# bilibili-video-analyzer P5 确定性 writer 实现记录

## 背景

在 v2.3.1 质量衰退修复（P0-P4）基础上，默认 `generate_report`（无 LLM）生成的报告虽然能通过 `verify_report.py`，但内容仍偏薄。用户要求继续提升**默认报告内容质量**，但拒绝重构架构，也拒绝默认启用 LLM writer（避免成本与当前本地 `omp` 超时）。

因此确定优先执行 5 个**纯确定性 writer**优化（P5-1 ~ P5-5），不依赖 LLM，只改 `scripts/video_analysis_engine.py` 和必要测试断言。

## 决策约束

- 不引入新依赖。
- 不修改 fetcher / CLI 入口行为。
- 不替换 `generate_report.py` / `verify_report.py` 底层流水线。
- 小范围 patch，CC 失败后直接 Hermes 手动接管。
- 修改 writer 输出格式时同步更新测试断言。

## P5-1：§1 逻辑链表格

### 目标

让 §1 默认走 `write_logic_chain_section()`，输出结构化表格/Mermaid，而不是只列证据 blockquote。

### 改动

- 在 `_emit_section_skeleton()` 中 `sid == '1'` 分支直接调用 `write_logic_chain_section()`，不再依赖默认证据注入。

### 输出示例

```markdown
### 逻辑链

| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |
| --- | --- | --- | --- | --- |
| 0:00 | 引入 | 提出主题 | 卡特尔垄断前的灯泡 | [0:00](https://www.bilibili.com/video/BVxxx?t=0) |
```

### 测试断言更新

- `tests/test_render_markdown_plan.py::test_transcript_evidence_injected_with_timestamp_url` 从断言 blockquote 改为断言表格结构和关键行。

## P5-2：§5 高光金句筛选

### 目标

从全部字幕候选中筛选出**可读、有信息密度、时间分布均匀**的金句。

### 改动

- `_is_noisy_highlight_fragment()`：
  - 长度阈值从 10 改为 **8-210** 字。
  - 新增广告关键词（企业级、API、优惠、扫码等）、元数据模式（`## P`、`Chunk `、`[00:00]`、中配/字幕/翻译）、纯疑问句过滤。
- `_split_long_quote_candidate()`：当候选无时间戳时，按**原顺序**取前 `target_quotes` 个，而不是按评分排序，保留自然阅读顺序。
- 时间分桶：确保 5 条 quote 尽量分布在不同时间点，避免扎堆。

### 验证

- `pytest tests/test_highlights_writer.py tests/test_writer_harness.py`：18 passed。
- fixture 样片 §5 5 条 quote 覆盖 5 个不同时间点（0:00, 0:30, 0:50, 1:15, 1:40）。

## P5-3：§2/§2.5 受众分析 writer

### 目标

给弹幕和评论分别做确定性深度分析，替代默认证据注入。

### §2 弹幕 `write_danmaku_section()`

- 情绪分类：正面 / 质疑 / 梗 / 中立（关键词匹配）。
- 输出结构：
  - `### 弹幕情绪分布`（表格）
  - `### 代表性弹幕`（按时间 top 5）
  - `### 争议与梗`（质疑/梗类弹幕 top 3）
- 无弹幕时输出降级框架：`### 弹幕信号` + `_数据不足：未提供弹幕。_`

### §2.5 评论 `write_comments_section()`

- 热评观点：按点赞排序 top 3（无 likes 时按原顺序）。
- 信息增量：基于长度 + 补充/资料/链接等关键词评分 top 3。
- 与弹幕差异：评论平均长度 + 评论/弹幕功能差异说明。
- 无评论时输出降级框架。

### 测试断言更新

- `tests/test_render_markdown_plan.py::test_comment_evidence_injected_without_url` 从断言 `> comments证据：...` 改为断言 `### 热评观点` 和具体文本。

## P5-4：§6 知识图谱增强

### 目标

从 transcript 候选中抽取更多概念和关系链，不再依赖极少数预定义概念。

### 改动

- 扩展 `_KG_CONCEPT_PATTERNS`：增加垄断、卡特尔、计划性报废、技术进步、商业激励、用户后果、商业模式等通用概念。
- 新增 `_extract_entities_from_text()`：用正则从文本提取 2-12 字中文短语或 2-12 字符英文/数字术语，过滤停用词和纯数字。
- `_concepts_in_text()`：先匹配预定义概念，再补充自动提取实体，上限 12 个。
- `_concept_link()`：对预定义概念或 Obsidian MOC 中的概念都输出 `[[...]]` 双链；否则保持原文。
- 关系链：当同一句子/候选中出现 ≥2 个概念时，构建 `A → B → C` 链（最多 3 个）。
- 行动项：识别更宽松，包含“可以/应该/需要/值得/转化为/落库/整理/行动/清单/Obsidian/知识卡片”。

### 验证

- `tests/test_draft_report_knowledge_graph.py`：4 passed。
- 注意：`_OBSIDIAN_MOC_FALLBACK` 需要保留 `虚拟偶像`、`人格资产`、`粉丝信任` 等测试概念，否则测试期望的 `[[虚拟偶像]]` 会失败。

## P5-5：§8 附录 writer

### 目标

让 §8 默认输出结构化附录，而非仅 Source Appendix 表。

### 改动

- 新增 `write_appendix_section(report)`：
  - `### 数据来源与可用性`：列出可用/不可用来源。
  - `### 方法限制`：每个可用来源的局限性说明。
  - `### 事实核查与外部研究`：claim 数、外部检索路由/原因。
- `_emit_section_skeleton()` 中 `sid == '8'` 直接调用 `write_appendix_section()`。
- 保留原 `_emit_source_appendix()` 在 §8 后追加 Source Appendix 表。

## 回归验证

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest tests/ -q
# 248 passed, 3 warnings

python3 scripts/run_quality_gate.py --input tests/fixtures/p2e_fetch_all.json --writer-provider fixture
# ✅ quality gate PASS
# verify_report: True
# coherence: True
# G1/G3/G4/G5/G7 PASS
```

## 关键教训

1. **CC 失败后 Hermes 直接接管**：当 CC 因 `Claude plan limit` 弹窗而 tmux 无输出时，kill session 并手动实现 bounded patch 比等待更快。
2. **同步更新测试断言**：writer 输出格式改变时，必须立即检查并更新对应测试断言，否则全量测试会失败。
3. **小范围纯确定性改动优先**：在 LLM 调用超时/成本敏感时，优先用规则、关键词、正则、简单统计提升报告质量，不要硬等 LLM。
4. **MOC 缓存与测试耦合**：`_OBSIDIAN_MOC_CACHE` 会缓存真实 MOC 内容；测试对 `[[概念]]` 的期望应通过 fallback 列表或预定义概念保证稳定。
5. **OMP 环境检查**：调用 `omp` 审计前，先确认 `omp --version` 显示已配 model，而不是把系统 `oh-my-posh` 的 `omp` 当成 LLM agent。
