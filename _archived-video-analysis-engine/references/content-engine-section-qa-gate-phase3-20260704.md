# Section QA Gate Phase 3 — report/quality metadata exposure (2026-07-04)

## Decision

Phase 3 makes section QA visible on the report/quality path as **machine-readable metadata** without changing Markdown rendering or pass/fail semantics.

```text
report_markdown(results, provider)
  → analyze_video()
  → assemble_draft_report_slice(..., provider=shared_cached_provider)
  → report["section_qa"] = JSON-able qa_results
  → render_debug_markdown(..., provider=shared_cached_provider)
```

`section_qa` is metadata. It is not rendered into Markdown, and it does not yet fail `run_quality_gate()`. A future phase can opt into QA-driven gate behavior.

## Why not make it a gate immediately?

Phase 2 showed `run_quality_gate.py → generate_report.report_markdown() → render_debug_markdown()` bypassed `assemble_draft_report_slice()`. The first fix is visibility: every quality run should surface section QA diagnostics in JSON output. Only after this metadata is stable should it affect pass/fail.

## Code changes

### `scripts/generate_report.py`

- Added `_CachingWriterProvider` to reuse LLM writer responses across QA assembly and legacy debug rendering.
- Added `_serialize_section_qa()` to convert `SectionQualityResult` / `DimensionResult` dataclasses into JSON-able dicts.
- `report_markdown()` now:
  1. builds the analysis report;
  2. runs `assemble_draft_report_slice(report, section_ids=("1", "3", "4", "5", "6", "7"), provider=shared_provider)`;
  3. stores `report["section_qa"]`;
  4. keeps Markdown output on the legacy/debug renderer.

Important correction during Hermes review: CC’s initial implementation would have called real writer providers twice — once during QA assembly and again during rendering. The final version wraps the provider in `_CachingWriterProvider`, so identical §3/§4/§7 prompts are only sent once.

### `scripts/run_quality_gate.py`

`run_quality_gate()` summary now includes:

```python
"section_qa": report.get("section_qa", {})
```

The `passed` calculation is unchanged:

```text
verify_passed
and coherence.passed
and not failed_due_to_fallback_warning
and not failed_due_to_publishable_gate
```

## Tests

Updated / added:

- `tests/test_generate_report_writer_provider.py`
  - `test_report_markdown_populates_section_qa_without_changing_rendered_markdown`
  - `test_report_markdown_reuses_provider_responses_for_qa_and_debug_render`
- `tests/test_run_quality_gate.py`
  - `test_quality_gate_summary_includes_section_qa_metadata`

The cache regression test verifies `provider` is called exactly 3 times for §3/§4/§7, not 6.

## Verification

Targeted:

```text
PYTHONPATH=scripts:$PYTHONPATH python -m pytest \
  tests/test_generate_report_writer_provider.py \
  tests/test_run_quality_gate.py -q

12 passed in 0.08s
```

Release gate:

```text
python scripts/release_gate.py

✅ release gate RUN PASS
fixture quality gate: PASS
pytest full suite excluding ASR config: 152 passed, 3 warnings
```

The release gate JSON now includes non-empty `section_qa`. Example notable signal: fixture output still passes engineering gates while `section_qa["6"]` reports a D5 skeleton blocker. This is expected because Phase 3 exposes diagnostics but does not yet fail the gate.

## OMP audit

- `omp-20260704-231323`
- severity: `concern`
- evidence: 12
- accepted by Hermes

Reason for concern: OMP could statically verify 4/5 criteria but its environment had no usable shell/pytest tool, so it could not independently run the release gate. Hermes accepted because local verification supplied the missing runtime evidence.

## Known next step

Phase 4 should add an explicit opt-in QA gate, likely:

```text
run_quality_gate.py --section-qa-gate
```

or equivalent, where P0 `blockers` fail the quality run and optionally P1/P2 issues can be configured as warnings vs failures. Do not make this default until section-specific exemptions/weights are agreed (e.g. §1 tables and §5 blockquotes currently trip `not-mechanical` despite being expected formats).
