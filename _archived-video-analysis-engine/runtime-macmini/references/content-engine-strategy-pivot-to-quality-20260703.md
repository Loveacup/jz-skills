# 路线切换：从架构安全优先 → 内容质量优先（2026-07-03）

## Decision context

自 P0/P1 publishable gate 止血后，管线已具备两样东西：

1. 架构安全层
  - publish gate 拦截 skeleton / 超长行 / raw transcript / appendix-only
  - DraftReport ↔ PublishedMarkdown 两种不同 artifact
  - `render_draft_markdown(draft)` 非发布预览面

2. 确定性草案层（D1/D3/D4/D5/D6/D7）
  - §1 logic chain table
  - §3/§4/§7 LLM writer outputs（显式 provider 才走）
  - §5 curated short highlights with truncation
  - §6 deterministic concept/relation/application extractor

但在补充这些切片的过程中暴露出一个新问题：

**确定性 extractor 虽然安全，但对内容质量上限贡献有限。**

特别是：
- §6 只能识别预定义概念，不能发现新概念、不做语义推理
- §1 表格虽结构化，但表达偏机械
- 各节缺少统一的质量评判标准

## Pivot decision

**从“继续补确定性小 extractor 消除剩余 skeleton”切换为“先建节级内容质量闸门”。**

新路线：

```text
EvidenceBundle → DraftSection writer（确定性或 LLM）
              → Section QA gate      ← 核心新增
              → DraftReport preview
              → PublishableReport
```

不打 skelton-trimming 消耗战了。先做 `SectionQualityResult` / `evaluate_draft_section_quality()`，让每节产出有统一的质量度量：

| Gate | 检查 |
|---|---|
| evidence-grounded | 每个判断是否有证据引用 |
| not-mechanical | 是否只是表格/keyword 堆砌 |
| human-readable | 是否像人写给人看的段落 |
| insight-density | 是否有解释/因果/转折，而不只是摘录 |
| no-skeleton | 无占位/模板残留 |

之后无论用确定性 writer 还是 LLM writer，都可以过同一个 QA gate。

## Next commit scope (CC plan → I execute → OMP audit)

1. CC planning-only: Section QA gate interface + test plan
2. I implement: RED tests → GREEN implementation
3. OMP audit: 4-criterion pass/fail
4. Reference/OB backfill + commit/push
