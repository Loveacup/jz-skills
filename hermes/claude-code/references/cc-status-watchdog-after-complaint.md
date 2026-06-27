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
5. **Resume manual Hermes patrol in the current conversation** if the task is still running. The recovery is not complete until the agent itself keeps doing `capture-pane → visible 📡 block` every 30–60s in the active thread.

## Manual patrol only — no watchdog unless explicitly requested

The user correction from 2026-06-08 is definitive: when they say “轮巡/持续监控”, they mean **the current Hermes agent must patrol manually**. Do **not** create a script, cron job, watchdog, helper process, or background automation as a substitute.

Allowed:
- `capture-pane` now → immediately send strict `📡 CC Agent Team [...]` block.
- Continue the conversation loop with another `capture-pane` within 30–60s, then another visible `📡` block.
- If CC finishes, do disk verification and stop patrol.

Only create a script/cron/watchdog if the user explicitly asks for automation/background monitoring, e.g. “建 watchdog”, “用 cron 自动巡”, or “后台自动报”. Otherwise, doing so is an execution lapse and violates the user’s low-noise preference.

## What not to do

- Do not say “I will monitor” without immediately running `capture-pane`.
- Do not batch multiple hidden polls and only report at the end.
- Do not treat a visible `❯` prompt as proof of idleness if a thinking line exists above it.
- Do not leave text sitting after `❯` and assume CC accepted it.
