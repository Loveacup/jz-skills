---
title: Content Engine P2-D LLM Writer Pipeline Triad
created: 2026-07-01
status: accepted
---

# Content Engine P2-D LLM Writer Pipeline Triad（2026-07-01）

## Scope

P2-D 将 P2-C 的 writer adapter 从「确定性上下文」推进到「可插拔 LLM writer 管线」，但仍保持旧版内容引擎为骨架基线：

- §3 Key Insights：LLM writer
- §4 Deep Dive：LLM writer
- §5 Highlights：确定性 writer（P2-C2）
- §7 Critical Review & Action：LLM writer
- §0/§1/§2/§2.5/§6/§8：保持 skeleton / deterministic rendering

## Implemented API

### Writer harness

- `WriterProvider = Callable[[str, str], str]`
- `WriterEvidenceCandidate`
- `WriterSectionContext`
- `WriterResult`
- `build_typed_writer_section_contexts(report)`
- `write_llm_section(context, provider, retries=2)`
- `validate_section(result, contract)`

Validation is deterministic:

1. no fabrication marker
2. evidence references must use valid `[E#]`
3. minimum item count
4. minimum words per item

### Providers

- `deepseek_writer_provider(system, user)`
  - direct DeepSeek API via stdlib `urllib`
  - requires `DEEPSEEK_API_KEY`
- `make_cli_writer_provider(command=None, timeout=None)`
  - default reads `BILI_WRITER_CLI`
  - fallback command: `omp -p --no-session --max-time 120 --no-skills --no-extensions --no-rules`
- `cli_writer_provider(system, user)`
  - default CLI provider wrapper
  - does not depend on `DEEPSEEK_API_KEY`

### Report entry wiring

`generate_report.py` now exposes:

```bash
--writer-provider none|cli|deepseek
```

Default is `none`, preserving old behavior. For CLI/OMP-backed writer generation:

```bash
PYTHONPATH=scripts \
BILI_WRITER_CLI='omp -p --no-session --max-time 120 --no-skills --no-extensions --no-rules' \
python scripts/generate_report.py \
  --input /tmp/BV_fetch_all.json \
  --output /tmp/BV_report.md \
  --writer-provider cli
```

## Coherence checker

Added deterministic cross-section checker:

- `ReportCoherenceIssue`
- `ReportCoherenceResult`
- `check_report_coherence(markdown)`

Rules:

1. `section_order`
2. `skeleton_residue` — scoped to LLM writer sections §3/§4/§7 only
3. `duplicate_paragraph`
4. `bad_evidence_citation`
5. `empty_llm_section`

Important fix: skeleton placeholders in non-LLM sections (§1/§6 etc.) must not trigger `skeleton_residue`; they are allowed while the remaining deterministic sections are still skeleton-backed.

## Runtime verification

Hermes ran:

```bash
PYTHONPATH=scripts python -m pytest tests/test_generate_report_writer_provider.py -v
# 4 passed

PYTHONPATH=scripts python -m pytest tests/test_report_coherence.py -v
# 7 passed

PYTHONPATH=scripts python -m pytest tests/ -q --ignore=tests/test_asr_config.py
# 93 passed, 3 expected warnings
```

End-to-end fake CLI smoke:

```bash
PYTHONPATH=scripts \
BILI_WRITER_CLI='/tmp/bili-fake-writer-cli.py' \
python scripts/generate_report.py \
  --input /tmp/BV_D6_SMOKE_fetch_all.json \
  --output /tmp/BV_D6_SMOKE_report.md \
  --no-fact-check \
  --writer-provider cli
```

Smoke evidence:

- report path: `/tmp/BV_D6_SMOKE_report.md`
- inserted markers: `CLI_WRITER_SECTION3_*`, `CLI_WRITER_SECTION4_*`, `CLI_WRITER_SECTION7_*`
- `check_report_coherence(report).passed == True`

Real CLI smoke:

```bash
PYTHONPATH=scripts BILI_WRITER_CLI_TIMEOUT=60 python - <<'PY'
from video_analysis_engine import cli_writer_provider
out = cli_writer_provider('你是测试回显器。', '只输出一行：CLI-OK')
print(out[:500])
PY
# CLI-OK
```

## OMP audit trail

- P2-D1 writer harness: `omp-20260701-004904`, severity=`pass`
- P2-D2 DeepSeek provider + §3: `omp-20260701-011017`, severity=`concern`, accepted after warning fix
- P2-D3/D4/D5: `omp-20260701-030106`, severity=`pass`
- CLI provider: `omp-20260701-032713`, severity=`pass`
- P2-D6 generate_report provider wiring + smoke: `omp-20260701-041527`, severity=`pass`

## Guardrails

- No transcript → no formal report remains unchanged.
- `render_markdown(report, provider=None)` default is backward-compatible.
- LLM failures or validation failures fallback to skeleton and emit `warnings.warn`.
- `cli_writer_provider` delegates model/provider/key configuration to the CLI; this is the preferred route when the caller wants to inherit OMP/Hermes-side model configuration.
- Do not accept bare `omp -p` audit results; audit verdicts must use call-omp workflow.
