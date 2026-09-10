# Gates G1–G10 — what `verify_minutes.py` checks

Fail-closed: any FAIL → exit 1 → the note is not deliverable. The script proves structure and pointer integrity, not truth; human QA (SKILL.md checklist) still runs.

| Gate | Check | Threshold (standard) | Deep delta |
|---|---|---|---|
| G1 frontmatter | YAML block present with `type`, `tags` (prefixed `type/`…), `participants`, `meeting_date`, `related` (≥ 3 wikilinks) | all present | — |
| G2 参会表 | Section 会议概况 contains a participants table with ≥ 2 rows having 姓名 + 方/角色 | ≥ 2 | — |
| G3 执行摘要 | Section 执行摘要 exists; prose ≥ 120 chars; contains `[!decision]` callout | present | — |
| G4 决策四要素 | Section 决策记录 table: every row has ≥ 6 non-empty cells incl. global ID `\d{2}W\d{2}-D\d{2}` and a `[hh:mm:ss]` evidence; ≥ 1 row | 100% rows | — |
| G5 行动项 | Section 行动项 table: every row has ID `\d{2}W\d{2}-A\d{2}`, 责任人 non-empty, 节点 matching a date/week/条件 (not 待定/TBD), evidence `[hh:mm:ss]` | 100% rows | — |
| G6 原话引用 | Count of `> [!quote]` callouts each followed by `[hh:mm:ss]` | ≥ max(3, 3 × hours) | ≥ max(5, 4 × hours) |
| G7 外部依据 | Section 外部情报与决策依据 exists with ≥ 1 table row containing `http` **or** the literal "未检索到" **or** "本期无外部搜索触发项" | present | ≥ 1 URL row |
| G8 订正表 | Appendix 订正表 table with ≥ 1 row **or** the literal "本期无新增订正" | present | — |
| G9 字数下限 | Body chars (frontmatter + code fences excluded) ≥ floor(transcript_chars) per writing-spec §6; without `--transcript`, floor = 1500 | see table | ×1.25 |
| G10 无占位符/无倾倒 | No `[待填]`, `TODO`, `TBD`, `[人名]`, `XXX`; no 200-char window of the note appearing verbatim in the transcript (dump check, only with `--transcript`); no paragraph > 1200 chars | 0 hits | — |

## Interpreting output

```text
G1 frontmatter            PASS
G4 决策四要素             FAIL  row 3 missing 拍板人; row 5 evidence not [hh:mm:ss]
...
=== 8 PASS / 2 FAIL → exit 1 ===
```

Fix only the listed rows; rerun. Two failed rounds → escalate to the user with the gate output, do not lower thresholds.

## Not covered (needs human QA)

- Whether a decision was really made (复述确认) vs. the writer promoting an idea.
- Whether quotes are the *定调* ones.
- Narrative quality, cross-section contradictions, translation of客户 jargon.
