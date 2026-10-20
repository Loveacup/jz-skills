# P3-A release gate runner — reusable lesson (2026-07-02)

## Trigger

Use this when changing `bilibili-video-analyzer` report generation, writer providers, quality gates, or rendering logic and you need a single pre-release validation command instead of remembering scattered commands from prior sessions.

## Stable command

Default release gate:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py
```

Default behavior is deliberately cheap and deterministic:

1. Runs `scripts/run_quality_gate.py` against `tests/fixtures/p2e_fetch_all.json` with `--writer-provider fixture --fail-on-fallback-warning --json`.
2. Runs `python -m pytest -q tests --ignore=tests/test_asr_config.py`.

Real sample smoke is opt-in because it may call model-backed writers and spend tokens/time:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py \
  --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
  --real-writer-provider cli
```

## Guardrails

- Do **not** make real sample/model calls the default gate.
- Real sample mode must reject `fixture` as a writer provider. It should be `cli` or `deepseek` only.
- Keep `--fail-on-fallback-warning` in both cheap and real-sample quality-gate invocations.
- Release gate should be fail-fast: if the first gate fails, later gates should not run and mask the root failure.
- Keep `--dry-run --json` available so future agents can inspect the exact command plan without spending tokens or running long tests.

## Tests to preserve

`tests/test_release_gate.py` should cover:

1. default command plan = fixture quality gate → pytest;
2. real sample command is opt-in and model-backed;
3. API-level guard rejects `fixture` for real sample smoke;
4. dry-run does not execute commands;
5. fail-fast stops after the first failing gate;
6. CLI dry-run emits JSON.

## Known verification anchor

Final validated state from the implementation session:

```text
PYTHONPATH=scripts pytest -q tests/test_release_gate.py tests/test_run_quality_gate.py
→ 10 passed

PYTHONPATH=scripts python3 scripts/release_gate.py --json
→ release gate RUN PASS
→ fixture quality gate PASS
→ pytest: 108 passed, 4 warnings

OMP: omp-20260702-220907, severity=pass, accepted
```

The 4 warnings were non-blocking: one local urllib3/LibreSSL warning and three intentional writer fallback warnings from negative tests.

## Why this matters

P2-D/E/F created the gates; P3-A turns them into a habit. Future sessions should run one boring command before claiming a report-engine change is safe, instead of reconstructing the validation sequence from chat history.
