# Section QA Gate Phase 4 — section exemptions + opt-in gate (2026-07-05)

## Decision

Phase 4 adds two capabilities to make section QA gating practical:

1. **Dimension-specific exemptions** for structural sections whose expected format triggers false positives.
2. An **opt-in `--section-qa-gate` flag** for `run_quality_gate.py`.

Without exemptions, §1 tables and §5 blockquotes fire `not-mechanical` and `insight-density`. These are correct formats for their section types. Phase 4 exempts only those two dimensions for those two sections.

```text
SECTION_DIMENSION_EXEMPTIONS = {
    "1": ["not-mechanical", "insight-density"],  # §1 logic chain = markdown table
    "5": ["not-mechanical", "insight-density"],  # §5 highlights = blockquotes
}
```

Exempted dimensions are forced `passed=true` with `issues=["exempted: structural section §N"]`. Other dimensions (`evidence-grounded`, `human-readable`, `no-skeleton`) are NOT exempted.

## What the flag does

```
--section-qa-gate (default: off)
  when ON: any P0 blocker in any section QA → passed=False for the whole run
  when OFF: identical to pre-Phase-4 behavior
```

P1 (`critical_issues`) and P2 (`improvements`) remain diagnostics only.

## Code changes

### `scripts/video_analysis_engine.py`

- `SECTION_DIMENSION_EXEMPTIONS: Dict[str, List[str]]` — config dict, extendable.
- `evaluate_draft_section_quality()` applies exemptions after dimension results are built, before blockers/critical_issues/improvements are classified.

### `scripts/run_quality_gate.py`

- `run_quality_gate(..., section_qa_gate: bool = False)`
- When enabled, iterates `report["section_qa"]` looking for any section with `blockers` → `failed_due_to_section_qa_gate=True`.
- Adds to summary: `section_qa_gate`, `section_qa_gate_passed`, `failed_due_to_section_qa_gate`.
- CLI: `--section-qa-gate` flag.

## Tests

### `tests/test_section_qa_gate.py` (+3 tests)

- `test_section_1_table_exempts_not_mechanical_and_insight_density`
- `test_section_5_blockquotes_exempt_not_mechanical_and_insight_density`
- `test_section_3_not_exempted`

### `tests/test_run_quality_gate.py` (+3 tests)

- `test_section_qa_gate_disabled_keeps_existing_behavior` — monkeypatch blocker, gate off → unaffected.
- `test_section_qa_gate_enabled_fails_on_p0_blockers` — monkeypatch blocker, gate on → fail.
- `test_section_qa_gate_enabled_passes_without_blockers` — fixture §6 has real blocker, gate on → fail.

## Verification

Targeted:

```text
PYTHONPATH=scripts:$PYTHONPATH python -m pytest \
  tests/test_section_qa_gate.py \
  tests/test_run_quality_gate.py -q

21 passed in 0.08s
```

Release gate:

```text
python scripts/release_gate.py

✅ release gate RUN PASS
fixture quality gate: PASS
pytest full suite: 158 passed, 3 warnings
```

Release gate JSON confirms:
- `section_qa["1"].overall_passed=true` with `not-mechanical` and `insight-density` marked `exempted: structural section §1`.
- `section_qa["6"].blockers` = `D5 no-skeleton` (fixture §6 has real blocker).
- `section_qa_gate: false`, `section_qa_gate_passed: true` (default).
- When run with `--section-qa-gate`, fixture §6 blocker would cause `passed=false`. This is tested in unit tests but the default release gate does not yet use `--section-qa-gate`.

## OMP audit

- `omp-20260705-001936`
- severity: `pass`
- evidence: 10
- accepted

OMP observation (non-blocker): the §5 exemption test fixture would pass `not-mechanical`/`insight-density` even without the exemption (4/6=66.7% blockquote → below 70% threshold; 2 prose paragraphs → enough for insight-density). The test still verifies exemption plumbing, but a boundary case should be added later.

## Known next steps

1. Strengthen §5 exemption test with a fixture that genuinely fails without the exemption.
2. Consider `--section-qa-gate` integration into `release_gate.py` as a separate flag (e.g. `--section-qa-gate` in the release gate runner) once the team agrees to commit to QA-driven gating.
3. Consider P1/P2 configurable strictness for `--section-qa-gate`.
4. Extend exemption mechanism to `context`-based overrides so callers can customize per-run.
