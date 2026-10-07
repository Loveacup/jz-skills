# CLI reference

Run `scripts/mac-doctor COMMAND --help` for the executable parser. Root options are `-h|--help` and `--version`. Every command is local; check and score require Darwin. JSON is enabled per subcommand where shown.

## Commands and flags

| Command | Flags / arguments | Result |
|---|---|---|
| `check` | `--category {performance,storage,security,hardware,network,devenv}` repeatable; `--id ID` repeatable; `--timeout S` (default 10, `0<S≤300`); `--json` | All registered checks by default; report envelope below. |
| `score` | `--timeout S`; `--json` | `{scores:{security,performance,storage,coverage},status}`. |
| `storage` | `--json` | Read-only scan summary: `items`, `item_count`, `known_size_bytes`, `unknown_size_count`, `report_only_count`, `read_only:true`. |
| `clean targets` | `--json` | Current target catalogue as JSON. |
| `clean plan` | `--target ID` repeatable; `--include-caution`; `--json` | Saves one-hour plan and emits its ID and items. SAFE only by default; `--include-caution` adds CAUTION items for review only (apply always refuses them). |
| `clean apply PLAN_ID` | required `--yes`; optional `--renew-if-unchanged`, `--json` | Revalidate and attempt exactly the approved plan; only SAFE items execute. Explicit unchanged-manifest renewal may replace an expired SAFE/native plan with a matching fresh plan, then immediately apply through normal gates; defaults still refuse expiry. |
| `clean receipts` | `--last N` (default 50); `--json` | Latest receipt rows. |
| `history` | `--hours N` (default 24, float); `--json` | Per-metric min/avg/max and optional disk depletion forecast. |
| `status` | `--json` | Observed LaunchAgent, snapshot freshness, Hermes adapter state. |
| `verify` | `--json` | `checks` array with `name`, `status` (`PASS|FAIL|UNKNOWN`), `observation`. Hermes cron is read from its jobs JSON, not through a shell `cronjob` command. |
| `install` | none | Installs LaunchAgent, verifies it with `launchctl print`, prints Hermes cron specs only; does not register them. Uses Homebrew Python if executable, else `/usr/bin/python3`. |
| `uninstall` | `--force` | Default dry-run. With force, boots out LaunchAgent only; Hermes jobs are unchanged and data is retained. |
| `preferences` | optional positional `target` (default `show`; `edit` or dotted key also accepted) | `show` prints preferences JSON; `edit` opens file using `$EDITOR` or `vi`; dotted key prints selected value. |
| `triage` | none | Dispatches to optional Hermes triage adapter; unavailable Hermes/adapter returns failure. |

## JSON shapes

`check --json` emits:

```json
{
  "schema_version": "1.0",
  "tool_version": "from the CLI package",
  "collected_at": "UTC ISO-8601",
  "host": {"model": "...", "os": "...", "arch": "..."},
  "results": [{"id":"...","category":"...","status":"pass|warn|crit|unknown|error|skip","title":"...","value":null,"unit":null,"evidence":"...","source":"...","duration_ms":0,"recommendation":null,"collected_at":"..."}],
  "scores": {"security": 0.0, "performance": null, "storage": 0.0, "coverage": 0.0}
}
```

A score group with no checks in this run is `null` (text output: "not checked"), never 0. `score --json` contains only `{scores:{security,performance,storage,coverage},status}`. `history --json` contains `{hours,metrics:{metric:{min,avg,max}},disk_full_forecast_days}`. Forecast is `null` without adequate decreasing samples. Metric names: `cpu_percent`, `swap_used_mb`, `swap_total_mb`, `disk_free_gb`, `disk_total_gb`, `battery_health`, `battery_cycles`, `thermal_throttled`, `load_avg_1min`, `load_avg_5min`, `load_avg_15min`.

`status --json` has:

- `launchagent`: `state`, `last_exit`, `run_interval` (or `error`/observation); state is loaded, not loaded, or UNKNOWN.
- `last_snapshot`: UTC `timestamp`, `age_seconds`, `health` (`ok|stale|unknown`); over 900 seconds is stale.
- `hermes_adapter`: detected state and any state-file data, or not installed/configured/unknown.

`verify --json` is `{checks:[{name,status,observation},...]}`. It checks LaunchAgent loaded state, latest snapshot freshness, and Hermes cron job definitions when Hermes exists. Missing Hermes is `UNKNOWN`, not a pass. UNKNOWN does not make verify fail; only a FAIL yields exit 1.

`storage --json` item entries include target/title/path, size (or `"unknown"`), class/action, mtime, and age. The Time Machine REPORT item carries count, dates, `estimated_purgeable_bytes:"unknown"`, per-date `manual_commands`, and status. The Homebrew REPORT item includes resolved cache path/size, `dry_run_command`, `dry_run_output`, `dry_run_item_count`, `dry_run_size_bytes`, `manual_command`, and status. Its manual command is `brew cleanup`; review the dry-run output because the command can remove old installed formula versions and autoremove dependencies. NEVER entries are omitted.

`clean plan` fields are documented in `cleanup.md`; `clean apply` reports refusal flag, per-item receipts, free bytes before/after/delta, nominal size sum, and explanatory note. `clean receipts --json` is a JSON array of receipt objects `{ts,plan_id,item,action,method,phase,result,reason,size_bytes,trash_path}`; `phase` is `attempt` or `outcome`. CAUTION items always produce a `refused` outcome with reason "CAUTION items are review-only by design".

`--renew-if-unchanged` is an additional authorization capability, not the default meaning of `--yes`. Use it only when the current user approval explicitly covers renewal of the displayed exact manifest. Renewal requires a nonempty SAFE/native plan, matching host, manifest bound to its saved plan ID, and complete item equality against fresh planning for the same targets. Differences or planning errors refuse without dispatch. The old plan remains unchanged; the fresh plan retains the one-hour TTL. Successful renewal output and its attempt/outcome receipts include `approved_plan_id` and `renewed_from`, both naming the original plan, while `plan_id` names the fresh applied plan. See [`cleanup.md`](cleanup.md).

## Exit codes

- **check/score:** 0 pass/skip; 1 warn, unknown, or error; 2 critical; 3 usage/internal error.
- **storage/clean:** storage and successful targets/plan return 0; clean plan invalid target/error returns 2; apply refusal returns 2, per-item failed action returns 1; receipts read/parse error returns 3; parser usage error returns 2.
- **status:** 1 when latest snapshot is stale/unknown or LaunchAgent is not loaded; otherwise 0.
- **verify:** 1 if any check is FAIL, otherwise 0 (UNKNOWN is not FAIL).
- **install/uninstall/history/preferences/triage:** 0 on successful operation; failures return nonzero (install/uninstall propagate subprocess status where available; history read error 1; invalid preference key 1; unavailable Hermes triage 1). Argparse usage errors return 2.

JSON data is evidence, not proof of full system visibility. Report unknown/error/skip and coverage alongside any score.
