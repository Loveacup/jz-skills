# Cleanup catalogue and safety gates

`storage` and `clean targets` are read-only. The source of truth for the CLI is `scripts/macdoctor/targets.json`; `clean plan` accepts only SAFE/CAUTION targets, writes a host-bound one-hour plan, and defaults to SAFE. `--include-caution` lists review candidates but cannot authorize CLI execution. NEVER targets cannot be planned; REPORT targets have no CLI execution path. The separately authorized native-interface workflow below changes who may operate an existing native UI, not the CLI catalogue or its gates.

## Current target catalogue

| ID | Class | Action / exact native scope |
|---|---|---|
| `npm-cache` | SAFE | `npm cache clean --force --cache <scope>`; scope `.npm`, resolved with `npm config get cache`. |
| `uv-cache` | SAFE | `uv cache clean` with `UV_CACHE_DIR=<scope>`; scope `.cache/uv`, resolved by `uv cache dir`; in-use check required. |
| `pip-cache` | SAFE | `python3 -m pip --cache-dir <scope> cache purge`; scope `Library/Caches/pip`, resolved by `python3 -m pip cache dir`. |
| `brew-cache` | REPORT | `storage` resolves `brew --cache`, measures the cache, and includes the bounded `brew cleanup --dry-run` output, parsed item count/size where available, and manual command `brew cleanup`. Not plannable. The manual command can remove prefix/older formula versions and autoremove dependencies; user must review the dry-run output before deciding. |
| `playwright-browsers` | CAUTION (CLI review-only) | Browser runtimes older than 30 days; Finder by the user or an authorized reviewed native-interface operator. |
| `xcode-derived-data` | CAUTION (CLI review-only) | DerivedData older than 14 days; same native-interface rule. |
| `ios-devicesupport` | CAUTION (CLI review-only) | DeviceSupport older than 90 days; same native-interface rule. |
| `npm-npx-stale` | CAUTION (CLI review-only) | `_npx` items older than 30 days; same native-interface rule. |
| `chrome-cache` | CAUTION (CLI review-only) | Chrome cache older than 7 days; quit Chrome first only with service-stop authority, then the same native-interface rule. |
| `hermes-profile-dev-cache` | CAUTION (CLI review-only) | Per-profile development caches older than 30 days, excluding the four native exceptions below; models/indexes remain protected. |
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

## Owner-authorized native-interface cleanup

This is an owner-approved supervised disposal workflow, not a new CLI command. CAUTION apply remains disabled. Native Finder operations also use mutable paths/selections: they do **not** solve macOS pathname ABA or provide atomic approved-inode binding. Fresh observation and independent review reduce operational risk, not eliminate it; never claim otherwise. Use this route only where the owner chose native-interface operation, not to work around a refused gate.

### Authority and scope

- The owner must authorize the current cleanup task. They may delegate exact-manifest approval to an independent reviewer (“full authority, only review required”); within that task, a reviewer-approved manifest needs no further per-item user confirmation. This is not standing permission for unrelated future cleanups, permission changes, process termination, publication, or arbitrary paths.
- Without delegated-review authority, show exact targets, operations and consequences and obtain explicit owner approval. Editing this skill alone is not authorization to delete anything.
- Resolve the real account home and inventory exact absolute paths, allocated sizes, age, purpose, active-use evidence, intended UI operation, irreversibility, and exclusions. No broad parent-folder removal, recursive path-deletion scripts, globs, symlink traversal, or guessed targets. Directory age alone does not prove inactivity. Unknown purpose/use or changed targets block that item.
- Inactive Hermes backup archives and offline database backup copies may be individually approved; they are not live databases. Review recovery value and whether a newer usable recovery point exists. Keep current upgrade rollback archives and Git bundles unless their recovery/unique-commit value has been reviewed and deletion is specifically approved. No bulk deletion of `~/.hermes/backups`.
- Active models/indexes/databases, credentials, system data, application containers, Docker volumes/VMs, and live runtime state remain protected, even with general delegated authority. No privilege escalation or TCC/security-setting changes. REPORT targets remain report-only.
- Whole Trash is the only collection-wide exception: the owner must explicitly request it, separately from moving items to Trash. Inventory the fresh contents and call out personal files, offline databases/models, workspaces and backups; the reviewer must account for those irreversible losses. This authorization covers only already-disposed items in the owner's native Trash, including offline copies of otherwise protected assets; it never authorizes deleting their originals or traversing symlinks. New or changed contents require a new review before confirmation. Trash on other volumes is excluded unless separately inventoried and authorized; if Finder cannot constrain its operation to the approved Trash scope, block rather than empty additional volumes.

### Review, execution and proof

1. Before any mutation, persist the manifest, current owner authorization, exclusions, read-only evidence, and a true/false acceptance checklist under a dated local audit directory. The checklist covers exact scope, recovery losses, no active/protected targets, driver availability, fresh native selection, and actual effect.
2. An independent reviewer, not the producing agent, must approve each item/operation with reachable evidence anchors. Silence, uncertainty, timeout or a report without evidence is not approval. A blocked item stays untouched; independent approved items may continue.
3. Load the installed native-computer-use skill and obey its permissions and freshness rules. Use the existing native Finder/app interface through its supported driver. Do not substitute AppleScript UI scripting, a different driver, filesystem APIs, `rm`, `sudo`, prune, hidden automation bypasses, or the disabled mac-doctor Trash implementation. If the driver/token/permission is unavailable, record BLOCKED and stop that operation; authorization cannot repair missing capability.
4. Immediately before the irreversible confirmation, reobserve the UI and verify the full approved selection/location against fresh filesystem metadata. Wrong selection, new items, changed evidence, in-use status or a permission dialog blocks execution and returns to review. Do not approve credential or security prompts on the owner's behalf.
5. Persist an attempt record before the action and an outcome afterward. Keep native-driver outputs separate from mac-doctor CLI receipts; include operation, exact targets, approval/reviewer anchors, timestamps, UI evidence, and error/partial status. Never silently turn a partial or unverified result into success.
6. Verify actual filesystem postconditions and APFS container free bytes before/after, plus any necessary app health check. Trash movement and native command delivery are not freed-space proof. Report nominal allocation and measured delta separately. If an operation fails, do not retry by another deletion method.


## Approval and apply sequence

1. Run `scripts/mac-doctor clean plan` (optionally narrow with `--target ID`; use `--include-caution` only when relevant). Inspect all exact paths, classes, actions, and sizes in the returned plan.
2. Present the plan and consequences to the user. Wait for explicit approval in the current turn for those listed actions. If the response may arrive after expiry, offer narrowly scoped unchanged-manifest renewal as part of that approval, rather than repeatedly generating plans that expire while waiting.
3. Only then run `scripts/mac-doctor clean apply PLAN_ID --yes`. If the current approval explicitly includes unchanged-manifest renewal, add `--renew-if-unchanged`; never infer this extra permission from ordinary approval or a prior turn. Never broaden the plan after approval.
   CAUTION remains CLI review-only (`CAUTION_APPLY_ENABLED = False`). macOS pathname rename cannot bind the operation to an approved inode. `apply` refuses every CAUTION item; any native-interface action requires the separate authority, review and driver gates above.
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


SAFE uses the declared tool-native command, scoped environment and verified scope. CAUTION remains review-only inside the CLI. The test-only Trash-move code stays behind `CAUTION_APPLY_ENABLED = False`; this policy revision does not enable it. Its fd-pinning/exclusive pathname rename and post-move checks cannot prove approved-inode binding under an ABA swap. The native-interface workflow makes no stronger atomicity claim and must not invoke that implementation.

## Plan, receipt, and result fields

A plan object contains `plan_id`, `host`, `created_at`, `expires_at`, and `items`. Each item records `target`, exact `path`, `size_bytes` (may be `"unknown"`), `dev`, `inode`, `mtime`, `file_type` (`directory|file|other`), `class`, `action`, `native_cmd`, `native_env`, `native_scope`, `min_age_days`, `inuse_check`, and `rebuildable`. The catalogue's `scope_path`, `resolve_cmd`, and policy fields remain authoritative; plan fields are checked against them and do not grant policy.

Each receipt line contains `ts`, `plan_id`, `item` path, `action`, `method`, `phase` (`attempt|outcome`), `result`, `reason`, `size_bytes`, and `trash_path`. Failed post-move verification receipts additionally include `actual_location`, `approved_object_location`, and `manual_recovery:true`; these are manual recovery pointers, not proof that the approved object remained at the original path. The attempt receipt is flushed and fsynced before dispatch; failure aborts the item without mutation. Apply output contains `plan_id`, `refused`, per-item `items`, free bytes before/after/delta, nominal size sum, and note. `clean receipts --last N` reads the latest N lines (default 50); it is not a cleanup action.

Time Machine snapshot deletion is never automated or bulk-performed. Its per-date command is report-only; the user decides whether to run it.
