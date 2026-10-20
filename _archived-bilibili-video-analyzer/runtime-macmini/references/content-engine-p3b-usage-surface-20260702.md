# P3-B usage surface note

## Trigger

Use this when maintaining `bilibili-video-analyzer` after release-gate work, especially when another agent needs to know the correct entry point before editing writer/render/fetch/report logic.

## Durable lesson

A quality gate that only lives in chat history, an Obsidian project note, or a deep `references/` file is easy to skip. Surface the minimum safe commands at the project front door (`README.md`) and mirror the pointer in `SKILL.md`.

## Required project-front-door commands

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/release_gate.py
```

This default gate should stay cheap and deterministic: fixture quality gate + full pytest excluding `tests/test_asr_config.py`. It must not call real model-backed writers by default.

Real sample smoke must remain explicit:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py \
  --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
  --real-writer-provider cli
```

## Pitfalls

- Do not make real sample smoke the default; it may spend time/tokens and depends on model-backed providers.
- Do not allow `fixture` to masquerade as a real sample writer. The release-gate runner should reject it at CLI and API layers.
- Do not preserve intermediate drafts/transcripts in Obsidian by default. Keep one user-facing report note; put QA evidence in a project validation record.

## Verification pattern

After changing docs/entry points, run both documented commands:

```bash
PYTHONPATH=scripts python3 scripts/release_gate.py --dry-run
PYTHONPATH=scripts python3 scripts/release_gate.py
```

Treat the release gate output as the evidence, not just the fact that the command exists in README.
