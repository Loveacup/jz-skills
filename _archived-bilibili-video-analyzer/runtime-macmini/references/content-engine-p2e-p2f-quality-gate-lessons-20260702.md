# P2-E/P2-F Quality Gate Lessons (2026-07-02)

## Why this matters

P2-D real-sample work showed that unit tests and a successful Markdown render are not enough. A report can render, and `check_report_coherence()` can pass, while `verify_report.py` still fails because §3/§4/§7 formatting or §5 quote quality drifted. Later, a model-backed writer can also fail validation and silently fall back to skeleton output unless warnings are treated as a quality signal.

## Durable pattern

Use one quality-gate entry point with two modes:

```bash
# Cheap deterministic regression: no network, no ASR, no LLM tokens.
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture

# Real sample smoke: model-backed writer, fail if writer falls back to skeleton.
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input /tmp/BV1B9T36nEvL_fetch_all.json \
  --writer-provider cli \
  --fail-on-fallback-warning
```

The fixture provider is **not** a content-quality substitute. It exists to exercise the same pipeline and catch structural regressions cheaply:

```text
fetch_all JSON
→ generate_report.report_markdown()
→ render_markdown(provider=fixture)
→ verify_report.evaluate(mode=full)
→ check_report_coherence()
```

## P2-E implementation lesson

`run_quality_gate.py` should default to deterministic fixture mode so it is safe in CI and local regression loops. It must report machine-readable JSON including:

- `verify_passed`
- `verify_gates`
- `coherence_passed`
- `coherence_issues`
- output path and video id

Tests should cover both Python API use and CLI use.

## P2-F implementation lesson

For real sample smoke, structural gates are necessary but insufficient. Capture warnings emitted during `generate_report.report_markdown()` and treat writer fallback warnings as first-class quality failures when requested.

Expected summary fields:

- `warnings`
- `fallback_warnings`
- `fallback_warning_count`
- `fail_on_fallback_warning`
- `failed_due_to_fallback_warning`

When `--fail-on-fallback-warning` is set:

```text
fallback_warning_count > 0 → passed=false → exit 1
```

## Tests to keep

- Fixture path: full pipeline passes, `fallback_warning_count == 0`.
- CLI path: `--fail-on-fallback-warning --json` exits 0 for clean fixture output and exposes JSON fields.
- Bad provider path: invalid writer output triggers LLM writer fallback warnings, and `fail_on_fallback_warning=True` makes the run fail.
- Full suite should still pass excluding ASR config tests when ASR env is intentionally absent.

## OMP audit results from this session

P2-E:

```text
task_id: omp-20260702-185440
severity: pass
evidence: 13
```

P2-F:

```text
task_id: omp-20260702-203358
severity: pass
evidence: 14
```

Key OMP confirmation for P2-F: fallback warnings from §3/§4/§7 `video_analysis_engine.py` warning sites are capturable via `warnings.catch_warnings(record=True)`, are filtered by `falling back to skeleton`, and are wired into `passed` / CLI exit code.
