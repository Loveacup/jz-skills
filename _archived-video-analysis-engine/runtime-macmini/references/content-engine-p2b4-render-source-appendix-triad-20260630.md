# P2-B4 render source appendix — triad record (2026-06-30)

## Decision

P2-B4 makes P2-B3 transcript metadata visible in the rendered report.

Scope:

```text
AnalysisInput.transcript metadata
→ evidence_gate.sources.transcript
→ render_markdown() plan skeleton
→ §0 / §8 Source Appendix
```

No change to:

- `generate_report.py`
- `Transcript` / `EvidenceCandidate` / `EvidenceMap` dataclass schema
- fetch/ASR/network paths
- LLM writer / RAG

## Problem

P2-B3 preserved transcript metadata (`end`, `language`, `json_path`, `txt_path`, `parts`, `failed_parts`), but P2-B2 rendering still showed only a section skeleton.

Users could not see the evidence source boundary in the report body. This violated the skill checklist requirement that formal reports expose transcript evidence source in §0/§8.

## Implementation

Changed files:

```text
scripts/video_analysis_engine.py
tests/test_render_markdown_sources.py
```

`video_analysis_engine.py` now emits a source appendix for `sid in ('0', '8')`:

```markdown
### Source Appendix

- transcript_available=true
- source: official | json_path=/tmp/BVsrc.json | txt_path=/tmp/BVsrc.txt | parts=2/3 | failed_parts=P3: transcribe failed
- language: zh-Hans
- segments: 2
- chars: 7
```

Source Appendix reads only:

```python
report["evidence_gate"]["sources"]["transcript"]
```

It does **not** depend on `evidence_map.by_section`, so it still renders when evidence candidates are empty.

Missing transcript case:

```markdown
### Source Appendix

- transcript_available=false
```

No fake `json_path=`, `txt_path=`, `parts=`, or `failed_parts=` are emitted when transcript is absent.

## Tests

Added `tests/test_render_markdown_sources.py` with coverage for:

- §0 has `### Source Appendix`
- §8 has `### Source Appendix`
- appendix reflects `evidence_gate.sources.transcript` fields
- appendix survives `report["evidence_map"]["by_section"] = {}`
- encoded P2-B3 source string remains visible: method/path/multi-P/failed parts
- missing transcript shows `transcript_available=false`
- missing transcript does not fabricate paths or failed parts

## Verification

Source repo:

```bash
cd ~/code/jz-skills
PYTHONPATH=shared/bilibili-video-analyzer/scripts pytest -q shared/bilibili-video-analyzer/tests
# 71 passed
```

Runtime skill:

```bash
cd ~/.hermes/skills/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q
# 85 passed
```

Smoke:

```text
SOURCE_APPENDIX_SMOKE=1
smoke_exit=0
```

## OMP audit

First OMP round `omp-20260630-214553` gave a substantive pass in raw text, but monitor rejected it because the output was not valid `{severity,evidence,summary}` JSON. It was not accepted.

Accepted compact JSON-only audit:

```text
task_id: omp-20260630-214754
severity: pass
evidence: 7
```

## Lesson

For small render slices, OMP may still wrap JSON in prose and fail monitor extraction. Follow the established rule:

```text
raw says pass but monitor rejected
→ do not accept
→ create compact bundle + runtime evidence
→ re-run JSON-only OMP
→ accept only reported/pass with evidence
```
