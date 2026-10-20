# P2-C1 · Writer Section Context Adapter（三方协作记录）

日期：2026-06-30

## 范围

P2-C1 是正式 writer 接入前的最小安全切片：只新增一个确定性的 writer adapter，不调用外部 LLM，不生成深度正文。

新增 API：

```python
build_writer_section_context(report: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]
```

输入为 `analyze_video(inp)` 的 report dict；输出为 JSON-serializable writer context，供后续正式 writer 消费。

明确不做：

- 不接 LLM writer。
- 不改 `render_markdown()` 输出行为。
- 不把 `writer_context` 自动塞进 `analyze_video()` report payload。
- 不改 ASR / fetch / subtitle / `generate_report.py` glue。
- 不新增依赖。

## 输出契约

顶层固定 key：

```text
baseline
mode
can_generate_formal_report
blocking_reason
source_appendix
sections
warnings
```

`source_appendix`：

- `transcript_summary`：§0 风格简洁摘要，只含 `transcript_available/method/language/segments/chars`。
- `table_rows`：复用 P2-B5 的 §8 Source Appendix table contract，即 `_source_table_rows(report)`。

`sections[]`：

- 按 `report_plan.sections` 原顺序输出。
- `heading` 固定为 `## {id}. {title}`，不破坏 `verify_report.py` 格式。
- `evidence` 来自 `evidence_map.by_section[id][:top_n]`。
- `draft_placeholder` 明确是占位，不冒充正式正文。
- `writer_contract` 带 evidence kinds、quality gate、min_items、min_words_per_item、no_fabrication 等约束。

## 无 transcript 规则

无 transcript 时：

- `can_generate_formal_report=False`
- `blocking_reason=missing_transcript`
- sections 只包含 `0` 和 `8`
- 所有 evidence 为空
- 不伪造 `json_path` / `txt_path` / `parts` / `failed_parts`
- warnings 中包含 missing transcript blocker

## 三方流程

1. Codex planning-only 产出执行包，建议仅改：
   - `scripts/video_analysis_engine.py`
   - `tests/test_writer_section_context.py`
2. CC session `cc-bili-p2c1` 实现 API 与 6 个测试。
3. Hermes 重新取证：读当前生产文件、审 diff、亲自跑 targeted/adjacent/full tests。
4. OMP 正确流程：
   - 第一轮：错误地用裸 `omp -p`，用户纠正；该结果废弃不采信。
   - 第二轮：按 `call-omp` skill 四步 `omp-start → omp-send → omp-monitor → omp-finish` 重跑；因工具白名单无 bash/eval，verdict=`blocker`，已 reject。
   - 第三轮：补 Hermes runtime evidence 后重派，raw schema rejected，未 accept。
   - 第四轮：compact bundle + JSON-only，通过 call-omp 四步，`omp-p2c1-writer-section-context-r3` severity=`pass`，accept。

## 验证

source repo：

```bash
cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer
PYTHONPATH=scripts pytest -q tests/test_writer_section_context.py
PYTHONPATH=scripts pytest -q \
  tests/test_writer_section_context.py \
  tests/test_evidence_map.py \
  tests/test_render_markdown_plan.py \
  tests/test_render_markdown_sources.py \
  tests/test_evidence_source_gate.py
PYTHONPATH=scripts pytest -q
```

结果：

```text
6 passed
42 passed
82 passed
```

OMP accepted verdict：

```text
task_id: omp-p2c1-writer-section-context-r3
severity: pass
evidence: 10 条
```

## 关键教训

- OMP 必须走 `call-omp` skill 工作流；不要裸用 `omp -p` 做审计。
- 当 OMP 无法自己运行 shell 测试时，Hermes 应先生成 runtime evidence 文件，再让 OMP 读证据裁决。
- monitor schema rejected 不等于通过；必须 compact bundle + JSON-only 重派，直到 `omp-monitor` 得到合法 severity/evidence，再 `omp-finish --accept`。

## 后续

P2-C1 只是 writer 输入契约。下一步 P2-C2 可以让真正 writer 消费这个 context，生成某一小节的正式正文（建议先从 §5 Highlights 或 §3 Key Insights 开始），再接 `verify_report.py` 的 depth gate。
