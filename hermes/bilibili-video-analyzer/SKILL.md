---
name: bilibili-video-analyzer
description: |
  深度分析 Bilibili 视频内容，生成结构化知识资产（13,000+ 字 Obsidian 级 Markdown 报告）。
  支持官方字幕、whisper.cpp/mlx-whisper 音频转录。功能：弹幕情绪分析、评论深度解读、逻辑拆解、批判审视。

  Use when: user provides Bilibili video link (BV号 or full URL), or says 解析B站视频 / analyze bilibili video / bilibili summary / 视频总结 / 弹幕分析 / 分析这个视频.

  DO NOT use for: non-Bilibili videos, general video editing, one-off transcript requests without analysis.
version: 2.1.0
author: "Hermes Agent (v2.1: adaptive output modes)"
---

# Bilibili 视频深度解析器 v2.1

Transform Bilibili videos into structured, searchable, actionable knowledge assets for Obsidian.

## 🚨 Red Flags: Don't Cut Corners on Analysis

| Excuse | Why it's wrong |
|--------|---------------|
| "The video is short, I'll skip ALL sections" | Even a short tutorial gets metadata + insights + action items. But adapt depth to video type—don't force 8-section analysis on a 10-min how-to. |
| "Danmaku is only 1-3 comments, I'll write 300 words about scarcity" | Acknowledge scarcity in ≤50 words and move on. Don't inflate empty data into a full section. "数据不足，跳过" is better than filler. |
| "I'll save to the old clawd path, the user won't notice" | Output path MUST be Obsidian 00-Inbox. Wrong path = lost file. |
| "Subtitles failed, I'll just summarize from memory" | Fallback chain: official → whisper.cpp → mlx-whisper. Exhaust fallbacks before summarizing. |
| "I'll skip adding YAML frontmatter, it's just metadata" | Obsidian CLAUDE.md requires frontmatter. Missing = broken knowledge graph. |
| "User didn't ask for full analysis, but I'll do it anyway" | **Check first.** Present metadata + ask the user which depth they want. Never assume. |

## 🔀 Decision Tree

```
Received Bilibili URL?
├── YES → Phase 0: Fetch metadata ONLY (no transcription yet)
│   ├── Get: title, author, duration, views, subtitle availability
│   └── ⚠️ STOP HERE. Present metadata to user. Ask: "先看看再说" or "完整版" or "精简版"?
│       ├── "先看看再说" → Wait for user decision. Do NOT transcribe.
│       ├── "完整版" → Phase 1 full: transcription + all sections (see 全量版 below)
│       └── "精简版" → Phase 1 full: transcription + condensed report (see 精简版 below)
├── Phase 1: Fetch data (metadata → subtitles → danmaku → comments)
│   ├── Subtitles: official → whisper.cpp → mlx-whisper (fallback chain)
│   ├── Danmaku: ≥30-60 samples
│   └── Comments: top 50 hot comments
├── Phase 2: Analysis (type diagnosis → depth selection → analysis)
│   ├── Type diagnosis: Tutorial / Interview / Review / Narrative / Speech
│   └── Depth: 全量版 vs 精简版 (see below)
├── Phase 3: Generate report (adaptive sections)
└── Phase 4: Save to Obsidian 00-Inbox + cleanup temp files
```

### Output Mode Selection

After Phase 0 metadata is shown, user picks one. If they don't specify, default to **presenting metadata first**, not auto-running full analysis.

| Mode | When to use | Sections | Good for |
|:---|:---|:---|:---|
| **全量版** | 深度访谈/演讲 ≥30min, or user explicitly says "完整版" | All 8 sections (0-8) | Interviews, keynotes, research talks |
| **精简版** | 教程/How-to <20min, or user says "精简版" | 0 (Meta) + 3 (Key Insights) + 7 (Action Items) + selected Deep Dive modules | Tutorials, config walkthroughs, quick demos |

**精简版 rules**:
- Skip or minimize §2 (Danmaku) and §2.5 (Comments) if data is sparse. One sentence acknowledging scarcity is enough.
- §4 (Deep Dive): reduce to 2-3 modules max, each ≤300 words
- §5 (Highlights): reduce to 2-3 quotes max
- §6 (Knowledge Graph): keep only the core concept table, skip cultural references
- Still include: YAML frontmatter, §0 Meta, §1 Logic Chain (shortened), §3 Key Insights, §7 Critical Review & Action, §8 Appendix
- Report target: 8-12KB (vs 全量版 20-25KB)

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

## Phase 3: Output (Adaptive — See 全量版/精简版 Mode Selection Above)

### 全量版 (All 8 Sections)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | 必填：status/type/priority/aliases/tags/created/modified（遵循 Obsidian CLAUDE.md） |
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

### 精简版 (Condensed)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | Same as 全量版 |
| 0 | Meta | Same as 全量版 |
| 1 | Logic Chain | Shortened: 表层逻辑 only, no meta-narrative |
| 2 | Danmaku/Comments | **Minimal**: ≤50 words if sparse. Write "数据不足" and move on — do NOT inflate. |
| 3 | Key Insights | 2-3 insights, tighter than 全量版 |
| 4 | Deep Dive | **2-3 modules max**, each ≤300 words |
| 5 | Highlights | **2-3 quotes max** |
| 6 | Knowledge Graph | Core concept table only. Skip cultural/meme analysis. |
| 7 | Critical Review & Action | Full — this is the highest-value section for tutorials |
| 8 | Appendix | Sources + version, skip extended reading |

**精简版 report target**: 8-12KB (全量版: 20-25KB)

**Timestamp formula**: Bilibili `?t={total_seconds}`. `02:30` → 150 seconds → `?t=150` (NOT `?t=230`!).

Full template: `references/output-template.md`

## Phase 4: Save & Cleanup

- ✅ Save to: `~/Documents/Obsidian/AlexCai/00-Inbox/视频解析_[关键词]_[作者名].md`
- ✅ Must include YAML frontmatter（status/type/priority/aliases/tags/created/modified）
- ✅ Clean temp files: `rm -f /tmp/BV* /tmp/cid_*`
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
- ⚠️ whisper.cpp: ~68-85s per 19-minute video (Apple M4 GPU)
- ⚠️ Fallback chain: official → whisper.cpp → mlx-whisper → summarize from context
- ⚠️ Tutorial/How-to videos <20min: use **精简版** — full 8-section analysis is overkill
- ⚠️ New videos (<24h, <500 views): expect 0-3 comments and 0-10 danmaku. Don't force analysis on empty data.

Changelog: `references/changelog.md` — timeout optimization, multi-P video support, BV号 direct access.

## ✅ Verification Checklist

- [ ] Phase 0 performed? (Metadata shown to user BEFORE transcription/analysis?)
- [ ] Output mode selected? (全量版 or 精简版 — user chose explicitly?)
- [ ] YAML frontmatter present? (status/type/priority/aliases/tags/created/modified)
- [ ] Timestamp links use correct `?t={seconds}` formula (NOT `?t=minutes*100+seconds`)?
- [ ] 精简版: report ≤12KB? Sections 2/4/5/6 appropriately condensed?
- [ ] 全量版: all 8 sections present? ≥3 Key Insights + ≥3 Deep Dive modules?
- [ ] Sparse danmaku/comments handled with ≤50 words, not inflated into full analysis?
- [ ] Output saved to Obsidian `00-Inbox/` (NOT clawd path or vault root)?
- [ ] Temporary files cleaned from `/tmp/`?

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: bilibili-video-analyzer" && git push`
