# Agent SkillHub Workflow

Use this reference for centralized SkillHub state changes in `~/.agents`. Load only the section matching the task after routing context through `agent-skillhub-context-map.md`.

## Directory semantics

| Path | Meaning |
|---|---|
| `~/.agents/skills` | temporary entry/landing zone; not stable canonical storage |
| `~/.agents/shared` | reviewed cross-CLI canonical skills |
| `~/.agents/pools/*` | reviewed specialized canonical pools |
| `~/.agents/归档` | cold archive; not a runtime target |
| `~/.agents/external-skill-links` | source/runtime-native evidence pointers, not runtime targets |

Source workspaces, canonical pools, runtime entries, and public repositories are separate planes. A write to one does not silently authorize writes to another.

## New skill or major rewrite

1. Define trigger/anti-trigger, consumer result, owner, risk tier, and intended canonical class.
2. Check for an existing skill that owns the capability; improve it instead of creating a competing source of truth.
3. Create or edit in the explicitly authorized source/canonical target, not in a runtime entry merely because it is convenient.
4. Keep the common path in `SKILL.md`; route environment, recovery, history, and research detail conditionally.
5. Update the ledger, lock, or tags only when this task changes the state represented by that record.
6. Runtime exposure and public publication remain separate gates.

## Existing skill modification

1. Read the active canonical file and each maintained source mirror in scope.
2. Read a runtime copy only when consumer behavior, deployment, or drift is part of the task.
3. If source is dirty or another plane is richer, classify and merge the relevant components; do not overwrite blindly.
4. Back up every changed file and make the narrow reviewed edit across intended mirrors.
5. Preserve runtime-only/private/generated material and unrelated dirty work.
6. Verify according to behavioral risk. A high-impact contract change needs a fresh independent verdict; a small wording edit does not need a scoring ceremony.
7. Report source/canonical/runtime states independently.

## GitHub or external-source import

Import means preparing or applying a reviewed payload to a canonical pool. It does not imply runtime exposure or remote publication.

1. Record the exact upstream source and revision.
2. Identify skill payload and exclude repository metadata, caches, generated output, and private state.
3. Classify origin, function, risk, and canonical target.
4. If a canonical copy already exists, compare semantically and preserve local extensions; mark unresolved conflicts instead of overwriting.
5. Apply only the reviewed payload when canonical application is authorized.
6. Update provenance/ledger/lock/tags only for state actually changed.
7. Run relevant link, syntax, behavior, and privacy checks.
8. Record whether runtime exposure and publication were unchanged, prepared, or separately authorized.

## Promotion from intake to a canonical pool

Promotion requires a source decision and reviewed target, not merely a usable `SKILL.md`.

- apply the dirty-source gate when a source workspace is involved;
- confirm critical companion files and referenced artifacts are present;
- preserve richer canonical/runtime content through semantic merge;
- update only records whose represented state changed;
- keep runtime repoint/exposure as a separate action.

An unresolved source owner, critical-file deletion, missing reference, or unexplained richer runtime blocks promotion. Record the blocked claim; do not hide it with a baseline or metadata change.

## Runtime exposure

Runtime exposure mutates a consumer entry and requires explicit authorization for a named target.

- Point only to a reviewed canonical target under `.agents/shared/*` or `.agents/pools/*`.
- Do not point runtimes at intake, archive, source repositories, or external-link evidence.
- Inspect the current entry before replacement and preserve rollback evidence.
- Do not broaden one target to all CLIs/profiles.
- Do not overwrite or delete an existing entry unless that replacement/removal is explicitly in scope.
- Verify the actual consumer after the change; symlink/file equality alone is not behavior proof.
- Update registry/ledger exposure fields only after observed state matches the record.

## Publication

Canonical application does not imply public publication. Follow `deployment.md` and `desensitization-audit.md` only when the current task authorizes publication to an identified repository.

Use explicit file scope, preserve unrelated dirty work, and do not run commit/push/release commands merely because an import or source mirror was prepared.

## Obsidian writeback

Resolve the target through `docs.yml` and update only the document whose function matches the state change:

| Change | Writeback class |
|---|---|
| run/validation evidence | monitor log or evidence index |
| architecture/function change | architecture changelog |
| tag/classification change | function-tags index |
| no governed documentation change | no writeback |

Do not dump execution logs into architecture documents or read the full project recursively.

## Completion evidence

Report:

- changed and backed-up paths;
- source/canonical/runtime/publication state actually reached;
- relevant records updated or deliberately unchanged;
- checks and scenarios actually run;
- fresh independent verdict when high-impact behavior changed;
- blocked claims and missing evidence;
- external writes, broad sync, deletion, repoint, config, and baseline changes not performed.
