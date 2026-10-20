# DraftReport §6 deterministic knowledge graph slice (2026-07-03)

## Context

`DraftReport` already supported written bodies for §1/§3/§4/§5/§7 and a non-publishable preview renderer. §6 still remained skeleton-only. This slice adds a deterministic knowledge graph extractor that is conservative enough for preview use and does not call LLM/network.

## Implementation

Changed files:

- `scripts/video_analysis_engine.py`
- `tests/test_draft_report_knowledge_graph.py`

New symbol:

```python
write_knowledge_graph_section(section_context, max_items=8) -> str
```

Assembler change:

```python
assemble_draft_report_slice(report, section_ids=("6",))
# writes draft.draft_sections["6"]
```

## Contract

`write_knowledge_graph_section()`:

- accepts only evidence with:
  - `source_type == "transcript"`
  - `reason in {"knowledge_candidate", "application_candidate"}`
- filters comments, danmaku, quote candidates, and blank text;
- extracts only known verbatim concept patterns, currently:
  - `虚拟偶像`
  - `人格资产`
  - `粉丝信任`
  - `商业化边界`
  - `过度商业化`
  - `连续互动`
  - `稳定人设`
  - `治理`
  - `知识卡片`
  - `行动清单`
  - `Obsidian`
- outputs three deterministic subsections:
  - `### 核心概念`
  - `### 关系链`
  - `### 可落库/可行动项`
- uses Obsidian wikilinks for concepts;
- uses ordered concept co-occurrence in the same evidence sentence for relation chains;
- application items come from `application_candidate` or text containing action/card/checklist markers;
- empty/irrelevant evidence returns skeleton placeholder:
  - `_骨架占位：暂无可用知识图谱证据。_`

## Boundary

This is not a semantic KG engine. It does not infer hidden entities, run NER, call LLM, search external sources, or claim ontology completeness. It is a deterministic preview slice that reduces §6 skeleton residue when transcript evidence contains known concepts.

## Tests

New file:

- `tests/test_draft_report_knowledge_graph.py`

Covered cases:

1. Outputs concepts / relation chains / applications.
2. Uses Obsidian wikilinks.
3. Filters comments / quote candidates / blank text.
4. Deduplicates concepts.
5. Empty evidence remains non-publishable skeleton.
6. `assemble_draft_report_slice(section_ids=("6",))` writes only `draft_sections["6"]` and keeps `DraftReport.publishable=False`.

## Verification

### RED

Initial run failed as expected:

```text
ImportError: cannot import name 'write_knowledge_graph_section'
```

### GREEN

```bash
PYTHONPATH=scripts pytest -q tests/test_draft_report_knowledge_graph.py
# 4 passed
```

### Targeted suite

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_draft_report_knowledge_graph.py \
  tests/test_render_draft_markdown.py \
  tests/test_draft_report_slice.py \
  tests/test_draft_report_llm_slice.py \
  tests/test_draft_report_boundary.py
# 20 passed
```

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# pytest full suite excluding ASR config: 137 passed, 4 warnings
```

Warnings are existing expected warnings:

- urllib3/LibreSSL;
- §3/§4/§7 fallback negative tests.

## OMP audit

First run:

- `omp-20260703-125805`
- rejected due to invalid output structure; not accepted.

Accepted run:

- `omp-20260703-130418`
- severity: `pass`
- evidence: 9
- accepted

OMP confirmed:

1. conservative filtering: transcript + knowledge/application only;
2. no LLM/network;
3. three-section output plus skeleton empty state;
4. assembler writes `draft_sections['6']` while retaining non-publishable DraftReport;
5. tests and release gate pass.

## Next safe slice

Two options:

1. add deterministic §2/§2.5 social signal clustering; or
2. add a CLI/debug path to emit `render_draft_markdown()` preview to `/tmp` only.
