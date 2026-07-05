# bilibili-video-analyzer

Bilibili / YouTube video analysis engine for producing Obsidian-ready deep reports with transcript evidence, comments/danmaku context, writer validation, and release quality gates.

## Quality-first pipeline (active roadmap)

After the P0/P1 skeleton guard and DraftReport boundary landed, the strategy pivoted from "fill every section with deterministic extractors" to **"build a section-level content quality gate first, then make every writer pass it."**

Current quality layers:

```text
EvidenceBundle → DraftSection writer → Section QA gate → DraftReport preview → PublishableReport
```

Delivered milestones:

- Phase 1: `evaluate_draft_section_quality()` — see `references/content-engine-section-qa-gate-phase1-20260703.md`.
- Phase 2: `assemble_draft_report_slice()` now auto-attaches `DraftReport.qa_results`; P0 skeleton blockers are kept out of `draft_sections`, while P1/P2 issues stay inspectable with warnings — see `references/content-engine-section-qa-gate-phase2-20260704.md`.
- Phase 3: `report_markdown()` and `run_quality_gate.py --json` now expose JSON-able `section_qa` metadata without rendering it into Markdown or changing pass/fail logic; provider responses are cached to avoid double LLM calls — see `references/content-engine-section-qa-gate-phase3-20260704.md`.
- Phase 4: §1 and §5 have dimension exemptions (not-mechanical + insight-density) so structural table/blockquote sections don't false-flag; `--section-qa-gate` flag enables opt-in P0 blocker gating — see `references/content-engine-section-qa-gate-phase4-20260705.md`.


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
It is an **engineering gate**, not a publishability guarantee for Obsidian notes.

## Publishable Obsidian gate

Pipeline artifact boundary:

```text
AnalysisInput → analyze_video() → DraftReport → debug Markdown → publish_markdown() → PublishedMarkdown
```

`render_markdown()` / `render_debug_markdown()` return debug/legacy Markdown strings. They are useful for engineering gates and inspection, but not publishable by themselves.

`DraftReport.draft_sections` is the current seam for written-but-not-yet-publishable section bodies. Today it has deterministic slices for §1 logic-chain tables, §5 short highlights, and §6 knowledge graph extraction via `assemble_draft_report_slice()`. When an explicit provider is passed, the same assembler can also route validated existing §3/§4/§7 LLM writer output into `draft_sections`; it still returns a non-publishable `DraftReport`, not `PublishedMarkdown`.

Use `render_draft_markdown(draft)` for human/CI preview only. It overlays `draft_sections` onto the plan while keeping unfinished sections as skeleton, and emits `publishable: false`; it is not a formal note writer.

Before saving a generated report as a formal `B站笔记_*.md`, run the stricter publish gate:

```bash
PYTHONPATH=scripts python3 scripts/verify_publishable_report.py /path/to/report.md
```

Or opt into it from the quality harness:

```bash
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture \
  --fail-on-fallback-warning \
  --publishable
```

Expected behavior:

- historical high-quality human-readable notes should pass;
- skeleton/debug reports fail;
- any generated formal `B站笔记_*.md` output is blocked if this gate fails.

## Real sample smoke

Use real sample smoke only when validating model-backed writer behavior before a release or after writer/prompt changes:

```bash
cd shared/bilibili-video-analyzer
PYTHONPATH=scripts python3 scripts/release_gate.py \
  --real-sample /tmp/BV1B9T36nEvL_fetch_all.json \
  --real-writer-provider cli
```

Real sample mode is opt-in because it may spend time/tokens. It fails if §3/§4/§7 writer output silently falls back to skeleton.

## Depth Profiles & Claim-First Architecture

### 深度分析模式（Depth Profile）

从 v2.7 起支持三档分析深度：

| 档位 | 说明 | 适用场景 |
|:---|:---|:---|
| **standard** | 默认模式，保留 v2.6 行为：确定性 extractor（§1/§5/§6）+ LLM writer（§3/§4/§7） | 常规分析，快速产出 |
| **v24-full** | 恢复 v2.4 深度分析框架：7 步推理链、Depth Quality Gates、8-section 内容资产，但不走 claim-first | 需要传统深度但无需 claim 审计的场景 |
| **claim-first-full** | 最严格模式：extract → synthesize → audit → render 的可测中间层，Claim/Insight/ClaimBundle 结构，D6-D8 QA gates + G8-G10 verify gates | 政策/新闻/技术解读类视频，需要证据溯源与 warrant 显性化的场景 |

选择方式：

```bash
# 常规分析（默认）
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli

# v2.4 深度框架
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli \
  --depth-profile v24-full

# Claim-first 全链路（含 claim 审计）
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli \
  --depth-profile claim-first-full
```

### Claim-First 架构

针对政策/新闻/技术解读类视频，`claim-first-full` 模式引入了如下流程：

```text
Evidence → extract_claims() → Claim[] → synthesize_insights() → Insight[]
  ↓                                ↓
  audit_claims()                   assign to §3/§4/§7
  ↓                                ↓
  ClaimBundle                      render with claim_context
```

核心数据结构：

- **Claim**: 单个可验证主张，含 `text`/`confidence`/`evidence_pointer`/`warrant`/`rebuttal`/`category`
- **Insight**: 从 Claim 合成的洞察，分配到 §3（核心洞察）、§4（Deep Dive）或 §7（行动项）
- **ClaimBundle**: 包含原始 claims、audit 后的 kept/downgraded/dropped、以及 insights

Claim 审计规则：

- **只能降级/删除，不能提高 confidence**（keep / downgrade / drop）
- 评论/弹幕数据不得升格为"事实性证据"，仅作 audience signal
- 每个 claim 必须绑定 `evidence_pointer`（transcript segment / metadata / external source）

质量闸强化：

- **Section QA D6-D8**（仅作用 §3/§4/§7）：
  - D6 `warrant-present`：推理许可显性
  - D7 `rebuttal-or-boundary`：边界/反证显性
  - D8 `actionability`：行动性
- **Verify G8-G10**（`--claim-first` opt-in）：
  - G8：§3 洞察含 claim/evidence/warrant/boundary
  - G9：§4 模块含显性/隐性/元叙事结构
  - G10：§7 行动项含证据引用或 claim id

启用 claim QA gate（P0 blocker）：

```bash
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

静态验证（verify）：

```bash
PYTHONPATH=scripts python3 scripts/verify_report.py \
  /tmp/depth_claim_quality_gate_report.md \
  --depth full \
  --claim-first \
  --json
```

详见 `references/content-engine-depth-claim-first-20260705.md`。

## Core commands

```bash
# Generate a report from fetch_all JSON
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli \
  --output /tmp/BVxxxx_report.md

# 带深度档位 + claim 质量门
PYTHONPATH=scripts python3 scripts/generate_report.py \
  --input /tmp/BVxxxx_fetch_all.json \
  --writer-provider cli \
  --depth-profile claim-first-full \
  --output /tmp/BVxxxx_report.md

# Verify report structural depth gates
PYTHONPATH=scripts python3 scripts/verify_report.py /tmp/BVxxxx_report.md

# Verify with claim-first gates
PYTHONPATH=scripts python3 scripts/verify_report.py /tmp/BVxxxx_report.md \
  --depth full \
  --claim-first

# Deterministic quality gate only
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/p2e_fetch_all.json \
  --writer-provider fixture \
  --fail-on-fallback-warning

# Quality gate with claim-first full pipeline
PYTHONPATH=scripts python3 scripts/run_quality_gate.py \
  --input tests/fixtures/depth_claim_fetch_all.json \
  --writer-provider fixture \
  --depth-profile claim-first-full \
  --section-qa-gate \
  --claim-qa-gate \
  --fail-on-fallback-warning
```

## Notes

- Formal Obsidian reports require transcript evidence. If all subtitle/ASR paths fail, output a clearly-labeled pre-analysis only.
- Final Obsidian save should keep one user-facing note per video; do not preserve intermediate drafts/transcripts unless explicitly requested.
- Use `terminal cp` for Obsidian vault saves, then verify with `ls`, `wc -c`, `verify_report.py`, and coherence checks.
