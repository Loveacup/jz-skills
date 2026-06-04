# Supermemory Dual-Pool Recurrence Runbook

Use when Supermemory Dashboard appears to show a second pool or cross-profile memory contamination after an earlier fix.

## Key distinction

Do not collapse all “双池” reports into the same root cause:

1. **Name-variant split**: `hermes-cabinet` vs `hermes_cabinet`
   - Likely cause: `_sanitize_tag()` or another sanitization path replacing `-` with `_`.
   - Probe: verify `_sanitize_tag("hermes-cabinet") == "hermes-cabinet"` in the code path actually loaded by the running provider.

2. **Routing/isolation split**: `hermes` vs `hermes-cabinet`
   - Likely cause: profile map/default fallback, profile-local config drift, or a long-running process still holding old config.
   - Desired policy in the current cabinet deployment:
     - `default` and `cron-worker` → `hermes`
     - `regent` and multi-agent worker profiles → `hermes-cabinet`

## Minimum verification before editing or reporting fixed

1. **Read Obsidian first**
   - Main audit note: `20-Areas/20_技术项目/hermes-s6m-a2a/06_审计/Supermemory双池审计.md`
   - Cleanup plan: `02-Plan&CQI/88_event-bridge-审计日志安置方案.md` §11

2. **Check both config planes**
   - Event Bridge / daemon plane: `~/.hermes/supermemory.json`
   - Provider/profile plane: `~/.hermes/profiles/<profile>/supermemory.json`
   - Do not infer one from the other; they can drift.

3. **Check actual loaded provider behavior**
   - Import the Hermes Supermemory provider from the active venv or run the same loader used by Hermes.
   - Verify representative profiles: `default`, `regent`, and one worker such as `gongbu` or `engineer`.

4. **Check long-running processes**
   - Gateway/Event Bridge may keep an old map in memory. If config is correct but new writes still route wrong, restart then verify a new write.
   - Do not rely only on the dashboard showing an old container tag; historical containers can remain visible after the bug is fixed.

5. **External cleanup is separate from config repair**
   - Do not delete or retag Supermemory documents merely because a pool exists.
   - For Event Bridge audit-noise cleanup, follow the dry-run + manifest + explicit delete approval flow in the CQI note §11.

## Documentation update pattern

When updating Ob after a recurrence:

- Add a dated recurrence section instead of rewriting the original root cause.
- State whether the recurrence is a name-variant split or routing/isolation split.
- Record verified config policy and sample provider-loaded results.
- Add the next diagnostic order: recent-write timeline → process restart → config-plane split → cleanup plan.

## Common false positives

- Dashboard still lists historical `hermes_cabinet` after `_sanitize_tag` was fixed.
- `hermes` and `hermes-cabinet` both exist by design; the bug is cross-writing, not coexistence.
- Event Bridge Supermemory sink may be disabled by deployment env while provider memory still works; distinguish the two write paths before concluding the system is broken.
