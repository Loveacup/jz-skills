# v2.3 Sampling Upgrade: Real-Video Testing Workflow

Session: 2026-07-08
Scope: bilibili-video-analyzer v2.3 sampling expansion (task packages 5–8) end-to-end validation with a real BVID.

## When to use this reference

- After changing `fetch_all.py`, `fetch_comments.py`, `fetch_danmaku_v2.py`, or `generate_report.py`.
- When the user says "实际测试一下" / "跑一轮真实样片" / "拉起 cli 再测一次".
- When the full `fetch_all.py --report` pipeline appears to hang or fail.

## Test target

Use a real BVID from a user-provided link. Resolve b23.tv short links first:

```bash
curl -sI -o /dev/null -w '%{redirect_url}' 'https://b23.tv/XXXXXXX'
# Extract BVxx from the redirected URL
```

Example: `BV1QcQfB7EtH` (26-min history/science 中配 video).

## 1. Clean old artifacts

Always clean `/tmp` files from the previous run to avoid stale data confusing the report:

```bash
rm -f /tmp/BV1QcQfB7EtH_*
```

## 2. Run the full pipeline (background, long timeout)

```bash
cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/fetch_all.py \
  BV1QcQfB7EtH --report --writer-provider cli --depth-profile claim-first-full \
  > /tmp/bv1qc_report.log 2>&1
```

Recommended timeout: 600–1800s. Use `terminal(background=True, notify_on_complete=True)`.

## 3. If the pipeline hangs

Common hang points in order of likelihood:

1. **YouTube comment fetching** (`fetch_youtube_comments.py`)
   - Depends on `youtube-comment-downloader` or `yt-dlp` parsing YouTube comments.
   - Network/anti-bot can block for many minutes with no output.
2. **H200 ASR** for long audio
3. **yt-dlp** subtitle extraction when cookies are stale

Diagnostic:

```bash
ps aux | grep fetch_all
ls -lt /tmp/BV1QcQfB7EtH_* | head
tail -f /tmp/bv1qc_report.log
```

If it hangs >5–10 min with no progress, `kill` the process and proceed with segmented validation.

## 4. Segment validation (bypass external blockers)

Run each sub-script independently to confirm the core sampling code works:

```bash
PYTHONPATH=scripts python3 scripts/fetch_danmaku_v2.py BV1QcQfB7EtH
PYTHONPATH=scripts python3 scripts/fetch_comments.py BV1QcQfB7EtH --count 150 --strategy mixed
PYTHONPATH=scripts python3 scripts/fetch_subtitle_auto.py BV1QcQfB7EtH
PYTHONPATH=scripts python3 scripts/fetch_youtube_comments.py 'https://www.youtube.com/watch?v=...' --limit 100
```

Expected:
- Danmaku: hundreds to 1000+ samples (stratified)
- Comments: up to 150 mixed comments + hot replies (bounded by actual video comment count)
- Subtitle: `h200-asr-chunked` or `official` path
- YouTube: best-effort; failure is OK for core Bilibili pipeline validation

## 5. Mock-input reconstruction for report generation

When the full pipeline is blocked by an external dependency (e.g., YouTube comments), you can still validate `generate_report.py` by reconstructing a mock input from the collected files:

```python
import json, os
bvid = 'BV1QcQfB7EtH'

results = {
    'bvid': bvid,
    'info': {'bvid': bvid, 'title': '<title from view API>', 'owner': '<owner>', 'status': 'ok'},
    'danmaku': json.load(open(f'/tmp/{bvid}_danmaku.json')),
    'comments': json.load(open(f'/tmp/{bvid}_comments.json')),
    'subtitle': {
        'method': 'h200-asr-chunked',
        'txt_path': f'/tmp/{bvid}_subtitle_whisper.txt',
        'text': open(f'/tmp/{bvid}_subtitle_whisper.txt').read(),
    },
    'cross_platform': None,  # or fill if YouTube data succeeded
}

with open(f'/tmp/{bvid}_mock_input.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

Then run:

```bash
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BV1QcQfB7EtH_mock_input.json \
  --output /tmp/BV1QcQfB7EtH_report.md \
  --writer-provider cli --depth-profile claim-first-full
```

Expected: `frontmatter.danmaku_count` > 0, `comment_count` > 0, `claim_bundle_stats.claims_count` > 0.

## 6. Quality checks

After the report is generated:

1. `danmaku_count` matches `/tmp/{BV}_danmaku.json` sampled count.
2. `comment_count` matches the expanded comment+reply total.
3. Report contains `## 3. 核心洞察` with at least 2–3 insights.
4. No `_骨架占位_` in final sections (unless it's a skeleton preview).
5. Run the full test suite: `pytest -q tests --ignore=tests/test_asr_config.py` → 228/228 passed.

## 7. Bugs discovered in this session

| Bug | Symptom | Fix |
|-----|---------|-----|
| `fetch_all.py` leaked `--writer-provider` / `--depth-profile` to child scripts | `fetch_comments.py: error: unrecognized arguments: --writer-provider` | Filter unknown flags in `fetch_all.py` before passing args to sub-scripts |
| `generate_report.py` only read `danmaku.data` | `danmaku_count: 0` despite 506 collected | `_build_danmaku` now supports both `data` and `danmaku` keys |

Both fixes are in commit `446200b`.

## 8. Key lesson

Real-video testing is non-negotiable after CLI/parameter changes. Unit tests pass format correctness but miss integration argument routing, stdout vs. file format drift, and external-dependency interaction. When external dependencies block, mock the blocked input rather than skipping report-generation validation entirely.
