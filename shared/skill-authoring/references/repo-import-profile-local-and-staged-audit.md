# Repo Import: Profile-Local Source and Dirty-Worktree Safety

Use this when preparing a skill from a profile-local/runtime source for a source repository, or when the repository already contains unrelated dirty work.

This workflow prepares a reviewed repository artifact. It does not itself authorize commit, push, runtime mutation, broad sync, or deletion.

## 1. Identify the actual source planes

Determine the loaded runtime path, declared canonical path, repository path, and source-ledger relation. Runtime and repository copies may be independent even when names and versions match.

Compare the affected files and classify each delta:

- intended portable change;
- host/profile-specific operation;
- private/runtime state;
- generated/cache evidence;
- historical material;
- unrelated pre-existing drift.

Do not move a whole runtime tree into a repository because it is newer or richer.

## 2. Prepare a non-destructive transfer

- Back up each target file before editing.
- Copy or merge the explicit reviewed files. Use non-destructive copy semantics by default.
- Do not use `rsync --delete`, directory replacement, or cleanup as an import shortcut.
- If obsolete repository files are discovered, list them as a separate retirement proposal; do not remove them without explicit authorization.
- Do not mutate the live profile merely to make a reverse-sync script see it.
- Keep profile paths, credentials, local config, caches, logs, generated reports, and unrelated helper scripts out of portable source.

A repository copy must remain executable/parseable after sanitization; privacy transformation is not complete until affected syntax and behavior are rechecked.

## 3. Decide mapping changes separately

Adding repository content does not automatically require a new forward-deploy or reverse-sync mapping.

Change mappings only when the authorized topology requires them, and review both directions:

- forward mappings must target only named authorized runtimes;
- reverse mappings must not pull private/runtime-only state into source;
- runtime exposure remains separate from repository preparation;
- an `all` target is never inferred from a single skill import.

## 4. Isolate unrelated dirty work

- Keep an explicit intended-path list.
- Never use broad staging in a dirty repository.
- Inspect the intended diff and staged set independently from unrelated working-tree changes.
- Do not rewrite, stage, commit, or clean files outside the reviewed scope.
- Reconcile another writer touching the same files before final review.

## 5. Audit privacy and provenance

Record the real source path and revision/state. Scan the complete intended publication set for personal names, private paths, internal hosts, credentials, IDs, local ports, runtime state, and generated evidence.

Known public VCS literals such as `git@github.com` may be allowlisted precisely; never blanket-ignore all email-like or credential-like matches.

## 6. Verify according to change risk

Choose checks from the changed artifact:

- references resolve and required companion files are present;
- syntax or schema checks cover changed executable/config files;
- the changed behavior is exercised with realistic scenarios;
- privacy transformations preserve semantics;
- source and maintained mirror files match where alignment is required;
- high-impact behavior has a fresh independent verdict.

Do not run a fixed suite merely to satisfy ceremony, and do not claim runtime behavior until the named consumer has actually been exercised.

## 7. Publication gate

If the current task does not explicitly authorize publication to the repository, stop with a prepared artifact and report that commit/push were not performed.

If publication is authorized, follow `deployment.md`: stage explicit paths, preserve unrelated dirty work, publish only to the named repository/branch, and verify the remote artifact before reporting success.
