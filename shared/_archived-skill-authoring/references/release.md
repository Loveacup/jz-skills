# Release, Deploy, and Retire a Skill

Use this workflow only when an authorized skill change crosses from preparation into a canonical pool, runtime, repository, public remote, or retirement action. Reconciliation belongs in [import](import.md); verification design and independent judgment belong in [evaluate](evaluate.md); publication-plane transformation belongs in [privacy](privacy.md).

## Report states independently

A release may reach one or more of these states. Never use one as evidence for another.

| State | Required observation |
|---|---|
| **Prepared** | The reviewed local artifact, exact scope, backups or rollback source, and required evidence exist. |
| **Canonical applied** | The reviewed artifact is present in the named canonical target. |
| **Runtime deployed** | The reviewed artifact is present at the named runtime and the actual consumer path has succeeded. |
| **Published** | The named remote repository and branch contain the reviewed artifact. |
| **Retired** | The exact obsolete entries were removed under authorized scope and rollback and non-resurrection evidence exist. |

A plan, dry run, local patch, import, file hash, or review reaches none of the later states by implication.

## Resolve authorization by named action

Before crossing a plane, name the action and its target: the canonical path, runtime consumer, repository and branch, or exact retirement set. Also identify whether the action changes a symlink or configuration, performs reverse synchronization, replaces directories, deletes data, or mutates a baseline.

An active instruction that explicitly authorizes an action on a named target is sufficient for that scope; do not ask again for each safe step. If the action or target was not authorized, stop at the highest state already authorized. Never infer authorization for:

- commit, push, release, publication, or a remote branch change from preparation or import;
- every runtime or profile from one named consumer;
- repointing, configuration changes, reverse synchronization, or unreviewed file overwrites from deployment;
- deletion, retirement, exact-mirror removal, broad sync, or baseline mutation from replacement;
- a fallback deployment elsewhere after one target fails.

If the target or destructive scope changes, obtain new authorization before that action.

## Freeze the artifact and repository scope

Before applying or publishing, record:

- the exact artifact and intended-path allowlist;
- the source, canonical, runtime, and remote targets that are in scope;
- current entry types and destinations for files, directories, and links that may change;
- working-tree changes, staged changes, and untracked release files as separate sets;
- unrelated dirty paths that must remain unchanged and unstaged;
- any other writer touching the same mutable files;
- backups or reversible prior targets and the rollback action.

Inspect the staged or release artifact itself, not only the working-tree diff. Stage explicit paths; never use broad staging in a dirty repository. The artifact that crosses the boundary must be the one reviewed. Apply [privacy](privacy.md) to the complete crossing set, including references, scripts, templates, tests, assets, and intended untracked files.

A timeout is missing evidence, not proof that another writer stopped. Before replacing or restarting work on the same mutable scope, obtain process exit, lease release, lock release, or an equivalent stop observation. Otherwise leave the conflicting write `BLOCKED`.

## Apply to a canonical target

Use the reviewed source-to-target pairs from [import](import.md). Back up changed targets and apply only those pairs with non-destructive semantics by default. Do not use whole-directory replacement, blanket synchronization, or recency to resolve drift.

Forward and reverse transfers are distinct capabilities. A forward apply does not authorize reverse sync; a reverse dry run is inspection, not permission to write source. If reverse sync is named and authorized, constrain it to the reviewed paths and exclude private, runtime-only, generated, cache, credential, log, and evidence state. Do not add or change mapping rules unless the authorized topology requires them.

## Deploy to a named runtime

For each authorized consumer:

1. Resolve the actual load path and current entry type before writing.
2. Preserve a reversible prior target, then install only the reviewed files. Repoint a consumer only when that action is separately named and authorized.
3. Leave other runtimes, profiles, configuration, schedules, and baselines unchanged unless named separately.
4. Exercise the real consumer's discovery path and the changed behavior. Byte equality or a valid symlink proves placement, not use.
5. If the smoke or behavior scenario fails, report that target as not verified, preserve the evidence, and use the prepared authorized rollback when continuing would leave an unsafe or unusable consumer. Do not overwrite new unrelated work during rollback.

Do not report `Runtime deployed` until the named consumer observation succeeds.

## Publish to a named remote

Reconcile concurrent writers and upstream state without rewriting unrelated work. Confirm the staged artifact and required high-risk independent verdict, then commit or publish only to the authorized repository and branch. Afterward, inspect the named remote revision or artifact. Local commit success or push output alone is not the `Published` observation.

## Conditional runtime compatibility branches

Use these branches only when the target architecture actually needs them.

### Compatibility entrypoint with retained runtime assets

When an old runtime directory must keep rollback scripts, references, tests, or private state, update only the reviewed entrypoint rather than replacing the directory. Examine forward and reverse transfer behavior so that a later normal sync cannot leak private state, delete retained assets, or resurrect the retired implementation. A prohibited reverse transfer must fail explicitly rather than silently report success. Any exact-mirror removal remains a separately authorized deletion set.

### Runtime-owned generated overlay

When a host-neutral canonical skill cannot be loaded directly by a runtime, a runtime repository may generate its own thin overlay. Treat canonical content as an explicit read-only input; write to one declared runtime-owned output; record provenance; keep host binding narrow; and retain no live source dependency or symlink back to canonical storage. The generator must reject path escapes and symlink-mediated output writes, leave the prior output intact on failure, and not discover targets from ambient home or runtime configuration. Generating the overlay does not authorize repointing the consumer.

These are compatibility contracts, not default deployment architecture and not a reason to add a dispatcher.

## Rename, replacement, retirement, and cleanup

For a rename or consolidation, classify old-name occurrences as active consumers, inbound references, mappings, generated outputs, compatibility surfaces, historical records, or unrelated text. Update only current references in authorized targets; preserve clearly labeled history rather than globally replacing it.

Before retiring or deleting anything:

- prove the replacement at every named consumer on which retirement depends;
- enumerate the exact paths, links, mappings, and retained assets proposed for removal;
- identify the generator, sync mapping, installer, or other source that could recreate them, and update that source only when it is authorized;
- preserve rollback material outside the active load surface;
- obtain explicit retirement or deletion authorization;
- show that the next ordinary regeneration or sync will not resurrect the old entry or erase the replacement.

A baseline records explained state; it must not hide unexplained drift, loss, shadows, or stale generators. Change a baseline only as a separately named action after the underlying state is understood and observed. Cleanup is not an import or deployment shortcut.

## Completion record

Report only observed facts:

- the exact changed, staged, published, deployed, retired, and backed-up paths;
- the authorization and named target for each external or destructive action;
- the state reached for each target;
- actual consumer and remote observations;
- rollback location and whether rollback was exercised or only prepared;
- privacy and behavior evidence, plus the independent verdict required for high-impact behavior;
- blocked claims and their missing evidence;
- reverse sync, broad sync, unrelated dirty work, configuration, baseline, deletion, and other targets deliberately left unchanged.