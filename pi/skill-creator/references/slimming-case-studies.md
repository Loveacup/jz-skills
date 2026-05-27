# Slimming Case Studies — Real Examples from jz-skills

## strategic-insight-longform: 513 → 130 lines (−75%)

**Problem**: 16-agent pipeline with Claude Code TeamCreate/TaskCreate pseudo-code (~220 lines), verbose agent roster table, config reference.

**What moved to references**:
- Full dispatch pipeline → `references/agent-pipeline.md`
- 16-agent roster → `references/agent-roster.md`

**What stayed in SKILL.md**: Hermes compatibility layer, 3-mode table, high-level architecture diagram, knowledge enhancement logic, output quality specs, learning system summary.

**Score**: 513 lines (❌) → 130 lines (✅). Red Flags + decision tree + verification checklist all added.

## voice-to-markdown-workflow: 349 → 133 lines (−62%)

**Problem**: 8-phase execution DAG with ASCII diagrams, per-phase detail, agent dispatch instructions.

**What moved to references**:
- Full execution flow with ASCII → `references/execution-flow.md`

**What stayed**: 8 core rules, high-level flow summary, scene routing table, verification gate logic, script reference, output strategy.

**Score**: 349 lines (❌) → 133 lines (✅). Red Flags + decision tree + verification checklist all added.

## xhs-crawler: 813 → 124 lines (−85%)

**Problem**: Massive catch-all document with 3 extraction modes, data integrity standards, script reference, P0 constraints, execution checklist, privacy rules, FAQ, changelog.

**What moved to references**: CloakBrowser mode details, CDP fallback, data integrity standards, architecture overview.

**What stayed**: 3-mode overview, Red Flags, decision tree, P0 constraints (7 mandatory sections + citation standards + privacy red lines), verification checklist.

**Score**: 813 lines (❌) → 124 lines (✅). Biggest relative reduction in jz-skills.

## auto-diary: 324 → 139 lines (−57%)

**Problem**: Duplicate workflow D (calendar backfill appeared twice), 7 version-history entries ("关键改进"), verbose troubleshooting section.

**What moved to references**: Version history → `references/changelog.md`.

**What stayed**: 4 workflows (A/B/C/D), tech stack, config drift warning, troubleshooting table, verification checklist.

**Score**: 324 lines (⚠️) → 139 lines (✅). Removed duplicate section, slimmed troubleshooting to table.

## bilibili-video-analyzer: 235 → 122 lines (−48%)

**Problem**: FAQ section (6 Q&A items), changelog entries, verbose script descriptions.

**What moved to references**: FAQ and changelog → `references/changelog.md`.

**What stayed**: 4-phase flow, 8-section output spec, script reference table, known limitations, verification checklist.

**Score**: 235 lines (✅ already compliant) → 122 lines. Light touch — just added Red Flags + decision tree + verification checklist.

## Key Pattern

The universal slimming pattern:
1. Identify the "engine" — what the skill must include to function (overview, core workflow, critical constraints)
2. Move everything else to `references/` with one-line pointers
3. Add compliance elements (Red Flags, decision tree, verification checklist)
4. Target: keep the engine under 150 lines
