# Scratch GC Recovery — 2026-05-27

## What Happened

Three parallel search lanes for 早新闻 2026-05-27:
- 路A (hanlinyuan): 28条中国新闻 → scratch workspace t_77fa4151
- 路B (hanlinyuan): 26条美国/国际新闻 → scratch workspace t_59d81973
- 路C (jiangzuojian): 市场/科技数据 → scratch workspace t_d6ea5a42

Assembly card (t_a0b6f58e) was blocked waiting for all three lanes. By the time it was unblocked, scratch GC had wiped all three workspaces — empty directories, zero files.

## Root Cause

Scratch workspaces are garbage-collected when tasks are archived/done. The assembly card was blocked (waiting for upstream), which created a time window where all three upstream tasks were `done` (scratch vulnerable to GC) but the assembly card hadn't read their output yet.

## Fix Applied

1. All future search lane task bodies must explicitly state: "Write output to persistent path: ~/.hermes/workspaces/morning-news-YYYYMMDD/"
2. Assembly card bodies must reference persistent paths, not scratch task IDs
3. If GC has already occurred: fall back to reading `kanban_show` → `latest_summary` from each search card as a recovery path

## Recovery Pattern (When GC Has Already Happened)

```bash
# Archive broken assembly/render/audit/final cards
hermes kanban archive <broken_card_ids>

# Create new assembly card that reads from Kanban summaries
hermes kanban create "早新闻·汇编v2(从Kanban读)" --assignee hanlinyuan --body '
Use kanban_show to read latest_summary from:
- t_<search_lane_A> (路A·中国)
- t_<search_lane_B> (路B·美国国际)
- t_<search_lane_C> (路C·市场科技)
Assemble and write to persistent path.'
```

## Prevention Checklist

- [ ] All search lane bodies contain explicit persistent workspace path
- [ ] Assembly card references persistent paths, not scratch task IDs
- [ ] If assembly is blocked >2 min, suspect GC — proactively check search workspaces
- [ ] Have the Kanban-summary fallback pattern ready as recovery
