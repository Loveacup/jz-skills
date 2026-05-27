---
name: bilibili-video-analyzer
description: |
  深度分析 Bilibili 视频内容，生成结构化知识资产（13,000+ 字 Obsidian 级 Markdown 报告）。
  支持官方字幕、whisper.cpp/mlx-whisper 音频转录。功能：弹幕情绪分析、评论深度解读、逻辑拆解、批判审视。

  Use when: user provides Bilibili video link (BV号 or full URL), or says 解析B站视频 / analyze bilibili video / bilibili summary / 视频总结 / 弹幕分析 / 分析这个视频.

  DO NOT use for: non-Bilibili videos, general video editing, one-off transcript requests without analysis.
version: 2.0.0
author: Hermes Agent (v2.0 compliance review)
---

# Bilibili 视频深度解析器 v2.0

Transform Bilibili videos into structured, searchable, actionable knowledge assets for Obsidian.

## 🚨 Red Flags: Don't Cut Corners on Analysis

| Excuse | Why it's wrong |
|--------|---------------|
| "The video is short, I'll skip some sections" | All 8 sections are mandatory. Missing sections = incomplete knowledge asset. |
| "Danmaku is only 3 comments, not worth analyzing" | Even sparse danmaku reveals audience reaction patterns. Analyze what's there, note the scarcity. |
| "I'll save to the old clawd path, the user won't notice" | Output path MUST be Obsidian 00-Inbox. Wrong path = lost file. |
| "Subtitles failed, I'll just summarize from memory" | Fallback chain: official → whisper.cpp → mlx-whisper. Exhaust fallbacks before summarizing. |
| "I'll skip timestamp links, they're tedious" | Bilibili timestamp formula is `?t={seconds}` (NOT minutes×100+seconds). Density: ≥1 clickable timestamp per 300 chars. |

## 🔀 Decision Tree

```
Received Bilibili URL?
├── YES → Phase 1: Fetch data (metadata → subtitles → danmaku → comments)
│   ├── Subtitles: official → whisper.cpp → mlx-whisper (fallback chain)
│   ├── Danmaku: ≥30-60 samples
│   └── Comments: top 50 hot comments
├── Phase 2: Deep analysis (type diagnosis → danmaku → comments → 3-layer dissection → critical review)
├── Phase 3: Generate report (8 mandatory sections)
└── Phase 4: Save to Obsidian 00-Inbox + cleanup temp files
```

## Phase 1: Data Collection

```bash
# One-shot all data (recommended)
python3 scripts/fetch_all.py BV1ut6YByEZq

# Individual scripts
python3 scripts/fetch_danmaku_v2.py BV1ut6YByEZq    # Danmaku
python3 scripts/fetch_comments.py BV1ut6YByEZq       # Comments
python3 scripts/fetch_subtitle_auto.py BV1ut6YByEZq  # Subtitles (auto-fallback)
```

See `references/execution-guide.md` for dependencies (yt-dlp, whisper.cpp) and troubleshooting.

## Phase 2: Deep Analysis

1. **Type diagnosis**: Tutorial / Interview / Review / Narrative / Speech
2. **Danmaku analysis**: 6 emotion categories, high-frequency terms, cultural memes → see `references/danmaku-analysis-guide.md`
3. **Comments analysis**: Hot comment curation, opinion clustering, creator interaction
4. **3-layer dissection**: Explicit / Implicit / Meta-narrative
5. **Critical review**: Validity / Blind spots / Audience fit

Full analysis framework: `references/v3-detailed-prompt.md`

## Phase 3: Output (8 Mandatory Sections)

| # | Section | Requirement |
|---|---------|------------|
| 0 | Meta | Video title, UP主, play count, CID, duration |
| 1 | Logic Chain | Narrative structure, argument flow |
| 2 | Danmaku Intelligence | Emotion quantification, meme analysis |
| 2.5 | Comments Analysis | Hot comments curation, opinion clustering |
| 3 | Key Insights | ≥3 insights |
| 4 | Deep Dive | ≥3 modules with layered analysis |
| 5 | Highlights & Quotes | Memorable moments with timestamps |
| 6 | Knowledge Graph | Concept map, cross-references |
| 7 | Critical Review & Action | Validity assessment, actionable takeaways |
| 8 | Appendix | Data sources, tools used, full quotes |

**Timestamp formula**: Bilibili `?t={total_seconds}`. `02:30` → 150 seconds → `?t=150` (NOT `?t=230`!).

Full template: `references/output-template.md`

## Phase 4: Save & Cleanup

- ✅ Save to: `~/Documents/Obsidian/AlexCai/00-Inbox/视频解析_[关键词]_[作者名].md`
- ✅ Clean temp files: `rm -f /private/tmp/BV* /private/tmp/cid_*`
- ❌ Never save to: `~/clawd/00-Inbox/` or vault root

## Script Reference

| Script | Function | Dependency |
|:---|:---|:---|
| `fetch_all.py` ⭐ | One-shot: danmaku + comments + subtitles | yt-dlp, whisper-cli |
| `fetch_danmaku_v2.py` | Danmaku (BV号 direct) | requests |
| `fetch_comments.py` | Comments (top 50 hot) | requests |
| `fetch_subtitle_auto.py` | Subtitles (auto-fallback chain) | yt-dlp, whisper-cli |
| `transcribe_whisper_cpp.sh` | Audio transcription | whisper-cli, ffmpeg |

## Known Limitations

- ⚠️ Official subtitle API requires login (SESSDATA); fallback to audio transcription
- ⚠️ Comment API returns max 3-5 hot comments for new videos (<24h)
- ⚠️ whisper.cpp: ~80-120s per 14-minute video
- ⚠️ Fallback chain: official → whisper.cpp → mlx-whisper → summarize from context

Changelog: `references/changelog.md` — timeout optimization, multi-P video support, BV号 direct access.

## ✅ Verification Checklist

- [ ] All 8 mandatory sections present in the report?
- [ ] Timestamp links use correct `?t={seconds}` formula (NOT `?t=minutes*100+seconds`)?
- [ ] ≥3 Key Insights + ≥3 Deep Dive modules?
- [ ] Danmaku section present even if count is low (analyze scarcity)?
- [ ] Output saved to Obsidian `00-Inbox/` (NOT clawd path or vault root)?
- [ ] Temporary files cleaned from `/private/tmp/`?

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: bilibili-video-analyzer" && git push`
