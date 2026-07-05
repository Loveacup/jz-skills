# bilibili-video-analyzer

Bilibili / YouTube video analysis engine for producing Obsidian-ready deep reports with transcript evidence, comments/danmaku context, writer validation, and release quality gates.

## Quality-first pipeline (active roadmap)

After the P0/P1 skeleton guard and DraftReport boundary landed, the strategy pivoted from "fill every section with deterministic extractors" to **"build a section-level content quality gate first, then make every writer pass it."**

Current quality layers:

```text
EvidenceBundle → DraftSection writer → Section QA gate → DraftReport preview → PublishableReport
```

Delivered milestones:

- Phase 1: `evaluate_draft_section_quality()` — see `references/content-engine-section-qa-gate-phase1-20260703.md`.
- Phase 2: `assemble_draft_report_slice()` now auto-attaches `DraftReport.qa_results`; P0 skeleton blockers are kept out of `draft_sections`, while P1/P2 issues stay inspectable with warnings — see `references/content-engine-section-qa-gate-phase2-20260704.md`.
- Phase 3: `report_markdown()` and `run_quality_gate.py --json` now expose JSON-able `section_qa` metadata without rendering it into Markdown or changing pass/fail logic; provider responses are cached to avoid double LLM calls — see `references/content-engine-section-qa-gate-phase3-20260704.md`.
- Phase 4: §1 and §5 have dimension exemptions (not-mechanical + insight-density) so structural table/blockquote sections don't false-flag; `--section-qa-gate` flag enables opt-in P0 blocker gating — see `references/content-engine-section-qa-gate-phase4-20260705.md`.


## Quick release check

Before changing writer/render/fetch/report logic, run the cheap deterministic release gate:

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/release_gate.py
```

Default release gate runs:

1. deterministic fixture quality gate (`run_quality_gate.py --writer-provider fixture --fail-on-fallback-warning`)
2. full pytest suite excluding local ASR config tests (`pytest -q tests --ignore=tests/test_asr_config.py`)

This path does **not** call network services or spend LLM tokens.
It is an **engineering gate**, not a publishability guarantee for Obsidian notes.

## Publishable Obsidian gate

Pipeline artifact boundary:

```text
AnalysisInput → analyze_video() → DraftReport → debug Markdown → publish_markdown() → PublishedMarkdown
```

`render_markdown()` / `render_debug_markdown()` return debug/legacy Markdown strings. They are useful for engineering gates and inspection, but not publishable by themselves.

`DraftReport.draft_sections` is the current seam for written-but-not-yet-publishable section bodies. Today it has deterministic slices for §1 logic-chain tables, §5 short highlights, and §6 knowledge graph extraction via `assemble_draft_report_slice()`. When an explicit provider is passed, the same assembler can also route validated existing §3/§4/§7 LLM writer output into `draft_sections`; it still returns a non-publishable `DraftReport`, not `PublishedMarkdown`.

Use `render_draft_markdown(draft)` for human/CI preview only. It overlays `draft_sections` onto the plan while keeping unfinished sections as skeleton, and emits `publishable: false`; it is not a formal note writer.

Before saving a generated report as a formal `B站笔记_*.md`, run the stricter publish gate:

```bash
PYTHONPATH=scripts python3 scripts/verify_publishable_report.py /path/to/report.md
```

Or opt into it from the quality harness:

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture \
  --fail-on-fallback-warning \
  --publishable
```

Expected behavior:

- historical high-quality human-readable notes should pass;
- skeleton/debug reports fail;
- any generated formal `B站笔记_*.md` output is blocked if this gate fails.

## Real sample smoke

Use real sample smoke only when validating model-backed writer behavior before a release or after writer/prompt changes:

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/release_gate.py \
  --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
  --real-writer-provider cli
```

Real sample mode is opt-in because it may spend time/tokens. It fails if §3/§4/§7 writer output silently falls back to skeleton.

## Core commands

```bash
# Generate a report from fetch_all JSON
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli \
  --output /tmp/BVxxxx_report.md

# Verify report structural depth gates
PYTHONPATH=scripts python3 scripts/verify_report.py /tmp/BVxxxx_report.md

# Deterministic quality gate only
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture \
  --fail-on-fallback-warning
```

## Notes

- Formal Obsidian reports require transcript evidence. If all subtitle/ASR paths fail, output a clearly-labeled pre-analysis only.
- Final Obsidian save should keep one user-facing note per video; do not preserve intermediate drafts/transcripts unless explicitly requested.
- Use `terminal cp` for Obsidian vault saves, then verify with `ls`, `wc -c`, `verify_report.py`, and coherence checks.
