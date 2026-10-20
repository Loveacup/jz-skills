# P2-G 真实样片修复：默认 `--report` 生成 skeleton + `claim-first-full` claim bundle 为空

> 记录 2026-07-06 对 `B站笔记_韩红走面儿京圈黄昏_20260706`（BV1anMP69ED5）的验证与修复。
> 相关 commit: 6bc3214 之后的修复工作流。

## 问题 1：默认 `fetch_all --report` 生成 skeleton 报告

### 现象

用户直接运行：

```bash
python3 scripts/fetch_all.py BV1anMP69ED5 --report
```

输出 `/tmp/BV1anMP69ED5_report.md` 的 §3、§4、§7 全是：

```markdown
### 💡 Skeleton Insight
_骨架占位：核心洞察待 LLM 基于上方证据填充。_

### 模块 1: Skeleton Module
_骨架占位：深度解析模块待 LLM 生成。_

### 观众反馈 Skeleton
_骨架占位：观众反馈与批判性审视待 LLM 生成。_
```

### 根因

- `fetch_all.py` 调用 `report_markdown(results, run_fact_check=True)` 时没有传 `provider` 和 `depth_profile`。
- `generate_report.py` 的 CLI 默认 `--writer-provider none`（向后兼容）。
- 当 `provider=None` 时，LLM 章节走确定性 skeleton 渲染，不调用任何 writer。

### 修复

在 `fetch_all.py` 的 `generate_report()` 中显式传入：

```python
from generate_report import report_markdown, cli_writer_provider

markdown, report = report_markdown(
    results,
    run_fact_check=True,
    provider=cli_writer_provider,
    depth_profile="claim-first-full",
    claim_qa_gate=True,
)
```

并增加 writer 可用性检查：

- 若 `BILI_WRITER_CLI` 未设置且 `/opt/homebrew/bin/omp` 不存在，直接返回 `None`，不生成骨架报告。

同时 `generate_report.py` 的 `main()` 中，当 `depth_profile` 为 `"claim-first-full"` 或 `"v24-full"` 时自动启用 `claim_qa_gate=True`。

### 正确用法

- 用户面：直接 `fetch_all.py BV1xx --report`（修复后默认走 cli writer）。
- 手动：

```bash
python3 scripts/generate_report.py \
  --bvid BV1xx \
  --writer-provider cli \
  --depth-profile claim-first-full \
  --output /tmp/BV1xx_report.md
```

- 验证是否启用 writer：生成的报告不应再出现 `Skeleton` / `_骨架占位`。

## 问题 2：`claim-first-full` 模式下 claim bundle 为空

### 现象

即使显式启用 `--writer-provider cli --depth-profile claim-first-full`，stdout 显示：

```json
claim_bundle_stats: {"claims_count": 0, "insights_count": 0}
```

且 §4 因格式验证失败 fallback 到 skeleton。

### 根因

`video_analysis_engine.py` 中的 `extract_claims_from_evidence(report)` 只读取：

```python
report.get('subtitle') or report.get('transcript')
report.get('comments', [])
```

但实际 transcript 证据已切片并存储在 `report['evidence_map']['by_section']` 中（`EvidenceCandidate` 列表），顶层字段不存在或不是文本。

同时：
- 证据 ID 格式为 `transcript_seg_1`、`comment_2`，与 writer prompt 中的 `[E1]`、`[E2]` 不一致。
- `synthesize_insights_from_claims()` 把所有 claim 都分配到 `target_section="3"`，没有 §4/§7 的 insight。

### 修复方向

1. `extract_claims_from_evidence()` 优先从 `evidence_map.by_section` 读取 transcript 候选。
   - 按 section 顺序遍历，优先 `'3'`、`'4'`、`'7'`。
   - 每个 `EvidenceCandidate` 生成一个 `Claim`。
   - 证据 ID 使用 `E{i}` 或 `[E{i}]`，与 writer prompt 对齐。
   - 评论/弹幕只生成少量 audience-signal claims，target section 为 `"7"`，confidence 低。

2. `synthesize_insights_from_claims()` 按 claim 语义分配 target section：
   - 机制性/解释性 claim → `"4"`
   - 事实/观察性 claim → `"3"`
   - 评论/弹幕/观众反应 → `"7"`

3. 确保 `claim_context` 格式化输出 `[C1] 文本（E1）` 形式，writer prompt 能正确识别。

### 验证命令

```bash
python3 scripts/generate_report.py \
  --bvid BV1anMP69ED5 \
  --writer-provider cli \
  --depth-profile claim-first-full \
  --output /tmp/BV1anMP69ED5_report_cli_claimfirst.md
```

修复后应满足：

- `claim_bundle_stats.claims_count >= 3`
- `claim_bundle_stats.insights_count >= 3`
- 报告中无 `_骨架占位` / `Skeleton`（在 §3/§4/§7 中）
- 通过 `verify_report.py` 和 `check_report_coherence()`

## 测试建议

- `tests/test_fetch_all_report_gate.py`：验证默认 `--report` 路径传入正确的 provider、depth_profile、claim_qa_gate。
- `tests/test_claim_first_pipeline.py`：验证从 `evidence_map` 提取 claim、insight 分配到 §3/§4/§7。
- 全量：`PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py`
- 真实样片 smoke：跑 `BV1anMP69ED5` 并人工检查报告可读性。

## 相关文件

- `scripts/fetch_all.py`
- `scripts/generate_report.py`
- `scripts/video_analysis_engine.py`
- `tests/test_fetch_all_report_gate.py`
- `tests/test_claim_first_pipeline.py`

## 经验教训

1. 默认用户面命令（`fetch_all --report`）必须直接产生可用输出，不能要求用户记住额外参数。
2. 新增 `depth_profile` 或 `claim-first` 架构时，必须在真实样片上验证 `claim_bundle_stats` 非空。
3. 证据字段名和 ID 格式必须在 `extract_claims`、`build_claim_bundle`、`writer prompt`、`verify_report` 四个环节保持一致。
4. 结构 gate 通过不等于 claim 系统工作；要同时检查 claim count 和 report 中是否无 skeleton 残留。
