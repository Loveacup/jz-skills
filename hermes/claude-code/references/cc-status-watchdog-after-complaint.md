# CC Status Watchdog After User Complaint

Use when the user complains that CC status was not monitored or forwarded.

## Immediate recovery sequence

1. **Acknowledge fault briefly** — no defending, no long explanation.
2. **Capture all tmux sessions immediately** and identify CC-like sessions:
   - session name starts with `hermes-cc`
   - `hermes-claude-longterm`
   - pane contains `Claude Code`, `bypass permissions`, `Opus`, `new task? /clear`, or `⏵⏵`
3. **Report each active/thinking/waiting CC session using the strict template**:
   ```text
   📡 CC Agent Team [now]
     ⚡ Leader: <session> — <current line/status>
     └─ 🔵 Worker/Session: 监控中（tmux capture-pane）
     📊 Token: <token or unknown> · 🛡️ Gate: <N> 次
   ```
4. **Handle stale input at the prompt**: if `❯ <text>` is visible and the task did not start, do not assume Enter worked.
   - First send `Enter`/`C-m` once.
   - If no `●` or thinking state appears, send `Escape`, then retype a short English instruction and `C-m`.
   - Verify with `capture-pane` that a thinking/tool state (`✢/✻/●`) appeared.
5. **Install a short-lived watchdog if the task is still running**. This avoids relying on the agent remembering to poll.

## Short-lived watchdog pattern

Create a profile-local script in the active profile's `scripts/` directory that prints nothing when no CC session needs attention and prints the strict `📡 CC Agent Team [...]` block when a session is active, thinking, or waiting on input.

Then create a no-agent cron job:

```python
cronjob(
    action="create",
    confirmed_by_user=True,  # if kanban gate asks for explicit confirmation
    name="cc-status-watchdog-<profile>",
    schedule="every 2m",      # avoid high-frequency 1m unless explicitly confirmed
    repeat=30,                # short-lived, do not spam forever
    deliver="origin",
    no_agent=True,
    profile="<active-profile>",
    script="cc-status-watchdog.py",  # relative filename, not absolute path
)
```

Important details:
- Cron `script` must be the relative filename under the profile's scripts directory; absolute paths are rejected.
- Prefer `every 2m` + limited repeats unless the user explicitly demands tighter polling.
- `no_agent=True` means stdout is sent verbatim; empty stdout is silent.

## What not to do

- Do not say “I will monitor” without immediately running `capture-pane`.
- Do not batch multiple hidden polls and only report at the end.
- Do not treat a visible `❯` prompt as proof of idleness if a thinking line exists above it.
- Do not leave text sitting after `❯` and assume CC accepted it.
