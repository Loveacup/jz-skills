# L1 collector and alerts

`scripts/collector-daemon.py` is a one-shot collector, normally invoked by its LaunchAgent. Default cadence is 600 seconds. Each run samples local metrics, stores a SQLite snapshot, evaluates configured threshold/anomaly/process alerts, optionally notifies, removes snapshots older than retention, and vacuums. It is separate from CLI `check`; installing it does not add Hermes cron jobs.

## Configuration

The collector reads the resolved data directory's `config.json`; if absent it writes defaults. `templates/config.json` includes explanatory template fields. Runtime behavior is implemented for these keys:

| Key | Default / meaning |
|---|---|
| `collection.interval_seconds` | 600; LaunchAgent cadence; documented range 60–3600 in template. |
| `collection.retention_days` | 90; old `snapshots` are deleted and database vacuumed. |
| `collection.quiet_hours.enabled`, `.start`, `.end` | true, 23, 7 local-hour window; supports midnight-wrap and same-day ranges. Noncritical native notifications are suppressed inside the window; red/critical notifications bypass quiet hours. |
| `alerts.cpu_threshold` | 80%; instantaneous process CPU alert applies only when `cpu_sustained.enabled` is false. |
| `alerts.memory_pressure_threshold` | `high`; pressure threshold. |
| `alerts.swap_threshold_gb` | template: 4; collector built-in fallback: 8. Alert if used swap exceeds configured GB. |
| `alerts.disk_threshold_percent` | 10; alert when free percent is below threshold. |
| `alerts.battery_health_threshold` | 80; alert below threshold. |
| `cpu_sustained.enabled`, `.threshold`, `.window_minutes` | true, 80%, 5 minutes. Per-process CPU must be above threshold for consecutive samples. Required sample count is `ceil(window_seconds / interval_seconds) + 1`, with a minimum of 1; gaps where the process is absent remove its watch state. |
| `anomaly.enabled`, `.baseline_days`, `.sigma` | true, 7 days, 2.0 standard deviations. Only worsening direction alerts: CPU/swap/memory rank/disk-used rising and disk-free falling. Better-direction changes do not alert. |
| `webhooks.enabled`, `.url`, `.min_severity`, `.include_anomaly` | false, empty URL, `red`, false. Sends HTTP POST JSON `{title,message,severity,timestamp}` to the configured URL; severity is `yellow` or `red`; webhook timeout is 5 seconds. Anomaly events require `include_anomaly=true`. |

The template also contains `profiles`, `output`, and `tiers` sections, but these do not drive the current collector. `output.json_schema_version` is used for collector JSON version; other output-format/fail-on-critical toggles and profile/tier mappings are not general CLI controls. Existing config is loaded as-is; it is not automatically merged with defaults.

## Outputs and notifications

Run `python3 scripts/collector-daemon.py --json` to collect and print structured JSON. The object contains `schema_version`, `timestamp`, `snapshot`, `diagnosis`, and `alerts`; each alert has `text`, `severity`, and `is_anomaly`. JSON mode persists the snapshot but exits before notifications and weekly forecasts. Normal mode may send macOS notifications and configured webhook POSTs; Sunday runs can emit disk/battery forecasts. Logs append to `collector.log` in the data directory when writable.

The periodic collector alerts differ from `check` thresholds. For CLI check thresholds and score semantics see `checks.md`.

## SQLite schema and history

`history.db` has `snapshots` with `id`, `timestamp`, `cpu_percent`, `memory_pressure`, `swap_used_mb`, `swap_total_mb`, `disk_free_gb`, `disk_total_gb`, `battery_health`, `battery_cycles`, `thermal_throttled`, `load_avg_1min`, `load_avg_5min`, `load_avg_15min`, `top_cpu_process`, and `top_mem_process`. An index covers `timestamp`.

`process_watch` stores `pid`, `ppid`, `cmd`, `first_above_ts`, `triggered_ts`, and `sample_count` (added compatibly when absent), with `(pid, ppid, cmd)` primary key. It persists consecutive process-watch samples between collector runs. Retention cleanup applies to snapshots; the process watcher removes records for processes not seen on a run.

`history --hours N` summarizes min/average/max for available metrics and may calculate `disk_full_forecast_days` when there are at least two timestamped disk-free points showing decline; otherwise it is `null`. History reads the database and does not trigger collection.

## Data location

The collector uses `macdoctor.paths`: `MAC_DOCTOR_DATA_DIR` first (legacy `MAC_DOCTOR_INSPECTION_DIR` accepted), then existing `~/.hermes/inspection`, then `~/Library/Application Support/mac-doctor`. Account home comes from the system account record, not a Hermes profile's redirected `HOME`.
