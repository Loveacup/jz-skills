# GitHub Skill Consolidation (8→1) — Case Study

**Date:** 2026-05-27
**Source skills:** `github-auth`, `github-issues`, `github-pr-workflow`, `github-repo-management`, `github-code-review`, `github-code-explorer`, `codebase-inspection` (7 GitHub + 1 codebase)
**Result:** 1 `github` skill, 112-line main file, 16 references

## Problem

7 GitHub skills totaling ~1,713 lines, each duplicating:
- Auth detection (same 30-line block in every skill)
- `owner/repo` extraction from git remote
- `AUTH` variable setup

Agent had to decide *which* github skill to load — auth first, then the operational one. Cross-domain tasks (triage an issue then open a PR) required loading 2+ skills.

multi-profile governance risk: agents could load an ops skill (e.g., `github-issues`) without loading `github-auth`, causing silent 401 failures.

## Design Options Evaluated

### Option 1: Main file + references/ (SELECTED)
Main SKILL.md as dispatch layer: auth detection, decision tree, quick reference. Domain content in `references/`.

### Option 2: 3-4 independent skills
Auth separate from ops skills. Rejected: hidden auth dependency in multi-profile governance.

### Option 3: Single monolithic file
All ~1,500 lines in one SKILL.md. Rejected: >300 line compliance violation.

**Deciding factor:** Governance lens — in multi-profile dispatch, Option 1 guarantees every profile that loads `github` gets auth detection. Option 2 requires remembering to pair auth + ops, which fails silently.

## Architecture

```
github/SKILL.md                  (112 lines)
  ├── 🚨 Red Flags (top 10%)
  ├── 🔀 Decision tree (top 15-30%)   ← agent picks reference by task type
  ├── 🔐 Auth detection (shared)      ← ONE block, run once per session
  ├── 📋 Quick Reference (gh↔curl)    ← 12 most common operations
  └── ✅ Verification checklist (bottom)

references/
  ├── auth.md                  ← setup details (HTTPS/SSH/gh login)
  ├── issues.md                ← CRUD operations
  ├── pr-workflow.md           ← branch→commit→PR→CI→merge
  ├── repo-management.md       ← clone/create/fork/release/secrets
  ├── code-review.md           ← local + PR review
  ├── code-explorer.md         ← L1→L4 exploration
  ├── codebase-inspection.md   ← pygount LOC stats
  └── [+9 auxiliary references]
```

## Key Design Rules

1. **Shared state lives in main file, never in references.** Auth detection, env setup, API client init — write once, reference from everywhere. If a reference embedded its own auth block, it would drift from the other references over time.

2. **References declare prerequisites explicitly.** Every reference starts with: "Prerequisite: Run the auth detection block from main SKILL.md."

3. **Decision tree maps task → reference.** Agent loads 1 skill, follows the tree, loads 1 reference. No more "which of 7 GitHub skills do I need?"

4. **Main file is a dispatch layer, not a content dump.** If it has detailed instructions beyond 80-120 lines, move to references. The main file is the "which door" — references are the rooms.

## Compliance Scorecard

| Dimension | Score | Evidence |
|-----------|:-----:|----------|
| Progressive disclosure | 5 | 112-line main, 16 references |
| Anti-rationalization | 5 | 5 excuse-rebuttal pairs at top |
| Rule positioning | 5 | Tree at 15-30%, checklist at bottom |
| Description quality | 5 | Explicit triggers + do-not |
| Verification | 5 | 6 actionable items |
| Runtime invocation | 4 | Replaces well-triggered skills |
| Deployment | 3 | No multi-profile sync rules (deferred) |
| **Average** | **4.6** | |

## Migration Checklist

When consolidating N skills into 1 umbrella:

- [ ] Extract shared state blocks from all source skills → merge → place in main SKILL.md
- [ ] Build decision tree mapping task domain → reference file
- [ ] Move domain content to references/ (strip frontmatter, keep operational content)
- [ ] Add "Prerequisite" header to each reference pointing to shared setup in main
- [ ] Create quick reference table in main (12 most common ops, gh↔curl)
- [ ] Migrate templates/ and scripts/ to new umbrella directory
- [ ] Run 7-dim compliance scorecard
- [ ] Search ALL skills for `related_skills` to old skill names → update to new umbrella
- [ ] Search body text for old skill name mentions → update
- [ ] Delete old skill directories
- [ ] Verify new skill loads via `skill_view`

## Results

- 7→1 skill, 1,713→112 line main file
- Auth detection: 7 duplications → 1 shared block
- Agent cognitive load: "which github skill?" → "github" → pick reference
- multi-profile: hidden auth dependency eliminated
- 16 updated cross-references in 6 external skills
