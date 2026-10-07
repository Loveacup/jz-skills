# Cleanup catalogue and safety gates

`storage` and `clean targets` are read-only. The source of truth is `scripts/macdoctor/targets.json`; `clean plan` accepts only SAFE/CAUTION targets, writes a host-bound plan under the resolved data directory's `plans/`, and expires it after one hour. Default planning includes SAFE targets only. `--include-caution` explicitly includes CAUTION candidates in the displayed plan; it does not authorize application. `--target ID` is repeatable. NEVER targets cannot be planned; REPORT targets are inventory-only and have no execution path.

## Current target catalogue

| ID | Class | Action / exact native scope |
|---|---|---|
| `npm-cache` | SAFE | `npm cache clean --force --cache <scope>`; scope `.npm`, resolved with `npm config get cache`. |
| `uv-cache` | SAFE | `uv cache clean` with `UV_CACHE_DIR=<scope>`; scope `.cache/uv`, resolved by `uv cache dir`; in-use check required. |
| `pip-cache` | SAFE | `python3 -m pip --cache-dir <scope> cache purge`; scope `Library/Caches/pip`, resolved by `python3 -m pip cache dir`. |
| `brew-cache` | REPORT | `storage` resolves `brew --cache`, measures the cache, and includes the bounded `brew cleanup --dry-run` output, parsed item count/size where available, and manual command `brew cleanup`. Not plannable. The manual command can remove prefix/older formula versions and autoremove dependencies; user must review the dry-run output before deciding. |
| `playwright-browsers` | CAUTION (review-only) | Browser runtimes in `Library/Caches/ms-playwright` older than 30 days; user moves them in Finder. |
| `xcode-derived-data` | CAUTION (review-only) | DerivedData older than 14 days; user moves it in Finder. |
| `ios-devicesupport` | CAUTION (review-only) | DeviceSupport older than 90 days; user moves it in Finder. |
| `npm-npx-stale` | CAUTION (review-only) | `_npx` items older than 30 days; user moves them in Finder. |
| `chrome-cache` | CAUTION (review-only) | Chrome cache older than 7 days; quit Chrome first; user moves it in Finder. |
| `hermes-profile-dev-cache` | CAUTION (review-only) | Per-profile development caches older than 30 days, excluding exactly the four owner-authorized native exceptions listed below. Every other profile cache remains manual; model/index paths are excluded. |
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

## Approval and apply sequence

1. Run `scripts/mac-doctor clean plan` (optionally narrow with `--target ID`; use `--include-caution` only when relevant). Inspect all exact paths, classes, actions, and sizes in the returned plan.
2. Present the plan and consequences to the user. Wait for explicit approval in the current turn for those listed actions. If the response may arrive after expiry, offer narrowly scoped unchanged-manifest renewal as part of that approval, rather than repeatedly generating plans that expire while waiting.
3. Only then run `scripts/mac-doctor clean apply PLAN_ID --yes`. If the current approval explicitly includes unchanged-manifest renewal, add `--renew-if-unchanged`; never infer this extra permission from ordinary approval or a prior turn. Never broaden the plan after approval.
   CAUTION items are review-only by design (`CAUTION_APPLY_ENABLED = False`, decided 2026-10-04): macOS renames only by directory fd + name, so a move cannot be bound to the approved inode. `apply` refuses every CAUTION item with a receipt. Present CAUTION entries so the user can move them in Finder.
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


SAFE uses the target's declared tool-native command with the catalogue-specified environment and verified scope. CAUTION is review-only by design (see above). The Trash-move code path remains in `clean.py` behind `CAUTION_APPLY_ENABLED` and is exercised only by tests. It uses an fd-pinned object, an exclusive `renameatx_np(RENAME_EXCL)`, post-move identity/binding checks, and fail-closed `manual_recovery` receipts. It is not reachable in production. Turning it on requires a new owner decision, because a pathname rename can be ABA-swapped by a same-user process (review rounds 3–5, 2026-10-04).

## Plan, receipt, and result fields

A plan object contains `plan_id`, `host`, `created_at`, `expires_at`, and `items`. Each item records `target`, exact `path`, `size_bytes` (may be `"unknown"`), `dev`, `inode`, `mtime`, `file_type` (`directory|file|other`), `class`, `action`, `native_cmd`, `native_env`, `native_scope`, `min_age_days`, `inuse_check`, and `rebuildable`. The catalogue's `scope_path`, `resolve_cmd`, and policy fields remain authoritative; plan fields are checked against them and do not grant policy.

Each receipt line contains `ts`, `plan_id`, `item` path, `action`, `method`, `phase` (`attempt|outcome`), `result`, `reason`, `size_bytes`, and `trash_path`. Failed post-move verification receipts additionally include `actual_location`, `approved_object_location`, and `manual_recovery:true`; these are manual recovery pointers, not proof that the approved object remained at the original path. The attempt receipt is flushed and fsynced before dispatch; failure aborts the item without mutation. Apply output contains `plan_id`, `refused`, per-item `items`, free bytes before/after/delta, nominal size sum, and note. `clean receipts --last N` reads the latest N lines (default 50); it is not a cleanup action.

Time Machine snapshot deletion is never automated or bulk-performed. Its per-date command is report-only; the user decides whether to run it.
