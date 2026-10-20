# ASR Evidence Gates + Single-Note Output

## Why this exists

A full-looking report can pass `verify_report.py` while still being source-thin. `verify_report.py` checks structural depth, not whether the report is grounded in a transcript. For Bilibili video analysis, transcript availability is now a blocking source gate.

## Hard rules

1. **No transcript, no formal full report**
   - Formal `B站笔记_...md` requires one of:
     - official/AI subtitle;
     - H200 ASR transcript;
     - local whisper/MLX transcript.
   - If all subtitle/ASR routes fail, only produce a clearly labeled `预分析_未通过ASR_...` draft, and do **not** save it as a normal user-facing note.

2. **One video link → one Obsidian note**
   - Default final vault state should contain exactly one user-facing note: `B站笔记_...md`.
   - Do not leave `完整记录稿_...`, raw transcripts, preanalysis files, or audit/intermediate drafts in the vault unless the user explicitly asks for source artifacts.
   - Temporary transcripts may exist in `/tmp` during processing, but clean or avoid vault persistence after the final report is verified.

3. **Source gate must run before structural gate**
   - `fetch_all.py --report` must check `frontmatter.has_transcript` before writing `/tmp/{BV}_report.md`.
   - Then run `verify_report.py` for G1/G3/G4/G5/G7 structural depth.

## PlayURL / H200 ASR production path

For no-subtitle long videos:

1. Resolve BV/CID with Bilibili public API.
2. Fetch PlayURL DASH audio list.
3. Select lowest `bandwidth` audio for ASR (high bitrate wastes download and conversion time).
4. Download via normal stream; if stream fails, retry with HTTP Range chunks.
5. For audio >= 15 minutes, cut into 5-minute WAV chunks:
   - `ffmpeg -ar 16000 -ac 1 -f segment -segment_time 300 ... chunk_%03d.wav`
6. POST chunks to H200 `/ASR/transcribe` and merge the text.
7. Generate formal report only after transcript exists.

## Regression tests to keep green

- `tests/test_fetch_all_report_gate.py`
  - skips formal report when `has_transcript=False`;
  - writes formal report when transcript exists.
- `tests/test_playurl_audio.py`
  - uses passed page CID;
  - picks lowest bitrate audio for ASR;
  - falls back to Range when normal stream download fails.
- `tests/test_asr_config.py::test_auto_long_audio_uses_h200_chunks`
  - 15min+ audio uses 5-minute H200 chunks and merges transcript.

## Verification commands

```bash
cd ~/.hermes/skills/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q
```

If changes are synced to `~/code/jz-skills/shared/bilibili-video-analyzer`, run the same command there too.
