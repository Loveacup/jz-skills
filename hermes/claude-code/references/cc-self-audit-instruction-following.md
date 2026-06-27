# CC Self-Audit: Instruction-Following Optimization Pattern

> Captured from 2026-06-01 session: using CC's own discussion protocol + CQI plan to audit and optimize the claude-code skill itself.

## When to use

- User says "optimize/improve this skill's instruction following"
- A CQI plan exists with documented violation patterns
- The skill is long/complex and agent compliance is slipping

## Pattern (4 phases)

### Phase 1: Load context
1. Read the CQI plan (Obsidian or equivalent) — identify violation hotspots
2. Load the target skill + its common-pitfalls reference
3. Identify the specific symptoms: which rules are being violated most?

### Phase 2: Multi-round CC discussion
1. Start a fresh CC session at max effort
2. Feed: context file summarizing symptoms + CQI plan excerpts
3. Ask CC to read the full skill + references
4. Run the discussion protocol dogfood-style — CC follows its own rules while auditing them
5. Key decision to settle early: Gate Stamp yes/no (structural vs. lightweight fix)

### Phase 3: Grill-with-docs verification
- CC verifies claims against source documents before accepting premises
- "先查事实再接受主张" — verify CQI plan sections, violation logs, line numbers
- This catches mismatches (e.g., "第十节" reference that doesn't exist in repo)

### Phase 4: Executable spec output
- ≤5 bullets, each with: exact landing point (line numbers), line budget, new files list
- Subtraction accounting: what gets removed to make room for additions
- Net line count delta
- Decision: red lines (behavioral) vs Gate Stamp (technical pre-checks) split

## Key design insight

Violations fall into two categories requiring different treatment:

| Type | Cause | Treatment |
|------|-------|-----------|
| Agent actively skips ("nothing to report", "优化=让我改") | Rationalization | 🔴 Top red lines (behavioral discipline) |
| Technical trap (false-idle #24, auto-resume #27) | Agent wants to comply but gets tricked | 🚦 Gate Stamp (state verification) |

Mixing them dilutes red line salience. Split them.

## R3 executable spec template

Each bullet should specify:
- Landing point (exact line numbers in SKILL.md)
- Content description (≤15 lines per section)
- Subtraction: what existing content is removed/reduced to make room
- Net line delta
- File manifest: new files created, existing files modified

## Example: 2026-06-01 claude-code optimization

5 bullets produced:
1. Red-line constitution atop SKILL.md (2 rules + grading declaration)
2. 📡 hard binding (capture-pane MUST pair with report block)
3. Gate Stamp before execution (4 checkboxes)
4. Anti-rationalization micro-tables per red line
5. Self-correction protocol (immediate fix, not "next time")

Subtraction: effort routing → references/effort-routing.md (−74), occupancy dedup (−15) = net −36 lines.
