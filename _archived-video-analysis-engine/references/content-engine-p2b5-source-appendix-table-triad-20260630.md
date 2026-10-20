# P2-B5 · Source Appendix §8 数据源表升级（三方协作记录）

日期：2026-06-30

## 范围

P2-B5 只升级 `render_markdown()` 的 Source Appendix 呈现契约：

- `§0 Meta`：保留简洁来源摘要，避免把完整路径/multi-P 细节塞进开头。
- `§8 Appendix`：升级为固定列、固定行顺序的 Markdown 数据源表，供后续正式 writer 接入。

明确不做：

- 不接 LLM writer。
- 不改 ASR / fetch / subtitle pipeline。
- 不改 `generate_report.py` 的 transcript metadata 生产逻辑。
- 不改变 `evidence_gate.sources` 上游 schema。

## 契约

`§8` 的 `### Source Appendix` 输出固定列：

```text
source_type | available | method | language | segments | chars | count | json_path | txt_path | parts | failed_parts | notes
```

固定行顺序：

```text
transcript → comments → danmaku → fact_checks → external_research
```

`transcript.source` 仍沿用 P2-B3 编码串：

```text
method|json_path=...|txt_path=...|parts=2/3|failed_parts=...
```

P2-B5 仅在 render 层解析该字符串到表格单元格；不把这些字段提升为新的上游 schema。

## 无 transcript 规则

无 transcript 时：

- `transcript_available=false`
- `transcript` 行 `available=false`
- `method/json_path/txt_path/parts/failed_parts` 单元格为空
- 全文不出现伪造的 `json_path=` / `txt_path=` / `parts=` / `failed_parts=` 原始字段文本

## 三方流程

1. Codex planning-only 给出窄执行包：只改 `video_analysis_engine.py` 与 `test_render_markdown_sources.py`。
2. CC session `cc-bili-p2b5` 实现：
   - `_SOURCE_TABLE_COLUMNS`
   - `_SOURCE_TABLE_ROW_ORDER`
   - `_parse_transcript_source()`
   - `_source_table_rows()`
   - `_emit_source_appendix(..., section)`
3. Hermes 重新取证：读当前生产文件、审 diff、亲自跑 targeted/adjacent/full source tests。
4. OMP 独立审核：`omp-p2b5-source-appendix-table`，severity=`pass`。

## 验证

source repo：

```bash
cd ~/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_render_markdown_sources.py
PYTHONPATH=scripts pytest -q \
  tests/test_render_markdown_sources.py \
  tests/test_render_markdown_plan.py \
  tests/test_evidence_source_gate.py \
  tests/test_generate_report_transcript_metadata.py
PYTHONPATH=scripts pytest -q
```

结果：

```text
12 passed
36 passed
76 passed
```

OMP 证据摘要：

- scope 仅 2 文件：`video_analysis_engine.py`、`test_render_markdown_sources.py`
- §0 无路径泄漏
- §8 固定 12 列 + 5 行顺序
- transcript source 只读解析
- no-transcript 不伪造路径/multi-P 字段
- appendix 仍读 `evidence_gate.sources`，不依赖 `evidence_map.by_section`

## 风险与后续

- 下游若按旧 §8 bullet 格式硬解析，需要改读表格；这是本切片的有意契约升级。
- `external_research.notes` 会随本地 WRR/fallback 检测结果变化；列头和行顺序稳定，内容按环境变化是预期。
- 下一步可以进入正式 writer 接入，但应先用这个 §8 表作为稳定数据源契约，不要让 writer 自己重新猜 source 字段。
