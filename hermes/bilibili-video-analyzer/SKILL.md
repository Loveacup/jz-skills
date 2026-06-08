---
name: bilibili-video-analyzer
description: >
  type: routine
  深度分析 Bilibili 视频内容，生成结构化知识资产（13,000+ 字 Obsidian 级 Markdown 报告）。
  支持官方字幕、whisper.cpp/mlx-whisper 音频转录。功能：弹幕情绪分析、评论深度解读、逻辑拆解、批判审视。
  支持多视频合并分析（同系列/同UP主）。

  Use when: user provides Bilibili video link (BV号 or full URL), or says 解析B站视频 / analyze bilibili video / bilibili summary / 视频总结 / 弹幕分析 / 分析这个视频.

  DO NOT use for: non-Bilibili videos, general video editing, one-off transcript requests without analysis.
version: 2.4.0
author: "Hermes Agent (v2.4: auto fallback chain official→yt-dlp→whisper.cpp→mlx + BV-prefixed danmaku + no null-masking + Depth Quality Gates rubric + verify_report.py)"
---

# Bilibili 视频深度解析器 v2.4

Transform Bilibili videos into structured, searchable, actionable knowledge assets for Obsidian.

## 🚨 Red Flags: Don't Cut Corners on Analysis

| Excuse | Why it's wrong |
|--------|---------------|
| "The video is short, I'll skip ALL sections" | Even a short tutorial gets metadata + insights + action items. But adapt depth to video type—don't force 8-section analysis on a 10-min how-to. |
| "Danmaku is only 1-3 comments, I'll write 300 words about scarcity" | Acknowledge scarcity in ≤50 words and move on. Don't inflate empty data into a full section. "数据不足，跳过" is better than filler. |
| "I'll save to the old clawd path, the user won't notice" | Output path MUST be Obsidian 00-Inbox. Wrong path = lost file. |
| "Subtitles failed, I'll just summarize from memory" | Fallback chain: `yt-dlp --cookies-from-browser chrome` → whisper.cpp → mlx-whisper. Exhaust fallbacks before summarizing. |
| "I'll write the Logic Chain as narrative prose with every quote" ★ | Logic Chain is a **structural overview**, not a transcript retelling. Use **tables (narrative arcs) + Mermaid flowcharts** — keep it under 100 lines. Move verbatim quotes and detailed analysis to Deep Dive / Key Insights. Bloated prose in §1 makes the report unreadable. |
| "I'll skip adding YAML frontmatter, it's just metadata" | Obsidian CLAUDE.md requires frontmatter. Missing = broken knowledge graph. |
| "Report looks thorough, I'll save without running verify_report.py" ★ | Phase 4 STEP 0 is a **blocking gate**. Run `scripts/verify_report.py <草稿>` before saving — "looks thorough" is exactly the judgment the gate exists to catch. Save only on exit 0. |
| "User didn't ask for full analysis, but I'll do it anyway" | **Check first.** Present metadata + ask the user which depth they want. Never assume. |
| "User said to just do it but I showed metadata anyway" ★ | When the user explicitly tells you what to do (整理文档 / 直接分析 / 用bilibili skill 帮我...), skip Phase 0 confirmation. Asking again when they already gave instructions is wasteful. Infer mode from video duration: <20min → 精简版, >=30min → 全量版, unknown → 精简版 (safe default). |
| "Full version report is done at 10KB" ★ | Size is **not** the bar — **Depth Quality Gates** are. 全量版 must pass G3 (≥3 insights × ≥200 字), G4 (≥3 modules × ≥500 字), G5 (≥5 金句), G7 (≥3 价值 + ≥2 局限 + ≥3 行动). A thin report fails gates regardless of KB. Run `scripts/verify_report.py` to check; if a gate fails, expand that section. |
| "Deep Dive modules are fixed at 3" ★ | Deep Dive modules are **extensible** — user can request additional modules (e.g. "加一个板块着重研究Codex"). Each module needs: concept definition, architectural context, multi-angle analysis, a Mermaid diagram where applicable, and explicit linkage to the user's own stack where relevant. |
| "I'll guess the danmaku file path" ★ | As of **v2.4** `fetch_danmaku_v2.py`/`fetch_all.py` save danmaku to **`/tmp/{BV号}_danmaku.json`** (BV-prefixed, aligned with comments/subtitle artifacts). Pure-CID input falls back to `/tmp/cid_{数字}_danmaku.json`. The RESULT_JSON `path` field is authoritative — read it, don't guess. |
| "Subtitle step failed — I'll just summarize from memory" ★ | As of **v2.4** the fallback chain (official → yt-dlp → whisper.cpp → mlx-whisper) runs **automatically inside** `fetch_subtitle_auto.py`, and `fetch_all.py` no longer masks failure as `null` — a failed step is `{"status":"failed","error":...}`. If subtitle status is `failed`, read the `error` (often bilibili **HTTP 412** → use `yt-dlp --cookies-from-browser chrome`) before summarizing from memory. |

## 🔀 Decision Tree

```
Received Bilibili URL(s)?
├── Multiple URLs (same creator/series)? → 🆕 Offer merged report. Collect all metadata first.
│   └── User confirms merge → Phase 1 for all videos → generate unified report
├── Single URL → Phase 0: Fetch metadata ONLY (no transcription yet)
│   ├── Get: title, author, duration, views, subtitle availability
│   └── ⚠️ STOP HERE. Present metadata to user. Ask: "先看看再说" or "完整版" or "精简版"?
│       ├── "先看看再说" → Wait for user decision. Do NOT transcribe.
│       ├── "完整版" → Phase 1 full: transcription + all sections (see 全量版 below)
│       ├── "精简版" → Phase 1 full: transcription + condensed report (see 精简版 below)
│       └── 🆕 BYPASS: User gave explicit instruction ("帮我整理文档到01", "直接分析",
│           "用bilibili skill 帮我...") → skip confirmation, auto-select mode:
│           <20min → 精简版, ≥30min → 全量版, unknown → 精简版 (safe default)
├── Phase 1: Fetch data (metadata → subtitles → danmaku → comments)
│   ├── Subtitles: yt-dlp → mlx-whisper (fallback chain)
│   ├── Danmaku: ≥30-60 samples
│   └── Comments: top 50 hot comments
├── Phase 2: Analysis (type diagnosis → depth selection → analysis)
│   ├── Type diagnosis: Tutorial / Interview / Review / Narrative / Speech
│   └── Depth: 全量版 vs 精简版 (see below)
├── Phase 3: Generate report (adaptive sections)
│   └── 🆕 Merged report: per-video Meta tables, interleaved analysis, unified Insights/Deep Dive
└── Phase 4: 🚦 verify_report.py depth gate (blocking) → Save to Obsidian 00-Inbox + cleanup temp files
```

### Output Mode Selection

After Phase 0 metadata is shown, user picks one. If they don't specify, default to **presenting metadata first**, not auto-running full analysis.

| Mode | When to use | Sections | Good for |
|:---|:---|:---|:---|
| **全量版** | 深度访谈/演讲 ≥30min, or user explicitly says "完整版" | All 8 sections (0-8) | Interviews, keynotes, research talks |
| **精简版** | 教程/How-to <20min, or user says "精简版" | 0 (Meta) + 3 (Key Insights) + 7 (Action Items) + selected Deep Dive modules | Tutorials, config walkthroughs, quick demos |
| **🆕 合并版** | Multiple related videos (same creator, same series) | 全量版 structure, per-video Meta tables, interleaved analysis | Series, build+Demo pairs, multi-part tutorials |

**精简版 rules**:
- Skip or minimize §2 (Danmaku) and §2.5 (Comments) if data is sparse. One sentence acknowledging scarcity is enough.
- §4 (Deep Dive): reduce to 2-3 modules max, each ≤300 words
- §5 (Highlights): reduce to 2-3 quotes max
- §6 (Knowledge Graph): keep only the core concept table, skip cultural references
- Still include: YAML frontmatter, §0 Meta, §1 Logic Chain (shortened), §3 Key Insights, §7 Critical Review & Action, §8 Appendix
- Quality bar: **Depth Quality Gates 精简版列** (G3 ≥2×150字, G4 2-3模块, G5 2-3, G7 full). Verify with `verify_report.py --mode condensed`. No KB target — size follows content.

**🆕 合并版 rules** (thresholds = Depth Quality Gates 合并版列):
- §0 Meta: per-video tables, then merged summary
- §1 Logic Chain: one flowchart per video (**G1: each ≤100 行**), then a "两篇的逻辑关系" comparison
- §2/2.5: per-video danmaku/comment analysis with data-sparsity guard
- §3 Key Insights: **G3: ≥3 unified insights** spanning both videos (not 3-per-video)
- §4 Deep Dive: **G4: ≥3 modules**, each drawing material from both videos where relevant
- §5 Highlights: **G5: ≥5 金句** pooled across videos
- §7 Critical Review & Action: **G7: ≥3 价值 + ≥2 局限 + ≥3 行动** (unified assessment)
- Verify: `verify_report.py <merged.md>` (full mode) treats the merged file as one report — unified §3/§4/§5/§7 clear full-版 gates directly; keep the combined §1 (all per-video arcs + comparison) within G1's ≤100 行.
- Filename: `B站笔记_[系列主题]_YYYYMMDD.md`

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

> [!note] 弹幕文件路径（v2.4 起 BV 前缀）
> `fetch_all.py`/`fetch_danmaku_v2.py` 现保存到 **`/tmp/{BV号}_danmaku.json`**（BV 前缀，与评论/字幕产物对齐）；纯 CID 输入时回退 `/tmp/cid_{数字}_danmaku.json`。无论哪种，RESULT_JSON 的 `path` 字段都是权威来源——直接读它，别猜路径。

## Phase 2: Deep Analysis

1. **Type diagnosis**: Tutorial / Interview / Review / Narrative / Speech
2. **Danmaku analysis**: 6 emotion categories, high-frequency terms, cultural memes → see `references/danmaku-analysis-guide.md`
3. **Comments analysis**: Hot comment curation, opinion clustering, creator interaction
4. **🆕 Dominant-entity detection**: During type diagnosis, scan for entities (tools/APIs/characters/technologies) referenced in ≥3 sections. If found, auto-propose an additional Deep Dive module for panoramic analysis. Example: Codex appeared in architecture, insights, demo, and critical review of the Niuma videos → triggered "模块 7：Codex 角色全景".
5. **3-layer dissection**: Explicit / Implicit / Meta-narrative
6. **Critical review**: Validity / Blind spots / Audience fit

Full analysis framework: `references/v3-detailed-prompt.md`

## Phase 3: Output (Adaptive — See 全量版/精简版 Mode Selection Above)

### 📏 Depth Quality Gates (深度质量门槛 — 取代 KB 体量目标)

> 报告质量按**结构充实度**衡量，不按文件大小。KB 数是深度的副产物，不是目标——
> 不要为了凑 KB 注水，也不要因为"到了 30KB"就停。用下表门槛自检，或运行
> `python3 scripts/verify_report.py <报告.md>`（`--mode condensed` 校验精简版）。

| Gate | 章节 | 全量版 | 精简版 | 合并版 |
|:---|:---|:---|:---|:---|
| **G1** | §1 逻辑链 | ≤100 行（含 Mermaid） | ≤100 行 | ≤100 行/视频 |
| **G3** | §3 核心洞察 | ≥3 洞察 × 每条 ≥200 字 | ≥2 洞察 × ≥150 字 | ≥3 洞察（跨视频统一） |
| **G4** | §4 Deep Dive | ≥3 模块 × 每个 ≥500 字 | 2–3 模块 × ≤300 字 | ≥3 模块（取材双视频） |
| **G5** | §5 高光时刻 | ≥5 条金句 | 2–3 条 | ≥5 条 |
| **G7** | §7 批判与行动 | ≥3 价值点 + ≥2 局限 + ≥3 行动项 | 同全量版（教程最高价值区，不削减） | ≥3 + ≥2 + ≥3（统一评估） |

> [!tip] 门槛是**下限**不是上限。访谈/演讲常超出 G3/G4，按内容自然展开；`verify_report.py` 只拦截"不足"。

### 全量版 (All 8 Sections)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | 必填：status/type/priority/aliases/tags/created/modified（遵循 Obsidian CLAUDE.md） |
| 0 | Meta | Video title, UP主, play count, CID, duration |
| 1 | Logic Chain | **G1**: Tables (narrative arcs) + Mermaid flowcharts — structural overview, NOT prose retelling. **≤100 lines**. Verbose quotes → Deep Dive. |
| 2 | Danmaku Intelligence | Emotion quantification, meme analysis |
| 2.5 | Comments Analysis | Hot comments curation, opinion clustering |
| 3 | Key Insights | **G3**: ≥3 insights, each ≥200 字 with verbatim support |
| 4 | Deep Dive | **G4**: ≥3 modules (extensible on user request), each ≥500 字, Mermaid diagram per module where applicable |
| 5 | Highlights & Quotes | **G5**: ≥5 金句 (视频金句 + 弹幕金句) with timestamps |
| 6 | Knowledge Graph | Concept map, cross-references, linkage to user's own stack |
| 7 | Critical Review & Action | **G7**: ≥3 价值点 + ≥2 局限/偏见 + ≥3 行动项 |
| 8 | Appendix | Data sources, tools used, full quotes, timestamp index |

**全量版 quality bar: 满足 Depth Quality Gates (G1/G3/G4/G5/G7) above.** 体量是副产物——别盯 KB 数，跑 `verify_report.py` 验门槛。

### 精简版 (Condensed)

| # | Section | Requirement |
|---|---------|------------|
| **YAML** | Frontmatter | Same as 全量版 |
| 0 | Meta | Same as 全量版 |
| 1 | Logic Chain | **G1**: ≤100 lines — same structure as 全量版, just fewer detail rows |
| 2 | Danmaku/Comments | **Minimal**: ≤50 words if sparse. Write "数据不足" and move on — do NOT inflate. |
| 3 | Key Insights | **G3 (relaxed)**: ≥2 insights × ≥150 字 |
| 4 | Deep Dive | **G4 (relaxed)**: 2-3 modules max, each ≤300 字 |
| 5 | Highlights | **G5 (relaxed)**: 2-3 quotes |
| 6 | Knowledge Graph | Core concept table only. Skip cultural/meme analysis. |
| 7 | Critical Review & Action | **G7 (full)**: ≥3 价值点 + ≥2 局限 + ≥3 行动项 — 教程最高价值区，不削减 |
| 8 | Appendix | Sources + version, skip extended reading |

**精简版 quality bar: 满足 Depth Quality Gates 精简版列.** Verify with `verify_report.py --mode condensed`. 体量随内容，不设 KB 目标。

**Timestamp formula**: Bilibili `?t={total_seconds}`. `02:30` → 150 seconds → `?t=150` (NOT `?t=230`!).

Full template: `references/output-template.md`

## Phase 4: Save & Cleanup

**🚦 STEP 0 — Depth gate (blocking, run BEFORE saving):**

```bash
# 先把草稿写到 /tmp，验门通过才落库
python3 scripts/verify_report.py /tmp/报告草稿.md            # 全量版
python3 scripts/verify_report.py /tmp/报告草稿.md --mode condensed   # 精简版
```

- ❌ **Any gate FAIL (exit 1) → do NOT save.** Go back, expand the named section (G3/G4/G5/G7), re-run until ✅ OVERALL PASS (exit 0).
- ✅ Gates green → proceed to save below. This is the same rubric as the §3 Depth Quality Gates — the script just enforces it mechanically so a thin report can't slip through.

**Then save:**

- ✅ Save to: `~/Documents/Obsidian/AlexCai/00-Inbox/B站笔记_[主题简述]_YYYYMMDD.md`
- ⚠️ **Filename convention**: follow the vault's CLAUDE.md — for this vault it's `B站笔记_主题简述_YYYYMMDD.md` (NOT `视频解析_...`). Check the target vault's CLAUDE.md for its actual convention.
- ✅ Must include YAML frontmatter（status/type/priority/aliases/tags/created/modified）
- ✅ Clean temp files: `rm -f /tmp/bili_hermes* /tmp/BV* /tmp/cid_* /tmp/报告草稿.md`
- ❌ Never save to: `~/clawd/00-Inbox/` or vault root

## Script Reference

| Script | Function | Dependency |
|:---|:---|:---|
| `fetch_all.py` ⭐ | One-shot: danmaku + comments + subtitles (dispatches sub-scripts via `/usr/bin/python3`; failures reported, not masked) | yt-dlp, mlx-whisper/whisper-cli |
| `fetch_danmaku_v2.py` | Danmaku (BV号 direct, BV-prefixed output) | requests |
| `fetch_comments.py` | Comments (top 50 hot) | requests |
| `fetch_subtitle_auto.py` | Subtitles (auto-fallback: official→yt-dlp→whisper.cpp→mlx) | yt-dlp, whisper.cpp, mlx-whisper |
| `mlx_transcribe.py` | mlx-whisper Python-API transcription (local snapshot, offline) | mlx-whisper (`/usr/bin/python3`) |
| `verify_report.py` 🆕 | Static Depth-Quality-Gate checker for a report `.md` | stdlib only |
| `transcribe_whisper_cpp.sh` | Audio transcription | whisper-cli, ffmpeg |

> [!note] 解释器要求：弹幕/评论/字幕子脚本需可用的 `requests` + 可用的 `xml/pyexpat`，请用 **`/usr/bin/python3`**（CommandLineTools 3.9 + `~/Library/Python/3.9` user site）运行；本机 homebrew python3.12 的 `pyexpat` 损坏，无法解析弹幕 XML。`fetch_all.py` 已内置该选择。

## Known Limitations

- ⚠️ Official subtitle API requires login (SESSDATA); **preferred path: `yt-dlp --cookies-from-browser chrome`** — single command extracts both official + AI subtitles without API calls (see below)
- ⚠️ Comment API returns max 3-5 hot comments for new videos (<24h)
- ⚠️ whisper.cpp: ~68-85s per 19-minute video (Apple M4 GPU) — only use as last resort when yt-dlp+cookie fails
- ⚠️ Fallback chain: `yt-dlp --cookies-from-browser chrome` → mlx-whisper (preferred on Apple Silicon, ~60s per 7-min video) → whisper.cpp → summarize from context
- ✅ **Fallback chain is automatic (v2.4)** — `fetch_subtitle_auto.py` runs official → yt-dlp(download) → whisper.cpp → mlx-whisper **in-process** and reports the engine that actually succeeded in the `method` field. `fetch_all.py` surfaces failures as `{"status":"failed","returncode":N,"error":...}` (no more silent `null`). When every transcription path fails (commonly bilibili **HTTP 412** on yt-dlp, which needs a login cookie), fall back to the `yt-dlp --cookies-from-browser chrome` method documented below.
- ⚠️ Multi-video merge: when user provides multiple B站 URLs from the same creator/series, offer to merge into a single unified report. Collect all data first, then interleave analysis with per-video Meta tables.
- ⚠️ Tutorial/How-to videos <20min: use **精简版** — full 8-section analysis is overkill
- ⚠️ New videos (<24h, <500 views): expect 0-3 comments and 0-10 danmaku. Don't force analysis on empty data.

### Subtitle Extraction — Verified Method (2026-06-02, double-validated)

When the user has a Bilibili login in Chrome, use `yt-dlp` with browser cookies. This method was verified twice in one session — it works reliably.

**Step 1: Diagnostic — check available subtitles** (always run first):

```bash
yt-dlp --cookies-from-browser chrome --list-subs '<URL>' 2>&1 | tail -10
```

This confirms which subtitle tracks exist (typically: `danmaku xml`, `zh srt`, `ai-zh srt`).

**Step 2: Extract to SRT files** (the reliable path):

```bash
# Allow 90s timeout — Chrome cookie extraction can be slow
yt-dlp --cookies-from-browser chrome \
  --write-subs --sub-lang "zh,ai-zh" \
  --skip-download --convert-subs srt \
  -o '/tmp/bv_hermes' '<URL>'
```

**Step 3: Read the SRT file** with `read_file`:

```bash
read_file /tmp/bv_hermes.ai-zh.srt
```

- `--cookies-from-browser chrome` — reuses user's Bilibili login session
- `--sub-lang "zh,ai-zh"` — requests both official (`zh`) and AI-generated (`ai-zh`) subtitles
- **DO NOT use `--write-auto-subs`** — it silently returns "There are no subtitles" even when `--list-subs` shows `ai-zh`. Use `--write-subs --sub-lang "zh,ai-zh"` instead.
- `--convert-subs srt` — converts to standard SRT format readable by `read_file`
- Output: `/tmp/bv_hermes.zh.srt` (official, ~296 lines) and `/tmp/bv_hermes.ai-zh.srt` (AI CC, ~257 lines for 10-min video, ~1028 lines total with timestamps)
- Timeout: allow **90s** (Chrome cookie extraction can be slow; Bilibili API sometimes delays JSON metadata download)
- Cleanup: `rm -f /tmp/bv_hermes* /tmp/bili_hermes*`

> [!tip] Prefer AI subtitles (`ai-zh`) over official (`zh`) — they're usually more complete and better punctuated. 257 entries for a 10-min video is typical.

**Pitfalls** (2026-06-02 verified across two extraction cycles):

- 🪤 `--write-auto-subs` alone fails with "There are no subtitles for the requested languages" even when `--list-subs` shows `ai-zh`. Use `--write-subs --sub-lang "zh,ai-zh"` instead — it reliably extracts both tracks.
- 🪤 `%(subtitles)j` JSON in `--print after_video` is unreliable — it returned `NA` when SRT files were successfully written to disk. Just use the SRT file path directly.
- 🪤 Browser native `browser_navigate` + JS console extraction is a dead end — Bilibili requires login for subtitle data, and the cookie-based API approach is the only reliable path for subtitle content.

### 🆕 mlx-whisper Transcription (Apple Silicon, Preferred Fallback)

When `yt-dlp` subtitle extraction fails (no `zh` or `ai-zh` tracks available), use mlx-whisper for local transcription. This is ~60s for a 7-minute video on Apple Silicon — faster than whisper.cpp.

**Step 1: Download audio** (run in background, allow 120s):

```bash
yt-dlp --cookies-from-browser chrome \
  -f 'bestaudio[ext=m4a]/bestaudio' \
  --extract-audio --audio-format wav \
  -o '/tmp/bv_audio.wav' '<URL>'
```

**Step 2: Transcribe with mlx-whisper** (run in background, allow 300s):

```python
from mlx_whisper import transcribe
result = transcribe('/tmp/bv_audio.wav',
    path_or_hf_repo='~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/<hash>')
# Write to SRT + plain text
```

**Step 3: Read the transcript:**

```bash
read_file /tmp/bv_transcript.txt
```

- **Always use local cache path** — do NOT pass the HuggingFace repo ID (`mlx-community/whisper-large-v3-turbo-mlx`). The HF API returns 401 even when the model is cached locally. Find the snapshot hash: `ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/`
- Pre-installed: `mlx-whisper` Python package (v0.4.3+). No CLI needed — use Python API directly.
- Model: `whisper-large-v3-turbo` (cached at `~/.cache/huggingface/hub/`)
- Output: 264 segments for 7.5-min Chinese video is typical
- Language detection: set `language="zh"` if auto-detect fails, but auto-detect usually works for Chinese content

> [!warning] 🪤 HF repo ID pitfall
> Using `path_or_hf_repo='mlx-community/whisper-large-v3-turbo-mlx'` triggers a HuggingFace 401 Unauthorized error even when the model is already cached locally. **Always resolve to the local snapshot path** — use `ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/` to find the hash, then pass the full path.

Changelog: `references/changelog.md` — timeout optimization, multi-P video support, BV号 direct access.

## ✅ Verification Checklist

- [ ] Danmaku file read from RESULT_JSON `path` (v2.4: `/tmp/{BV号}_danmaku.json`, BV-prefixed)?
- [ ] Subtitles extracted via `yt-dlp --cookies-from-browser chrome` first (not whisper unless cookie method failed)?
- [ ] Subtitle step: if status `failed`, checked the `error` field (e.g. 412 → cookies) before manual fallback?
- [ ] If yt-dlp subtitles unavailable, mlx-whisper used with local cache path (not HF repo ID)?
- [ ] Output mode selected? (全量版 or 精简版 — user chose explicitly?)
- [ ] 🆕 Multi-video merge: per-video Meta tables + interleaved analysis?
- [ ] YAML frontmatter present? (status/type/priority/aliases/tags/created/modified)
- [ ] Timestamp links use correct `?t={seconds}` formula (NOT `?t=minutes*100+seconds`)?
- [ ] **Depth Quality Gates pass?** Run `python3 scripts/verify_report.py <报告.md>` (全量版) or `--mode condensed` (精简版) — G1/G3/G4/G5/G7 all ✅?
- [ ] 全量版: all 8 sections present, G3 (≥3×200字) + G4 (≥3×500字) + G5 (≥5) + G7 (≥3+2+3) met?
- [ ] 精简版: sections 2/4/5/6 condensed, G7 kept full (≥3+2+3)?
- [ ] Dominant entities scanned? (tools/APIs/characters referenced in ≥3 sections → extra Deep Dive module?)
- [ ] Sparse danmaku/comments handled with ≤50 words, not inflated into full analysis?
- [ ] Output saved to Obsidian `00-Inbox/` (NOT clawd path or vault root)?
- [ ] Temporary files cleaned from `/tmp/`?

---

## Deployment & Sync

After ANY update: `cd ~/code/jz-skills && ./deploy/sync-back.sh && git commit -am "sync: bilibili-video-analyzer" && git push`
