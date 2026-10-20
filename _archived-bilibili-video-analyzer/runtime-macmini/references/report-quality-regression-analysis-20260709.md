# bilibili-video-analyzer 报告质量衰退分析与优化方向（2026-07-09）

## 背景

用户简报：`00-Inbox/简报_bilibili-video-analyzer-skill质量衰退与优化方向_20260709.md`

核心观察：新版报告能通过 `verify_report.py` 静态阈值，但与 2026-06-29 的老版高质量报告（Hermes LLM Wiki、Pi coding agent）相比，丢失了多个增值结构。

## 衰退信号

| 维度 | 老版报告 | 新版报告 |
|------|---------|---------|
| 结构 | §0–§8 完整，含弹幕情绪、评论深度、知识图谱、批判审视 | 常有章节缺失或只剩骨架 |
| 数据稀疏处理 | 0 弹幕/1 评论时仍输出降级框架 + 明确标注 | 直接跳过或删除整节 |
| 洞察子结构 | 定义 / 深度解析 / 弹幕反馈 / 定位 | 只剩一句话结论 |
| 深度模块 | 核心论点 / Mermaid / 论证展开 / 用户栈关联 / 批判审视 | 只剩概述 |
| 个人知识库双链 | 每篇 3–5 个 `[[...]]` | 几乎无 |
| 附录 | 数据源、ASR 链路、失败 fallback、版本记录 | 缺失或极简 |
| 跨平台 | 充分利用 YouTube 原片字幕 + 评论 | 受 B站 ASR 限制，未对齐原片 |

## 根因分析

1. **生成逻辑从“完整模板”退化为“通过校验的最小集”**：writer 学会了满足 Depth Quality Gates 但不保留旧版增值分面。
2. **模板结构被简化/覆盖**：`output-template.md` 或 `ReportPlan.sections` 没有强制 §0–§8 的完整骨架。
3. **数据稀疏无 fallback**：当 `danmaku`/`comments` 为空或极少时，writer 选择删除章节而非保留降级框架。
4. **个人知识库未注入**：writer prompt 没有要求读取 `知识库MOC.md` 并插入 `[[...]]` 双链。
5. **时间/内容压缩**：ASR 与报告生成时间压缩，导致 writer 优先保通过而非保质量。
6. **跨平台证据利用不足**：B站搬运/中配视频仍以 B站 ASR 为主，未优先用 YouTube 原片字幕和评论。

## 优化方向 Top 5

| 优先级 | 修复项 | 改动位置 | 验证方式 |
|--------|--------|----------|----------|
| P0 | 恢复旧版 §0–§8 模板结构 | `references/output-template.md`、`video_analysis_engine.py` 的 `ReportPlan` / `SectionSpec` | 报告必须含所有 8 节标题；verify_report.py 通过 |
| P0 | 数据稀疏场景降级而非跳过 | `build_evidence_map()`、`write_danmaku_section()` / `write_comments_section()` | 0 弹幕/1 评论样例仍输出框架 + 标注“数据不足” |
| P1 | 强制注入个人知识库双链 | `write_knowledge_graph_section()`、`write_deep_dive_section()` writer prompt | 每篇至少 3 个 `[[...]]` 且与 MOC 概念一致 |
| P1 | 恢复洞察子结构与深度模块 | `write_insights_section()`、`write_deep_dive_section()` writer prompt | §3 每条含定义/解析/弹幕反馈/定位；§4 每模块含核心论点/Mermaid/论证/用户栈关联/批判审视 |
| P2 | 附录补全数据源与 ASR 链路 | `render_markdown()` / `render_draft_markdown()` §8 渲染 | 固定输出数据来源、转录工具链、失败 fallback、事实核查、版本记录 |

## 优化方案产出流程

当用户要求“看一下简报/优化方向/质量衰退”时：

1. 阅读简报文件，提取核心衰退信号和根因。
2. 同步阅读项目现状：
   - `SKILL.md`（当前口径、Red Flags、Decision Tree）
   - `scripts/video_analysis_engine.py`（当前引擎结构）
   - `scripts/generate_report.py`（当前报告生成入口）
   - `references/output-template.md`（老版模板）
3. 用 Codex 规划 + CC 小包执行（或 Hermes 直接整合）产出优化方案。
4. 方案必须包含：优先修复项排序、具体改动位置、验证方式、风险回滚、明确边界。
5. 不要只给摘要；要给出可执行的 next step，并询问用户是否进入修复。

## 边界

- 不引入新架构或新依赖（如 jieba、BERT、向量数据库）。
- 不替换现有 `generate_report.py` / `verify_report.py` 底层流水线。
- 不修改 fetcher 代码（`fetch_all.py`、`fetch_subtitle_auto.py` 等）以控制范围。
- 不承诺恢复老版 100% 行文风格，只恢复结构、分面和双链密度。

## 相关文件

- `00-Inbox/简报_bilibili-video-analyzer-skill质量衰退与优化方向_20260709.md`
- `SKILL.md`（当前口径）
- `scripts/video_analysis_engine.py`
- `scripts/generate_report.py`
- `references/output-template.md`
- `references/v2-3-sampling-real-video-testing-workflow-20260708.md`
- `references/v2-3-sampling-upgrade-and-cli-interface-pitfall-20260708.md`
