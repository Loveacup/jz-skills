# P2-B2 Render Skeleton Triad Record (2026-06-30)

## Context

After P2-A (`ReportPlan` / `SectionSpec`) and P2-B1 (`EvidenceMap`), the next blocker was that `render_markdown()` still rendered the old four ad-hoc sections:

```text
## §1 基本信息
## §2 内容分析
## §3 评论分析
## §4 关键声明核查
```

`verify_report.py` only recognizes old framework headings in the exact format:

```text
## 1. ...
## 3. ...
## 4. ...
## 5. ...
## 7. ...
```

So P2-B2's goal was **not** to generate a full report. It was to build a plan-aware skeleton renderer that eliminates `section missing` failures and creates a bridge from `ReportPlan + EvidenceMap` to future full writing.

## Triad workflow

- Codex: planning-only execution package.
- CC/cc-tmux: bounded implementation in `cc-bili-p2b2`.
- OMP: independent audit.
- Hermes: diff review, real tests, runtime sync, OB writeback, GitHub push.

## Implementation boundary

Only these files were changed:

```text
scripts/video_analysis_engine.py
tests/test_render_markdown_plan.py
```

Do **not** expand this slice into full writing logic. P2-B2 is a skeleton bridge.

## Contract locked by tests

`render_markdown(report)` now:

1. If `report["report_plan"]["sections"]` exists, renders sections in `SectionSpec` order.
2. Uses exact heading format:

```text
## {section.id}. {section.title}
```

This includes the special decimal heading:

```text
## 2.5. 评论深度分析 (Comments Analysis)
```

3. Injects up to 3 `evidence_map.by_section[section_id]` candidates.
4. Evidence with URL renders as:

```markdown
> [2:30](https://www.bilibili.com/video/BVxxx?t=150) 原文片段  <!-- source=transcript reason=logic_candidate -->
```

5. Evidence without URL renders as:

```markdown
> comments证据：评论原文  <!-- source=comments reason=comment_signal -->
```

6. Gives `verify_report.py` minimum recognizable substructure:

```text
§3 → ### 💡 Skeleton Insight
§4 → ### 模块 1: Skeleton Module
§5 → blockquote evidence
§7 → ### 独特价值 / ### 局限与偏见 / ### 可行动项
```

7. If no `report_plan.sections` exists, falls back to legacy `report["sections"]` rendering.

## Verification meaning

The correct smoke result is:

```text
NO_SECTION_MISSING=1
overall=False
```

`overall=False` is expected because skeleton content does not satisfy G3/G4/G5/G7 depth thresholds. The acceptance criterion is only:

- G1/G3/G4/G5/G7 are found by `verify_report.evaluate(...)`.
- None of their `measured` values contains `section missing` or `缺失`.

Do not treat depth-gate failure as a P2-B2 failure.

## OMP audit pitfall from this slice

First OMP audit found the correct answer but wrapped JSON in markdown/code fences; `omp-monitor` rejected it as schema-invalid. Correct handling:

1. Do **not** accept schema-invalid OMP output.
2. Extract the useful finding only as diagnostic context.
3. Create a compact bundle under `/tmp/...-omp-compact-bundle.md`.
4. Re-run OMP with explicit `ONLY JSON, no markdown fences, no prose outside JSON`.
5. Accept only after `omp-monitor` reports valid `severity=pass` with evidence.

For this slice, the accepted OMP task was `omp-20260630-204838`.

## Commits / verification snapshot

Source repo commit:

```text
301ee6b feat(bilibili): render report plan skeleton
```

Verification at close:

```text
source repo: 54 passed
runtime skill: 68 passed
OMP: omp-20260630-204838 pass
```

## Next slice

P2-B3 should address `generate_report.py` transcript metadata fidelity:

```text
end / language / path / multi-P boundaries
```

Without that, future quote/citation rendering will lose source precision before it reaches `EvidenceMap`.
