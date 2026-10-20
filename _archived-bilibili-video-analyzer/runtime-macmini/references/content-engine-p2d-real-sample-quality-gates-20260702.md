# P2-D Real Sample Quality Gate Findings (2026-07-02)

## Context

Real sample: `BV1B9T36nEvL` (13:29, cross-platform搬运 video). After P2-D LLM writer integration, the first realistic end-to-end run exposed issues that unit tests and `check_report_coherence()` alone did not catch.

## Durable lessons

### 1. Always validate LLM writer output against `verify_report.py`, not just coherence

`check_report_coherence()` can pass while `verify_report.py` fails depth/format gates. For P2-D writer output, acceptance requires both:

```bash
PYTHONPATH=scripts python3 scripts/verify_report.py /tmp/<report>.md
PYTHONPATH=scripts python3 - <<'PY'
from pathlib import Path
from video_analysis_engine import check_report_coherence
res = check_report_coherence(Path('/tmp/<report>.md').read_text(encoding='utf-8'))
print(res.passed, len(res.issues))
PY
```

Known real-sample failure modes:
- LLM result duplicated the section title (`### ## 3...`) so old verifier could not recognize §3 structure.
- §4/§7 returned heading-only / empty structure; validator passed because it checked references/items but not section-specific format.
- §5 had enough blockquotes only after long ASR chunks were split into independent quote groups.

### 2. `validate_section()` must enforce old verifier format contracts

For §3/§4/§7, validation must reject content that `verify_report.py` will not count:

- §3 insight headers: `### 💡 ...`
- §4 deep-dive modules: `### 模块 N：...` with Arabic digits
- §7 critical/action structure: headings containing `独特价值`, `局限`/`偏见`, `可行动`/`行动项`; value/blind-spot lists use `- ` bullets
- Empty/heading-only content is invalid even if it contains `[E1]`
- Fallback after validation failure must warn (`warnings.warn(...)`), not silently degrade

### 3. §5 highlight writer needs noise filtering plus enough quote groups

ASR/transcript chunks often contain title lines and rhetorical bridge questions. The deterministic §5 writer should:

- Filter title lines (`## ...`)
- Filter short standalone questions (`len < 35` and ends with `？` or `?`)
- Split long transcript candidates on sentence boundaries to satisfy G5 (`≥5` blockquote groups)
- Apply the same noise filter to each split sentence, not only the original candidate

Regression test pattern:

```python
md = write_highlights_section({'quality_gate': 'G5', 'evidence': [...]})
assert '> "那么后来发生了什么？"' not in md
assert '> "它最后去了哪里？"' not in md
assert len([line for line in md.splitlines() if line.startswith('> ')]) >= 5
```

### 4. Real sample acceptance needs a compact evidence bundle for OMP

When OMP needs to re-audit runtime quality, first create a compact evidence file with:

- `git status --short`
- relevant `git diff`
- targeted pytest output
- full pytest output (`tests --ignore=tests/test_asr_config.py` when ASR config is environment-dependent)
- `verify_report.py` output
- `check_report_coherence()` output
- §5 excerpt / scan proving no short-question noise
- `.cookies` probe + git-ignore evidence if cookies were involved

Then give OMP read-only scope over the evidence file, generated report, and directly relevant production/tests. This avoids huge raw context while preserving independent auditability.

Example evidence path from this session: `/tmp/bili-p2d-v6-omp-evidence.md`.

### 5. Cookie artifacts are repo hygiene, not report evidence

If browser cookies are dumped under the skill repo (`shared/bilibili-video-analyzer/.cookies/`), do not commit them. Add/keep this repo-root ignore rule:

```gitignore
shared/bilibili-video-analyzer/.cookies/
```

Verify before final review:

```bash
test -d .cookies && echo '.cookies exists' || echo '.cookies absent'
git check-ignore -v .cookies/bilibili.txt || true
```

## Real-sample acceptance evidence from session

Final v6 report:

- `verify_report.py`: OVERALL PASS; G5 measured 5 highlight blockquote groups
- `check_report_coherence`: `passed=True`, `issues=0`
- Full tests: `98 passed` (excluding `tests/test_asr_config.py`)
- OMP: `omp-20260702-160110`, severity `pass`, accepted with 12 evidence items

§5 final shape: exactly 5 long blockquotes, no short rhetorical question fragments.
