# Section QA gate Phase 1 — triad record (2026-07-03)

## Strategic context

After the 2026-07-03 pivot from "architecture safety first" to "content quality first", the first new infrastructure slice is a per-section content quality evaluator. It gives every writer (deterministic or LLM) a shared metric for whether its output is "good enough."

CC planned Phase 1 as:

- `evaluate_draft_section_quality()`: core evaluator, no pipeline integration
- 5 quality dimensions (D1–D5)
- 3 priority levels (P0 blockers, P1 critical, P2 improvements)

## Implementation

Changed files:

- `scripts/video_analysis_engine.py`
- `tests/test_section_qa_gate.py`

New dataclasses:

- `DimensionResult(dimension, passed, score, issues)`
- `SectionQualityResult(section_id, overall_passed, dimension_results, blockers, critical_issues, improvements, word_count, evidence_refs_count, time_anchor_count)`

New function:

```python
evaluate_draft_section_quality(
    section_id: str,
    section_body: str,
    context: Optional[WriterSectionContext] = None,
) -> SectionQualityResult
```

## Quality dimensions

| D# | Name | Detection | Priority |
|---|---|---|---|
| D1 | evidence-grounded | `[E#]` or `MM:SS` anchor present | P1 |
| D2 | not-mechanical | table+blockquote line ratio < 70% | P1 |
| D3 | human-readable | ≥2 complete sentences | P2 |
| D4 | insight-density | causal keyword or ≥2 prose paragraphs | P2 |
| D5 | no-skeleton | no `_骨架占位`/TODO/template residue | P0 |

This revision intentionally does NOT exempt §5 (highlights) or §6 (knowledge graph) — CC's original plan assumed those were pure data dumps. In our actual system they carry narrative content that must pass quality checks.

## Tests

New file:

- `tests/test_section_qa_gate.py`

9 tests covering:

- passing with evidence
- passing with time anchors + mixed format
- failing empty
- failing skeleton residue
- failing no evidence
- failing table only
- mixed pass/fail dimensions
- result structure completeness
- issue priority order

## Verification

### RED

```text
ImportError: cannot import name 'evaluate_draft_section_quality'
```

### GREEN

```text
PYTHONPATH=scripts pytest -q tests/test_section_qa_gate.py
# 9 passed
```

### Release gate

```text
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# pytest: 146 passed, 4 warnings
```

## OMP audit

- `omp-20260703-135936`
- severity: `pass`
- evidence: 10
- accepted

## Commit

```text
<sha> feat(bilibili): add section-level content quality evaluator
```

## Boundary

Phase 1 exposes the evaluator but does not wire it into the assembler or publish gate. No existing contracts are changed.

Next slice (Phase 2): wire `evaluate_draft_section_quality()` into `assemble_draft_report_slice()` to auto-collect per-section quality results and attach them to `DraftReport.qa_results`.
