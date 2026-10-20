# P2-B1 EvidenceMap triad workflow — 2026-06-30

## When to use

Use this reference when continuing the bilibili/video-analysis content engine after `ReportPlan` / `SectionSpec`.

This was the first successful triad slice for the content engine:

```text
Codex planning-only → CC/cc-tmux implementation → OMP independent audit → Hermes verification/push/OB
```

## Durable outcome

P2-B1 added an evidence graph layer without touching rendering:

```python
EvidenceCandidate
EvidenceMap
build_evidence_map(inp, report_plan)
```

`analyze_video()` now exposes:

```python
{
  "frontmatter": ...,
  "evidence_gate": ...,
  "report_plan": ...,
  "evidence_map": ...,
  "sections": ...,
}
```

## Schema contract

`EvidenceCandidate` must keep these fields:

```python
source_type: str       # transcript | danmaku | comments | future external_research
section_id: str        # SectionSpec.id, e.g. 1 / 2 / 2.5 / 3 / 4 / 5 / 7
start: float | None
end: float | None
timestamp: str
url: str
text: str
context: str
score: float
reason: str
```

`EvidenceMap` must keep:

```python
video_id: str
baseline: str
by_section: dict[str, list[EvidenceCandidate]]
warnings: list[str]
```

The first CC implementation passed tests but had a too-narrow schema (`source`, no `video_id`, no `baseline`, no `score`, no `reason`). Hermes rejected it and sent a focused schema-fix task. Future agents should review schema against the Codex/OB contract, not only pytest.

## Evidence allocation rules

- transcript → `§1 / §3 / §4 / §5 / §7`
- danmaku → `§2`, only when danmaku exists
- comments → `§2.5`, only when comments exist
- no comments/danmaku → do **not** fabricate `§2 / §2.5`
- no transcript → transcript-backed sections stay empty and warnings include `no_transcript`

Bilibili timestamp URLs use seconds, not MMSS:

```text
start=150 → https://www.bilibili.com/video/<BV>?t=150
start=305.7 → ?t=305
```

## Verification evidence from the slice

Commands used after CC implementation and after runtime sync:

```bash
cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_report_plan.py tests/test_evidence_source_gate.py tests/test_evidence_map.py
PYTHONPATH=scripts pytest -q

cd /Users/alexcai/.hermes/skills/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_report_plan.py tests/test_evidence_source_gate.py tests/test_evidence_map.py
PYTHONPATH=scripts pytest -q
```

Known counts at commit `450f83c`:

```text
source repo: 46 passed
runtime skill: 60 passed
OMP audit: omp-20260630-194922 severity=pass, 12 evidence items
```

## Triad coordination notes

1. Codex should be planning-only and produce a small execution package: max 2 files, tests first, explicit non-goals.
2. CC should execute a small file task. If the first pass is semantically narrow but tests pass, reject with a schema-specific fix task instead of broad critique.
3. OMP should audit after Hermes has produced a runtime evidence bundle with real pytest output.
4. Hermes must independently review diff and rerun tests; never accept CC/OMP self-report alone.

## Next logical slice

P2-B2 should make `render_markdown()` plan-aware:

```text
report_plan.sections + evidence_map
→ old §0–§8 headings/skeleton
→ quote anchors from evidence_map
→ verify_report.py can recognize old framework structure
```

Do not jump to RAG/embedding/LLM writer before P2-B2 closes the `report_plan` ↔ renderer gap.