# Real video full-workflow smoke pattern (2026-07-03)

Use this when the user asks to "测试一下全流程" for a new Bilibili video after quality-gate work. This is a smoke test, not automatically an Obsidian save.

## What to run

1. **Fetch all data**

```bash
PYTHONPATH=scripts python3 scripts/fetch_all.py <BV> | tee /tmp/<BV>_fetch_all_stdout.json
```

Extract the `RESULT_JSON` block into `/tmp/<BV>_fetch_all.json` before passing it downstream.

2. **Run real model-backed quality gate**

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input /tmp/<BV>_fetch_all.json \
  --output /tmp/<BV>_real_sample_report.md \
  --writer-provider cli \
  --fail-on-fallback-warning \
  --json | tee /tmp/<BV>_quality_gate_stdout.txt
```

This verifies the report with both `verify_report.py` and `check_report_coherence()`, and fails if §3/§4/§7 silently fall back to skeleton.

3. **Direct re-checks**

```bash
PYTHONPATH=scripts python3 scripts/verify_report.py /tmp/<BV>_real_sample_report.md
PYTHONPATH=scripts python3 - <<'PY'
from pathlib import Path
from video_analysis_engine import check_report_coherence
md = Path('/tmp/<BV>_real_sample_report.md').read_text(encoding='utf-8')
r = check_report_coherence(md)
print('passed=', r.passed)
print('issues=', len(r.issues))
print(r.issues)
PY
```

4. **Optional independent audit**

For quality-first sessions, package a concise evidence file under `/tmp/<BV>_full_workflow_omp_evidence.md` and run `call-omp` audit with read-only allowed paths for:

- fetch_all JSON
- transcript TXT
- generated report MD
- quality gate stdout
- evidence file
- relevant scripts (`run_quality_gate.py`, `verify_report.py`, `video_analysis_engine.py`)

## What to inspect

Minimum facts to report:

- `ok=true`, `failed_steps=[]`
- danmaku/comment counts and status
- subtitle method, transcript path, `parts/total_parts`, `failed_parts`
- subtitle trace (e.g. official subtitle failures → H200 ASR success)
- quality gate result and gates G1/G3/G4/G5/G7
- `fallback_warning_count=0`
- direct coherence `passed=True, issues=0`

## Decision boundary

Do **not** automatically save to Obsidian after a smoke test. Stop after reporting pass/fail and ask/offer whether to落库正式稿. A smoke test can leave artifacts in `/tmp`; formal save is a separate Phase 4 action (`cp` into vault + verify saved file).

## Example validated pattern

`BV1zrTq6sEPB` had no official subtitles and yt-dlp subs hit HTTP 412, but the automatic fallback chain succeeded via `h200-asr-chunked` (`parts=1/1`, `failed_parts=[]`). The real `cli` writer quality gate passed with `fallback_warning_count=0`, `verify_report` overall pass, and coherence `issues=0`. This validates the no-subtitle → H200 ASR → cli writer → quality gate path.
