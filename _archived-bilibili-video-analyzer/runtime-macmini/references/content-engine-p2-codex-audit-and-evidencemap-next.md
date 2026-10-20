# Content Engine P2 Codex Audit + P2-B EvidenceMap Direction

Use this reference when continuing `bilibili-video-analyzer` content-engine work after P2-A (`ReportPlan` / `SectionSpec`).

## Verdict

P2-A is directionally correct but incomplete:

- `ReportPlan` / `SectionSpec` correctly preserve Alex's old `§0–§8` report framework as the baseline.
- BiliNote / OpenNote / NoteTaker-py are additive references only; do not replace the old report framework.
- The current gap is that `report_plan` exists, but `render_markdown()` still emits lightweight skeleton sections rather than old-style `## N.` sections that `verify_report.py` can validate.

Treat P2-A as **planning layer completed**, not content-engine completion.

## High-risk gaps to address next

| Priority | Gap | Why it matters |
|---|---|---|
| P0 | `report_plan` and `render_markdown()` are disconnected | Planned `§0–§8` does not yet become gate-valid Markdown |
| P1 | Evidence gate still uses coarse legacy sections | Risks dual section systems: evidence gate vs `SectionSpec.id` |
| P1 | No timestamp/citation evidence model | Sections cannot yet cite transcript evidence deterministically |
| P1 | `generate_report.py` transcript rebuild loses `end`, language, path, multi-P boundaries | EvidenceMap will be weaker unless transcript metadata is preserved |
| P2 | `external_research.available=True` means route availability, not evidence availability | Do not treat WRR/search route as an already verified source |

## P2-B target: EvidenceMap per SectionSpec

Next slice should be **EvidenceMap**, not LLM writing, RAG, or BiliNote-style app architecture.

Add lightweight stdlib dataclasses:

```python
@dataclass
class EvidenceCandidate:
    source_type: str       # transcript | comment | danmaku | external_research
    section_id: str        # 0 / 1 / 2 / 2.5 / 3 / 4 / 5 / 6 / 7 / 8
    start: float | None
    end: float | None
    timestamp: str         # MM:SS / H:MM:SS
    url: str               # Bilibili ?t={seconds}
    text: str              # short exact quote / raw evidence text
    context: str
    score: float
    reason: str

@dataclass
class EvidenceMap:
    video_id: str
    baseline: str
    by_section: dict[str, list[EvidenceCandidate]]
    warnings: list[str]
```

Add:

```python
def build_evidence_map(inp: AnalysisInput, report_plan: ReportPlan) -> EvidenceMap:
    ...
```

Minimum scope:

- Only generate timestamped quote candidates from transcript.
- Cover `§1`, `§3`, `§4`, `§5`, `§7` first.
- Put comments/danmaku into `§2` / `§2.5` only when those sections are allowed; never fabricate social evidence.
- Every transcript candidate needs exact text + seconds-based URL (`?t={seconds}`).

## TDD checklist

Create `tests/test_evidence_map.py` with RED tests before implementation:

1. `test_build_evidence_map_groups_timestamped_candidates_by_section`
   - transcript input produces candidates under old section IDs.
   - `by_section["5"]` has quote candidates.
   - each candidate includes `start`, `timestamp`, `url`, `text`.

2. `test_evidence_map_respects_disallowed_sparse_social_sections`
   - no comments/danmaku means sections `2` / `2.5` are disallowed or empty.
   - EvidenceMap must not create fake social evidence.

3. `test_analyze_video_exposes_evidence_map_without_replacing_report_plan`
   - `report["report_plan"]` remains.
   - `report["evidence_map"]` is added.
   - IDs use `0/1/2/2.5/3/4/5/6/7/8`.

4. `test_timestamp_url_uses_bilibili_seconds_formula`
   - `start=150` becomes `https://www.bilibili.com/video/<BV>?t=150`.
   - Never encode `02:30` as `?t=230`.

Verification:

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_report_plan.py tests/test_evidence_source_gate.py tests/test_evidence_map.py
PYTHONPATH=scripts pytest -q
```

## Things not to do yet

- Do not introduce FastAPI / DB / frontend.
- Do not replace `output-template.md` or `v3-detailed-prompt.md`.
- Do not add vector DB / embedding / RAG before EvidenceMap is stable.
- Do not copy BiliNote's `NoteGenerator` template.
- Do not build a full LLM writer before headings and evidence candidates are gate-compatible.
- Do not treat `external_research.available=True` as a verified source; it only means a route exists.

## Recommended commit slices

1. `feat(bilibili): add evidence map for timestamped transcript candidates`
2. `test(bilibili): lock evidence map and report plan contract`
3. `refactor(bilibili): align renderer headings with depth gates`
