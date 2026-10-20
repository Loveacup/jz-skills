# P2-D6 CLI Writer Provider Integration Triad — 2026-07-01

## Context

P2-D 已将 §3/§4/§7 接入可插拔 LLM writer harness，但真实 DeepSeek API 路径受 `DEEPSEEK_API_KEY` 环境变量影响。用户要求质量优先，并倾向让 LLM 配置沿用调用方 CLI。D6 的目标是把 writer provider 正式接入 `generate_report.py` 命令行入口，并提供不依赖 DeepSeek env 的 CLI provider 路径。

## Outcome

新增/确认两层 provider：

```python
def make_cli_writer_provider(command: Optional[str] = None, timeout: Optional[int] = None) -> WriterProvider

def cli_writer_provider(system: str, user: str) -> str
```

默认命令：

```text
BILI_WRITER_CLI
  -> 若设置，用该 CLI 命令
  -> 未设置，fallback 到：
     omp -p --no-session --max-time 120 --no-skills --no-extensions --no-rules
```

`generate_report.py` 新增：

```bash
--writer-provider none|cli|deepseek
```

- `none`：默认，保持旧骨架/确定性渲染行为
- `cli`：沿用 `BILI_WRITER_CLI` 或默认 OMP CLI 的模型配置
- `deepseek`：直接走 `DEEPSEEK_API_KEY` 的 DeepSeek API provider

`report_markdown(..., provider=...)` 正式把 provider 传入 `render_markdown(report, provider=provider)`。

## Important Design Lesson

CLI provider 是解决“沿用调用 CLI 配置”的正确接缝：

- 不把 DeepSeek/OpenAI/Claude 配置写死在视频引擎里
- 不要求当前 shell 一定有 `DEEPSEEK_API_KEY`
- 由被调用 CLI 自己负责 provider/model/key/session 配置
- 视频引擎只负责拼接 `system + user` prompt 并读取 stdout

未来换成 Hermes CLI、OMP、Codex、Claude Code 或其它 LLM CLI，只需改 `BILI_WRITER_CLI`，不用改 content engine。

## Tests Added / Runtime Evidence

新增 `tests/test_generate_report_writer_provider.py`：

- `resolve_writer_provider('none') -> None`
- `resolve_writer_provider('cli') -> cli_writer_provider`
- `resolve_writer_provider('deepseek') -> deepseek_writer_provider`
- `report_markdown(..., provider=fake_provider)` 确认 provider 传入 `render_markdown`

新增/扩展 `tests/test_writer_harness.py`：

- configured command 路径
- env command 路径
- nonzero exit raises
- empty output raises

真实 CLI smoke：

```bash
PYTHONPATH=scripts \
BILI_WRITER_CLI='/tmp/bili-fake-writer-cli.py' \
python scripts/generate_report.py \
  --input /tmp/BV_D6_SMOKE_fetch_all.json \
  --output /tmp/BV_D6_SMOKE_report.md \
  --no-fact-check \
  --writer-provider cli
```

Evidence:

- report generated: `/tmp/BV_D6_SMOKE_report.md`
- markdown chars: `8176`
- inserted markers: `CLI_WRITER_SECTION3_*`, `CLI_WRITER_SECTION4_*`, `CLI_WRITER_SECTION7_*`
- `check_report_coherence(report)` returned `passed True`
- full suite: `93 passed, 3 expected warnings`
- OMP audit: `severity=pass`, 12 evidence items, accepted

## Coherence Checker Pitfall Fixed

D6 smoke exposed a false positive in `check_report_coherence()`:

> Rule `skeleton_residue` originally scanned the entire markdown. Non-LLM sections such as §1/§6 may legitimately contain ordinary skeleton placeholders (`_骨架占位：暂无证据候选。_`) while §3/§4/§7 are successfully LLM-written.

Fix:

- `skeleton_residue` now only scans LLM writer sections: §3, §4, §7
- added regression test: `test_coherence_allows_skeleton_residue_in_non_llm_sections`

Lesson: cross-section coherence gates must distinguish “LLM writer output quality” from “ordinary deterministic skeleton placeholders.” A global regex gate is too blunt.

## OMP / Audit Pattern

For D6-style entrypoint work, OMP audit should receive:

- changed entrypoint file (`scripts/generate_report.py`)
- writer harness file (`scripts/video_analysis_engine.py`)
- provider/coherence tests
- runtime evidence file containing targeted tests, full suite output, CLI smoke output, and coherence result
- smoke output markdown path

Do not ask OMP to infer runtime behavior from source only; give it `/tmp/<task>-runtime-evidence.txt` and the generated smoke report.
