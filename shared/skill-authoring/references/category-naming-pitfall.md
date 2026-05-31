# Category Naming Pitfall (2026-05-29)

## Problem

Creating a category directory that houses only a single skill results in dead-weight naming. The user sees `note-taking/` and asks "what is note-taking?" — the category name obscures rather than organizes.

## Rule

**Do not create category directories for single skills.** Place them at top level:

```
❌ skills/note-taking/obsidian/     # Single skill, vague category
✅ skills/obsidian/                  # Direct, discoverable
```

Only create categories when housing **3+ skills** under them. Examples of valid categories:
- `governance/` — grill-with-docs, skill-authoring, cross-profile-api-bridge
- `research/` — web-research-router, arxiv, source-search, source-verification
- `creative/` — ascii-art, html-visual-design, comfyui, p5js

## Case Study

`obsidian` was placed under `skills/note-taking/obsidian/` with only a `DESCRIPTION.md` as sibling. User response: "note-taking？这是啥？" — immediate move to `skills/obsidian/`.
