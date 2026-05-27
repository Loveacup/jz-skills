# Reviewing AI design / agent-skill repositories

Use this note when evaluating repositories that are not conventional libraries but **agent skills, prompt bundles, design systems, or local agent workbenches** (e.g. HTML/PPT design skills, academic-writing skills, Claude Design alternatives).

## Classify the repo first

Do not compare all repos on the same axis. Put each repo in one of these buckets:

1. **Full product / workbench** — has UI, daemon/server, storage, agent adapters, release artifacts. Review architecture, runtime security, install surface, and stability.
2. **Single skill bundle** — centered on `SKILL.md` plus `references/`, `assets/`, `scripts/`. Review trigger scope, workflow quality, dependencies, and how cleanly it can be imported into the local skill library.
3. **Skill collection** — multiple `skills/<name>/` units. Review each unit separately and recommend selective import, not all-or-nothing installation.
4. **Design-system/template pack** — mostly examples, assets, templates, and style rules. Review reuse value, license, and asset provenance.

## Minimum evidence to gather

- GitHub metadata: stars, forks, open issues, license, created/pushed dates, latest releases, top contributors.
- README claims and install instructions.
- Root tree and key package files (`package.json`, `pyproject.toml`, `requirements.txt`, `pnpm-workspace.yaml`, `Dockerfile`, `docker-compose.yml`).
- Count files/lines/bytes by extension and identify large binaries/assets.
- Read all top-level license files and note if source, binary, model, or asset licenses differ.
- For skills: inspect `SKILL.md`, `references/`, `scripts/`, and `assets/`; do not judge from README alone.
- For workbenches: inspect architecture docs, local daemon/server behavior, credential storage, agent spawning, preview sandboxing, and default Docker images.

## Analysis dimensions

For each repo, report:

- **What it is**: product vs single skill vs skill collection vs template pack.
- **What it actually ships**: files, scripts, assets, docs, releases, binaries.
- **How it runs**: runtime versions, package manager, CLI/server/daemon commands, optional external APIs.
- **Best use cases** and clear non-use cases.
- **Import/migration fit**: whether to import wholesale, selectively import, or only observe/try in isolation.
- **Risks**: fast-moving main branch, large opaque assets, external API credentials, daemon/file-system blast radius, broad skill trigger scope, academic/citation hallucination risk.
- **Verification hooks**: validators, tests, preview commands, export scripts, or missing QA steps.

## Skill-library import guidance

- Prefer **class-level umbrella skills** over one repo = one permanent skill.
- For single focused skills with small assets and clean MIT/Apache licensing, whole-folder import is usually OK.
- For broad skills, slim the import: keep `SKILL.md` + essential `references/` first; add heavy media/assets/scripts only when needed.
- For skill collections, import only the high-value subskills first; keep the upstream repo clone as reference.
- For complete products/workbenches, do not “migrate” the product into the skill library. Trial it in isolation and extract reusable ideas/patterns instead.

## Report style for the user

Lead with an actionable ranking, then detailed per-repo sections. Avoid treating star count as quality. Explicitly call out whether the repo is immediately useful in Hermes/Obsidian workflows, and whether it should be installed, selectively migrated, or merely observed.
