# Content Engine Upgrade Principles (2026-06-30)

## Why this exists

The `bilibili-video-analyzer` project must not become a pile of fetchers. Alex explicitly corrected the direction: the analysis and content-generation engine is the core asset; scraping is only the data supply layer.

The old content/report framework was distilled by Alex through prior use. Treat it as product IP, not scaffolding.

## Non-negotiable principles

1. **Preserve the old content engine as baseline**
   - Keep the full/condensed/merged report modes.
   - Keep §0–§8 structure unless there is an explicit replacement with equal or better coverage.
   - Keep Depth Quality Gates and `verify_report.py` as baseline quality controls.

2. **GitHub projects are additive references, not replacements**
   - BiliNote / jz-skills can contribute architecture ideas: Downloader/Transcriber/GPT/NoteGenerator separation, chunking, checkpointing, and recovery.
   - Do not replace Alex's report framework with a generic NoteGenerator template.

3. **Separate fetch from analysis**
   - Fetch scripts should produce standardized inputs: metadata, transcript, danmaku, comments, cross-platform sources, fact-check sources.
   - Analysis, report planning, evidence organization, rendering, and gates belong in `video_analysis_engine.py` and report/verification modules.

4. **Upgrade target**
   - Move from "we fetched the data" to "we produced a high-quality Obsidian knowledge asset".
   - Upgrade around `ReportPlan`, `SectionSpec`, `EvidenceMap`, and `QualityGateResult` concepts.

5. **Quality Gates should move earlier**
   - `verify_report.py` remains the blocking post-generation gate.
   - Future engine work should also use gates during planning/generation so thin sections are prevented, not merely rejected after writing.

## Phase-4/P2 checklist

- [ ] Inventory old assets: `v3-detailed-prompt.md`, `output-template.md`, `verify_report.py`, full/condensed/merged section schemas.
- [ ] Map each old section to the new engine schema.
- [ ] Add chunk/checkpoint support for long videos without losing global synthesis.
- [ ] Preserve evidence traceability: transcript, danmaku, comments, WRR sources.
- [ ] Add source/claim maps for technical, policy, and cross-platform videos.
- [ ] Validate with at least two real videos using the same fetched data before/after engine upgrade.

## Pitfall

If an implementation task spends most of its effort on fetchers, stop and re-scope. Fetching is necessary, but the next major product-quality gains should come from the content engine.
