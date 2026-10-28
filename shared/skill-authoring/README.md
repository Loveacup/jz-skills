# Skill Authoring has moved

The maintained source is now **[Loveacup/skill-authoring](https://github.com/Loveacup/skill-authoring)**, a standalone public repository. Follow its README for current installation and usage instructions.

This directory is a migration notice, not an installable skill. It intentionally contains no `SKILL.md`. Do not deploy it, recreate the old entry, or copy runtime changes back here.

## Deployment boundary

- `deploy/sync-all.sh` no longer deploys Skill Authoring to Hermes, Hermes profiles, Claude Code or pi.
- `deploy/sync-back.sh` no longer maps Skill Authoring back into this collection; explicitly requesting the retired path fails with an error.
- Existing runtime installations are not removed by this repository change. Migrate each consumer separately using the standalone source; do not run a broad collection sync as a migration step.
- Only Skill Authoring is retired here. The rest of `jz-skills` remains active; the collection itself is not archived.

## History and rollback source

The final pre-retirement source is preserved in [Git history at 3dda0dea5b27b52aec9932f200056f17fb0b4a45](https://github.com/Loveacup/jz-skills/tree/3dda0dea5b27b52aec9932f200056f17fb0b4a45/shared/skill-authoring).

An unchanged historical snapshot is also retained in [`../_archived-skill-authoring/`](../_archived-skill-authoring/), with its former entry renamed to `LEGACY.md` so recursive skill discovery cannot load a second active copy. That snapshot is historical, not a maintained alternative. Restoring it requires a separately authorized rollback; do not re-enable the removed sync mappings during ordinary maintenance.
