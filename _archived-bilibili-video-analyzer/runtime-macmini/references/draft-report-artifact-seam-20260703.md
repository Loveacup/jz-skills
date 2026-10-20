# DraftReport artifact seam and publish boundary (2026-07-03)

## Why this exists

A real regression showed that engineering gates can pass while a video note is still unreadable: skeleton residue, long ASR transcript dumps, evidence scaffolding, and overlong quote blocks can slip through `verify_report.py`, coherence checks, and even an external audit if the artifact boundary is wrong.

The durable lesson is architectural: do not promote `ReportPlan` / `EvidenceMap` / debug skeleton Markdown directly into a formal Obsidian note.

## Artifact chain

Use this mental model for the Bilibili content engine:

```text
AnalysisInput
→ EvidenceBundle / EvidenceMap
→ ReportPlan
→ DraftReport                 # non-publishable artifact
→ draft_sections              # written-but-not-publishable section bodies
→ QualityResult / publish gate
→ PublishedMarkdown           # only after publish gate passes
```

Current concrete seams:

- `DraftReport.publishable == False`
- `PublishedMarkdown` is only created by `publish_markdown(markdown)` after `verify_publishable_report.evaluate()` passes.
- `render_markdown()` / `render_debug_markdown()` are legacy/debug string renderers; their output is not publishable by itself.
- `generate_report.py` must block formal paths such as `B站笔记_*.md` and `30-Resources/60_视频笔记/` when publish gate fails.

## Current DraftReport writer slices

`DraftReport.draft_sections` is the seam for written-but-not-yet-publishable sections.

Implemented slices:

| Section | Current writer | Notes |
|---|---|---|
| §1 Logic Chain | `write_logic_chain_section()` | deterministic table; not raw blockquote dump |
| §3 Key Insights | existing `write_llm_section()` via explicit provider | provider defaults to `None`; no default network call |
| §4 Deep Dive | existing `write_llm_section()` via explicit provider | validation failure downgrades to placeholder + warning |
| §5 Highlights | `write_highlights_section()` | deterministic short quote blocks; long ASR chunks are truncated/split |
| §7 Critical/Action | existing `write_llm_section()` via explicit provider | validation failure downgrades to placeholder + warning |

Still missing:

- §0 deterministic meta body in `draft_sections`
- §2 / §2.5 social signal clustering
- §6 deterministic knowledge graph extractor
- §8 deterministic source appendix body in `draft_sections`
- `render_draft_markdown(draft)` non-publishable preview composer

## Safe implementation pattern

1. **TDD first**: write RED tests against the desired seam, not against incidental implementation.
2. Keep each slice narrow:
   - deterministic writers for sections that can be derived from local evidence;
   - explicit `provider` only for LLM-backed sections;
   - never default to network/LLM calls.
3. Do not change `render_markdown()` / `render_debug_markdown()` casually. They are legacy/debug compatibility paths.
4. Do not return `PublishedMarkdown` from writer/assembler code. Only `publish_markdown()` can create it.
5. If writer validation fails, write a placeholder and append `draft.warnings`; do not silently promote broken output.
6. Before formal Obsidian save, run publishable/human-readable QA, not just engineering gates.

## Verification commands used for this class of slice

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_draft_report_slice.py
PYTHONPATH=scripts pytest -q tests/test_draft_report_llm_slice.py
PYTHONPATH=scripts pytest -q tests/test_draft_report_boundary.py tests/test_writer_harness.py tests/test_writer_integration.py
PYTHONPATH=scripts python3 scripts/release_gate.py --json
```

Expected current release gate shape after the 2026-07-03 slices:

- fixture quality gate PASS
- full pytest excluding ASR config PASS
- warnings from expected writer fallback tests are acceptable

## Documentation discipline

For this project, code slices must update three durable surfaces before moving on:

1. `references/<slice>.md` in the skill/repo for session-specific evidence and boundary notes;
2. `SKILL.md` / README pointer so future agents find the reference;
3. Obsidian project control docs + qmd refresh when the work changes project status.

If a code slice is pushed before docs are updated, fix the documentation debt before starting the next slice.