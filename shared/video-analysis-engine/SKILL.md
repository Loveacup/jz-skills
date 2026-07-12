---
name: video-analysis-engine
description: >
  Analyze one Bilibili, YouTube, or Douyin video into an evidence-grounded Markdown knowledge asset.
  Use when the user provides a single video/share link or asks 视频分析、视频总结、B站解析、YouTube分析、抖音视频解析、弹幕或评论分析.
  Routes platform acquisition through typed adapters, requires transcript evidence for formal publication, and runs shared writer/quality gates.
  DO NOT use for batch crawling, creator-page harvesting, feed monitoring, video editing, downloading without analysis, or transcript-only requests.
version: 4.1.0
author: Hermes Agent
license: MIT
---

# Video Analysis Engine v4

Turn one supported video into one readable, evidence-grounded knowledge asset. Platform acquisition varies; analysis, Writer and release quality do not.

## 🚨 Red Flags

| Temptation | Why it is wrong |
|---|---|
| “Metadata is enough to write the report” | Only `ready` evidence may enter the formal Writer. `metadata_only` is diagnostic, not publishable. |
| “The extractor returned comments, so they are facts” | Comments/danmaku are audience signals, never factual evidence without independent support. |
| “The quality scripts passed, so prose is good” | Engineering gates do not replace human readability review. Check skeleton residue, repetition, transcript dumps and unsupported claims. |
| “A short Douyin video deserves a weaker bar” | Short duration changes depth, not evidence integrity or prose quality. Do not pad. |
| “One URL worked, so batch is harmless” | Batch/creator-page/feed crawling is explicitly out of scope. |
| “Keep the old Bilibili scripts as a second implementation” | `bilibili-video-analyzer` is forwarding-only. The canonical implementation lives here. |

## Decision Tree

```text
Input contains exactly one supported video?
├─ No match → stop: unsupported source
├─ Multiple platforms/URLs → stop: ambiguous; ask for one video
└─ One platform
   ├─ Bilibili → BilibiliAdapter / legacy collector migration path
   ├─ YouTube → YouTubeAdapter + metadata/transcript provider
   └─ Douyin → DouyinAdapter + yt-dlp metadata + optional H200 media ASR

EvidenceBundle.status?
├─ ready → shared analysis → Writer → quality gates → human QA → one final note
├─ metadata_only → show metadata/diagnosis only; do not publish formal report
├─ auth_required → request authorized access; do not expose credentials
└─ unavailable → report safe reason; do not invent evidence
```

## Core Contract

External consumers receive versioned `EvidenceBundle` only. Platform-private responses, cookies, headers, signed media URLs and raw API bodies must not cross the adapter seam.

Required states:

- `ready`: stable identity + metadata + transcript + provenance hash; formal Writer allowed.
- `metadata_only`: metadata exists, transcript/media evidence does not; Writer blocked.
- `auth_required`: authorized session is required; Writer blocked.
- `unavailable`: source cannot be resolved safely; Writer blocked.

Only `ready` is publishable. Validate with `scripts/evidence_contract.py`; never bypass `is_publishable()`.

## Workflow

1. **Resolve one source**
   - Accept one Bilibili BV/full/short link, one YouTube watch/short/youtu.be link, or one Douyin share/direct link.
   - Reject zero or multiple platform matches.
2. **Collect typed evidence**
   - Bilibili: official subtitle → PlayURL audio → H200 ASR → local fallback; comments/danmaku remain audience signals.
   - YouTube: yt-dlp metadata plus transcript provider; comments are typed audience signals.
   - Douyin: controlled yt-dlp metadata; optional single-video media download → H200 ASR; no private signer code.
3. **Validate bundle**
   - Require schema compatibility, stable identity, provenance, safe errors and no private payload leakage.
   - Formal analysis stops unless status is `ready`.
4. **Analyze through the shared engine**
   - Preserve the existing claim/evidence/warrant/boundary framework.
   - Use official/first-party sources to verify external product, API, paper, policy and numeric claims.
5. **Write adaptively**
   - Prefer insight density over fixed length.
   - Short/tutorial content: condensed depth; interviews/keynotes: full depth.
   - Never dump long transcript blocks or inflate sparse social data.
6. **Run release gates**
   - Run report structure, claim/evidence, publishable and corpus gates.
   - The Pi accepted-gold sample remains blocking regression evidence.
7. **Human QA and save**
   - Read the actual final Markdown.
   - Save exactly one user-facing note unless source artifacts were explicitly requested.

## Configuration

Canonical ASR variables:

```text
VIDEO_ANALYSIS_ASR_ENDPOINT
VIDEO_ANALYSIS_ASR_LANGUAGE=zh|en|auto
VIDEO_ANALYSIS_ASR_PROVIDER=auto|h200_asr|whisper_cpp|mlx_whisper
VIDEO_ANALYSIS_ASR_MODEL
VIDEO_ANALYSIS_ASR_MODEL_PATH
```

`BILI_ASR_*` variables are temporary deprecated aliases. Do not expose endpoint values, credentials or local model paths in published reports.

## Developer Verification

From this skill directory:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3.12 -m pytest -q -p no:cacheprovider tests
python3.12 -m py_compile scripts/evidence_contract.py scripts/platform_router.py scripts/adapters/*.py scripts/providers/*.py
python3 scripts/run_quality_gate.py --corpus-manifest references/p6r-corpus-manifest.json --lane blocking --json
```

Detailed legacy collector, Writer, gate and historical design records live under `references/`. Historical references may retain the old skill name as provenance; active commands and mappings must use `video-analysis-engine`.

## Scope Boundaries

- One input video per run.
- No creator-page, profile, playlist, feed or batch crawling.
- No Feishu export in v4 initial release.
- No copied/private `a_bogus` implementation.
- No formal report without transcript evidence.
- No second core implementation under the old skill name.

## ✅ Verification Checklist

- [ ] Exactly one supported source and one canonical identity?
- [ ] `EvidenceBundle` validates and status is `ready` before Writer?
- [ ] Private payloads, credentials and signed URLs excluded?
- [ ] Claims trace to transcript or verified first-party sources?
- [ ] Structure/publishable/blocking-corpus gates passed with real command output?
- [ ] Final Markdown manually checked for readability, skeleton residue and transcript dumping?
- [ ] Exactly one user-facing note saved, with no unauthorized batch/export side effects?
