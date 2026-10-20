# Section QA Gate Phase 2 — assembler integration (2026-07-04)

## Decision

Phase 2 wires the section-level QA evaluator into the `DraftReport` assembly seam, **not** into the publishable/report-generation path yet.

This keeps the artifact boundary intact:

```text
Draft section body → evaluate_draft_section_quality() → DraftReport.qa_results
                                      ├─ P0 blocker: do not insert into draft_sections
                                      └─ P1/P2 issue: insert, but warn
```

Phase 3 will connect this signal to `run_quality_gate.py` / publishable gating. That is intentionally out of scope for Phase 2.

## Role split

- Codex: planning-only implementation plan.
- CC (`cc-tmux`): initial implementation.
- 小黄: coordination, independent validation, diff review, follow-up correction.
- OMP (`call-omp`): independent audit.

## Code changes

### `scripts/video_analysis_engine.py`

`DraftReport` now carries section QA results:

```python
qa_results: Dict[str, SectionQualityResult] = field(default_factory=dict)
```

`assemble_draft_report_slice()` now evaluates every generated section body before insertion:

1. deterministic sections (§1/§5/§6) produce `body`;
2. LLM sections (§3/§4/§7) produce `body` after writer validation;
3. LLM exception / validation failure produces placeholder `body`;
4. `evaluate_draft_section_quality(sid, body)` stores `draft.qa_results[sid]`;
5. `qa_result.blockers` prevents `draft_sections[sid]` insertion;
6. `critical_issues` / `improvements` without blockers still insert the section and append a QA warning.

Critical correction during Hermes review: CC’s initial patch allowed LLM validation-fallback skeleton placeholders to remain in `draft_sections`. 小黄 rejected that and patched the common QA path so fallback placeholders are also evaluated and blocked by D5/no-skeleton.

## Tests

Updated / added:

- `tests/test_draft_report_slice.py`
  - non-skeleton QA-failing §1 remains inserted with warning;
  - skeleton §5 is blocked from insertion while preserving `qa_results`.
- `tests/test_draft_report_llm_slice.py`
  - bad provider validation fallback for §3/§4/§7 yields `qa_results` and no `draft_sections` insertion;
  - QA-failing but non-skeleton §3 remains inserted with warning.

## Verification

Targeted:

```text
PYTHONPATH=scripts:$PYTHONPATH python -m pytest \
  tests/test_section_qa_gate.py \
  tests/test_draft_report_slice.py \
  tests/test_draft_report_llm_slice.py -q

21 passed in 0.03s
```

Release gate:

```text
python scripts/release_gate.py

✅ release gate RUN PASS
fixture quality gate: PASS
pytest full suite excluding ASR config: 149 passed, 3 warnings
```

The three warnings are existing negative writer fallback tests.

## OMP audit

- R1 `omp-20260704-224139`: rejected; auditor exceeded overly narrow scope.
- R2 `omp-20260704-224540`: rejected; auditor correctly noticed `run_quality_gate.py` does not exercise Phase 2, but treated Phase 3 integration as a Phase 2 blocker.
- R3 `omp-20260704-225004`: accepted.

Accepted verdict:

```text
severity: pass
evidence: 9
summary: Phase 2 assembler contract 全部满足：qa_results 覆盖 deterministic/LLM/placeholder 三类 body 产出路径；P0 阻断正确阻止插入并保留证据；P1/P2 非阻断失败正确插入带 warning；LLM 验证失败占位正确经 QA 评估后被阻断。
```

## Known next step

Phase 3 must connect section QA to the publishable/report-generation path. OMP R2’s observation is important for the next slice:

```text
run_quality_gate.py → generate_report.report_markdown() → render_debug_markdown()
```

currently bypasses `assemble_draft_report_slice()` and therefore does not populate `DraftReport.qa_results`. That is expected after Phase 2, but must be resolved before this gate can protect formal generated notes.
