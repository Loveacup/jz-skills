# Douyin sparse PublishedMarkdown — acceptance record (2026-07-13)

## Decision

Short/low-evidence `ready` inputs use an explicit `EvidenceBudget`. `--mode auto` may select `sparse`; explicit `full`/`condensed` overrides remain intact and no-transcript inputs remain `preanalysis`.

Sparse keeps the unified §0–§8 report contract, but §§1/3/4/7 are deterministic, transcript-grounded, provider-free, and protected by exact report-aware fidelity. It does not lower evidence integrity or pad to full-mode quotas.

## Human-QA correction

The first real report passed automated gates but was rejected by human QA because generic §1 labeled rocket telemetry as `提出问题`. D1 replaced sparse §1 with a literal transcript timeline and extended `P0_SPARSE_REPORT_FIDELITY` to §§1/3/4/7. The final note contains no synthetic narrative stages.

## Repository verification

Executed from `shared/video-analysis-engine`:

- D1 focused suite: `59 passed`.
- Full suite: `486 passed`, with three expected writer-fallback warning tests.
- Release gate: PASS.
  - existing full fixture lane: PASS;
  - provider-free sparse fixture lane: PASS;
  - release pytest lane: PASS.
- `git diff --check`: PASS.

Raw release evidence: `/tmp/douyin-final-release-gate-after-human-qa.json`.

## Real Douyin E2E

Real cached browser-captured Douyin audio was used; transcript text was not injected:

```text
yt-dlp attempt (expected failure)
→ bounded media_fallback copies real audio into provider tempdir
→ live H200 HTTP ASR
→ DouyinAdapter
→ EvidenceBundle ready
→ analysis bridge
→ EvidenceBudget auto=sparse
→ assembled deterministic DraftReport
→ report-aware PublishedMarkdown
```

Observed:

- `ytdlp_attempts=1`;
- `fallback_calls=1`;
- `transcript_source=h200-asr`;
- `transcript_chars=146`;
- `effective_mode=sparse`;
- structure/coherence/publish/fidelity: PASS;
- human QA: no synthetic `提出问题/深化分析/得出结论/叙事阶段`, no unsupported NASA/SpaceX/Byzantine material.

Artifacts:

- summary: `/tmp/douyin-sparse-real-e2e-summary.json`;
- formal Markdown: `/tmp/Douyin笔记_长征十号乙火箭_sparse_e2e_20260713.md`.

## Independent audit

- OMP bundle-only audit was stopped by the 20 MB raw fuse at 24,999,344 bytes. It ended with `stopReason=toolUse`, zero evidence, and no legal JSON verdict. The run was formally rejected. This is an audit-tool failure, neither code blocker nor pass.
- Per fallback policy, Codex performed a clean read-only source/test-contract review and returned `severity=pass`, with evidence for all seven criteria and no required fixes. Verdict artifact: `/tmp/codex-audit-douyin-final.json`.

## Runtime deployment

Scoped deployment copied only the 18 changed scripts/tests from the repository into `~/.hermes/skills/video-analysis-engine`; runtime-only references, cookies, and private caches were preserved. Backup:

`/tmp/video-analysis-engine-runtime-20260713-214501.tar.gz`

Post-deploy evidence:

- source/runtime hashes: `18/18` match;
- runtime-applicable tests: `470 passed`;
- runtime full fixture: PASS;
- runtime sparse fixture: PASS;
- runtime real H200 E2E and human-QA checks: PASS.

Five repository-context tests are intentionally not runnable from the installed skill directory: four require the repository `.git` and `deploy/*.sh`, and one requires a private P6R cache excluded from deployment. They passed in the canonical repository suite before deployment.

## Boundaries

- One video only; no batch/feed/profile crawling.
- No copied/private `a_bogus` implementation.
- Private cookies, signed URLs, ASR endpoint values, and `.p6r-cache` payloads are not published.
- No commit or push was performed.
