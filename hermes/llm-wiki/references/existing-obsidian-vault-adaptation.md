# Existing Obsidian Vault Adaptation

Use this when applying the LLM Wiki / GBrain pattern to an existing Obsidian vault with established structure.

## Principle

Do not impose the default `wiki/raw/entities/concepts` tree if the vault already has a working taxonomy. Map the LLM Wiki layers onto the existing vault instead.

## Adaptation Pattern

1. Resolve and read the vault's local operating instructions first (`CLAUDE.md`, `AGENTS.md`, or equivalent).
2. Preserve existing human navigation conventions, especially a declared single root MOC.
3. Add agent-facing control files with non-conflicting names when needed:
   - `SCHEMA.md` for structure/rules.
   - `RESOLVER.md` for filing decisions.
   - `WIKI_INDEX.md` for agent-oriented index, not a second human MOC.
   - `WIKI_LOG.md` for append-only agent operations.
4. Map layers rather than creating duplicate roots:
   - Raw input -> existing Inbox/capture area.
   - Staging/review -> existing staging/review area.
   - Compiled wiki pages -> existing projects/areas/resources/self sections.
   - Archives -> existing archive area.
   - System files -> existing system/admin area.
5. Patch the vault's local instructions with a short pointer to the new control files.
6. Keep the first implementation small: create governance files and a runbook; do not batch-rewrite old notes or install a new runtime unless explicitly requested.
7. Refresh the local search index (qmd or equivalent) after material changes and verify search can find the new control files.

## Pitfalls

- Do not create a second human-facing root MOC if the vault has a single-MOC rule.
- Do not flatten a mature vault into the generic LLM Wiki example tree.
- Do not enable automatic private-data ingestion, cron enrichment, or broad page rewrites as part of an initial skeleton.
- Distinguish agent operational memory from knowledge assets: Hermes memory/Hindsight/skills are not the same layer as the Obsidian wiki.

## Verification

- New control files exist and have valid frontmatter if the vault requires it.
- The existing root instruction file points to the control files.
- Search index can retrieve the new schema/resolver/log/index by distinctive phrases.
- The operation log records what changed and what was intentionally not changed.
