# DraftReport deterministic §1/§5 writer slice (2026-07-03)

## Context

After the DraftReport/PublishedMarkdown boundary landed, `DraftReport` could carry non-publishable intermediate artifacts but did not yet contain written section bodies. The first safe writer slice should improve only the sections that can be generated deterministically from transcript evidence:

- §1 Logic Chain: structure transcript snippets into a readable timeline/table, not raw blockquote dumps.
- §5 Highlights: keep short quote-level highlights and prevent long ASR chunks from passing through.

This slice intentionally does **not** implement a full §0–§8 final writer.

## Implementation

Changed files:

- `scripts/video_analysis_engine.py`
- `tests/test_draft_report_slice.py`

New/changed symbols:

- `DraftReport.draft_sections: Dict[str, str]`
- `write_logic_chain_section(section_context)`
- `_truncate_quote_text(text, limit=210)`
- `assemble_draft_report_slice(report, section_ids=("1", "5"))`

## Contracts

### §1 Logic Chain writer

`write_logic_chain_section()`:

- accepts only evidence where:
  - `source_type == "transcript"`
  - `reason == "logic_candidate"`
  - `text.strip()` is non-empty
- sorts by `start` time;
- deduplicates repeated snippets by normalized text prefix;
- outputs a Markdown table, not raw transcript blockquotes;
- uses deterministic stage/action labels:
  - stage: 起点 / 推进 / 转折 / 收束 / 补充 N
  - action: 提出问题 / 展开机制 / 补充条件 / 形成结论 / 补充证据
- limits evidence summary cell length;
- does not call LLM/network and does not infer unseen facts;
- empty evidence returns `_骨架占位：暂无可用逻辑链证据。_`, preserving publish-gate failure.

Table shape:

```markdown
| 时间 | 阶段 | 逻辑动作 | 证据摘要 | 链接 |
| --- | --- | --- | --- | --- |
```

### §5 Highlights writer

`write_highlights_section()` was tightened:

- target quote count is capped at 5 for `G5`;
- long quote candidates are split by sentence;
- if no sentence boundary exists, text is deterministically truncated to 210 chars + `...`;
- resulting blockquote groups remain below publish gate's 300-char cap;
- non-transcript / non-`quote_candidate` evidence is ignored;
- no candidate still returns skeleton placeholder, preserving publish-gate failure.

### DraftReport assembler

`assemble_draft_report_slice()`:

- returns a non-publishable `DraftReport`;
- populates only:
  - `draft_sections["1"]`
  - `draft_sections["5"]`
- does not mutate legacy render paths;
- does not produce `PublishedMarkdown`;
- does not claim a full final report.

## Verification

### RED

`tests/test_draft_report_slice.py` initially failed because `assemble_draft_report_slice` did not exist.

### Targeted

```bash
PYTHONPATH=scripts pytest -q tests/test_draft_report_slice.py
# 6 passed
```

Additional compatibility set:

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_draft_report_slice.py \
  tests/test_draft_report_boundary.py \
  tests/test_render_markdown_plan.py \
  tests/test_writer_harness.py::test_highlights_writer_splits_long_quote_candidates_to_meet_g5 \
  tests/test_writer_harness.py::test_highlights_writer_filters_title_and_short_fragments \
  tests/test_verify_publishable_report.py
# 25 passed
```

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# G1: PASS — §1: 8 行
# G5: PASS — §5: 5 highlight blockquote groups
# pytest: 127 passed, 4 warnings
```

The 4 warnings are expected existing warnings:

- urllib3 LibreSSL warning;
- §3/§4/§7 fallback warning tests.

## OMP audit

Task:

- `omp-20260703-110630`

Result:

- severity: `concern`
- accepted

Reason for concern:

- OMP requested stronger evidence for the exact diff and highlight gate body.

Follow-up evidence was manually checked before commit:

- `git diff -- shared/bilibili-video-analyzer/scripts/video_analysis_engine.py` showed:
  - `DraftReport.draft_sections` field addition;
  - new §1 writer;
  - quote truncation and target cap changes;
  - `assemble_draft_report_slice()` only writes `draft_sections['1']` and `draft_sections['5']`;
  - `render_debug_markdown()` / `render_markdown()` were not changed.

## Commit

```text
c9ef412 feat(bilibili): add deterministic §1/§5 DraftReport writer slice
```

## Boundary

This is **not** a publishable final report generator.

It only proves that the DraftReport seam can host deterministic written section bodies while preserving the publish gate and legacy debug rendering behavior.

Next safe slice: route existing §3/§4/§7 LLM writer outputs into `DraftReport.draft_sections` without changing the legacy renderer.
