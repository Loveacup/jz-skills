# P2-F real-sample fallback guard — triad record (2026-07-02)

## Decision

P2-F extends the P2-E quality gate instead of adding a second script.

The same entry point now supports two modes:

```bash
# CI / cheap structural regression — deterministic, no network, no LLM
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture

# Real sample smoke — model-backed writer, fail if writer silently falls back
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input /tmp/BV1B9T36nEvL_fetch_all.json \
  --writer-provider cli \
  --fail-on-fallback-warning
```

The key new contract: a real sample run may pass `verify_report` structurally while still being unacceptable if §3/§4/§7 fell back to skeleton. `--fail-on-fallback-warning` makes that visible and machine-failable.

## Implementation

Changed files:

```text
scripts/run_quality_gate.py
tests/test_run_quality_gate.py
```

`run_quality_gate.py` now:

- captures Python warnings emitted during `generate_report.report_markdown()`;
- extracts fallback warnings containing `falling back to skeleton` / LLM fallback language;
- adds summary fields:
  - `warnings`
  - `fallback_warnings`
  - `fallback_warning_count`
  - `fail_on_fallback_warning`
  - `failed_due_to_fallback_warning`
- adds CLI flag:
  ```text
  --fail-on-fallback-warning
  ```
- prints fallback-warning count in the human-readable CLI output;
- returns exit 1 when gates/coherence pass but fallback warnings are present and the flag is enabled.

## Tests

`tests/test_run_quality_gate.py` now covers:

1. fixture provider path has `fallback_warning_count == 0`;
2. CLI path works with `--fail-on-fallback-warning` and emits JSON fields;
3. bad writer provider causes fallback warnings and fails when the flag is enabled.

## Verification

Commands run:

```bash
PYTHONPATH=scripts pytest -q tests/test_run_quality_gate.py
# 4 passed

PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --output /tmp/p2f_quality_gate_report.md \
  --writer-provider fixture \
  --fail-on-fallback-warning \
  --json
# exit 0; quality gate PASS; fallback warn: 0

PYTHONPATH=scripts pytest -q \
  tests/test_run_quality_gate.py \
  tests/test_generate_report_writer_provider.py \
  tests/test_report_coherence.py
# 15 passed

PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
# 102 passed, 3 warnings
```

## Key lesson

`verify_report` validates the rendered Markdown structure, not the reason why that structure exists. For real-sample validation, fallback warnings are part of the quality contract: a skeleton fallback is a regression even if some deterministic sections still let the report render.
