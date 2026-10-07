# Manual diagnostics playbook

Start with a narrow CLI category; expand only when the evidence points to a specific cause. These commands are observational. Do not elevate privilege to make a failed probe appear complete. If access is unavailable, report unknown and let the user decide whether to inspect it.

## Crash / swap symptoms

1. Run `scripts/mac-doctor check --category performance` and note `performance.swap_usage`, memory pressure, and aggregated processes. The >2 GiB / >5 GiB swap thresholds are findings, not proof of a particular process crash cause.
2. If a Hermes service is affected, inspect its existing service and log state through the user's normal Hermes operations; check timestamps and confirm reconnect status rather than trusting a single “running” line. Check port conflicts only when logs indicate them. Do not rewrite databases or credentials as a generic recovery step.
3. Re-run `status`/`verify` and report service state, last snapshot age, and any unknown probes separately. Do not assume a Telegram connection from gateway process presence alone.

## Zombie processes

A zombie has already exited; sending a signal to its PID does not reap it. Identify PID, PPID, process state, and parent identity first. Avoid killing a parent casually: it may own live work or restart under launchd.

The Hermes watchdog's zombie action is opt-in and limited to configured known parent identities with `auto_kill` enabled, applicable gates, and a three-hour cooldown. It sends SIGTERM, waits one second, then rechecks PID, PPID, start time, and command. SIGKILL is sent only if all identity fields still match. A changed/missing identity, failed probe, or failed gate must not be bypassed with manual bulk signals. Review actual preference/config gates and watchdog output before considering any action; retain explicit user approval for manual process termination.

## Low-space investigation

- Begin with `check --category storage` and `storage`. Container free space is measured through `diskutil`; APFS `df -h /` is a volume view and may not describe container availability.
- When free space is critically low, avoid a full-tree recursive scan that can stall on congested storage. Check selected known directories one at a time; a failed/slow scan is incomplete evidence.
### Common large-data paths (inspect locally; no assumed size or disposability)

| Account-home path pattern | What it is | Assessment | Classification |
|---|---|---|---|
| `~/.npm/_cacache` | npm download cache | Inspect current inventory | `npm-cache` (SAFE; native npm cleanup only) |
| `~/.cache/uv` | uv package cache | Inspect current inventory | `uv-cache` (SAFE; native uv cleanup only) |
| `~/Library/Caches/Homebrew` | Homebrew downloads cache; `storage` also reports bounded `brew cleanup --dry-run` candidates | Inspect current inventory | `brew-cache` (REPORT only; `brew cleanup` can affect prefix/older formula versions and autoremove dependencies—review dry-run first) |
| `~/Library/Caches/ms-playwright` | Playwright browser runtimes | Inspect current inventory | `playwright-browsers` (CAUTION; review-only) |
| `~/Library/Developer/Xcode/DerivedData` | Xcode build products | Inspect current inventory | `xcode-derived-data` (CAUTION; Trash only) |
| `~/.hermes/profiles/<profile>/home/{.cache/uv,.cache/puppeteer,.npm/_cacache,Library/Caches/ms-playwright,pip,node-gyp}` | Profile-isolated development caches | Inspect current inventory | `hermes-profile-dev-cache` (CAUTION; only catalogued paths) |
| `~/.cache/qmd/models` or profile qmd model directory | qmd model assets; indexes are separate, stateful data | Inspect current inventory | `qmd-models` (NEVER; protected) |
| `~/.cache/huggingface` | Downloaded/production models | Inspect current inventory | `huggingface-models` (NEVER; protected) |
| `~/Library/Application Support/Claude/vm_bundles` | Claude Code environment bundles | Inspect current inventory | Investigate-only; no cleanup target |
| `~/Library/Application Support/Google/Chrome` | Browser profile and application data, not just cache | Inspect current inventory | Investigate-only; no cleanup target |
| `~/Library/Application Support/{Trae,Cursor,BraveSoftware,Discord}` | Application support/state | Inspect current inventory | Investigate-only; no cleanup target |

Current inventory from `storage` and a reviewed exact plan—not historical sizes or path names—is the basis for decisions; target classes do not bypass approval.

If a swap increase coincides with gateway termination, treat it as an incident signal, not a proven cause. Inspect the Hermes service's logs for termination/shutdown context, load fields, port conflicts, and keepalive failures; then confirm actual reconnect status rather than relying on process presence alone. These logs are Hermes-specific and may not exist on a non-Hermes Mac.

- Collect `check --category performance` evidence first; a swap reading alone does not establish why a gateway exited.
- Do not edit tokens, restart services, or repair databases as an assumed fix; report observed signal and ask before any service/config change.

- Inspect caches individually and review the actual path, owner, and contents before planning. The cleanup catalogue is intentionally narrow; unlisted data is not implicitly safe.
- `clean plan` gives exact candidate objects. Display and review it with the user before a same-turn explicit approval and gated apply. Never manually replace a refused action with raw deletion or a wider glob.
- For local Time Machine snapshots, `storage` reports dates and per-date commands only. Consider at most one exact snapshot command after user review; never bulk-thin/delete snapshots as part of a routine.

## Profile cache duplication and models

Hermes may redirect a profile process's `HOME`, so a profile's `.cache`, `.npm`, or `Library/Caches` may be distinct from the account user's directories. mac-doctor data paths use the system account home; use actual discovered profile paths only for diagnosis. Compare inventory/paths rather than assuming identical caches.

qmd model assets and Hugging Face models may be production dependencies. qmd's model assets must be distinguished from per-profile indexes/SQLite state; indexes are stateful and must not be combined or removed as a deduplication shortcut. Any model sharing/symlink redesign is an explicit configuration change requiring a separate review and user approval; it is not a cache-cleanup action.

## Apps, privacy, and TCC

Use `storage` and targeted read-only inspection for large app data. Browser profiles, application support directories, messaging data, containers, backups, keychains, Photos/Mail/iCloud, and project workspaces are not disposable just because large. Telegram Group Containers hold message databases. Use `clean targets` to see the protected classifications; do not extrapolate to unlisted app paths.

TCC (Privacy & Security) databases may be inaccessible without Full Disk Access. Inaccessibility is unknown; do not request or use `sudo` as a workaround. A TCC grant is sensitive permission data, not a bloatware verdict. Review unfamiliar access entries with the user and distinguish observed identifiers from conclusions. Similarly, app signatures, helper process counts, LaunchAgents, and listener ports are leads for investigation, not proof of malware. Avoid fuzzy process-name matches and do not terminate/disable services based only on a name.

For every manual finding, record command/source, time, exact evidence, limitations, and whether any change was made. This reference does not grant permission to change settings, kill processes, delete files, or disable services.
