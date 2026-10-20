# P0/P1 publishable gate — triad record (2026-07-03)

## Context

BV1zrTq6sEPB exposed a severe gap: the pipeline could pass `verify_report.py`, `check_report_coherence()`, and OMP audit while producing a note that was not human-readable enough for Obsidian.

Root cause: P2 turned `ReportPlan`/`EvidenceMap` skeleton output into the default rendered artifact, then only filled §3/§4/§7 with LLM writer output. Mechanical gates checked structure, not publishability.

## Decision

Separate gates:

| Gate | Purpose | Command |
|---|---|---|
| Engineering gate | Pipeline regression: fixture writer + depth gates + coherence + pytest | `PYTHONPATH=scripts python3 scripts/release_gate.py` |
| Publishable gate | Human-readable Obsidian note blocker | `PYTHONPATH=scripts python3 scripts/verify_publishable_report.py <report.md>` |

`release_gate.py` remains cheap/deterministic by default and does **not** imply publishability.

## Implementation

Files:

- `scripts/verify_publishable_report.py`
- `scripts/generate_report.py`
- `scripts/run_quality_gate.py`
- `tests/test_verify_publishable_report.py`
- `tests/test_generate_report_publishable_guard.py`
- `tests/test_run_quality_gate.py`
- `README.md`
- `SKILL.md`

### New publishable gate blockers

- `P0_NO_SKELETON`: reject `_骨架占位` / skeleton/debug placeholders.
- `P0_REQUIRED_SECTIONS`: require §0/§1/§2/§2.5/§3/§4/§5/§6/§7/§8.
- `P0_NO_LONG_LINES`: reject raw transcript dump lines over 1000 chars.
- `P1_LOGIC_CHAIN_STRUCTURED`: §1 must have table, Mermaid, or timeline structure; blockquote-only logic chain fails.
- `P1_SHORT_HIGHLIGHTS`: §5 quote groups must be ≤300 chars.
- `P1_NO_APPENDIX_ONLY_SECTIONS`: core prose sections §3/§4/§6/§7 cannot be only blockquotes/tables/source appendix.

### Formal output guard

`generate_report.py` now treats these as formal publish paths:

- basename starts with `B站笔记_` and ends with `.md`;
- path contains `/30-Resources/60_视频笔记/`.

If publishable gate fails, it exits `1` and refuses to write the file.

Debug/tmp reports with non-formal names are still allowed as engineering artifacts.

### Optional quality harness layer

`run_quality_gate.py --publishable` runs the stricter publishable gate after `verify_report` and coherence.

Default `run_quality_gate.py` and `release_gate.py` remain engineering gates.

## Verification

Evidence file: `/tmp/bili_p01_publishable_gate_evidence.md`

### Targeted tests

```bash
PYTHONPATH=scripts pytest -q \
  tests/test_verify_publishable_report.py \
  tests/test_generate_report_publishable_guard.py \
  tests/test_run_quality_gate.py::test_quality_gate_can_run_publishable_gate_as_stricter_layer
# 9 passed
```

### Release gate

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --json
# release gate RUN PASS
# fixture quality gate PASS
# pytest full suite excluding ASR config: 117 passed, 4 warnings
```

### Real note anchors

| Anchor | Expected | Result |
|---|---|---|
| `/tmp/bili_bad_reports/B站笔记_AI虚拟偶像与Yuri尤栗_20260703_BAD.md` | fail | failed: skeleton + long lines + overlong highlights |
| `30-Resources/60_视频笔记/B站笔记_Niuma语音Agent_20260607.md` | pass | passed all 6 publish gates |
| `30-Resources/60_视频笔记/B站笔记_那些因为解决了问题而被停产的产品_20260702.md` | fail | failed: skeleton + 5013-char line |

### Formal output guard

```bash
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --output /tmp/B站笔记_P0阻断测试_20260703.md \
  --writer-provider none
# exit 1
# written=NO
```

### OMP audit

- task: `omp-20260703-042943`
- verdict: `pass`
- finish: `ACCEPTED`
- evidence: 7

OMP confirmed all 6 acceptance criteria:

1. bad report fails;
2. good historical note passes;
3. P2-D skeleton report fails;
4. formal output guard refuses file write;
5. default release gate remains engineering and passes;
6. tests cover verifier, formal guard, and `--publishable`.

## Next

P0/P1 is a stopgap. It prevents bad notes from entering Obsidian, but it does not create high-quality notes.

Next architectural work:

```text
AnalysisInput → EvidenceBundle → ReportPlan → DraftReport → QualityResult → PublishedMarkdown
```

`_render_plan_skeleton()` should eventually be demoted to debug/export-only, and `DraftReport` should become the only publishable source.
