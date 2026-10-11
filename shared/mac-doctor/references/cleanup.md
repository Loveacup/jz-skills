# Cleanup catalogue and safety gates

`storage` and `clean targets` are read-only. The source of truth for the CLI is `scripts/macdoctor/targets.json`; `clean plan` accepts only SAFE/CAUTION targets, writes a host-bound one-hour plan, and defaults to SAFE. `--include-caution` lists review candidates but cannot authorize CLI execution. NEVER targets cannot be planned; REPORT targets have no CLI execution path. The separately reviewed owner-authorized workflow below permits existing command/filesystem/UI tools without changing the CLI catalogue or engine.

## Current target catalogue

| ID | Class | Action / exact native scope |
|---|---|---|
| `npm-cache` | SAFE | `npm cache clean --force --cache <scope>`; scope `.npm`, resolved with `npm config get cache`. |
| `uv-cache` | SAFE | `uv cache clean` with `UV_CACHE_DIR=<scope>`; scope `.cache/uv`, resolved by `uv cache dir`; in-use check required. |
| `pip-cache` | SAFE | `python3 -m pip --cache-dir <scope> cache purge`; scope `Library/Caches/pip`, resolved by `python3 -m pip cache dir`. |
| `brew-cache` | REPORT | `storage` resolves `brew --cache`, measures the cache, and includes the bounded `brew cleanup --dry-run` output, parsed item count/size where available, and manual command `brew cleanup`. Not plannable. The manual command can remove prefix/older formula versions and autoremove dependencies; user must review the dry-run output before deciding. |
| `playwright-browsers` | CAUTION (CLI review-only) | Browser runtimes older than 30 days; exact-target disposal may use the separately reviewed workflow. |
| `xcode-derived-data` | CAUTION (CLI review-only) | DerivedData older than 14 days; same reviewed workflow. |
| `ios-devicesupport` | CAUTION (CLI review-only) | DeviceSupport older than 90 days; same reviewed workflow. |
| `npm-npx-stale` | CAUTION (CLI review-only) | `_npx` items older than 30 days; same reviewed workflow. |
| `chrome-cache` | CAUTION (CLI review-only) | Chrome cache older than 7 days; active use blocks disposal. Closing Chrome requires service-stop authority. |
| `hermes-profile-dev-cache` | CAUTION (CLI review-only) | Per-profile development caches older than 30 days, excluding the four native exceptions below; live models/indexes remain protected. |
| `hermes-regent-uv-cache` | SAFE | `regent/home/.cache/uv`; `UV_CACHE_DIR` set to that exact scope; resolve with `uv cache dir`, clean with `uv cache clean`; in-use check and 30-day minimum age required. |
| `hermes-regent-npm-cache` | SAFE | `regent/home/.npm/_cacache`; scope is `regent/home/.npm`, `npm_config_cache` set to that scope; resolve with `npm config get cache`, clean with `npm cache clean --force --cache <scope>`; in-use check and 30-day minimum age required. |
| `hermes-regent-pip-cache` | SAFE | `regent/home/Library/Caches/pip`; `PIP_CACHE_DIR` set to that exact scope; resolve with `python3 -m pip cache dir`, clean with `python3 -m pip --cache-dir <scope> cache purge`; in-use check and 30-day minimum age required. |
| `hermes-cron-worker-pip-cache` | SAFE | `cron-worker/home/Library/Caches/pip`; `PIP_CACHE_DIR` set to that exact scope; resolve with `python3 -m pip cache dir`, clean with `python3 -m pip --cache-dir <scope> cache purge`; in-use check and 30-day minimum age required. |
| `tm-local-snapshot` | REPORT | Lists snapshots and prints an exact per-date `tmutil deletelocalsnapshots DATE` command for user review; engine never executes it. |
| `huggingface-models` | NEVER | Protected models. |
| `qmd-models` | NEVER | Protected models and per-profile indexes. |
| `telegram-postbox` | NEVER | Telegram Group Containers message data. |
| `library-containers` | NEVER | Application containers. |
| `ios-backups` | NEVER | Device backups. |
| `docker-volumes` | NEVER | Docker volumes and VM data. |
| `keychains` | NEVER | Credentials and cryptographic identities. |
| `mail-photos-icloud` | NEVER | Mail, Photos, and iCloud data. |

Homebrew report-only caution: `brew cleanup --dry-run` is the preview, not proof that `brew cleanup` is limited to cache downloads. The printed `brew cleanup` may affect the Homebrew prefix, old installed formula versions, and dependencies. mac-doctor never runs that manual command; present the report and let the user review/decide.


Paths above are rooted at the account home, not an assumed user path. CAUTION minimum-age rules use each target's catalogue policy. Native targets declare `scope_path`, `resolve_cmd`, `native_env`, and `native_cmd`; effective scope must match the declared scope when planning and again when applying. Check `clean targets --json` for live definitions before presenting a plan.

## Owner-authorized reviewed cleanup

The owner may authorize direct command cleanup and delegate exact-manifest approval to an independent reviewer for the current task. Manual-only, native-interface-only and catalogue-only execution restrictions do not apply to this separate workflow. The mac-doctor CLI itself is unchanged; do not flip `CAUTION_APPLY_ENABLED`, invent a new CLI capability, or portray a catalogue refusal as an executable CLI plan.

### Authority and scope

- Authorize the task, review exact absolute targets/methods/consequences, and execute the approved manifest. With explicit delegated-review authority (“full authority, only review required”), do not ask the owner again for each reviewed item. Without it, obtain explicit approval of the manifest. Editing this skill alone grants no cleanup authority; unrelated future tasks require their own authorization.
- Prefer tool-native scoped cleanup where it covers the reviewed target. Exact-path commands or filesystem APIs may dispose of an explicitly reviewed file or directory; native UI is optional, not mandatory. A single approved directory may be removed recursively using an fd-relative, symlink-resistant implementation. Do not use broad parent-root removal, shell-expanded globs, guessed targets or symlink traversal.
- Resolve the real account home and record allocated bytes, type, device/inode/mtime, purpose, active-use evidence, intended operation and exclusions. Pin the containing directory and use basename-relative operations where supported; reject symlinked target/parent components and unexpected devices. Refuse changed identity, unknown use or a nonempty open-handle probe. Directory age alone does not prove inactivity.
- Rechecks, dirfds and symlink resistance reduce scope/selection errors, but cannot make a pathname unlink/rmtree/rename atomic with prior approved-inode observation. Same-user pathname replacement (ABA), mutable contents and concurrent allocation remain residual risks. Never claim immutable-object binding or guaranteed freed bytes; the reviewer must explicitly account for this risk and irreversible loss rather than treating a successful precheck as elimination of the race.
- Inactive Hermes archive/database backup copies may be individually disposed of after recovery-loss review; they are not live databases. Identify retained newer recovery materials and disclose what integrity/recoverability has or has not been checked. Preserve current upgrade rollback archives and Git bundles unless their recovery/unique-commit value has been reviewed and deletion specifically approved. Do not remove the whole backups parent merely because old children are approved.
- Live models/indexes/databases, credentials, system data, application containers, Docker volumes/VMs and runtime state remain protected under general cleanup authority. Do not elevate privileges, change TCC/security settings, stop processes without separate authority, or use shell-only filesystem manipulation to bypass those protections. REPORT targets remain report-only.
- Whole Trash is a collection-wide exception only when explicitly authorized by the owner. Review the current account Trash contents and irreversible loss of personal files, offline models/databases, workspaces and backups. This covers already-disposed copies, not their live originals. Dispose of reviewed immediate children, not the Trash directory itself; never traverse symlinks or include another volume without separate scope review. New/changed entries or mounted nested volumes require a new review, not a wider deletion.

### Review, execution and proof

1. Persist the manifest, task authorization, exclusions, read-only evidence and a true/false acceptance checklist under a dated local audit directory before mutation. Checklist: exact scope, recovery loss, no active/protected targets, available execution tool, fresh identity/use checks, writable audit records and actual effect.
2. An independent reviewer must approve each item/method with reachable evidence anchors. Missing evidence, silence, uncertainty or timeout is not approval. A blocked item stays untouched; independently approved items may proceed.
3. Use the approved scoped native command, exact-path filesystem operation or supported native UI. The selected method must be runnable in the current environment; no GUI driver is required for command execution. If choosing UI, load its skill and obey its permissions; missing GUI capability blocks that method only. No hidden permission bypass, disabled mac-doctor move implementation or change of method after a failure without renewed review.
4. Immediately before dispatch, revalidate the complete selection/manifest and target/parent identity against fresh filesystem metadata, verify containment/symlinks/device and active use, then persist the attempt record. A failed CLI identity/use/protection gate is equally a failure here; a CLI lack of capability/catalogue entry is not itself evidence of unsafe or forbidden owner-authorized disposal.
5. Record outcomes separately from mac-doctor CLI receipts when using another tool. Include exact targets, operation, owner/reviewer anchors, timestamp, output/exit/error/partial status, and postconditions. Keep attempted, completed and measured effects separate. Do not silently convert partial/unverified execution into success.
6. Verify filesystem postconditions and APFS container free bytes before/after, plus necessary retained app-state checks. Moving to Trash and command delivery alone prove no reclaimed space. Report nominal allocation and measured delta separately; permanent removal has no “Put Back”. Do not retry a failed operation by another method without independent review.


## Approval and apply sequence

1. Run `scripts/mac-doctor clean plan` (optionally narrow with `--target ID`; use `--include-caution` only when relevant). Inspect all exact paths, classes, actions, and sizes in the returned plan.
2. Present the plan and consequences to the user. Wait for explicit approval in the current turn for those listed actions. If the response may arrive after expiry, offer narrowly scoped unchanged-manifest renewal as part of that approval, rather than repeatedly generating plans that expire while waiting.
3. Only then run `scripts/mac-doctor clean apply PLAN_ID --yes`. If the current approval explicitly includes unchanged-manifest renewal, add `--renew-if-unchanged`; never infer this extra permission from ordinary approval or a prior turn. Never broaden the plan after approval.
   CAUTION remains CLI review-only (`CAUTION_APPLY_ENABLED = False`). `apply` refuses it. Owner-authorized exact-target disposal uses the separate reviewed workflow above, not this CLI implementation; active-use, identity and protection failures remain blockers.
4. Report each result and receipt, plus before/after/delta measured free bytes from `diskutil info -plist /`. A missing measurement is unknown, not zero. Item nominal sizes are estimates, not reclaimed space.

`--yes` is a CLI gate, not a substitute for the conversational approval gate. Do not apply changed or expired plans, or unclear approvals. The only expiry exception is explicitly authorized `--renew-if-unchanged`, whose equality check creates and immediately applies a separate fresh plan; it never extends the old plan's lifetime.

### Explicit unchanged-manifest renewal

Both the approved scan and the fresh scan must contain known, nonnegative integer sizes. `"unknown"` size values, invalid types, or negative sizes refuse renewal; two failed measurements never count as unchanged allocation. This extra gate is specific to renewal and does not alter ordinary non-renewing apply policy.

For an expired plan, `clean apply PLAN_ID --yes --renew-if-unchanged` requires a nonempty list of SAFE/native items on the current host. Its item identity/target list must still match the saved plan ID's original fingerprint seed. The engine selects only those target IDs, performs fresh planning without CAUTION inclusion, and compares the host and every complete item dictionary, including size, identity, native scope/environment/command and policy fields. Missing, additional or changed items, unknown added fields, native resolver failures and other planning errors refuse without cleanup. The old plan's bytes remain unchanged.

Only an exact match proceeds immediately through normal apply gates using the new plan ID: one-hour TTL, current catalogue policy, age, containment, fingerprint, in-use checks, native scope and durable receipt writability remain enforced. CAUTION/protected/report-only/empty manifests cannot renew. A fresh scan does not replace the in-use check or authorize a different deletion method.

Renewed output and durable attempt/outcome receipts use the fresh `plan_id` and include `approved_plan_id` / `renewed_from` naming the original approved plan. Plan-file creation is exclusive; a same-second ID collision receives a numeric suffix instead of overwriting the existing plan.

## Apply gate order and fail-closed behavior

The engine requires `--yes`, loads the saved plan, rejects expired plans, preflights receipt-log writability, then captures Data-volume free bytes. For each item it loads policy from the current catalogue—not from mutable policy fields in the saved plan—and revalidates:

1. target is currently declared SAFE/CAUTION and action is native or Trash;
2. hard-deny rules reject protected system/user data;
3. path remains inside the exact catalogue-declared pattern; symlink escapes are rejected;
4. `(dev, inode, mtime)` still matches and catalogue class/action/native command/environment/in-use/minimum-age/rebuildable policy matches the plan;
5. current minimum age still holds; SAFE requires the catalogue native command; CAUTION is always refused (review-only by design);
6. when required, `lsof` exit 1 counts as idle only if stderr is empty and the path still exists. Positive, error, timeout, or any other result is unknown/in-use and refuses;
7. after the in-use probe, revalidate the path; resolve and verify native scope from the catalogue again at apply, then revalidate path identity again before authorizing the operation;
8. append and fsync a durable `phase:"attempt"` receipt before mutation. If this write fails, do not dispatch the action. Revalidate the path once more immediately before dispatch; append a `phase:"outcome"` receipt after the attempt or refusal.


SAFE uses the declared tool-native command, scoped environment and verified scope. CAUTION remains review-only inside the CLI. The test-only Trash-move code stays behind `CAUTION_APPLY_ENABLED = False`; this revision does not enable it. Neither its fd-pinning/exclusive pathname rename nor the separate reviewed filesystem/UI workflow guarantees approved-inode binding under ABA replacement. Do not invoke the disabled implementation or claim the new policy fixes that operating-system limitation.

## Plan, receipt, and result fields

A plan object contains `plan_id`, `host`, `created_at`, `expires_at`, and `items`. Each item records `target`, exact `path`, `size_bytes` (may be `"unknown"`), `dev`, `inode`, `mtime`, `file_type` (`directory|file|other`), `class`, `action`, `native_cmd`, `native_env`, `native_scope`, `min_age_days`, `inuse_check`, and `rebuildable`. The catalogue's `scope_path`, `resolve_cmd`, and policy fields remain authoritative; plan fields are checked against them and do not grant policy.

Each receipt line contains `ts`, `plan_id`, `item` path, `action`, `method`, `phase` (`attempt|outcome`), `result`, `reason`, `size_bytes`, and `trash_path`. Failed post-move verification receipts additionally include `actual_location`, `approved_object_location`, and `manual_recovery:true`; these are manual recovery pointers, not proof that the approved object remained at the original path. The attempt receipt is flushed and fsynced before dispatch; failure aborts the item without mutation. Apply output contains `plan_id`, `refused`, per-item `items`, free bytes before/after/delta, nominal size sum, and note. `clean receipts --last N` reads the latest N lines (default 50); it is not a cleanup action.

Time Machine snapshot deletion is never automated or bulk-performed. Its per-date command is report-only; the user decides whether to run it.
