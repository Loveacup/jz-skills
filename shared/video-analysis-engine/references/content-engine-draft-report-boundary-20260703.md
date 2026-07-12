# DraftReport / PublishedMarkdown boundary — triad record (2026-07-03)

## Context

After P0/P1, the system can block bad notes from being written as formal `B站笔记_*.md`, but the internal rendering path still blurred three artifacts:

```text
ReportPlan / EvidenceMap skeleton
→ debug Markdown
→ publishable Obsidian note
```

The next slice deliberately does **not** implement a full §0–§8 writer. It only makes the artifact boundary explicit.

## Contract

| Artifact | Meaning | Publishable? |
|---|---|---|
| `DraftReport` | Structured draft wrapper around `analyze_video()` output; may contain skeleton/debug evidence | No |
| debug Markdown | Legacy/rendered skeleton view for engineering inspection and tests | No, unless promoted |
| `PublishedMarkdown` | Markdown that has passed `verify_publishable_report.evaluate()` | Yes |

## Implementation

Files changed:

- `scripts/video_analysis_engine.py`
- `scripts/generate_report.py`
- `tests/test_draft_report_boundary.py`
- `tests/test_generate_report_writer_provider.py`

### New symbols

- `DraftReport`
- `PublishedMarkdown`
- `PublishableReportError`
- `build_draft_report(report)`
- `render_debug_markdown(draft_or_report, provider=None)`
- `publish_markdown(markdown)`

### Behavior

`render_markdown(report, provider=None)` remains a legacy/debug string alias for backwards compatibility. It does **not** imply publishability.

`generate_report.report_markdown()` now explicitly runs:

```text
results → AnalysisInput → analyze_video() → build_draft_report() → render_debug_markdown()
```

Formal output paths are still protected by the P0/P1 publish gate:

- `B站笔记_*.md`
- `/30-Resources/60_视频笔记/`

## Verification

### RED

`tests/test_draft_report_boundary.py` initially failed because `DraftReport` did not exist:

```text
ImportError: cannot import name 'DraftReport' from 'video_analysis_engine'
```

### GREEN targeted

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_draft_report_boundary.py \
  tests/test_render_markdown_plan.py \
  tests/test_generate_report_writer_provider.py \
  tests/test_generate_report_publishable_guard.py \
  tests/test_run_quality_gate.py::test_quality_gate_can_run_publishable_gate_as_stricter_layer
# 20 passed
```

### Behavior anchors

| Anchor | Result |
|---|---|
| debug non-formal output | `exit=0`, `written=YES` |
| formal `B站笔记_DraftBoundary_20260703.md` skeleton output | `exit=1`, `written=NO`, `P0_NO_SKELETON` |
| bad report `/tmp/bili_bad_reports/...BAD.md` | publish gate fail |
| historical good report `B站笔记_Niuma语音Agent_20260607.md` | publish gate pass |

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# RUN PASS
# fixture quality gate PASS
# pytest full suite excluding ASR config: 121 passed, 4 warnings
```

### OMP audit

First OMP attempt failed due invalid output format and was rejected:

- `omp-20260703-101623`: rejected; no valid audit JSON.

Second OMP attempt passed and was accepted:

- `omp-20260703-102054`
- severity: `pass`
- evidence: 21
- accepted

OMP confirmed:

1. `DraftReport` is explicitly non-publishable;
2. `PublishedMarkdown` only comes from publish gate success;
3. `generate_report` uses `build_draft_report → render_debug_markdown`;
4. formal output refuses skeleton debug Markdown;
5. release gate still passes;
6. the slice does not claim a complete §0–§8 writer.

## Boundary

This is an architecture boundary slice only.

It prevents future code from pretending that skeleton/debug output is a publish artifact, but it still does not write high-quality final notes. The next implementation should introduce a real `DraftReport` writer/assembler that fills sections beyond §3/§4/§7 and promotes only via `publish_markdown()`.
