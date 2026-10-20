# YouTube Single-Video Runbook

Use this when a user provides one YouTube video and expects an evidence-grounded Obsidian note.

## 1. Collect a typed EvidenceBundle

The current top-level `video_analysis_engine.py` is a self-test/demo entrypoint, not a URL ingestion CLI. Invoke the YouTube adapter directly:

```bash
cd ~/.hermes/skills/video-analysis-engine
PYTHONPATH=scripts python3 - <<'PY'
import json
from dataclasses import asdict
from datetime import datetime, timezone
from adapters.youtube import YouTubeAdapter, YtDlpYouTubeProvider
from platform_router import SourceInput, CollectOptions

url = "https://www.youtube.com/watch?v=VIDEO_ID"
out = "/tmp/VIDEO_ID_evidence.json"
adapter = YouTubeAdapter(
    YtDlpYouTubeProvider(),
    lambda: datetime.now(timezone.utc).isoformat(),
)
bundle = adapter.collect(SourceInput(url), CollectOptions(timeout_s=120))
with open(out, "w", encoding="utf-8") as f:
    json.dump(asdict(bundle), f, ensure_ascii=False, indent=2)
print({
    "status": bundle.status,
    "id": bundle.identity.canonical_id,
    "transcript_chars": len(bundle.transcript.text) if bundle.transcript else 0,
    "segments": len(bundle.transcript.segments) if bundle.transcript else 0,
    "errors": [asdict(e) for e in bundle.errors],
})
PY
```

Proceed to formal writing only when `status == "ready"`. Treat metadata-only output as diagnostic.

## 2. Ground changing claims

For videos about an actively maintained repository or product:

- Treat the transcript as evidence of what the speaker said.
- Verify current repository names, files, and behavior against upstream source.
- Inspect the user's local fork/current implementation before writing migration implications.
- Separate confirmed facts, inferences, and gaps. Do not promote video view/star/download counts into current facts without independent verification.

## 3. Write to the current Vault contract

Read the Vault root `AGENTS.md` and `.vault-structure.json` at runtime. For a YouTube event note, use the current naming rule (typically `YouTube笔记_主题_YYYYMMDD.md`) and required frontmatter. Save exactly one user-facing note unless artifacts were requested.

If the subject intersects a local fork, include a clearly labeled impact section but do not modify the fork merely because the video recommends upgrading. Personalized forks require controlled upstream absorption, not destructive clear-and-reinstall migration.

## 4. Gate-compatible report shape

The deterministic gates expect exact numbered sections and some exact subsection markers. A readable condensed report can use:

```markdown
## 0. 视频元数据与证据
## 1. 逻辑链
## 2. 主要变更
## 2.5. 受众反馈与证据边界
## 3. 核心洞察
### 💡 洞察一：...
### 💡 洞察二：...
## 4. 内容深度拆解
### 模块 1：...
### 模块 2：...
## 5. 高光时刻
> quote 1

> quote 2
## 6. 本地影响或知识图谱
## 7. 批判性评价与行动
### 独特价值
- ...
### 局限与盲点
- ...
### 可行动项
1. ... [timestamp/evidence]
## 8. 来源、确认项与链接关系
```

Important parser constraints:

- `verify_report.py` recognizes sections only as `## N.`.
- Insight subsections must contain `💡`.
- Module subsections must match `### 模块 <digit>` or `### Module <digit>`; Chinese numerals such as `模块一` are not recognized.
- `verify_publishable_report.py` requires sections `0, 1, 2, 2.5, 3, 4, 5, 6, 7, 8`.
- In condensed mode, use at least 2 insights, 2 modules, 2 separate blockquote groups, 3 value bullets, 2 limitation bullets, and 3 action items.
- With `--claim-first`, each insight needs claim/evidence/reasoning/boundary language; each module needs explicit/implicit/system/mechanism language; each action needs a timestamp or evidence ID.

Run both gates against the actual final Vault file:

```bash
python3 scripts/verify_report.py /absolute/final-note.md --mode condensed --claim-first
python3 scripts/verify_publishable_report.py /absolute/final-note.md
```

A publishable pass does not compensate for a depth-gate failure, and vice versa.

## 5. Human QA and indexing

After the scripts pass:

- Read the final Markdown itself, especially the middle and tail.
- Check for skeleton residue, transcript dumping, unsupported audience claims, local temp/model paths, and fake or unresolved WikiLinks.
- Verify timestamps point to the canonical YouTube ID.
- Refresh the configured qmd collection (`qmd collection list` first; do not guess the collection name), then run update and embed.
