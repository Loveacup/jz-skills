# Changelog

## Unreleased

### Cleanup

- Added explicit `clean apply PLAN_ID --yes --renew-if-unchanged` for current-turn approval that includes exact-manifest renewal. Default expired plans still refuse; only nonempty SAFE/native plans can renew after host, plan-ID binding, and complete fresh-manifest equality checks. The original plan is preserved, fresh plans retain the one-hour TTL and all normal apply gates, and output/durable receipts link both plan IDs. Plan files are created exclusively with collision suffixes rather than overwriting an existing plan. CAUTION/protected/report-only targets gain no execution permission.

- Added exactly four owner-authorized native Hermes-profile cache targets (`hermes-regent-uv-cache`, `hermes-regent-npm-cache`, `hermes-regent-pip-cache`, `hermes-cron-worker-pip-cache`), each bound to its profile path/tool scope with in-use and 30-day age checks. Excluded only these four paths from legacy `hermes-profile-dev-cache`; all other profile caches remain manual. Chrome caches, old backups, models/indexes/databases and other runtime data remain unchanged/protected/manual. A fresh exact plan and separate approval in the current turn remain required; no broad or wildcard deletion is authorized. Real native smoke evidence concerns throwaway fixtures only; no live cleanup or reclaimed-space claim.

## 3.0.0 — 2026-10-04

### Breaking and behavior changes

- Replaced the former tiered skill instructions and invented unified health grade with a concise CLI router; `score` reports security, performance, storage, and coverage separately.
- The CLI is Darwin-only. `check` provides performance, storage, security, hardware, network, and devenv categories with structured `pass|warn|crit|unknown|error|skip` findings. Unknown/error/skip never add score; coverage counts only pass/warn/crit. No automatic sudo path.
- Added a narrow cleanup catalogue and explicit `clean plan` → user review/approval → `clean apply` flow. Plans expire after one hour and execution revalidates deny rules, path roots/symlinks, identity fingerprint, class, use state, and receipt writability. SAFE uses scoped native tool cleanup, CAUTION is review-only, NEVER is protected, and REPORT targets are inventory-only; Time Machine and Homebrew print manual commands. No deletion action exists in the engine.
- SAFE native cleanup is bound to an explicit catalogue scope: resolver output is checked while planning and again at apply, with scoped environment/arguments. Apply takes target policy from the catalogue rather than trusting plan policy fields; in-use probing, path identity rechecks, and durable fsynced attempt/outcome receipts gate dispatch. The `brew-cache` REPORT includes measured cache size and bounded `brew cleanup --dry-run` output; the manual `brew cleanup` may affect prefix/older formula versions and autoremove dependencies, so review the preview first.
- CAUTION targets are review-only by design (owner decision 2026-10-04 after five independent review rounds): macOS renames only by directory fd + name, so an automated Trash move cannot be bound to the approved inode (ABA swap). `apply` refuses every CAUTION item with a receipt; the user moves them in Finder. The fd-pinned exclusive-rename implementation remains behind `CAUTION_APPLY_ENABLED = False` and is test-only.
- Cleanup reports measured APFS container free-byte delta separately from nominal item sizes.
- `status` and `verify` report observed LaunchAgent/snapshot/Hermes state; unavailable evidence is UNKNOWN. `install` verifies the LaunchAgent and only prints Hermes cron specs; it does not register cron. `uninstall` is a dry-run unless `--force`, which only boots out the LaunchAgent and leaves Hermes cron unchanged.
- Data paths now resolve from `MAC_DOCTOR_DATA_DIR` (legacy `MAC_DOCTOR_INSPECTION_DIR` accepted), existing `~/.hermes/inspection`, then `~/Library/Application Support/mac-doctor`; account home does not follow a redirected Hermes profile `HOME`.
- Collector alerts only flag anomalies in the worse direction; sustained CPU uses consecutive samples derived from collection interval and alert window. Collector JSON has snapshot/diagnosis/alerts and history keeps its schema while adding `process_watch.sample_count`.
- Preferences corruption backups are content-addressed once per SHA-256; list/prune helpers require explicit use. Removed obsolete `cleanup_safety.oplog_enabled` and `cleanup-whitelist` template keys.
- Zombie cleanup is opt-in with gates and a three-hour cooldown; it sends SIGTERM, waits one second, rechecks PID/PPID/start/command identity, and only then sends SIGKILL if identity is unchanged.
- Hermes-specific watchdog/triage code and cron specs are separated under `adapters/hermes/`. Hermes rejects cron scripts that resolve outside the profile's `scripts/` directory, so the cron-worker compatibility names are copies of `adapters/hermes/cron-shim.py`, which runs the adapter from the skill directory.
- Added an opt-in, fail-open Jev (TypeSafe) semantic push gate for non-critical Hermes watchdog alerts. It defaults to `mode: shadow`, which logs `shadow_action` but never suppresses; `enforce` is required to silence anything. It writes a redacted local decision log and adds the `jev preview` / `jev ask` CLI commands. The API key is read from `TYPESAFE_API_KEY` or `~/.config/typesafe/api_key`.
- Fixed named cache checks to use the cleanup catalogue's paths: pip and Playwright under `Library/Caches`, npm download cache under `.npm/_cacache`, plus uv and Xcode. Storage inventory retains directly declared paths with unreadable metadata as unknown rather than crashing or omitting them; cleanup authorization is unchanged.

### Pre-3.0 history

The 2.x line grew from tiered manual checks into periodic monitoring. The three-layer cron architecture was introduced in June 2026: L1 collection, L2 watchdog, and L3 triage. A guarded zombie-process hook followed in July 2026. Those historical designs do not override the 3.0 CLI, cleanup, or authorization contract.
