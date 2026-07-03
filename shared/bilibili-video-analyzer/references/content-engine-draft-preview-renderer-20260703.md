# DraftReport non-publishable preview renderer (2026-07-03)

## Context

`DraftReport.draft_sections` can now carry written bodies for §1/§3/§4/§5/§7, but there was no composed preview surface. `render_debug_markdown()` intentionally remains the legacy skeleton/engineering renderer, so a separate preview renderer is needed to inspect draft section bodies without promoting them to `PublishedMarkdown`.

## Implementation

Changed files:

- `scripts/video_analysis_engine.py`
- `tests/test_render_draft_markdown.py`

New symbol:

```python
render_draft_markdown(draft: DraftReport) -> str
```

Behavior:

- accepts only `DraftReport`; non-DraftReport input raises `TypeError`;
- emits explicit marker:

```html
<!-- artifact_kind: draft_markdown_preview; publishable: false -->
```

- follows `report_plan.sections` order;
- when `sid in draft.draft_sections`, uses that written body;
- otherwise falls back to `_emit_section_skeleton()` for inspection;
- keeps §0/§8 Source Appendix emission;
- returns a plain preview string, not `PublishedMarkdown`;
- does not mutate or affect `render_debug_markdown()` / `render_markdown()`.

## Tests

New file:

- `tests/test_render_draft_markdown.py`

Covered cases:

1. Preview overlays `draft_sections` for §1/§3/§5 and includes non-publishable marker.
2. Preview remains rejected by `verify_publishable_report` because unfinished sections still contain skeleton.
3. Legacy debug renderer is not affected by `draft_sections`.
4. Non-DraftReport input is rejected.

## Verification

### RED

Initial run failed as expected:

```text
ImportError: cannot import name 'render_draft_markdown'
```

### GREEN

```bash
PYTHONPATH=scripts pytest -q tests/test_render_draft_markdown.py
# 3 passed
```

### Targeted suite

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_render_draft_markdown.py \
  tests/test_draft_report_llm_slice.py \
  tests/test_draft_report_slice.py \
  tests/test_draft_report_boundary.py \
  tests/test_generate_report_writer_provider.py
# 20 passed
```

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# pytest full suite excluding ASR config: 133 passed, 4 warnings
```

## OMP audit

Task:

- `omp-20260703-121926`

Result:

- severity: `pass`
- evidence: 11
- accepted

OMP confirmed:

1. `render_draft_markdown()` accepts only `DraftReport`;
2. preview emits `publishable:false` marker;
3. `draft_sections` overlays written bodies;
4. unfilled sections keep skeleton / Source Appendix for inspection;
5. `render_debug_markdown()` / `render_markdown()` are not affected;
6. targeted and release gates pass.

## Boundary

This preview is not a publish surface. It is a human/CI inspection artifact.

Next safe slice:

- implement deterministic §6 knowledge graph extractor into `draft_sections['6']`; or
- add CLI/debug command to emit draft preview to `/tmp` only, never formal `B站笔记_*.md`.
