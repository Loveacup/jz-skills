# Preparation, Publication, and Named-Target Deployment

Read this reference only when a skill change may cross from local authoring into a source repository, canonical pool, runtime, or public remote.

## State model

These states are separate and must be reported separately:

1. **Prepared** — reviewed files, backups, diff/manifest, privacy checks, and relevant behavior evidence exist locally.
2. **Canonical applied** — the reviewed change is present in the named canonical pool.
3. **Runtime deployed** — the reviewed files are present at an explicitly named runtime target and that consumer path has been exercised.
4. **Published** — an explicitly named remote repository/branch contains the reviewed artifact.
5. **Retired** — obsolete entries or data were removed under separate authorization and rollback evidence exists.

Reaching one state does not imply any later state. A dry run, patch, import, audit, or fresh-agent review is preparation, not permission to publish or mutate a runtime.

## Authority and target gates

Before a write crosses planes, identify:

- source path and ownership;
- canonical path from the ledger or governing rules;
- exact runtime path, if deployment is requested;
- exact repository and branch, if publication is requested;
- whether deletion, replacement, baseline mutation, or broad sync is involved.

An explicit instruction in the active task to publish or deploy to a named target authorizes that scoped action; do not ask again unless the target, scope, or risk changes. Without that instruction, stop at `Prepared`.

Never infer authorization for:

- `git commit`, `git push`, release/publish commands, or remote branch changes;
- deployment to every profile/platform when only one target was named;
- runtime symlink/repoint/config changes;
- `rsync --delete`, directory replacement, old-entry removal, or watchdog baseline updates.

## Prepare the artifact

1. Read the repository/runtime rules and source ledger relevant to the named skill.
2. Back up every file that will change.
3. Compare source, canonical, and affected runtime files. If one plane is richer or dirty, classify the delta and merge semantically; do not choose by recency or copy a whole directory blindly.
4. Edit the narrow reviewed set. Preserve unrelated dirty files, runtime-only state, caches, credentials, history, and generated evidence.
5. Run only the checks required by the changed behavior. For high-impact changes, obtain a fresh independent verdict against the original acceptance contract.
6. Scan the complete intended publication set for sensitive paths, identifiers, credentials, private state, and syntax damage from sanitization.
7. Record changed paths, target state, verification evidence, blocked claims, and rollback source.

Preparation may include a deployment plan or dry run. It must not apply that plan automatically.

## Source and canonical application

A source repository, canonical pool, and runtime copy can legitimately differ. Use these rules:

- Treat upstream content as a proposal when canonical has local changes or more complete content.
- Apply only reviewed file pairs; do not broad-sync unrelated drift.
- Add or change deploy/reverse-sync mappings only when the requested release topology needs them.
- A canonical import does not automatically expose the skill to a runtime.
- Runtime exposure does not make the runtime copy canonical.
- Keep host-specific operations outside a shared portable core unless they are explicitly conditional and supported.

If a profile-local source is involved, follow `repo-import-profile-local-and-staged-audit.md`.

## Publication gate

Publication is an external write. Execute it only when the current task explicitly names or clearly identifies the repository publication.

Before publishing:

- freeze or reconcile concurrent writers to the same files;
- inspect the exact intended file set and diff;
- stage explicit paths rather than broad repository state;
- run relevant privacy and semantic checks on the staged/release artifact;
- ensure the artifact being published is the one independently reviewed when high impact;
- keep unrelated dirty work uncommitted and unstaged.

After an authorized publication, verify the named remote/branch contains the intended artifact before reporting `Published`. Do not convert a request to prepare/import/review into commit or push.

## Named-target runtime deployment

Runtime deployment mutates a consumer surface. Execute only the named target or the exact target set explicitly authorized.

1. Resolve the target path and current entry type before writing.
2. Back up the target files or record a reversible prior target.
3. Copy or link only the reviewed files using a non-destructive operation by default.
4. If exact mirroring requires removals, enumerate the proposed deletion set and obtain authorization for that destructive scope; do not use `rsync --delete` as the default.
5. Do not change runtime configuration, symlink topology, other profiles, schedules, or watchdog baselines unless each is in scope.
6. Exercise the actual named consumer path after deployment. File equality alone proves bytes, not discovery or behavior.
7. Report consumer behavior as unverified until the smoke/behavior scenario succeeds.

A failure at one target does not authorize broad sync or fallback deployment elsewhere.

## Sync scripts are capabilities, not defaults

`deploy/sync-all.sh` and `deploy/sync-back.sh` may exist in `jz-skills`, but their names do not grant authority:

- reverse-sync dry run is inspection only;
- reverse-sync apply must be explicitly scoped to the reviewed repository path;
- forward sync changes runtime state and requires a named authorized platform/target;
- an `all` target is broad deployment and must be requested explicitly;
- script output must be reconciled with the actual source/canonical/runtime relation.

Never assume a script's sanitizer is complete. Use `desensitization-audit.md` when publication is possible, and rerun syntax/behavior checks after transformation.

## Retirement and cleanup

Retirement is separate from deployment. Before removing an old skill, shadow, mapping, or retained rollback asset:

- identify all consumers and references;
- prove the replacement works at the named target;
- back up the old state;
- obtain explicit deletion/retirement authorization;
- bound cleanup to the reviewed paths;
- verify that normal future sync will not resurrect or re-delete the wrong artifact.

Do not update a watchdog baseline to hide unexplained drift or missing content. Resolve and evidence the underlying state first; baseline mutation remains a separately authorized operation.

## Evidence to report

Report only states actually observed:

- changed and backed-up paths;
- source/canonical/runtime relation;
- prepared/applied/deployed/published/retired state for each named target;
- checks and scenarios actually run, with result anchors;
- independent verdict for high-impact behavior;
- blocked claims and missing evidence;
- external writes deliberately not performed.
