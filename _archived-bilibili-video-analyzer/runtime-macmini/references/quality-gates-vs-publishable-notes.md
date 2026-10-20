# Engineering gates vs publishable Obsidian notes

## Trigger

Use this reference whenever a generated Bilibili/YouTube report passes mechanical gates but the user is judging whether it is good enough for Obsidian.

This came from the BV1zrTq6sEPB failure: `verify_report.py`, coherence, and OMP all passed, but the report was unreadable because skeleton/debug output and long transcript dumps were treated as a final note.

## Durable lesson

Do not equate these:

```text
fetch succeeds + ASR succeeds + verify_report passes + coherence passes
```

with this:

```text
human-readable, publishable Obsidian video note
```

The first is an engineering gate. The second needs a publishable gate and human-eye QA.

## Minimum publishability checks

Before saving a formal `B站笔记_*.md` or anything under `30-Resources/60_视频笔记/`:

1. Run the structural gate:
   ```bash
   PYTHONPATH=scripts python3 scripts/verify_report.py <report.md>
   ```
2. Run coherence:
   ```python
   from video_analysis_engine import check_report_coherence
   result = check_report_coherence(markdown)
   assert result.passed
   ```
3. Run the publish gate:
   ```bash
   PYTHONPATH=scripts python3 scripts/verify_publishable_report.py <report.md>
   ```
4. Do human-eye QA before claiming it is usable:
   - no `_骨架占位` / `Skeleton` residue;
   - no §1 raw transcript dump masquerading as logic chain;
   - §1 has table / Mermaid / timeline structure;
   - §5 quotes are short, selected, and interpreted, not 5-minute ASR chunks;
   - metadata counts match `fetch_all` source data;
   - ASR noise terms do not enter titles, insights, or high-value quotes;
   - source/evidence markers are readable to the user, not only machine-oriented `[E#]` debris.

## Artifact boundary

Keep the mental model explicit:

```text
AnalysisInput
→ analyze_video()
→ DraftReport              # non-publishable; may contain skeleton/debug evidence
→ render_debug_markdown()  # engineering/debug Markdown string
→ publish_markdown()       # publish gate promotion
→ PublishedMarkdown        # can be saved as formal note
```

`render_markdown()` / `render_debug_markdown()` output is not publishable by itself.

## Response discipline when quality is challenged

If Alex says the quality is bad, do not defend gates or OMP. Immediately:

1. acknowledge the miss;
2. remove the bad note from OB if it was written, preserving evidence under `/tmp`;
3. read the actual Markdown with human QA criteria;
4. identify whether the failure is data, writer, renderer, or gate;
5. update this skill/reference if the gate missed a new class of badness.

## What not to save as a rule

Do not record transient provider failures or one-off OMP formatting failures as durable tool facts. Capture only the reusable pattern: self-reported or mechanical pass is not enough for publishable content; verify the actual artifact.