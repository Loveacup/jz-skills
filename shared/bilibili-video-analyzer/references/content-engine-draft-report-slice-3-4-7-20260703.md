# DraftReport §3/§4/§7 LLM writer slice (2026-07-03)

## Context

The previous slice added deterministic written bodies for §1 and §5 inside `DraftReport.draft_sections`. The project already had validated LLM writers for §3, §4, and §7, but those were wired only through the legacy/debug renderer path. This slice connects those existing writers to the DraftReport seam without changing `render_markdown()` / `render_debug_markdown()`.

## Implementation

Changed files:

- `scripts/video_analysis_engine.py`
- `tests/test_draft_report_llm_slice.py`

Contract change:

```python
assemble_draft_report_slice(
    report,
    section_ids=("1", "5"),
    provider: Optional[WriterProvider] = None,
) -> DraftReport
```

Behavior:

- deterministic §1/§5 still run without provider;
- §3/§4/§7 run only when an explicit provider is passed;
- no provider means no LLM-backed `draft_sections` are written;
- valid `write_llm_section()` output is stored in `draft.draft_sections[sid]`;
- invalid output or provider exception creates a section placeholder and appends warning;
- output remains `DraftReport(publishable=False)`, never `PublishedMarkdown`.

## Tests

New file:

- `tests/test_draft_report_llm_slice.py`

Covered cases:

1. Valid provider writes §3/§4/§7 into `draft_sections` and calls provider exactly 3 times.
2. Bad provider degrades §3/§4/§7 to skeleton placeholders and records warnings.
3. No provider does not write LLM-backed draft sections.

## Verification

### RED

Initial run failed as expected:

```text
TypeError: assemble_draft_report_slice() got an unexpected keyword argument 'provider'
```

### GREEN targeted

```bash
PYTHONPATH=scripts pytest -q tests/test_draft_report_llm_slice.py
# 3 passed
```

### Writer suite

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_draft_report_llm_slice.py \
  tests/test_draft_report_slice.py \
  tests/test_draft_report_boundary.py \
  tests/test_writer_harness.py \
  tests/test_writer_integration.py
# 34 passed, 3 warnings
```

The warnings are expected fallback tests for §3/§4/§7 legacy renderer behavior.

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# pytest full suite excluding ASR config: 130 passed, 4 warnings
```

## OMP audit

Task:

- `omp-20260703-113142`

Result:

- severity: `pass`
- evidence: 4
- accepted

OMP confirmed:

1. `provider` defaults to `None`, so no default network/LLM call;
2. §3/§4/§7 only run when provider and typed contexts exist;
3. valid provider output enters `draft_sections`;
4. invalid provider output degrades to placeholder + warning;
5. release gate remains green with 130 tests passing.

## Boundary

This is still not a full publishable report writer. It wires existing writer outputs into the DraftReport seam while keeping the publish gate and legacy renderer unchanged.

Next safe slice:

- add a non-publishable `render_draft_markdown(draft)` preview that composes `draft_sections` over debug skeleton; or
- implement §6 deterministic knowledge graph extraction before preview rendering.
