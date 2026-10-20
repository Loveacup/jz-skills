# Publishable report gate lesson (2026-07-03)

## Trigger

A real BV smoke (`BV1zrTq6sEPB`, AI 虚拟偶像 / Yuri 尤栗) produced a Markdown report that passed `verify_report.py`, coherence, and OMP mechanical audit, but the user rejected it as completely unusable. Manual reread confirmed severe content-quality failure: skeleton residue, raw ASR dumps, overlong quotes, ASR noise in prose, and topic drift.

## Durable lesson

Separate **engineering gates** from **publish gates**:

- `verify_report.py`, `check_report_coherence()`, `run_quality_gate.py`, and default `release_gate.py` prove the pipeline is structurally alive.
- They do **not** prove a report is suitable for Obsidian or human reading.
- Formal `B站笔记_*.md` output must pass a publishable/human-readability gate or explicit human QA.

## Failure signature to block

Hard blockers for formal video notes:

- `_骨架占位` / `Skeleton` residue.
- Required §0–§8 missing.
- Any line over 1000 chars (usually raw transcript dump).
- §1 logic chain has no table / Mermaid / timeline structure.
- §5 quote group over 300 chars.
- Core prose sections (§3/§4/§6/§7) are only blockquotes/tables/source appendix.
- `verify_report.py` pass but the note still reads like evidence scaffolding.

## Validation anchors

Use at least one good and one bad anchor when changing report generation:

| Anchor | Expected |
|---|---|
| `/tmp/bili_bad_reports/B站笔记_AI虚拟偶像与Yuri尤栗_20260703_BAD.md` | publish gate fail |
| `30-Resources/60_视频笔记/B站笔记_Niuma语音Agent_20260607.md` | publish gate pass |
| `30-Resources/60_视频笔记/B站笔记_那些因为解决了问题而被停产的产品_20260702.md` | publish gate fail until rewritten |

## Manual execution

`scripts/verify_publishable_report.py` is **not shipped** in this repository. The publish gate is a manual QA step. Use `references/publishable-report-manual-checklist.md` as the concrete checklist, or run the same assertions by hand before saving any formal `B站笔记_*.md` to Obsidian.

## Preferred implementation pattern

```text
AnalysisInput → EvidenceBundle → ReportPlan → DraftReport → QualityResult → PublishedMarkdown
```

`ReportPlan` and `EvidenceMap` are intermediate planning/material artifacts. `_render_plan_skeleton()` must be treated as debug/export-only unless the publish gate confirms the output is human-readable.

## Commands from the session

```bash
PYTHONPATH=scripts python3 scripts/verify_report.py <report.md>

# Publishable gate is manual — see references/publishable-report-manual-checklist.md

PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture \
  --fail-on-fallback-warning \
  --publishable
```
