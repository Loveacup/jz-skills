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

Cleanup is separate from diagnosis. Owner authorization plus review of exact targets/methods/consequences is required; the owner may delegate item approval to an independent reviewer for the current task, avoiding repeated confirmation. The reviewed workflow permits scoped tool-native commands, exact-path filesystem operations or available native UI, including inactive Hermes backup copies and explicitly requested whole Trash. It is not GUI-only, manual-only or limited to CLI catalogue entries, and needs no desktop driver for command execution. CLI code is unchanged: SAFE/native gates remain, CAUTION apply stays disabled, REPORT stays inventory-only and NEVER stays protected. No privilege/security changes or live-state deletion; filesystem rechecks do not remove pathname replacement races. See [`references/cleanup.md`](references/cleanup.md).

**Approval delayed past the one-hour expiry?** Do not repeatedly generate plans that expire while waiting for a response. Present the exact manifest and offer explicit unchanged-manifest renewal as part of the user's current approval. Only with that authorization, run `scripts/mac-doctor clean apply PLAN_ID --yes --renew-if-unchanged`. The engine renews only expired, nonempty SAFE/native plans whose host, plan-ID binding, and complete item manifest match a freshly scanned plan for the same targets; it immediately runs the normal apply gates. Differences refuse without cleanup. The original plan remains unchanged, the fresh plan still expires after one hour, and output/receipts link the fresh `plan_id` to `approved_plan_id` / `renewed_from`. No general deletion permission or CAUTION execution is enabled.

## Architecture

### Storage attribution and offline reports

`scripts/mac-doctor storage analyze --json` surveys account-home/Library hot spots and Applications under a 30-second command budget. Use repeatable `--root /absolute/directory` for targeted follow-up, `--min-mb`, `--top`, `--max-entries` and `--budget-sec` (maximum 120) to control work. Existing `storage --json` remains the unchanged narrow cleanup catalogue.

For a private, shareable-by-choice static view, add `--html /absolute/new-report.html`. It is escaped, self-contained, and has no external resources, JavaScript, filesystem server or deletion buttons; an existing file is never overwritten. No browser is opened automatically. Group paths can reveal private names, so do not publish/upload the report without permission.

The analysis distinguishes APFS container free space, observed allocated directory sizes, incomplete measurements and unknown reclaimability. Parent groups are not summed; planned detailed roots avoid redundant aggregate du calls and same-inode aliases are excluded from repeat measurement/ranking. Models, toolchains, app containers and databases never become automatically disposable from their names. See [storage analysis](references/storage-analysis.md). Collector, cron configuration, cleanup catalogue and approval requirements are unchanged.


- **Core CLI** (`scripts/mac-doctor`, `scripts/macdoctor/`): on-demand checks, scores, storage scan, clean plan/apply/receipts, history, status, and install/uninstall. Checks and scans are read-only.
- **L1 collector** (`scripts/collector-daemon.py`): optional LaunchAgent samples metrics to local SQLite, evaluates alerts, and prunes history according to retention. Installing it does not register Hermes jobs.
- **Optional Hermes adapter** (`adapters/hermes/`): watchdog and triage scripts plus cron-job specifications. The JSON is a specification; `mac-doctor install` prints it but does not register jobs. To edit jobs in the cron-worker profile, use `hermes -p cron-worker cron edit`. See [`adapters/hermes/README.md`](adapters/hermes/README.md).

## Data and configuration

Paths are resolved by `scripts/macdoctor/paths.py`. The data directory precedence is `MAC_DOCTOR_DATA_DIR` (legacy override `MAC_DOCTOR_INSPECTION_DIR` is also accepted), then an existing `~/.hermes/inspection`, then `~/Library/Application Support/mac-doctor`. Account home comes from the OS account database rather than an agent profile's redirected `HOME`. Collector settings are initialized from `templates/config.json`; existing config is read from the resolved data directory. Data stays local unless the optional webhook is configured.

## FAQ

**Does it run on non-macOS systems?** No. The CLI refuses unsupported platforms; no `sudo` is used. Controls that require elevated privilege are skipped rather than elevated automatically.

**What does uninstall do?** `scripts/mac-doctor uninstall` is a dry-run. `scripts/mac-doctor uninstall --force` boots out the LaunchAgent; it leaves Hermes cron jobs untouched. The collector data is not removed.

**Must an authorized agent use Finder or ask me to delete files myself?** No. After exact-manifest review, scoped commands or filesystem APIs may perform approved disposal; native UI is optional. Current-task delegated review avoids repeated per-item confirmation. There is no new CLI command or enabled CAUTION engine path. Independent review must account for irreversible loss and pathname races; actual postconditions and APFS free-space delta are checked. Moving items to Trash alone frees no space.

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
| [storage-analyzer](https://github.com/KKKKhazix/khazix-skills/tree/322346ded8129436b3f64707789a73e732ae24d9/storage-analyzer) | root groups, ownership hints, top consumers and offline report reading flow | independently implemented; no upstream scanner/server/template copied, no automatic green cleanup or delete service |
