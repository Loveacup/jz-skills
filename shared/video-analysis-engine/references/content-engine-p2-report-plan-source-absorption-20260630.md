# Content Engine P2-A Source Absorption — ReportPlan / SectionSpec (2026-06-30)

## Decision

P2-A upgrades `video_analysis_engine.py` by adding an explicit planning layer:

```text
EvidenceSourceGate
→ ReportPlan
→ SectionSpec[]
→ later rendering / WRR / quality gates
```

This keeps Alex's old `§0–§8` video-note framework as the baseline. BiliNote and other GitHub projects are used only as additive architecture references.

## Sources inspected

### Old content engine assets

- `references/output-template.md`
- `references/v3-detailed-prompt.md`
- `scripts/verify_report.py`
- `references/content-engine-upgrade-principles-20260630.md`

Durable assets preserved:

- Full / condensed / merged modes.
- `§0–§8` section structure.
- Depth Quality Gates: G1 / G3 / G4 / G5 / G7.
- Sparse danmaku/comment rule: acknowledge scarcity, do not inflate.
- §7 Critical Review & Action remains full-strength even in condensed mode.

### BiliNote

Repository: `https://github.com/JefferyHcool/BiliNote`
Commit inspected: `6d67e5a76a2c8da1dd73067943d39021ed137c26`

Files inspected:

- `backend/app/services/note.py`
- `backend/app/gpt/request_chunker.py`
- `backend/app/gpt/prompt_builder.py`
- `backend/app/gpt/prompt.py`

Absorbed mechanisms:

| BiliNote mechanism | Decision |
|---|---|
| Subtitle/cache-first orchestration | Keep as data-layer principle; already aligned with EvidenceSourceGate |
| `RequestChunker` byte-budget chunking | Absorb as future long-context strategy for Deep Dive / evidence-backed generation |
| Checkpoint/cached markdown/transcript artifacts | Absorb conceptually for retry/resume, but do not leave artifacts in Obsidian by default |
| Prompt style knobs | Absorb as plan metadata, not as a replacement for Alex's report template |
| FastAPI / DB / frontend task framework | Do not absorb into Hermes skill; too heavy for script-first workflow |

### WRR / GitHub search auxiliary projects

Discovery mode used: GitHub/source discovery via WRR discipline. Public repo quality was low, but two mechanisms are worth keeping as optional future ideas:

| Project | Mechanism | Decision |
|---|---|---|
| `xreme/OpenNote` | transcript chunks → embeddings → timestamped retrieval/citations | Absorb as future evidence-citation model for section grounding |
| `IbrahimHabibeh/NoteTaker-py` | ~60s chunks → salience scoring → clustering → hierarchical topic sections | Absorb as future section-planning heuristic, not current dependency |

Rejected/low-priority:

- Generic YouTube summarizers that only do chunk-summary-merge without strong section planning.
- Full-stack RAG apps whose value is UI/chat rather than durable Obsidian report quality.

## Implemented in P2-A

Files:

- `scripts/video_analysis_engine.py`
- `tests/test_report_plan.py`

New dataclasses:

```python
SectionSpec
ReportPlan
```

New function:

```python
build_report_plan(input: AnalysisInput, evidence_gate: dict | None = None) -> ReportPlan
```

`analyze_video()` now returns:

```python
{
  "frontmatter": {...},
  "evidence_gate": {...},
  "report_plan": {...},
  "sections": {...},
}
```

## Contract locked by tests

- Full videos (`duration >= 30min`) produce `mode == "full"`.
- Short videos produce `mode == "condensed"`.
- Missing transcript produces `mode == "preanalysis"` and blocks formal report.
- Full/condensed formal plans preserve old section IDs:

```text
0, 1, 2, 2.5, 3, 4, 5, 6, 7, 8
```

- Condensed mode can mark sparse social sections optional, but keeps §7 full-strength.
- Plan metadata records absorbed patterns from BiliNote/OpenNote/NoteTaker-py.

## Verification

```bash
cd ~/.hermes/skills/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_report_plan.py
# 4 passed

PYTHONPATH=scripts pytest -q
# 50 passed
```

## Next slice

P2-B should not add more planning fields randomly. The next useful step is:

```text
ReportPlan + transcript chunks
→ EvidenceMap per SectionSpec
→ timestamped quote/citation candidates
```

This is where BiliNote `RequestChunker`, OpenNote timestamped retrieval, and NoteTaker-py salience/clustering become implementation inputs.
