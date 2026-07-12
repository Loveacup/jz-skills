# P3-A release gate runner — triad record (2026-07-02)

## Decision

P3-A adds one stable pre-release validation entry point instead of spreading commands across chat history and references.

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py
```

Default mode is intentionally cheap and deterministic:

1. `scripts/run_quality_gate.py` with fixture provider and `--fail-on-fallback-warning`.
2. `pytest -q tests --ignore=tests/test_asr_config.py`.

Real sample smoke is opt-in because it may call model-backed writers and spend time/tokens:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py \
  --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
  --real-writer-provider cli
```

## Implementation

Added:

```text
scripts/release_gate.py
tests/test_release_gate.py
```

`release_gate.py` provides:

- `build_commands(...)` — builds the ordered release-gate command plan.
- `run_release_gate(commands, dry_run=False)` — executes commands fail-fast.
- `--dry-run` — prints the plan without executing.
- `--json` — emits a machine-readable `RESULT_JSON` block.
- `--real-sample` — appends model-backed real sample quality gate.
- `--skip-pytest` — debugging escape hatch only; not for release use.

Real sample mode deliberately does **not** allow `fixture` as the real writer provider; choices are `cli|deepseek`.

## Tests

`tests/test_release_gate.py` covers:

1. default command plan = fixture quality gate → pytest;
2. real sample command is opt-in and model-backed;
3. API-level guard rejects `fixture` for real sample smoke;
4. dry-run does not execute commands;
5. fail-fast stops after the first failing gate;
6. CLI dry-run emits JSON.

## Verification

Commands run:

```bash
PYTHONPATH=scripts pytest -q tests/test_release_gate.py
# 6 passed

PYTHONPATH=scripts python3 scripts/release_gate.py --json
# release gate RUN PASS
# fixture quality gate: exit 0, verify_report true, coherence true, fallback warn 0
# pytest: 108 passed, 4 warnings
```

The 4 warnings are expected/non-blocking:

- one urllib3 LibreSSL warning from the local Python runtime;
- three intentional writer fallback warnings from `test_writer_integration.py`.

## Key lesson

P2-D/E/F created the gates; P3-A turns them into a reusable release habit. The goal is not more validation complexity, but one boring command that prevents future agents from forgetting the correct minimum gate set.
