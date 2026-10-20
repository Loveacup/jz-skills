# P0 regression lock · BiliBili fallback chain (2026-06-30)

Use this reference when changing `fetch_subtitle_auto.py`, `bilibili_dm_patch.py`, or `fetch_all.py`.

## Locked behavior

Bilibili no-subtitle fallback order is:

```text
Player API / WBI subtitles
→ yt-dlp subtitles best-effort
→ PlayURL API direct DASH audio per page.cid
→ whisper / mlx-whisper transcription
→ yt-dlp audio only as last fallback
```

Do **not** diagnose Bilibili HTTP 412 as “needs cookie” by default. Cookie is login-state help, not a universal 412 fix.

BiliNote’s `dm_img` patch protects in-process `yt_dlp` only. It does not protect `yt-dlp` CLI subprocesses. Hermes runtime must rely on PlayURL direct audio as the stable no-subtitle path.

## Regression tests added

- `tests/test_bilibili_dm_patch.py`
  - required dm keys exist
  - patch idempotent
  - dm params reach yt-dlp `_download_playinfo` request path
  - caller query preserved
- `tests/test_playurl_audio.py`
  - `download_audio(bvid, path, cid=P2)` uses passed P2 cid, not P1
  - PlayURL success does not invoke yt-dlp/subprocess fallback
- `tests/test_multi_p_whisper_merge.py`
  - mock `pages[]`
  - each P calls download/transcribe separately
  - merged transcript preserves `## P1` / `## P2`
- `tests/test_result_json_failure_not_null.py`
  - subprocess failure returns structured `status=failed`
  - parse failure returns `status=ok, parsed=False`
  - successful RESULT_JSON returns `status=ok, parsed=True`

## Verification evidence from session

Hermes reran:

```bash
python3 -m pytest -q tests/test_bilibili_dm_patch.py tests/test_playurl_audio.py tests/test_multi_p_whisper_merge.py tests/test_result_json_failure_not_null.py
# 16 passed, 1 warning in 0.15s

python3 -m pytest -q
# 16 passed, 1 warning in 0.07s

python3 -m py_compile scripts/fetch_subtitle_auto.py scripts/fetch_all.py scripts/bilibili_dm_patch.py
# compile ok
```

OMP audit task `omp-20260630-011247` passed with 26 evidence items and was accepted.

## Process lesson

For future changes to this fallback chain, use the same four-way lock:

```text
Codex planning-only → CC implementation → Hermes test rerun/diff review → OMP independent audit
```

Do not commit unless the user explicitly authorizes git commit/push.
