# Agent SkillHub Context Map

Use this reference only for centralized SkillHub work that touches governance, canonical placement, source records, runtime exposure, tags, or Obsidian writeback. Ordinary skill wording and reference edits do not require this map.

## Routing rule

Start with the target artifact and its nearest owning instruction. Add a governance source only when a decision depends on it. Do not load the full config set, ledger, lock file, tag table, audit tree, or Obsidian project by default.

## Task-specific context

| Decision or task | Minimum context | Add only when |
|---|---|---|
| Edit an existing skill without changing ownership/exposure | active canonical file, source mirror if maintained, nearest repo/runtime rules | ledger only if source/canonical relation is unclear; runtime copy only if consumer behavior or drift is in scope |
| Choose canonical pool or promote from intake | `~/.agents/config/agent-skills/governance-policy.yml`, relevant source, target pool, source-ledger row | `source-taxonomy.yml` when origin class is uncertain; dirty-source evidence when the source workspace is involved |
| Import from GitHub | upstream artifact/commit, target pool, `~/.agents/.skill-lock.json`, source-ledger row | `secrets-policy.yml` when content may contain private material; tags only if classification is part of the task |
| Resolve source/canonical/runtime drift | affected copies, source-ledger row, owning rules | runtime registry only if exposure or consumer path may change; prior audit only when its claim is needed |
| Change runtime exposure | `~/.agents/runtime-cli-registry.json`, canonical target, exact current entry, governance policy | other runtimes only when explicitly included in the named target set |
| Change tags or classification | affected skill and `~/.agents/skill-function-tags.tsv` | taxonomy/config generator only if regeneration would overwrite the decision |
| Resolve documentation path | `~/.agents/config/agent-skills/docs.yml` | the single resolved Obsidian document required for the writeback |
| Change paths/config schemas | the specific config file and `~/.agents/config/agent-skills/paths.yml` when path resolution is involved | adjacent configs only for an actual cross-file invariant |

The config files are available sources, not an eight-document pre-flight ritual:

- `paths.yml` resolves governed paths.
- `docs.yml` resolves human-facing documentation targets.
- `governance-policy.yml` governs placement and exposure decisions.
- `source-taxonomy.yml` governs source classification.
- `secrets-policy.yml` governs privacy-sensitive transfer/publication.
- `skill-sources.md` records source/canonical/runtime relationships.
- `.skill-lock.json` records GitHub-backed provenance.
- `skill-function-tags.tsv` records functional classification/exposure metadata.

## Obsidian boundary

Never read the SkillHub Obsidian directory recursively merely because the task mentions centralized governance. Resolve and read one document when a writeback or historical claim requires it.

Broader reading is justified only for a project-level architecture change, a migration spanning several governed documents, a contradictory historical claim that cannot be resolved from direct evidence, or an explicit user request.

## Evidence boundary

Record only evidence relevant to the state that changed:

- changed and backed-up paths;
- source/canonical/runtime relation when affected;
- dirty-source result when a source workspace was used;
- runtime exposure result or `unchanged` when exposure was in scope;
- checks actually run and blocked claims;
- writeback target when a governed document changed.

Do not update unrelated ledger, tag, lock, audit, or Obsidian surfaces just to complete a ceremony.
