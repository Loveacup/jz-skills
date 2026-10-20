# P2-E quality gate harness — triad record (2026-07-02)

## Decision

P2-E turns the real-sample lessons from P2-D into a deterministic regression gate:

```text
fetch_all JSON fixture
→ generate_report.report_markdown()
→ render_markdown(provider=fixture)
→ verify_report.evaluate(mode=full)
→ check_report_coherence()
```

The default path must be safe for CI / local regression: no network calls, no ASR, no LLM token usage.
Real model-backed sample checks remain available through `--writer-provider cli|deepseek`.

## Implementation

Changed / added files:

```text
scripts/run_quality_gate.py
tests/test_run_quality_gate.py
tests/fixtures/p2e_fetch_all.json
tests/fixtures/p2e_subtitle.json
tests/fixtures/p2e_subtitle.txt
```

`run_quality_gate.py` provides:

- `fixture_writer_provider(system, user)` — deterministic writer provider for §3/§4/§7.
- `run_quality_gate(input_path, output_path, writer_provider='fixture', mode='full')`.
- CLI:
  ```bash
  PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
    --input tests/fixtures/p2e_fetch_all.json \
    --output /tmp/p2e_quality_gate_report.md \
    --writer-provider fixture \
    --json
  ```

The fixture provider is intentionally **not** a content-quality substitute. It exists to catch regressions in:

- prompt routing / writer-provider wiring;
- exact §3/§4/§7 heading formats required by `verify_report.py`;
- §5 blockquote group generation;
- final report coherence checks.

## Tests

`tests/test_run_quality_gate.py` covers:

1. Python API path: fixture provider runs the full pipeline and passes all gates.
2. CLI path: `scripts/run_quality_gate.py --json` exits 0 and emits machine-readable status.
3. Negative path: `writer_provider='none'` fails full gates, proving the harness catches skeleton/fallback output.

## Verification

Runtime evidence bundle:

```text
/tmp/bili-p2e-quality-gate-omp-evidence.md
```

Commands run:

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --output /tmp/p2e_quality_gate_report.md \
  --writer-provider fixture \
  --json
# exit 0; quality gate PASS; G1/G3/G4/G5/G7 PASS; coherence true

PYTHONPATH=scripts pytest -q \
  tests/test_run_quality_gate.py \
  tests/test_generate_report_writer_provider.py \
  tests/test_report_coherence.py
# 14 passed

PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
# 101 passed, 3 warnings
```

## OMP audit

Final accepted audit:

```text
task_id: omp-20260702-185440
severity: pass
evidence: 13
```

OMP verified that:

- the default fixture provider does not use network/LLM tokens;
- `cli` and `deepseek` entry points remain available for real sample smoke;
- API / CLI / failure paths are covered by tests;
- runtime evidence shows quality gate CLI exit 0, targeted pytest 14/14, and full pytest 101 passed.

## Key lesson

P2-D's real video sample found issues that unit-level writer tests missed. P2-E locks those lessons into a cheap regression gate: every future writer/render change can run one command and know whether the report still satisfies the structural contract.
