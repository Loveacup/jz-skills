# P2-E quality gate harness (2026-07-02)

## Context

P2-D real-video validation showed that passing `check_report_coherence()` alone is insufficient: a report can still fail `verify_report.py` because legacy gates require exact §3/§4/§7 heading formats and §5 quote counts/noise filtering.

P2-E adds a cheap deterministic regression gate for future writer/render changes.

## Pattern

Add/run a no-token quality gate harness:

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --output /tmp/p2e_quality_gate_report.md \
  --writer-provider fixture \
  --json
```

Pipeline:

```text
fetch_all JSON fixture
→ generate_report.report_markdown()
→ render_markdown(provider=fixture)
→ verify_report.evaluate(mode=full)
→ check_report_coherence()
```

## Fixture provider rule

`fixture_writer_provider` is deterministic and must not call network or LLMs. It is **not** a content-quality substitute. It only catches regressions in:

- writer-provider routing;
- exact verifier-compatible §3/§4/§7 structure;
- §5 blockquote generation;
- coherence gate integration.

Real sample checks still use:

```bash
--writer-provider cli
--writer-provider deepseek
```

## Test shape

`tests/test_run_quality_gate.py` should cover:

1. Python API path: fixture provider produces a report that passes full gates + coherence.
2. CLI path: `run_quality_gate.py --json` exits 0 and emits machine-readable status.
3. Negative path: `writer_provider='none'` fails full gates, proving skeleton/fallback output is caught.

## Verification commands from session

```bash
PYTHONPATH=scripts pytest -q tests/test_run_quality_gate.py
# 3 passed

PYTHONPATH=scripts pytest -q tests/test_run_quality_gate.py tests/test_generate_report_writer_provider.py tests/test_report_coherence.py
# 14 passed

PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
# 101 passed, 3 warnings
```

OMP audit accepted:

```text
task_id: omp-20260702-185440
severity: pass
evidence: 13
```
