---
name: bilibili-video-analyzer
description: >
  Deprecated compatibility entry for historical Bilibili video-analysis requests.
  Use only when an existing workflow explicitly invokes bilibili-video-analyzer; immediately forward the task to video-analysis-engine.
  DO NOT implement, analyze, fetch, write reports, or store scripts under this legacy skill.
version: 4.0.0
replaced_by: video-analysis-engine
sunset_after: 2026-08-12
legacy_use_count: 0
warning_threshold: 5
author: Hermes Agent
license: MIT
---

# Deprecated: forward to `video-analysis-engine`

This skill is a compatibility shim only. The canonical implementation, scripts, tests, references, Writer and quality gates live in `video-analysis-engine`.

## Mandatory forwarding

1. Load `video-analysis-engine`.
2. Execute the request using its platform router and evidence contract.
3. Tell the user only when the legacy name was explicitly invoked: `bilibili-video-analyzer 已迁移为 video-analysis-engine`.
4. Do not create or restore `scripts/`, `tests/`, `references/`, caches or a second implementation here.

## Retirement telemetry

- Increment `legacy_use_count` only in the deployment telemetry/control plane; do not rewrite this source file per invocation.
- If usage reaches `warning_threshold`, report the stale caller before retirement.
- Removal after `sunset_after` requires explicit user authorization and verified zero active callers.

## ✅ Verification Checklist

- [ ] Forwarded to `video-analysis-engine`?
- [ ] No implementation or evidence stored under this directory?
- [ ] No formal report produced from metadata-only evidence?
