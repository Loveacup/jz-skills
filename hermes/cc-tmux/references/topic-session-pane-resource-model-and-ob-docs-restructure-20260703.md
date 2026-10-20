# Topic-Session-Pane resource model + OB docs restructure lessons (2026-07-03)

## Trigger

Use when planning or documenting cc-tmux session/pane lifecycle, same-topic reuse, multi-CC collaboration, or restructuring the cc-tmux Obsidian technical docs library.

## Resource model decision

Adopt **Topic continuity + Session isolation + Pane presentation**:

- Hermes topic owns user-facing continuity.
- Managed tmux session owns one CC worker / Claude process lifecycle.
- tmux pane/window is presentation/support/scratch only, not a managed worker identity.
- Default shape: **1 topic → 1 primary tmux session + N child tmux sessions**.

## Reuse / fork / clear rules

| Scenario | Rule |
|---|---|
| Same topic, sequential follow-up, same scope, primary idle/fresh | Reuse primary session |
| Same topic but context is long/dirty | `/clear` first, then reuse primary |
| Same topic, parallel review/audit/second CC | Fork a child tmux session, do not use another CC pane in same session |
| repo/worktree/branch/write-scope/danger-class changes | Fork child/new session |
| stale/resurrected/uncertain worker | Do not reuse; classify suspected / review manually |

Do **not** put multiple managed Claude workers in the same tmux session under the current cc-tmux status-key scheme: `cc-status-writer.sh` keys status/heartbeat/turn-done/output by `CC_TMUX_SESSION`, so same-session multi-CC panes collide.

## Topic map evolution

Current implementation is `topic -> session` 1:1 (R9b v1.22 baseline). Target schema should evolve to:

```json
{
  "topic_id": {
    "primary": {"session": "...", "role": "primary", "reuse_state": "idle"},
    "children": [
      {"session": "...", "role": "reviewer", "fork_reason": "parallel_review"}
    ]
  }
}
```

This registry is ownership/routing metadata only. Do not rebuild a lifecycle event bus; hook/status files remain state authority.

## OB technical docs restructuring workflow

For cc-tmux OB docs (`20-Areas/20_技术项目/cc-tmux Skill 与 Agent 协作`):

1. Keep existing taxonomy unless there is strong evidence: `10_cc-tmux核心/`, `20_Agent协作/`, `30_审计/`, `40_相关项目/`, root README/AGENTS.
2. Authority chain:
   - `README.md` = MoC/navigation
   - `AGENTS.md` = directory work contract
   - `10_cc-tmux核心/CC-TMUX核心需求.md` = PRD authority
   - `10_cc-tmux核心/CC-TMUX核心构架.md` = architecture authority
   - resource model note = current Topic/Session/Pane decision
   - code repo `SKILL.md`/`AGENTS.md` = implementation authority
3. Prefer moves/archives, not deletion. Preserve filenames so Obsidian wikilinks continue to resolve.
4. Mark old collaboration/incident notes with historical banners when their old “always new session”/manual scan advice conflicts with current managed reuse/fork policy.
5. Duplicate content: keep canonical in `10_cc-tmux核心/`; move duplicate snapshot to `30_审计/` with a warning banner and verify body hash after excluding the banner.

## Verification checklist

- PRD and architecture agree on current implemented baseline vs target model.
- No authority doc implies a second managed CC can run as another pane/window in the same tmux session.
- `README.md` navigation matches actual file locations.
- All edited markdown has frontmatter.
- Use qmd refresh after bulk moves:
  - `HOME=/Users/alexcai qmd update -c alexcai-vault`
  - `HOME=/Users/alexcai qmd embed -c alexcai-vault`
  - Verify a query for the new resource model returns the new note as a top hit.

## CC quota / fallback pattern

If CC hits a quota/plan prompt mid-task:

1. Stop any wait process.
2. Capture pane tail to confirm the prompt/state.
3. Kill only the specific CC tmux session (`tmux kill-session -t <session>`), not the tmux server.
4. Hand the same bounded execution package to Codex with “continue from current filesystem state”.
5. Run OMP audit and Hermes final verification after Codex completes.
