# P2-B3 generate_report transcript metadata preservation — triad record (2026-06-30)

## Decision

P2-B3 fixes the glue layer between `fetch_all.py` / subtitle artifacts and `video_analysis_engine.AnalysisInput`.

Scope is deliberately small:

```text
fetch_all subtitle result / /tmp subtitle artifacts
→ generate_report.py::_build_transcript()
→ AnalysisInput.transcript
→ EvidenceMap / render_markdown downstream
```

No schema change to `video_analysis_engine.py`.
No render/ReportPlan/EvidenceMap change.
No network or ASR call.

## Problem

Before P2-B3, `generate_report.py::_build_transcript()` reconstructed subtitle JSON like this:

```python
start = float(item.get('from', 0) or 0)
text = item.get('content', '')
segments.append(TranscriptSegment(start=start, text=text))
...
duration = int(max((s.start for s in segments), default=0))
return Transcript(segments=segments, language='unknown', source=method), duration
```

This dropped metadata needed by P2-B1/P2-B2:

- `TranscriptSegment.end` was never set.
- `duration` used `max(start)`, so it could truncate the final segment tail.
- `Transcript.language` was hard-coded to `unknown`.
- `Transcript.source` only recorded method, not `json_path`, `txt_path`, or multi-P boundary (`parts`, `failed_parts`).

## Implementation

Changed files:

```text
scripts/generate_report.py
tests/test_generate_report_transcript_metadata.py
```

`generate_report.py` now has narrow helpers:

- `_coerce_float(value)`
- `_segment_end(item, start)` — `to → end → start + duration → None`
- `_pick_language(data)` — `language → lang → lan`
- `_encode_transcript_source(...)` — encodes method/path/multi-P info into the existing `Transcript.source` string

`_build_transcript()` now preserves:

- JSON subtitle item `to` / `end` / `duration` into `TranscriptSegment.end`
- transcript `duration = int(max(end if present else start))`
- step-level language first, then JSON-level language
- source details:
  - `method`
  - `json_path=`
  - `txt_path=`
  - `parts=done/total`
  - `failed_parts=...`

## Tests

Added `tests/test_generate_report_transcript_metadata.py` with coverage for:

- `to` → segment end
- `end` → segment end
- `duration` → `start + duration`
- missing end falls back to start for duration
- language from subtitle step (`language/lang/lan`)
- language from JSON data when step lacks language
- source encodes method/path/multi-P/failed parts
- JSON body preferred over TXT fallback, while source still records both paths
- `build_analysis_input()` end-to-end duration and language
- TXT-only backward compatibility

## Verification

Source repo:

```bash
cd ~/code/jz-skills
PYTHONPATH=shared/bilibili-video-analyzer/scripts pytest -q shared/bilibili-video-analyzer/tests
# 64 passed
```

Runtime skill:

```bash
cd ~/.hermes/skills/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q
# 78 passed
```

Runtime smoke:

```text
language= zh-Hans
ends= [15.5, 30.0]
duration= 30
source= official | json_path=... | txt_path=... | parts=2/3 | failed_parts=P3: transcribe failed
METADATA_SMOKE=1
```

## OMP audit

Final accepted audit:

```text
task_id: omp-20260630-212834
severity: pass
evidence: 14
```

Two earlier OMP rounds were intentionally rejected:

1. `omp-20260630-211843` — `concern`: OMP read `video_analysis_engine.py` as schema anchor outside the initial allowed-path scope. This was an audit-scope issue, not a code issue.
2. `omp-20260630-212144` — `blocker`: caught that CC's first self-report said tests passed, but `generate_report.py` was still old code. This was real and prevented a false pass.

## Key lesson

Do not trust CC self-report for file writes/tests. In this slice, CC initially claimed:

```text
34 passed
64 passed
```

but `git status` showed only the test file untracked and no production-file modification; direct test execution showed `9 failed, 1 passed`.

The correct acceptance pattern is:

```text
CC result file
→ read current production file
→ git diff/status
→ run tests yourself
→ OMP audit with production file + tests + runtime evidence in scope
```

This pattern caught the false positive and should be reused for future bilibili content-engine slices.
