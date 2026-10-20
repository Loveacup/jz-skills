# BiliNote + jz-skills Source Absorption Notes (2026-06-30)

Use this reference when improving `bilibili-video-analyzer` after a session that compared:

- Upstream BiliNote: `https://github.com/JefferyHcool/BiliNote`, inspected at commit `6d67e5a76a2c8da1dd73067943d39021ed137c26`
- Old jz-skills implementation: `/Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer`

This is a condensed source-absorption note. It records durable design lessons, not a session diary.

## Top-level synthesis

BiliNote and the old skill solve different layers:

| Source | Durable strength | Absorb as |
|---|---|---|
| BiliNote | Backend architecture boundaries: Downloader / Transcriber / GPT / NoteGenerator, with cache, status, chunking, checkpointing | v3 architecture blueprint |
| jz-skills old skill | Hermes-native execution: small scripts, `RESULT_JSON_START/END`, explicit trace, real-home/user-site handling, PlayURL audio practice | Runtime stability substrate |

Do **not** copy BiliNote's FastAPI/DB/frontend shape into the Hermes skill. Do absorb its boundaries and long-context strategy while keeping the old skill's script-first, diagnosable workflow.

## BiliNote source evidence to remember

### Note orchestration

File: `backend/app/services/note.py`

Key flow:

```text
_get_downloader(platform)
→ transcript cache
→ downloader.download_subtitles(video_url)
→ only if no transcript: _download_media()
→ _get_transcript(audio_file)
→ _summarize_text()
→ markdown post-processing
→ status/cache save
```

Important lessons:

- Platform subtitles are tried before media download.
- If subtitles exist and screenshot/video-understanding is not requested, media download is skipped and only metadata is extracted.
- Audio/transcript/markdown caches are distinct artifacts.
- Status files are written atomically via temporary file + replace.

### Downloader interface

File: `backend/app/downloaders/base.py`

Useful clean-room interface shape:

```python
class Downloader:
    def download(video_url, output_dir=None, quality="fast", need_video=False, skip_download=False) -> AudioDownloadResult: ...
    def download_video(video_url, output_dir=None) -> str: ...
    def download_subtitles(video_url, output_dir=None, langs=None) -> TranscriptResult | None: ...
```

For Hermes, keep this as a light adapter convention rather than a heavy service framework.

### Bilibili subtitle path

Files:

- `backend/app/downloaders/bilibili_downloader.py`
- `backend/app/downloaders/bilibili_subtitle.py`

BiliNote flow:

```text
extract BV / p
→ view API for cid
→ x/player/wbi/v2 for subtitle tracks
→ choose track: manual Chinese > AI Chinese > any Chinese > first non-empty
→ fetch subtitle_url JSON body[]
→ TranscriptResult(segments, full_text, raw)
→ fallback to yt-dlp subtitles
```

Hermes improvement implied: use the explicit track priority instead of naive "first subtitle" selection.

### dm_img patch is TDD-protected but not enough for CLI yt-dlp

Files:

- `backend/app/downloaders/bilibili_dm_patch.py`
- `backend/tests/test_bilibili_dm_patch.py`

BiliNote tests prove:

- `dm_img_*` + `web_location` keys exist.
- patch is idempotent.
- params reach `_sign_wbi` before the playurl request.
- caller query params survive the merge.

Hermes pitfall: this monkey patch only affects **in-process** `yt_dlp` imports. It does not patch CLI subprocess calls (`subprocess.run(['yt-dlp', ...])`). Therefore do not rely on dm_img patch to fix Bilibili audio downloads in the current script runtime.

### YouTube subtitles and proxy

Files:

- `backend/app/downloaders/youtube_downloader.py`
- `backend/app/downloaders/youtube_subtitle.py`

Lessons:

- Prefer `youtube-transcript-api` for subtitles before downloading media.
- Choose manual transcript first, generated transcript second, any available third.
- Proxy injection belongs at downloader/fetcher boundary, not in report generation.

### Long-context analysis

Files:

- `backend/app/gpt/request_chunker.py`
- `backend/app/gpt/universal_gpt.py`
- `backend/tests/test_request_chunker.py`

Durable pattern:

```text
segments + optional images
→ RequestChunker by byte budget
→ chunk-level summaries
→ merge summaries recursively
→ checkpoint partials so failures can resume
```

Tests verify order/content preservation, oversized segment splitting, image distribution, and text grouping by budget. This is the right model for future deep reports; current `video_analysis_engine.py` is only a skeleton/basic statistics layer.

## Old jz-skills source evidence to remember

### RESULT_JSON protocol

File: `scripts/fetch_all.py`

Durable pattern:

- Human-readable stdout is allowed.
- Machine output is delimited by `RESULT_JSON_START` / `RESULT_JSON_END`.
- Failed substeps return structured `{status:'failed', returncode, error}` rather than `None`.

Keep this. It fits Hermes terminal/subprocess execution better than a service-only API.

### Environment substrate

File: `scripts/bili_env.py`

Lessons:

- Hermes profiles may rewrite `$HOME`; do not use `expanduser('~')` for real-user assets.
- Use `pwd.getpwuid(os.getuid()).pw_dir` for real home.
- Append user site-packages, do not insert at index 0, to avoid shadowing stdlib extensions.

### PlayURL direct audio is the stable Bilibili audio fallback

Old source: `scripts/audio_to_text.py`; validated in runtime on `BV1MPjr6zEa8`.

Correct fallback ordering for audio/transcript recovery:

```text
Player/API subtitles
→ yt-dlp subtitles if useful
→ x/player/playurl direct DASH audio stream
→ whisper.cpp/mlx-whisper
→ yt-dlp audio only as last resort
```

Do not say "needs cookie" just because yt-dlp CLI returns 412. First test direct PlayURL audio. In the Supacode case, direct PlayURL fetched both P1/P2 audio and mlx-whisper produced a merged transcript.

### Multi-P rule

Bilibili `duration` from `x/web-interface/view` is total duration across pages. A two-part video may be two audio versions (e.g. bilingual + pure original audio), not extra content. For whisper fallback, iterate `pages[]`, pass each page's `cid`, transcribe each part, and merge with explicit headings (`## P1`, `## P2`, ...). Before reporting success, verify the merged TXT contains all expected part headings.

## Immediate P0 tests to add when modifying this skill

1. `test_bilibili_dm_patch.py`: fake `_sign_wbi`; assert dm params appear pre-signing and caller query survives.
2. `test_playurl_audio.py`: mock `requests.get`; assert `download_audio(bvid, path, cid=...)` uses the passed CID and streams bytes.
3. `test_multi_p_whisper_merge.py`: mock `get_video_info`, `download_audio`, `transcribe_audio`; assert `## P1` / `## P2` and all pages are merged.
4. `test_result_json_failure_not_null.py`: ensure `fetch_all.py` preserves failed substep status/error.

## Recommended architecture direction

```text
old skill's scripts/trace/env resilience
+ BiliNote-style downloader/transcript/chunker boundaries
- BiliNote's FastAPI/DB/frontend deployment weight
```

Next abstraction target: introduce small standard-library models (`TranscriptSegment`, `TranscriptResult`, `AudioMeta`, `VideoMeta`) so `generate_report.py` no longer guesses from `/tmp/{BV}_*.json/txt` paths.
