# Publishable quality gate + DraftReport lesson (2026-07-03)

## Trigger

A real Bilibili sample (`BV1zrTq6sEPB`) passed the mechanical pipeline:

- `fetch_all` succeeded
- H200 ASR succeeded
- `writer-provider=cli` completed
- `fallback_warning_count=0`
- `verify_report.py` passed
- `check_report_coherence()` passed
- OMP audit accepted the mechanical evidence

But the note was human-quality garbage when opened in Obsidian. The user correctly rejected it. The draft was removed from `00-Inbox` and preserved as a bad-report artifact under `/tmp/bili_bad_reports/` during that session.

## Root cause

The problem was architectural, not merely prompt quality.

Current pipeline had collapsed these different artifacts into one path:

```text
ReportPlan / EvidenceMap / skeleton
→ partial LLM fill
→ Markdown render
→ verify_report/coherence PASS
→ treated as publishable B站笔记
```

The stable historical workflow was different:

```text
transcript/materials
→ human/agent reads output-template + v3-detailed-prompt
→ logical reconstruction + writing
→ human-readable Obsidian note
→ verification
```

The key regression point was around `301ee6b feat(bilibili): render report plan skeleton`: `render_markdown()` began preferring `report_plan.sections` and `_render_plan_skeleton()` over the older `report['sections']` render path. P2-D later added LLM writers only for §3/§4/§7, leaving §0/§1/§2/§2.5/§5/§6/§8 as evidence dumps or placeholders.

## Symptoms that must block publishing

A report is **not publishable** if any required section contains:

- `_骨架占位` or `Skeleton`
- raw transcript blockquotes masquerading as logic chain
- any line longer than roughly 1000 chars
- §5 quote blocks longer than roughly 300 chars
- required sections that contain only `_目的` + evidence blockquotes
- §1 without a real table/Mermaid/timeline-like logic chain
- §5 without short, selected, quote-accurate highlights
- metadata/count mismatches, e.g. hot-comment count used as total comment count
- `[E#]` references that are machine-useful but not reader-explainable
- fallback warnings in a formal report path

## Architecture correction

Do **not** keep patching `_render_plan_skeleton()` as if it were the product.

Introduce/restore a publication boundary:

```text
AnalysisInput
→ EvidenceBundle
→ ReportPlan
→ DraftReport
→ QualityResult
→ PublishedMarkdown
```

Recommended interfaces:

```python
DraftSection:
    id: str
    title: str
    status: written | degraded | blocked | placeholder
    body: str
    evidence_used: list
    warnings: list

DraftReport:
    frontmatter: dict
    sections: list[DraftSection]
    source_appendix: dict
    mode: full | condensed | preanalysis | debug
    publishable: bool
```

Rules:

- `ReportPlan` decides structure and evidence budget only.
- `EvidenceMap`/`EvidenceBundle` is material, not prose.
- `render_markdown()` should only render already-written section bodies.
- `_render_plan_skeleton()` is a debug artifact, not a formal report path.
- Formal report fallback should return `blocked/degraded`, not silently publish skeleton.

## External references absorbed

### BiliNote

Useful mechanisms:

- subtitle/cache-first pipeline
- task status and cache files (`audio`, `transcript`, `markdown`, `status`)
- request chunking by message budget
- post-processing for links/screenshots
- model/style knobs as generation parameters, not final quality proof

### BiliSum

Useful mechanism:

- Markdown export combines pre-existing structured fields (`overview`, `key_points`, `timeline`, `knowledge_note`, optional `transcript`) instead of generating content in the export layer.

### bilibili-obsidian-notes

Useful warning:

- It explicitly says the tool creates “笔记骨架 + 关键帧”, then a later “讲义式整理/refine” step turns it into a study note. This maps exactly to the distinction between debug skeleton and publishable note.

### Academic patterns

- KCVR: Plan-then-Generate; planning must be video/evidence-supported, not prompt-only structure injection.
- RankCut: long transcript summarization benefits from multi-stage pipeline: high-recall coverage → explicit selection rule/object → windowed extractive ranking.
- ARC-Chapter: long videos need chaptering, hierarchical summaries, and timestamp alignment.

## Recommended staged fix

1. **P0 stop publishing skeleton**
   - Treat `verify_report/coherence/OMP pass` as engineering evidence only.
   - Add `verify_publishable_report` before any Obsidian save.
   - Bad samples with skeleton/raw transcript dumps must fail.

2. **P1 separate debug and publish paths**
   - Keep skeleton output as `debug_report_plan.md` / evidence preview only.
   - Formal `B站笔记_*.md` requires `DraftReport.publishable=True`.

3. **P2 add DraftReport interface**
   - Every required `SectionSpec` must map to a `DraftSection` with status.
   - Formal output forbids `placeholder` status.

4. **P3 improve EvidenceBundle**
   - Split transcript into sentence/paragraph/chapter-level candidates.
   - Do not feed 5-minute ASR chunks as quote candidates.
   - Add comment/danmaku clusters and metadata source appendix.

5. **P4 writer coverage**
   - Deterministic writers: §0, §2/§2.5 sparse social summaries, §8 appendix.
   - LLM or hybrid writers: §1 logic chain, §3 insights, §4 deep dive, §6 knowledge graph, §7 critique/actions.
   - Extractive-rank writer: §5 highlights.

## Operational rule

Before saving any Bilibili analyzer output into Obsidian as `B站笔记_...`, do a human-readable QA pass or a strict publish gate. Mechanical gates alone are not enough.