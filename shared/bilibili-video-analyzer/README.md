# bilibili-video-analyzer

Bilibili / YouTube video analysis engine for producing Obsidian-ready deep reports with transcript evidence, comments/danmaku context, writer validation, and release quality gates.

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
