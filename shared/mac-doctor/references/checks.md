# Checks, IDs, and scores

`check` is a read-only Darwin command. The implemented check registry is in `scripts/macdoctor/checks/`; each result has `id`, `category`, `status`, `title`, `value`, `unit`, `evidence`, `source`, `duration_ms`, `recommendation`, and `collected_at`. Parsers evaluate full command output; evidence text alone is truncated and redacted before output. An unavailable command, permission limitation, parse failure, or timeout is not a pass. No check invokes `sudo`; sudo-only controls are explicitly skipped. Desktop models skip battery checks.

## Check catalogue

| ID | Category | What is observed / command source |
|---|---|---|
| `performance.cpu_load` | performance | Load averages, idle %, core count: `top -l 1 -n 0`, `sysctl -n hw.ncpu`; warn when 1-min load exceeds cores or idle <20%; critical when load >2× cores and idle <10%. |
| `performance.memory_pressure` | performance | `memory_pressure`; warning for reported pressure or <10% free; critical for critical pressure. |
| `performance.swap_usage` | performance | `sysctl vm.swapusage`; warn >2 GiB, critical >5 GiB. |
| `performance.top_processes` | performance | Aggregate normalized process names from `ps -eo %cpu,%mem,comm`; warn if any aggregate CPU ≥20%. |
| `storage.apfs_container_free` | storage | `diskutil info -plist /`; warn free <15%, critical <5% of APFS container. |
| `storage.tm_local_snapshots` | storage | Read-only `tmutil listlocalsnapshots /`; reports count; command failure is unknown. This check does not remove snapshots. |
| `storage.cache.npm` | storage | `du -sk` account-home `.npm/_cacache` (the catalogue's npm download cache, not all of `.npm`). |
| `storage.cache.uv` | storage | `du -sk` account-home `.cache/uv`. |
| `storage.cache.pip` | storage | `du -sk` account-home `Library/Caches/pip`. |
| `storage.cache.playwright` | storage | `du -sk` account-home `Library/Caches/ms-playwright`. |
| `storage.cache.user_cache` | storage | `du -sk` account-home `.cache`. |
| `storage.cache.library_caches` | storage | `du -sk` account-home `Library/Caches`. |
| `storage.cache.xcode_derived_data` | storage | `du -sk` account-home Xcode DerivedData. |

Each cache check warns above 5 GiB. A confirmed absent path is pass/0; unreadable, command error, parse error, or timeout is unknown, not 0.

Named npm, uv, pip, Playwright and Xcode cache checks read their paths from `targets.json`, the same catalogue used by `storage`; aggregate `.cache` and `Library/Caches` checks remain separate. Values use MiB rounded to one decimal (the CLI's `MB` label). `storage` reports exact allocated bytes from `du -sk`; compare after rounding and allow for cache mutations between observations. Age-filtered CAUTION items may be omitted from the inventory even while the size check reports them. For directly declared paths, metadata permission failures remain inventory entries with `size_bytes:"unknown"` and unknown age/mtime rather than disappearing; this does not authorize cleanup.

| ID | Category | What is observed / command source |
|---|---|---|
| `security.sip` | security | `csrutil status`; enabled passes, disabled warns. |
| `security.gatekeeper` | security | `spctl --status`; enabled passes, disabled warns. |
| `security.filevault` | security | `fdesetup status`; off is critical. |
| `security.firewall` | security | Application firewall `--getglobalstate`; disabled is critical. |
| `security.firewall_stealth` | security | Application firewall `--getstealthmode`; disabled warns. |
| `security.ssh_remote_login` | security | `launchctl print-disabled system` override for `com.openssh.sshd`: enabled warns; disabled or no override passes; unreadable is unknown. |
| `security.screen_lock` | security | `sysadminctl -screenLock status`; reported delay `immediate` or ≤5 seconds passes, longer/off warns. If status is ambiguous, the `defaults` idleTime fallback remains unknown because it does not establish the screen-lock/password delay. |
| `security.auto_update` | security | `softwareupdate --schedule`; disabled warns. |
| `security.sharing_services` | security | `launchctl print-disabled system` overrides for Screen Sharing and File Sharing (SMB): any enabled warns; unreadable is unknown. |
| `security.sudo_only_controls` | security | Always skip: privileged controls are intentionally not invoked. |
| `hardware.battery` | hardware | Model and battery condition/cycles via `system_profiler`, `ioreg`; desktop Mac skips; health <80% or cycles >1000 warns, health <70% critical. |
| `hardware.thermal` | hardware | `pmset -g therm`; scheduler limit <100 warns. |
| `hardware.recent_panics` | hardware | Kernel reports under `/Library/Logs/DiagnosticReports` from last 30 days; any found warns. |
| `network.listening_tcp` | network | `lsof -iTCP -sTCP:LISTEN -nP`; Telnet (23), VNC (5900), or RDP (3389) listeners warn. SSH (22) and SMB (445) are reported with risk labels but are not by themselves warning statuses. Without sudo, `lsof` only sees the user's own sockets; launchd-held system sockets (SSH, Screen Sharing, SMB) are invisible here — use `security.ssh_remote_login` / `security.sharing_services` for those. |
| `network.dns_servers` | network | `scutil --dns`; no readable nameserver or command failure is unknown. |
| `network.proxy` | network | `scutil --proxy`; reports enabled system proxy settings. |
| `devenv.brew_outdated` | devenv | `brew outdated`; nonzero result is unknown, packages listed warn, absent Homebrew skips. |
| `devenv.brew_doctor` | devenv | `brew doctor`; diagnostics/warnings warn, nonzero with no diagnostic is unknown, absent Homebrew skips. |
| `devenv.dead_launchagents` | devenv | Reads account-home LaunchAgent plists; warns for absolute executable paths that do not exist; unreadable plist makes result unknown. |

## Scores and coverage

`score` runs the same check set and returns `scores` plus worst `status`; detailed `check` output includes the full report. Three scores are deliberately separate:

- `security`: only security checks; critical deducts 15 points, warning deducts 4.
- `performance`: performance, hardware, network, and devenv checks; critical deducts 10, warning deducts 3.
- `storage`: storage checks; critical deducts 10, warning deducts 3.

Each pass contributes 100; warn/crit contribute 100 minus that category's deduction; unknown/error/skip contribute zero. A score is the arithmetic mean over its selected checks, rounded to one decimal. A group with no checks in this run (e.g. `check --category storage`) is `null` in JSON and "not checked" in text, never 0. `coverage` is the percent of all results whose status is pass, warn, or crit; unknown/error/skip do not count. There is no aggregate health score. `check --category` accepts repeatable `performance|storage|security|hardware|network|devenv`; `--id` is repeatable. `--timeout` is per command, default 10 seconds, accepts values >0 and ≤300 seconds.

Exit codes: 0 pass/skip; 1 warning, unknown, or error; 2 critical finding or refusal; 3 usage/internal error. For check/score, status ordering is pass, skip, unknown, warn, error, crit; an error is not success even though it does not earn score.
