# jz-skills Coordination

This repo is a personal source/deploy surface for skills used by multiple CLIs.
It is not the only source of truth: runtime state and the `.agents` canonical
pool must be checked before broad sync or publication.

## Read First

- Repo rules: `CLAUDE.md`
- Reverse sync safety: `deploy/sync-back.sh --help`
- Drift summary: `deploy/skill-drift-summary.sh`
- Hub ledger: `~/.agents/skill-sources.md`
- Obsidian governance: `~/Documents/Obsidian/AlexCai/20-Areas/20_技术项目/Agent Skills 中心化治理/AGENTS.md`

## Daily Work

- Single-skill edits are fine when the diff is narrow and readable.
- Run `deploy/skill-drift-summary.sh` before commit/push review.
- `sync-back.sh` is report-only by default. Apply runtime writeback with an explicit scope:

```bash
./deploy/sync-back.sh --apply --only shared/obsidian
```

## Stop And Confirm

- Do not use full runtime sync-back as the default workflow.
- Do not batch unrelated drift into one commit.
- Do not delete critical skill files or publish to GitHub without explicit approval.
- If runtime has richer content than this repo, do a semantic merge instead of overwriting.
