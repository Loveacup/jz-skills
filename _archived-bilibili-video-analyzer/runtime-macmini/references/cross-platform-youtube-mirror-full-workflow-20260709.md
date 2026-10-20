# Cross-platform workflow: Bilibili Chinese-dub mirror + YouTube original (2026-07-09)

## Trigger

Bilibili video title/description contains `中配`、`搬运`、`来源：youtube.com/watch?v=` or similar, and the B站 community signals are sparse (0 danmaku, ≤3 comments). The original English video is the authoritative source; the B站 version is a translated/dubbed mirror.

Example: `BV14fTc6TEi5` — title `【中配】【Coding Agent】如何将 Pi 打造成终极编程智能体`, description points to YouTube `6xXjHM3V1zM`, 0 danmaku, 1 comment, 1,427 views.

## Primary source decision

For **Chinese-dubbed/translated mirrors of English originals**, always treat the **YouTube original transcript** as the primary analysis source, and the B站 transcript/ASR only as a cross-check. Reasons:

1. The original English audio is usually the speaker's native delivery — cleaner, more precise, and better timestamped via YouTube auto-subs than a Chinese dub ASR.
2. B站 H200/local ASR has no sentence-level timestamps, making exact `[mm:ss]` attribution hard.
3. Chinese dub ASR introduces translation artifacts and recognition errors (e.g. "P I" split into two tokens, "Open Code" vs "OpenCode" vs "Open Core").
4. YouTube comments are typically richer and closer to the original creator community than B站 comments on a low-view mirror.

## Workflow

### 1. Get B站 metadata quickly

```bash
curl -s 'https://api.bilibili.com/x/web-interface/view?bvid=BV14fTc6TEi5' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' \
  -H 'Referer: https://www.bilibili.com/' | python3 -m json.tool
```

Extract: `title`, `owner.name`, `duration`, `stat.view|danmaku|reply`, `cid`, `desc`.

### 2. Fetch YouTube original subtitles + comments

```bash
cd /tmp
yt-dlp --write-auto-subs --sub-lang 'en.*' --skip-download --convert-subs srt \
  -o 'yt_6xXjHM3V1zM' 'https://www.youtube.com/watch?v=6xXjHM3V1zM'
```

Gotchas:
- `--write-auto-subs` may produce `.vtt` even with `--convert-subs srt` if the track is auto-generated. Just parse the VTT or accept VTT as the artifact.
- `--sub-lang 'en.*'` captures `en` and `en-orig`. Use `en` (auto-generated English) if `en-orig` is unavailable.
- Do NOT rely on `yt-dlp --write-comments` alone to produce a comments file; it writes comments into the info JSON only if `--write-info-json` is also set. Prefer the dedicated script:

```bash
cd /Users/alexcai/.hermes/skills/bilibili-video-analyzer
python3 scripts/fetch_youtube_comments.py 'https://www.youtube.com/watch?v=6xXjHM3V1zM' --limit 100
# output: /tmp/6xXjHM3V1zM_youtube_comments.json
```

### 3. Get B站 audio for cross-check ASR

If `fetch_all.py` or `fetch_subtitle_auto.py` hangs/timeouts (common when the video has no official/AI subtitles and `yt-dlp` hits 412), fall back to PlayURL direct audio + H200 ASR.

```bash
# Get CID from step 1; then playurl API
CID=39539248568
curl -s "https://api.bilibili.com/x/player/playurl?bvid=BV14fTc6TEi5&cid=${CID}&qn=80&fnval=16&fourk=1" \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36' \
  -H 'Referer: https://www.bilibili.com/' | python3 -m json.tool

# Extract data.dash.audio[0].baseUrl or data.dash.audio[0].base_url
AUDIO_URL="<url from above>"
curl -sL -o /tmp/BV14fTc6TEi5_audio.m4s \
  -H 'User-Agent: Mozilla/5.0 ...' \
  -H 'Referer: https://www.bilibili.com/' "$AUDIO_URL"

ffmpeg -y -i /tmp/BV14fTc6TEi5_audio.m4s -ar 16000 -ac 1 /tmp/BV14fTc6TEi5_audio.wav
```

### 4. Run H200 ASR

Default H200 endpoint in this environment is `http://172.16.27.10:8088/ASR/transcribe`. If the env var `BILI_ASR_ENDPOINT` is unset, the script may default to a different port (e.g. 8080) and fail. Override explicitly:

```bash
cd /Users/alexcai/.hermes/skills/bilibili-video-analyzer
BILI_ASR_ENDPOINT=http://172.16.27.10:8088 BILI_ASR_PROVIDER=h200_asr \
  python3 scripts/fetch_subtitle_auto.py BV14fTc6TEi5
```

Or run as background for long audio:

```bash
BILI_ASR_ENDPOINT=http://172.16.27.10:8088 BILI_ASR_PROVIDER=h200_asr \
  python3 scripts/fetch_subtitle_auto.py BV14fTc6TEi5 > /tmp/bv14_asr.log 2>&1 &
```

H200 ASR for 21-minute audio took ~10 minutes in this session. Output: `/tmp/BV14fTc6TEi5_subtitle_whisper.txt` (text only, no per-sentence timestamps).

### 5. Hand-write the full 8-section report

Do NOT save the YouTube engine skeleton (`/tmp/yt_6xXjHM3V1zM_youtube_report.md`) or the B站 engine skeleton directly. Use them as evidence only. Write:

- `## 0. 元信息` — include cross-platform source table, note B站 is mirror, note data sparsity.
- `## 1. 逻辑链` — use Mermaid flowchart + short narrative arcs.
- `## 2 / 2.5` — state data scarcity in ≤50 words; move to YouTube comments for community signal.
- `## 3. 核心洞察` — `### 💡 洞察 N：...` format, ≥200 words each.
- `## 4. 深度拆解` — `### 模块 N：...` format, ≥500 words each.
- `## 5. 高光时刻` — blockquotes with YouTube timestamp links.
- `## 7. 批判与行动` — `独特价值` / `局限|偏见` / `可行动|行动项` keywords.
- `## 8. 附录` — data source table with status columns, language note, timestamp precision note.

### 6. Frontmatter compliance (AlexCai vault v2)

Do not use `status: publishable` / `type: video-note` / `priority: P3` / bare tags. Use:

```yaml
---
status: 常青
type: 学习笔记
priority: 正常
aliases: [Pi coding agent, Pi extension system, Pi ultimate coding agent]
tags: [type/学习笔记, status/常青, src/视频, src/bilibili, topic/AI工具, ai/coding-agent]
created: YYYY-MM-DD HH:MM
modified: YYYY-MM-DD HH:MM
---
```

### 7. Verify, save, re-verify, cleanup

```bash
# Verify the draft
python3 scripts/verify_report.py /tmp/报告草稿.md

# Save via terminal cp, NOT write_file
cp /tmp/报告草稿.md "/Users/alexcai/Documents/Obsidian/AlexCai/30-Resources/60_视频笔记/B站笔记_<主题>_YYYYMMDD.md"
ls -la "/Users/alexcai/Documents/Obsidian/AlexCai/30-Resources/60_视频笔记/B站笔记_<主题>_YYYYMMDD.md"
wc -c "/Users/alexcai/Documents/Obsidian/AlexCai/30-Resources/60_视频笔记/B站笔记_<主题>_YYYYMMDD.md"

# Re-verify on the saved file
python3 scripts/verify_report.py "/Users/alexcai/Documents/Obsidian/AlexCai/30-Resources/60_视频笔记/B站笔记_<主题>_YYYYMMDD.md"

# Cleanup large temp files
rm -f /tmp/报告草稿.md /tmp/BV*_audio.m4s /tmp/BV*_audio.wav /tmp/yt_*.en.vtt /tmp/yt_*.en-orig.vtt
```

## Key pitfalls

| Pitfall | Why it happened | Fix |
|---|---|---|
| `fetch_subtitle_auto.py` timed out after 300s | Video had no official/AI subtitles; `yt-dlp` subtitle step hung on 412 | Switch to PlayURL → ffmpeg → H200 ASR |
| `yt-dlp --write-comments` produced no comments file | `--write-comments` writes into info JSON only with `--write-info-json` | Use `scripts/fetch_youtube_comments.py` |
| `--convert-subs srt` still produced VTT | yt-dlp behavior with auto-generated subs | Accept VTT, parse with VTT parser |
| H200 ASR default endpoint failed | Env default was `192.168.2.251:8080`; actual gateway is `172.16.27.10:8088` | Set `BILI_ASR_ENDPOINT=http://172.16.27.10:8088` |
| `verify_report.py` G3/G4 failed | Section heading formats / word counts | Use `### 💡` for insights, `### 模块 N：` for modules, expand shortest sections |
| Saved file landed with 600 permissions | `cp` from umask | Run `chmod 644` if needed |
| Frontmatter rejected by vault rules | Used `publishable`, `video-note`, bare tags | Align with AGENTS.md four-dimensional tag scheme |

## Output artifact from this session

Final note: `/Users/alexcai/Documents/Obsidian/AlexCai/30-Resources/60_视频笔记/B站笔记_如何将Pi打造成终极编程智能体_20260709.md` — 23,195 bytes, `verify_report.py` full mode PASS.
