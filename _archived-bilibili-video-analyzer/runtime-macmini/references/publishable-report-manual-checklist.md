# Publishable Report Manual Checklist

`scripts/verify_publishable_report.py` does **not exist** in this repository. The publishable gate is performed manually by the agent before saving any formal `B站笔记_*.md` to Obsidian. Run this checklist after `verify_report.py` passes.

## Hard blockers (must all be false)

- [ ] Any `_骨架占位` or `Skeleton` residue in §0–§8.
- [ ] Any required section §0–§8 missing.
- [ ] Any line > 1000 characters (usually raw transcript dump).
- [ ] §1 logic chain has no table / Mermaid / timeline structure.
- [ ] Any §5 quote block > 300 characters.
- [ ] Core prose sections (§3/§4/§6/§7) are only blockquotes / tables / source appendix.
- [ ] `verify_report.py` passed but the note still reads like evidence scaffolding.

## Readability QA (must all be true)

- [ ] §1 is a structural overview, not a transcript retelling.
- [ ] §3 insights read like authored analysis, not bullet lists of transcript claims.
- [ ] §4 modules connect concepts to the user's own context where relevant.
- [ ] §5 quotes are curated and short; no 1500+ char transcript dumps.
- [ ] Evidence IDs like `[E3]` are either resolved or replaced with timestamp links.
- [ ] Metadata counts in §0 match the actual source totals.
- [ ] ASR hallucination/noise terms are called out or cleaned.
- [ ] Frontmatter follows the target vault's AGENTS/CLAUDE.md convention.

## When this gate fails

Quarantine the draft as a bad draft (do not save to Obsidian), return to Phase 3, and rewrite the failing sections. Do not rely on `verify_report.py`, `check_report_coherence()`, or OMP mechanical audit as proof of human readability.
