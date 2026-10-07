# mac-doctor

mac-doctor is a local, read-only-by-default macOS diagnostic CLI. It runs evidence-based checks across performance, storage, security, hardware, network, and developer environment; reports scoped scores with coverage; inventories narrow cleanup targets; and can retain local collector history. It does not combine these into a misleading single health grade or clean as a side effect of checking.

## Quick start

Run commands from the skill directory, or use its absolute path as installed. The executable is `scripts/mac-doctor`.

```sh
scripts/mac-doctor install                 # install and verify the LaunchAgent collector
scripts/mac-doctor status                  # inspect LaunchAgent and latest snapshot
scripts/mac-doctor check                   # all supported checks
scripts/mac-doctor score --json            # subsystem scores and coverage
scripts/mac-doctor storage                 # read-only cleanup-target inventory
scripts/mac-doctor clean plan              # create a one-hour plan; review it, do not auto-apply
```

Cleanup is separate from diagnosis. Show a freshly generated exact plan and obtain explicit approval in the current turn before running `scripts/mac-doctor clean apply PLAN_ID --yes`; a previous approval or plan display is insufficient. Only SAFE items run, using their tool-native cleanup command. The sole owner-authorized Hermes-profile exception is exactly four native caches: `hermes-regent-uv-cache` (`regent/home/.cache/uv`, `UV_CACHE_DIR`), `hermes-regent-npm-cache` (`regent/home/.npm/_cacache`, scoped to `regent/home/.npm` via `npm_config_cache`), `hermes-regent-pip-cache` (`regent/home/Library/Caches/pip`, `PIP_CACHE_DIR`), and `hermes-cron-worker-pip-cache` (`cron-worker/home/Library/Caches/pip`, `PIP_CACHE_DIR`). They use native scoped cache commands and require in-use checks and a 30-day minimum age. These four paths are excluded from the legacy `hermes-profile-dev-cache` CAUTION group; every other profile cache remains manual. No wildcard or broad deletion is authorized. Chrome caches, old Hermes backups, models/indexes/databases, and other runtime data are unchanged/protected/manual. CAUTION items remain review-only: they appear with `--include-caution`, `apply` refuses them, and users may move them to Trash in Finder. REPORT items (Time Machine and Homebrew) are inventory-only; review printed commands before deciding. See [`references/cleanup.md`](references/cleanup.md).

**Approval delayed past the one-hour expiry?** Do not repeatedly generate plans that expire while waiting for a response. Present the exact manifest and offer explicit unchanged-manifest renewal as part of the user's current approval. Only with that authorization, run `scripts/mac-doctor clean apply PLAN_ID --yes --renew-if-unchanged`. The engine renews only expired, nonempty SAFE/native plans whose host, plan-ID binding, and complete item manifest match a freshly scanned plan for the same targets; it immediately runs the normal apply gates. Differences refuse without cleanup. The original plan remains unchanged, the fresh plan still expires after one hour, and output/receipts link the fresh `plan_id` to `approved_plan_id` / `renewed_from`. No general deletion permission or CAUTION execution is enabled.

## Architecture

- **Core CLI** (`scripts/mac-doctor`, `scripts/macdoctor/`): on-demand checks, scores, storage scan, clean plan/apply/receipts, history, status, and install/uninstall. Checks and scans are read-only.
- **L1 collector** (`scripts/collector-daemon.py`): optional LaunchAgent samples metrics to local SQLite, evaluates alerts, and prunes history according to retention. Installing it does not register Hermes jobs.
- **Optional Hermes adapter** (`adapters/hermes/`): watchdog and triage scripts plus cron-job specifications. The JSON is a specification; `mac-doctor install` prints it but does not register jobs. To edit jobs in the cron-worker profile, use `hermes -p cron-worker cron edit`. See [`adapters/hermes/README.md`](adapters/hermes/README.md).

## Data and configuration

Paths are resolved by `scripts/macdoctor/paths.py`. The data directory precedence is `MAC_DOCTOR_DATA_DIR` (legacy override `MAC_DOCTOR_INSPECTION_DIR` is also accepted), then an existing `~/.hermes/inspection`, then `~/Library/Application Support/mac-doctor`. Account home comes from the OS account database rather than an agent profile's redirected `HOME`. Collector settings are initialized from `templates/config.json`; existing config is read from the resolved data directory. Data stays local unless the optional webhook is configured.

## FAQ

**Does it run on non-macOS systems?** No. The CLI refuses unsupported platforms; no `sudo` is used. Controls that require elevated privilege are skipped rather than elevated automatically.

**What does uninstall do?** `scripts/mac-doctor uninstall` is a dry-run. `scripts/mac-doctor uninstall --force` boots out the LaunchAgent; it leaves Hermes cron jobs untouched. The collector data is not removed.

**Why doesn't mac-doctor move CAUTION items to Trash itself?** macOS can only rename by directory + name, so an automated move cannot be bound to the object you approved; a same-user process could swap it in between. The plan lists exact paths and sizes so you can move them in Finder (which keeps "Put Back"). Trash frees space only when emptied.

**What is the optional Jev watchdog gate?** Jev (TypeSafe) judges whether a non-critical alert is covered by past notes. In the default `shadow` mode it only records what it would have suppressed; `enforce` must be set explicitly before it can silence anything. It is fail-open and never authorizes cleanup, process kills or security decisions. The key is read from `TYPESAFE_API_KEY` or `~/.config/typesafe/api_key`. Run `scripts/mac-doctor jev preview --json` (local) or `jev ask --json` (live). See [`references/jev.md`](references/jev.md).

**Where are command details and current cleanup targets?** See [`references/cli.md`](references/cli.md), [`references/checks.md`](references/checks.md), and [`references/cleanup.md`](references/cleanup.md).

## Inspiration

| Source | Adopted idea | Boundary |
|---|---|---|
| [Mole](https://github.com/tw93/Mole) | explicit cleanup targets and review-before-action | no broad purge, TUI, or deletion semantics copied |
| [Mac Audit](https://github.com/gfreedman/mac_audit) | stable check results and scoped score model | unavailable results do not earn points |
| [macguard-audit](https://github.com/Neo23x0/macguard-audit) | structured outputs and bounded checks | no root-check default |
| [Pearcleaner](https://github.com/alienator88/Pearcleaner) | Trash as a reversible destination | Trash movement is not reported as freed space |
| [mSCP](https://github.com/usnistgov/macos_security) | traceable security controls | no automatic enforcement of personal-device baselines |
| [Anthropic skills](https://github.com/anthropics/skills) | concise skill routing with scripts/references | implementation stays in tested CLI |
