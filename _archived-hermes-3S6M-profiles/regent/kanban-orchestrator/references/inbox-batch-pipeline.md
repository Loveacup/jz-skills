# Obsidian Inbox Batch Processing Pipeline

Complete example from the 2026-05-18 session: 88 inbox .md files → 55 auto-archived, 8 staged for human review.

## Task Graph

```
T1 planner     (classify 88 files)
  ↓
T2 reviewer    (review classification, flag staging)
  ↓
T3a-d engineer (4 batches × ~22 each, with 将作监)
  ↓
T4 auditor     (verify YAML/naming/placement)
  ↓
T5 archivist   (qmd re-index + execution record)
```

## What Went Wrong

T3a, T3b, T3c all hit `Iteration budget exhausted`:
- T3a (90/90): processed 14/22, left Python script in workspace for remaining 8
- T3b (45/45): **completed all 22**, left detailed comment, couldn't call kanban_complete
- T3c (90/90): no output at all
- T3d: succeeded

Root cause: engineer monitoring Claude Code via tmux polling consumed too many iterations. 22 files × monitoring loop = budget exhausted.

## Recovery

| Task | Action | Rationale |
|------|--------|-----------|
| T3b | `unblock` → `dispatch` | Work done, just needs kanban_complete |
| T3a | `archive` | Partial state (script unrun) |
| T3c | `archive` | No output |
| T3e+f | Created (11 each, no 将作监) | Smaller batch, direct processing |

T3e+f both succeeded in ~5 minutes.

## Key Design Decisions

1. **Hybrid A+B**: Reviewer marks each file "auto-archive" or "needs-review→Staging". Emperor approved this before task creation.
2. **Batch size 11**: Safe for engineer direct processing. 22 with 将作监 monitoring = risky.
3. **将作监 not used**: YAML + rename + move is mechanical, not analytical. Claude Code adds no value here.
4. **Emperor decision autonomy**: Emperor prefers orchestrator to make recovery decisions when context is clear.

## Task Body Template (engineer batch)

```
处理收件箱剩余 N 篇中的前 M 篇。直接处理，不用将作监。

步骤：
1. 从父任务 workspace 读取分类表
2. 对每篇：读取全文 → 补YAML frontmatter → 重命名 → 审阅=Staging否则目标区
3. kanban_complete: 处理数/Staging数/各区分布/失败数

注意：不要监控 Claude Code，直接逐文件处理。每篇 3-5 次工具调用。
```

## Verification

After pipeline completes:
- `ls $VAULT/00-Inbox/*.md` should return empty
- `ls $VAULT/01-Staging/*.md` lists human-review files
- Auditor checks: YAML completeness, naming compliance, tag validity
- Archivist re-indexes qmd
