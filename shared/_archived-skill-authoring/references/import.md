# Import and Reconcile a Skill

Use this workflow to bring an external, repository, canonical, or runtime copy into the maintained skill without silently discarding useful local behavior. Import produces a concrete reviewed artifact. It does not publish, deploy, repoint a runtime, retire an old copy, or authorize those actions.

## Establish identity and provenance

Identify the planes that actually exist for this skill:

- the proposed source and the exact revision or observable state reviewed;
- the maintained source workspace, if different;
- the declared canonical copy and its ownership record;
- the loaded runtime copy only when runtime behavior or drift is relevant;
- the intended destination and the rules that govern it.

Use the skill's frontmatter identity, source records, repository history, and actual path relationships together. A matching name, manifest entry, version, timestamp, or hash is evidence about one property; none alone establishes ownership, completeness, quality, or permission to synchronize. If the source is a dirty workspace, record which relevant files are dirty and keep unrelated changes outside the import.

## Decide whether the capability belongs

Before merging an attractive implementation, identify the problem it solves and the existing skill or module that owns that problem. Import a capability only when there is a concrete need and it fits the target architecture.

When the need is real but the architecture differs, extract the portable contract or principle instead of importing the external framework. When an existing owner already provides the behavior, improve that owner or leave the proposal out rather than creating a competing route. Do not import orchestration, lifecycle machinery, scheduled services, or host policy merely because they accompanied useful skill content.

Record rejected material and unresolved conflicts in the import summary; do not hide them by choosing the largest or newest tree.

## Classify every delta

Inventory the relative paths in the affected planes, then classify each added, missing, or changed component by meaning:

| Class | Treatment |
|---|---|
| Portable skill behavior | Merge into the maintained portable artifact if it is needed and compatible. |
| Host or runtime binding | Keep in its owning host layer, or express a narrow adapter contract without embedding host configuration in the portable core. |
| Local safety or policy extension | Preserve unless the current governing contract explicitly replaces it; reconcile wording rather than overwriting it. |
| Private or runtime state | Exclude from portable source and handle under [privacy](privacy.md). |
| Generated, cache, vendor, or captured evidence | Exclude as an import source; preserve separately only when it is needed as evidence. |
| Historical material | Keep as history when useful, but do not reactivate its procedure as current instruction. |
| Unrelated pre-existing drift | Leave untouched and report it separately. |
| Executable or compatibility component | Define its callers, inputs, outputs, failure behavior, and host layer before accepting it. |

For changed common files, compare behavior and contracts, not just bytes. Check entrypoints, linked references, schemas, tool assumptions, fallback behavior, and downstream callers. A runtime-only helper can be a valid candidate when it has an independent useful contract; an older runtime pipeline is not a valid replacement merely because it currently runs.

## Build the merged artifact

Work from an explicit destination-path list. Back up files that will change, preserve unrelated dirty work, and merge at component level:

1. Keep the current owner and entrypoint unless the requested change explicitly changes architecture.
2. Preserve richer local safeguards, private/generated boundaries, and compatible local extensions.
3. Add only the source behavior required by the accepted delta; adapt it to existing terminology and interfaces.
4. Include required companion files and close internal links. Do not copy repository metadata or an entire runtime tree as a shortcut.
5. Keep host-specific settings and operations in their owning layer. If a portable core needs host support, state the seam and supported degraded behavior rather than inventing infrastructure.
6. Reconcile simultaneous edits to the same destination before finalizing; do not select a writer by timestamp.

Within an already authorized preparation or canonical-application scope, complete this merge instead of stopping for a ceremonial approval. Ask for a decision only when the target, ownership, destructive scope, or external action is not authorized. Missing evidence that is required to resolve a component leaves that component `BLOCKED`; it does not justify overwriting either side.

## Verification and result

For a content-only merge, resolve affected references and inspect the accepted delta against the requested behavior directly. Read [evaluate](evaluate.md) for a nontrivial behavioral comparison, executable change, or required independent review. Validate changed structured or executable files through their relevant interface. If privacy transformation changed syntax or behavior, verify the transformed artifact rather than the pre-transformation input. Do not claim runtime behavior unless the named consumer was actually exercised under an authorized deployment.

Return the merged artifact together with:

- source identity and revision/state;
- destination and exact changed paths;
- the material accepted, adapted, excluded, preserved, or blocked, with reasons;
- the source/canonical/runtime relationship observed;
- unresolved links or compatibility questions;
- actions not taken, including publication, deployment, reverse synchronization, retirement, and broad cleanup.

If a later action is authorized, continue with [release](release.md). Import itself ends at the state it actually reached.