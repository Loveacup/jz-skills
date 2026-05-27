# Blocked final-review + mirror-sync recovery pattern

Use this when a governed Kanban chain reaches final review but blocks on a narrow consistency issue between canonical documents and mirror/registry files.

## Trigger

- User asks for progress or complains a blocker was not handled.
- A final reviewer card is `blocked` after most upstream cards are `done`.
- The block reason is narrow and actionable, such as:
  - Obsidian document updated, but `~/.hermes/notes/...` mirror/registry not updated.
  - Skill/profile copy updated, but the intended default/regent copy is missing the same rule.
  - Audit approved one location but final review checked a second location and found drift.

## Required response

Do not merely report the blocked status. Inspect the blocker summary/comment, then immediately create a minimal recovery chain:

1. **Fix card** assigned to the correct executor (`archivist` for knowledge-base/notes sync, `engineer` for deterministic file edits, etc.).
2. **Review card** depending on the fix card, assigned to `reviewer`.
3. **Final-review closure card** depending on the review card, assigned to `reviewer`, to close the original chain and produce the user-facing conclusion.

The original blocked reviewer card remains as audit trail; do not unblock it unless the system specifically expects the same card to be retried.

## Fix-card body checklist

- Quote the exact blocked reason.
- Name the exact target file(s) and target text.
- Require minimal modification only.
- Require verification against both canonical and mirror paths.
- Require summary fields: `changed_files`, `verification`, `delivery_required=yes`.

## Progress-report wording

Keep it short:

- State the current blocker in one sentence.
- State the recovery chain IDs and which card is currently running.
- Make clear whether it is narrow sync work vs. broad rework.

Example:

> 主链到终复，但门下卡住一处镜像同步：Obsidian 已补，`~/.hermes/notes/agent-registry.md` 缺同条规则。已建恢复链 `fix → review → final`，当前 fix 正在运行；不是大面积返工。
