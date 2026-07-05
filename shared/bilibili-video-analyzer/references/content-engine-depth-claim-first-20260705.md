# Content Engine Depth & Claim-First Architecture — 20260705

## 问题与动机

### v2.6 现状诊断

截至 2026-07-05，`bilibili-video-analyzer` 已完成：

- P2-D LLM Writer Pipeline：`WriterProvider` 可插拔，§3/§4/§7 LLM writer，默认 `provider=None` 向后兼容
- P3-A Release Gate：`release_gate.py` 统一质量入口（fixture gate + pytest）
- P0/P1 Publishable Gate：`verify_publishable_report.py` 阻止 skeleton/debug 稿入库
- Section QA Gate Phase 1-4：
  - D1-D5 五维评估（evidence-grounded / not-mechanical / human-readable / insight-density / no-skeleton）
  - P0 skeleton blocker 不进入 `draft_sections`，P1/P2 issue 保留并 warning
  - JSON-able `section_qa` 元数据暴露
  - §1/§5 dimension exemptions（not-mechanical + insight-density）
  - `--section-qa-gate` opt-in P0 blocker gating

但仍有如下缺口（相比 v2.4 深度分析框架）：

1. **Claim 中间层缺失**：`DraftReport` 直接从 `evidence_map` → `draft_sections`，缺 extract → synthesize → audit → render 的可测中间层。
2. **Writer Prompt 偏轻**：当前 `WRITER_PROMPTS["3"|"4"|"7"]` 缺 v2.4 的类型诊断、显性/隐性/元叙事、信息降噪、多维对比、批判审视。
3. **Section QA 缺 warrant/rebuttal/actionability 维度**：D1-D5 确保结构完整，但不检查**推理许可显性化**、**边界/反证显性化**、**行动性**。
4. **Verify 缺 claim-first gates**：`verify_report.py` 已有 G1/G3/G4/G5/G7，但没有 G8-G10（claim/warrant/rebuttal 检查）。
5. **深度模式未分档**：用户无法选择"标准快速产出"vs"v2.4 深度"vs"claim-first 审计"。

### 目标

在**保留当前 `Claim-first / DraftReport / Section QA / publishable gate` 架构**的前提下，恢复并超过 v2.4 深度分析框架：

- 不是回到黑盒重 prompt，而是把 v2.4 的 7 步推理链、Depth Quality Gates、8-section 内容资产，**落到可测试的数据结构、writer contract 与质量闸里**。
- 引入 `Claim` / `Insight` / `ClaimBundle` / `audit` 流程，明确"评论/弹幕不升格为事实"。
- 扩展 Section QA 到 D6-D8（warrant/rebuttal/actionability），扩展 verify 到 G8-G10。
- CLI 提供 `--depth-profile` / `--claim-qa-gate` 选项，向后兼容。

---

## 设计方案

### 深度分析模式（Depth Profile）

三档分析深度：

| 档位 | 说明 | 适用场景 |
|:---|:---|:---|
| **standard** | 默认模式，保留 v2.6 行为：确定性 extractor（§1/§5/§6）+ LLM writer（§3/§4/§7） | 常规分析，快速产出 |
| **v24-full** | 恢复 v2.4 深度分析框架：7 步推理链、Depth Quality Gates、8-section 内容资产，但不走 claim-first | 需要传统深度但无需 claim 审计的场景 |
| **claim-first-full** | 最严格模式：extract → synthesize → audit → render 的可测中间层，Claim/Insight/ClaimBundle 结构，D6-D8 QA gates + G8-G10 verify gates | 政策/新闻/技术解读类视频，需要证据溯源与 warrant 显性化的场景 |

CLI 接口：

```bash
# 常规分析（默认）
python3 scripts/generate_report.py --input /tmp/BV.json --writer-provider cli

# v2.4 深度框架
python3 scripts/generate_report.py --input /tmp/BV.json --writer-provider cli --depth-profile v24-full

# Claim-first 全链路（含 claim 审计）
python3 scripts/generate_report.py --input /tmp/BV.json --writer-provider cli --depth-profile claim-first-full
```

### Claim-First 架构

流程：

```text
Evidence → extract_claims() → Claim[] → synthesize_insights() → Insight[]
  ↓                                ↓
  audit_claims()                   assign to §3/§4/§7
  ↓                                ↓
  ClaimBundle                      render with claim_context
```

核心数据结构：

```python
@dataclass
class Claim:
    id: str                      # Claim unique identifier
    text: str                    # 主张文本
    confidence: float            # 0.0-1.0
    evidence_ids: List[str]      # List of evidence IDs (e.g., ["E1", "E2"])
    source_type: ClaimSourceType  # Literal["transcript", "comment", "danmaku", "audience", "metadata", "external"]
    grounds: List[str]           # Toulmin grounds (factual basis)
    warrant: str                 # 推理许可（为什么这个证据能支撑这个主张）
    backing: str                 # Toulmin backing (support for warrant)
    qualifier: str               # Toulmin qualifier (degree of certainty)
    rebuttal: str                # 反证/边界（什么情况下这个主张不成立）
    claim_type: ClaimType         # Literal["observed", "inferred", "recommendation"]

@dataclass
class Insight(Claim):
    """An insight is a Claim with additional depth/novelty/targeting metadata."""
    depth: float                 # Depth score (0.0-1.0)
    novelty: float               # Novelty score (0.0-1.0)
    target_section: TargetSection # Literal["3", "4", "7"]

@dataclass
class ClaimAuditResult:
    action: AuditAction          # Literal["keep", "downgrade", "drop"]
    original_claim: Claim        # Original claim before audit
    reason: str                  # 审计原因

@dataclass
class ClaimBundle:
    claims: List[Claim]          # 原始抽取的 claims
    audit_results: List[ClaimAuditResult]
    insights: List[Insight]      # 从 kept claims 合成的 insights
```

### 审计规则（Audit Rules）

1. **只能降级/删除，不能提高 confidence**：
   - `keep`：保留原 confidence
   - `downgrade`：high → medium, medium → low
   - `drop`：从 bundle 移除

2. **评论/弹幕不升格为事实**：
   - 评论/弹幕数据只能作为 `audience_signal`，不能直接成为 `factual` claim 的证据
   - 但可以作为 `interpretive` / `evaluative` claim 的支撑（如"观众普遍认为 X"）

3. **证据指针必填**：
   - 每个 claim 必须绑定 `evidence_pointer`
   - 格式：`transcript:segment_id` / `metadata:field_name` / `external:url`

### Section QA 扩展（D6-D8）

在 Phase 4 已有 D1-D5 基础上，新增：

| 维度 | 检查项 | P 级 | 说明 |
|:---|:---|:---:|:---|
| **D6** | `warrant-present` | P1 | §3/§4/§7 每个洞察/模块/行动项需含推理许可（为什么证据能支撑结论） |
| **D7** | `rebuttal-or-boundary` | P1 | §3/§4/§7 需含边界/反证（什么情况下不成立） |
| **D8** | `actionability` | P2 | §7 行动项需含具体可执行步骤或证据引用 |

适用范围：

- D6-D8 仅作用于 §3/§4/§7（insight/analysis/action sections）
- §1/§5/§6 保持现有 exemptions（not-mechanical + insight-density）

### Verify 扩展（G8-G10）

`verify_report.py` 新增 `--claim-first` opt-in：

| Gate | 章节 | 要求 |
|:---|:---|:---|
| **G8** | §3 核心洞察 | 每条洞察含 claim/evidence/warrant/boundary（检查 blockquote、bullet、wikilink 等结构） |
| **G9** | §4 Deep Dive | 每个模块含显性/隐性/元叙事或等价结构（如"核心论点 / 论证展开 / 批判审视"） |
| **G10** | §7 行动项 | 行动项含证据引用或 claim id（如"`[来源：§3-洞察2]`"或"`[证据：transcript:seg_42]`"） |

用法：

```bash
# 标准 verify（G1/G3/G4/G5/G7）
python3 scripts/verify_report.py /tmp/report.md --depth full

# 加 claim-first gates（G8-G10）
python3 scripts/verify_report.py /tmp/report.md --depth full --claim-first
```

### CLI Surface 扩展

**`run_quality_gate.py`**：

```python
parser.add_argument("--depth-profile", choices=["standard", "v24-full", "claim-first-full"], default="standard")
parser.add_argument("--claim-qa-gate", action="store_true", help="Enable claim QA gate (P0 blocker)")
```

summary 增加字段：

```python
{
    "depth_profile": "claim-first-full",
    "claim_bundle_stats": {
        "total_claims": 12,
        "kept": 8,
        "downgraded": 2,
        "dropped": 2,
        "insights": 5
    },
    "claim_qa_gate_passed": True,
    "failed_due_to_claim_qa_gate": False
}
```

**`generate_report.py`**：

```python
parser.add_argument("--depth-profile", choices=["standard", "v24-full", "claim-first-full"], default="standard")
```

**`verify_report.py`**：

```python
parser.add_argument("--depth", choices=["full", "condensed"], help="Alias for --mode (for claim-first compat)")
parser.add_argument("--claim-first", action="store_true", help="Enable G8-G10 claim-first gates")
```

---

## 测试策略

### 新增 fixture

- `tests/fixtures/depth_claim_fetch_all.json`：包含政策/新闻/技术解读类视频的完整 fetch_all 输出
- `tests/fixtures/depth_claim_subtitle.txt`：对应的字幕文本，含可验证 claims

### 新增测试文件

1. **`tests/test_depth_quality_contract.py`** — v2.4 深度框架合约测试
   - `test_writer_prompts_contain_v24_seven_step_framework`
   - `test_section_qa_d6_warrant_present`
   - `test_section_qa_d7_rebuttal_or_boundary`
   - `test_section_qa_d8_actionability`

2. **`tests/test_claim_first_pipeline.py`** — Claim/Insight/ClaimBundle 流程测试
   - `test_extract_claims_from_evidence`
   - `test_synthesize_insights_from_claims`
   - `test_audit_claims_only_downgrade_or_drop`
   - `test_build_claim_bundle`
   - `test_claim_bundle_to_dict`

3. **`tests/test_verify_report_claim_first.py`** — G8-G10 测试
   - `test_verify_g8_insight_has_claim_warrant_boundary`
   - `test_verify_g9_module_has_explicit_implicit_meta`
   - `test_verify_g10_action_has_evidence_or_claim_ref`

4. **`tests/test_run_quality_gate_depth_profile.py`** — CLI 集成测试
   - `test_run_quality_gate_depth_profile_standard`
   - `test_run_quality_gate_depth_profile_v24_full`
   - `test_run_quality_gate_depth_profile_claim_first_full`
   - `test_run_quality_gate_claim_qa_gate_blocker`
   - `test_run_quality_gate_summary_contains_claim_stats`

### 测试顺序（RED-first）

1. **先写测试并确认 RED**：
   ```bash
   cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer
   PYTHONPATH=scripts pytest -q \
     tests/test_depth_quality_contract.py \
     tests/test_claim_first_pipeline.py \
     tests/test_verify_report_claim_first.py \
     tests/test_run_quality_gate_depth_profile.py
   ```
   预期 RED：`Claim` / `ClaimBundle` / `extract_claims_from_evidence` 不存在，`verify_report.py --depth full` 不支持，等。

2. **逐步实现到 GREEN**：
   - Step 1: Claim pure functions（`extract_claims` / `synthesize_insights` / `audit_claims` / `build_claim_bundle`）
   - Step 2: Writer integration（扩展 `WriterSectionContext`、prompt、validation）
   - Step 3: Gates（扩展 Section QA 与 `verify_report.py`）
   - Step 4: CLI surface（`--depth-profile` / `--claim-qa-gate`）

3. **Full suite 验证**：
   ```bash
   PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
   PYTHONPATH=scripts python3 scripts/release_gate.py
   ```

---

## 验证命令

### Deterministic fixture gate（不联网、不烧 LLM）

```bash
cd /Users/alexcai/code/jz-skills/shared/bilibili-video-analyzer

PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/depth_claim_fetch_all.json \
  --output /tmp/depth_claim_quality_gate_report.md \
  --writer-provider fixture \
  --depth-profile claim-first-full \
  --fail-on-fallback-warning \
  --section-qa-gate \
  --claim-qa-gate \
  --json
```

预期：

- `claim_bundle_stats` 显示抽取/审计/合成结果
- `section_qa` 含 D6-D8 评估
- `passed=True`（fixture 产出应通过所有 gates）

### Static verify（带 claim-first gates）

```bash
PYTHONPATH=scripts python3 scripts/verify_report.py \
  /tmp/depth_claim_quality_gate_report.md \
  --depth full \
  --claim-first \
  --json
```

预期：

- G1/G3/G4/G5/G7 通过
- G8/G9/G10 通过（fixture 产出应符合 claim/warrant/rebuttal 要求）

### Real sample smoke（联网、烧 LLM）

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input /tmp/BV1B9T36nEvL_fetch_all.json \
  --output /tmp/BV1B9T36nEvL_claim_first_report.md \
  --writer-provider cli \
  --depth-profile claim-first-full \
  --fail-on-fallback-warning \
  --section-qa-gate \
  --claim-qa-gate \
  --json
```

预期：

- §3/§4/§7 明确体现主张、证据、推理许可、边界/反证、行动项
- 无 fallback warning（`--fail-on-fallback-warning` 会在 writer 失败时 fail）
- 真实 LLM 产出通过 D6-D8 QA

---

## 风险与缓解

| 风险 | 缓解措施 |
|:---|:---|
| 重 prompt 增加 fallback | 保留 fixture gate；real smoke 必须 `--fail-on-fallback-warning`；继续用 `_CachingWriterProvider` |
| claim gate 误伤结构章节 | D6-D8 默认只作用 §3/§4/§7；§1/§5 保持 exemptions |
| 评论/弹幕误作事实 | audit 规则显性：comments/danmaku 只能是 audience signal，不能直接成为 factual claim 的证据 |
| 破坏旧 CLI | `--depth-profile` 默认 `standard`，`--claim-first` opt-in；完全向后兼容 |
| `DraftReport` 字段扩展破坏序列化 | 新增字段默认空，并提供 `claim_bundle_to_dict()`；旧代码不调用新函数不受影响 |
| 短视频被强行注水 | 保留 `ReportPlan.mode` full/condensed 自适应；`claim-first-full` 只在用户显式选择时启用 |
| 真实样片文件缺失 | real smoke 只做手动 release checklist，不要求自动化运行 |

---

## 实施顺序

1. **Tests only**：新增 RED tests 和 fixtures（4 个测试文件，≥24 个测试）
2. **Claim pure functions**：实现 `Claim` / `ClaimBundle` / extract/synthesize/audit
3. **Writer integration**：扩展 `WriterSectionContext`、prompt、validation
4. **Gates**：扩展 Section QA 与 `verify_report.py`
5. **CLI surface**：扩展 `run_quality_gate.py` / `generate_report.py`
6. **Docs**：同步 README / SKILL / reference（本文档）

每步完成后跑 full suite：

```bash
PYTHONPATH=scripts pytest -q tests --ignore=tests/test_asr_config.py
```

---

## 验收标准

- [x] 新增测试 ≥20，先 RED 后 GREEN
- [ ] `pytest -q tests --ignore=tests/test_asr_config.py` 通过
- [ ] `release_gate.py` 通过
- [ ] `verify_report.py --depth full --claim-first` 可检查 G1/G3/G4/G5/G7 + G8/G9/G10
- [ ] `writer-provider none` 仍不能绕过 publish gate
- [ ] real sample `cli` smoke 无 fallback warning
- [ ] §3/§4/§7 明确体现主张、证据、推理许可、边界/反证、行动项

---

## 参考文献

### 学术与理论依据

1. **Toulmin Argumentation Model**
   - 六要素：claim / grounds / warrant / backing / qualifier / rebuttal
   - 来源：Purdue OWL, SJSU Writing Center, Nature Humanities & Social Sciences Communications
   - URL: https://owl.purdue.edu/owl/general_writing/academic_writing/historical_perspectives_on_argumentation/toulmin_argument.html
   - URL: https://www.nature.com/articles/s41599-024-03151-w

2. **Argument Mining 数据集与任务**
   - IAM (Integrated Argument Mining) 数据集：约 70k 句子，标注 claim/stance/evidence 等
   - URL: https://aclanthology.org/2022.acl-long.162/

3. **SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection**
   - arXiv: 2303.08896
   - URL: https://arxiv.org/abs/2303.08896
   - GitHub: https://github.com/potsawee/selfcheckgpt

4. **RARR: Researching and Revising What Language Models Say**
   - arXiv: 2210.08726
   - URL: https://arxiv.org/abs/2210.08726

5. **FActScore: Fine-grained Atomic Evaluation of Factual Precision**
   - GitHub: https://github.com/shmsw25/FActScore

6. **Google DeepMind SAFE (Search-Augmented Factuality Evaluator)**
   - arXiv: 2403.18802
   - GitHub: https://github.com/google-deepmind/long-form-factuality

### 开源实现参考

1. **arguebuf / ArgueMapper**
   - GitHub: https://github.com/recap-utr/arguebuf
   - 语言：Python / TypeScript
   - 用途：结构化 argument graph（AIF 格式），Protocol Buffers 编码

2. **ClaimBuster**
   - GitHub: https://github.com/utaresearch/claimbuster-spotter
   - 语言：Python/PyTorch
   - 用途：识别"值得核查的事实性主张"

3. **Argdown**
   - GitHub: https://github.com/argdown/argdown
   - 语言：TypeScript
   - 用途：轻量级 argumentation markdown 语法，生成 argument map

### 设计原则（来自外部证据的综合）

1. **原子化**：先把文本拆成原子事实/claim，再综合。SelfCheckGPT + FActScore + SAFE 都支持这一路径。
2. **证据优先**：每个 claim 必须绑定 evidence pointer；没有证据的 claim 降级或删除。
3. **审计单向**：只能 keep / downgrade / drop，不能 raise confidence。RARR 的 post-edit ≠ ours 保留输出，ours 只标记 unsupported。
4. **可解释性**：Toulmin 六要素天然适合作为 claim 的字段；Argdown 可作为可视化中间格式。
5. **分阶段验证**：extract → synthesize → audit → render，每阶段都有明确输出和 gate。
6. **避免幻觉增强**：审计阶段不能调用 LLM 来"补充"证据；任何补充证据必须来自 transcript/comments/danmaku 或外部搜索层（Phase C 以后）。

---

## 版本记录

- **2026-07-05**: 初版，定义 Depth Profile / Claim-First 架构 / D6-D8 / G8-G10
