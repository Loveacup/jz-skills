# Optional Hermes adapter

The Hermes adapter is separate from the portable core CLI. Its entry points are `watchdog.py` and `triage.py`; cron definitions are in `cron-jobs.json`. Adapter code resolves the skill directory via `Path(__file__).resolve()` and shared locations via `macdoctor.paths`, so symlinks from a Hermes profile can target the same source.

## Installation boundary

`mac-doctor install` installs and verifies only the macOS LaunchAgent collector. It prints the cron specifications from `cron-jobs.json` for reference; it does **not** register or update Hermes jobs. Register or update them with the Hermes CLI against the cron-worker profile, e.g. `hermes -p cron-worker cron list` to find job IDs, then `hermes -p cron-worker cron edit <job_id> --prompt "<prompt from cron-jobs.json>"` (or `cron create` for a missing job). Use `mac-doctor verify` to inspect the configured jobs file read-only; it checks the expected job names and enabled state when Hermes is present.

Hermes refuses cron scripts whose real path is outside the profile's `scripts/` directory, so these names cannot be symlinks into the skill. Copy (do not symlink) `cron-shim.py` under each compatibility name. The file name selects the adapter, and the shim runs it from the skill directory (`MAC_DOCTOR_SKILL_DIR`, default `<account home>/.agents/shared/mac-doctor`):

```sh
cp "$SKILL_DIR/adapters/hermes/cron-shim.py" "$HERMES_HOME/profiles/cron-worker/scripts/mac-doctor-watchdog.py"
cp "$SKILL_DIR/adapters/hermes/cron-shim.py" "$HERMES_HOME/profiles/cron-worker/scripts/mac-doctor-triage.py"
```

Adapter changes take effect without recopying; recopy only when `cron-shim.py` itself changes. Resolve `SKILL_DIR` and `HERMES_HOME` for your environment first.

## Adapter behavior

- The watchdog calls the L1 collector in JSON mode and inspects findings. It is designed to remain quiet when there is no actionable notification; state/cooldown and triage trigger data use the resolved data directory.
- Triage is an optional Hermes-dependent interpretation layer. The core CLI works without Hermes; `triage` reports unavailable when Hermes or its adapter is absent.
- Optional zombie handling is not a general process killer. It requires configured known parent identities with `auto_kill` enabled and watchdog gates, observes a three-hour cooldown, sends SIGTERM, waits one second, then rechecks PID, PPID, start time, and command. It sends SIGKILL only when the identity is still the same. Unknown identity/probe results do not authorize a kill.
- Preferences corruption backups are content-addressed once per SHA-256. Backup listing/pruning utilities are explicit; normal load does not prune backups.

Hermes scheduled behavior is optional and independent of read-only CLI commands. Do not infer that installing the collector registered jobs, or that job JSON being present proves a job is enabled or has run. `status` and `verify` report observed state and may return unknown.
