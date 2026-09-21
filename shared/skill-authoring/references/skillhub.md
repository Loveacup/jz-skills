# Local SkillHub Adapter

Read this reference only when a task changes placement, provenance, runtime exposure, generated entrypoints, governance records, or Obsidian writeback under `~/.agents`. An ordinary portable skill edit does not require SkillHub configuration, the full ledger, the runtime registry, or the Obsidian project.

This adapter explains how to discover local authority. It does not replace [import](import.md), [release](release.md), or the live rules at the target.

## Start from the target

Read `~/.agents/AGENTS.md` as the hub-level coordination entrypoint and the nearest instructions governing the target. Then add only the row or policy section needed for the current decision:

| Decision | Read |
|---|---|
| Edit an already-pooled skill without changing ownership or exposure | The skill's row in `skill-sources.md`, its named maintained source, and the nearest source/target rules. |
| Choose a canonical pool, promote from intake, or overwrite canonical content | The relevant target section in `config/agent-skills/governance-policy.yml`, the target pool rules, and the skill's source row. Read source-classification policy only if origin is unresolved. |
| Reconcile source, canonical, and runtime drift | The affected copies and source row. Read the exact runtime registry entry only if exposure or consumer identity is part of the task. |
| Review an upstream update | The exact `.skill-lock.json` entry, the pinned or observed upstream revision, and evidence of local customization. |
| Change runtime exposure | The exact entry in `runtime-cli-registry.json`, the canonical target, and the matching placement policy. Do not load unrelated runtime entries. |
| Change generated entrypoints | `config/agent-skills/agents-entrypoints.yml` and the configured generator. |
| Write governance documentation | The exact route in `config/agent-skills/docs.yml` and the single mapped Obsidian document. |

Do not rely on remembered paths, past audits, or a previous policy snapshot when the live target rules and rows are available. A policy exception applies only to a target that is explicitly listed in the current policy. In particular, do not generalize a runtime-owned or active-development exception into agent lifecycle management, automatic promotion, reverse sync, or runtime control.

## Respect directory meaning

Resolve placement through current policy. The usual meanings are:

- `~/.agents/skills` is intake or a temporary registered entry, not stable canonical storage;
- `~/.agents/shared` contains reviewed cross-runtime canonical skills;
- `~/.agents/pools/*` contains reviewed specialized canonical skills;
- `~/.agents/external-skill-links` is source or runtime-native evidence, not a runtime target;
- `~/.agents/归档` is cold history, not a load surface.

Do not point a consumer at the hub root, intake root, archive, source repository, or evidence pointers merely because a `SKILL.md` exists there. If the live governance row gives the target a different registered status, follow that row and report the exception rather than rewriting the general rule.

## Hub records require human authorization

Current hub rules require explicit human approval before changing any of these authority records:

- `skill-sources.md`;
- `.skill-lock.json`;
- `runtime-cli-registry.json`.

A skill edit, import, canonical apply, or runtime observation does not imply permission to mutate them. If the active request already authorizes the named record change and exact skill or runtime target, continue without asking again; otherwise prepare the proposed row or delta and stop before the record write.

After authorization, change only the row or entry whose represented state actually changed. Record observed paths, revisions, canonical decisions, exposure, and blocked facts; do not update a record in advance to make an intended state look complete. A ledger row does not prove the filesystem state, a lock entry does not prove semantic compatibility, and a registry entry does not prove consumer behavior.

Other tables or configuration have their own live owner rules. Do not edit tags, taxonomy, paths, secrets policy, audits, or documentation merely to complete a ritual.

## Generated entrypoint stubs

`~/.agents/AGENTS.md` is the hub-level canonical entrypoint. Pool and runtime `AGENTS.md` files are generated stubs: never hand-edit them. Change only the configured canonical wording or target in `config/agent-skills/agents-entrypoints.yml`, then use its designated generator and check mode. Generator output is not authority to change a discovered runtime target; any resulting exposure or repoint still follows [release](release.md).

Do not copy generated stubs into a portable skill or treat them as independently maintained policy.

## Obsidian writeback

`config/agent-skills/docs.yml` is the source for Obsidian project paths and writeback classes. Resolve one mapped document and update it only when the authorized work changed the state that document owns, for example:

- run or validation evidence to the configured evidence or monitor record;
- architecture or function changes to the configured architecture changelog;
- classification changes to the configured function-tags document.

Do not guess a vault path, recursively read the project, or duplicate raw execution logs into architecture documents. No governed documentation change means no Obsidian writeback. If strategy changed, follow the hub's current strategy-writeback rule rather than an older audit's location.

## Apply the shared workflows

For upstream or runtime reconciliation, use [import](import.md) and preserve host-only, private, generated, and richer local safety content. For canonical application, runtime exposure, publication, repointing, or retirement, use [release](release.md). These actions remain separate even when the same task authorizes more than one.

When a runtime is named, verify its actual loader or consumer after an authorized change. A link target, registry row, manifest, or hash proves only the property inspected. Do not invoke historical runtime-owner lifecycle, profile-fleet, schedule, watchdog, or baseline procedures unless the current named target policy and request specifically require that operation.

## Result

Report the target-specific authority read, rows or entries changed or deliberately unchanged, canonical placement, runtime exposure state, consumer observation when applicable, mapped documentation target when used, and any claim left `BLOCKED` by missing evidence. Do not present a prepared proposal as an applied hub state.