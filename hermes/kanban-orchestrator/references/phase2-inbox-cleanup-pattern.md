# Phase 2 Inbox Cleanup Pattern — Two-CC-Phase + Adversarial Review

Production-proven pattern from D19-D20 (2026-06-12): Kanban + CC lane end-to-end Inbox classification and execution, gated by adversarial review at both stages.

## When to use

- Obsidian Inbox has 15+ loose notes needing classification, frontmatter fixes, and moves
- You want adversarial review (D17 Gap 2) at BOTH classification and execution stages
- The task benefits from CC's deep reading but Hermes/Kanban owns lifecycle and verification

## Pattern: four Kanban cards, two adversarial gates

```
Card A (default, claude-code/tmux): Classification
  │  CC reads Inbox → produces structured report
  │  Output: /tmp/.../report.md
  ▼
Card B (regent, adversarial review): Classification review
  │  metadata.review.adversarial_prompt present
  │  Checks: classification quality, missed files, frontmatter diagnosis accuracy
  │  Decision: pass → proceed / request changes → fix report
  ▼
Card C (default, claude-code/tmux): Execution
  │  CC reads report + CLAUDE.md → executes moves/renames/frontmatter fixes
  │  Output: /tmp/.../cleanup-log.md
  ▼
Card D (regent, adversarial review): Execution review
  │  metadata.review.adversarial_prompt present
  │  Checks: files in correct zones, frontmatter valid, wikilinks intact, no forbidden paths
  │  Decision: pass / request changes / reject
```

## Card A: Classification

**Skills:** `claude-code`, `kanban-orchestrator`, `obsidian`

**Task for CC:**
- List all files in `00-Inbox/`
- For each: read content, classify by theme, suggest target zone, diagnose frontmatter
- Output structured report with per-file: path, size, summary, classification, target zone, rename suggestion, frontmatter issues, tag suggestions
- Skip: binary files, database files, files needing human judgment (flag explicitly)

**Substrate:** `claude-code/tmux` (mature, good for deep reading)

**Forbidden:** No writes to Obsidian vault. Read-only.

## Card B: Classification adversarial review

**Skills:** `claude-code`, `kanban-orchestrator`

**Adversarial prompt:**
```
Before approving, list 3 specific ways this classification could be wrong:
(1) misclassified a note's content type due to ambiguous domain,
(2) suggested wrong target zone because vault structure evolved,
(3) missed frontmatter issues invisible to regex.
Then explain why each is or isn't applicable.
```

**Parent:** Card A (must be `done` / `implementation-ready-for-review`)

## Card C: Execution

**Skills:** `claude-code`, `kanban-orchestrator`, `obsidian`

**Task for CC:**
- Read classification report from Card A
- Read CLAUDE.md for vault conventions (type enum, tag rules, naming)
- For each classified file: move to target zone, fix frontmatter, rename per conventions
- Write cleanup log with per-file before/after
- Skip: files flagged for human judgment, binary files

**Allowed paths:** Target zones within vault
**Forbidden:** 99-System/, 88-审计/, deletes (moves/renames only)

## Card D: Execution adversarial review

**Skills:** `claude-code`, `kanban-orchestrator`

**Adversarial prompt:**
```
Before approving, list 3 specific ways this cleanup could have gone wrong:
(1) files moved to wrong target zone due to ambiguous classification,
(2) frontmatter fix broke YAML validity,
(3) renamed file broke existing wikilinks.
Then explain why each is or isn't applicable.
```

**Parent:** Card C (must be `done` / `implementation-ready-for-review`)

## Real-world evidence (D19-D20, 2026-06-12)

- 22 Inbox notes classified (report 336 lines, 19.5KB)
- 19 files executed (moved, frontmatter fixed, renamed)
- 3 files skipped (bookmark indexes, human judgment)
- Both adversarial reviews PASSED
- CC Opus 4.8, effort high, ~7min per CC phase
- 5 📡 status blocks per CC run
- Additional finding: CLAUDE.md type enum was incomplete (fixed separately)

## Pitfalls

- **CC overthinks the classification.** If token count grows past 10k without output, interrupt with: "Write the report now. Include per-file entries. Do not inspect more files."
- **Frontmatter fixes need CLAUDE.md in CC context.** Always pass CLAUDE.md path or key excerpts in the card body.
- **Inbox may have non-md files.** Filter explicitly in task scope.
- **Wikilinks break on rename without aliases.** CC must preserve old filename in `aliases` frontmatter field when renaming.
