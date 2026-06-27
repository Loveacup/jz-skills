# Mode B Operational Gotchas v1.0

Lessons from 2026-06-04 Mode B (Kanban Swarm) execution.

## Pre-flight: Gateway Readiness

**Before running `hermes kanban swarm`, all worker/verifier/synthesizer profiles must have their gateways running.**

```
hermes profile list  # Check gateway column
```

If any are `stopped`:
```bash
for p in lane-zh lane-en lane-mixed lane-tech auditor publisher; do
  hermes gateway start --profile "$p"
done
```

Why: The kanban swarm command creates tasks and marks them `running`, but the actual agent processes are spawned by each profile's gateway dispatcher. If gateways are down, tasks sit in `running` indefinitely with no agent working.

## Recovery: Stuck Workers

**Symptom**: `hermes kanban ls --status running` shows workers but `hermes kanban log <task>` shows only "Initializing agent..." with no progress.

**Root cause**: Tasks were created/claimed while gateways were down. The "running" status is a claim, not an actual running process.

**Fix**:
```bash
# 1. Start the gateway first (if still stopped)
hermes gateway start --profile <assignee_name>

# 2. Reclaim to release the stale claim
hermes kanban reclaim <task_id>

# 3. Dispatch to spawn fresh workers (gateway must be running for this to work)
hermes kanban dispatch
```

Exact sequence matters: reclaim before dispatch. Dispatch alone won't reclaim stale claims. Gateway must be running before dispatch — otherwise dispatch reports `Spawned: 0`.

## Brave Rate Limiting (429)

During 4-way parallel search, Brave API may return 429 (rate limit). This is **not fatal** — workers retry naturally. Individual queries fail but other engines (Exa, web_search) continue providing coverage. No intervention needed unless ALL engines fail.

## Publisher Stability

v4.0 testing showed publisher crashing 54 times. Root cause: `platforms.api_server.extra.port` default (8460) conflicts across profiles. **Fix**: assign unique ports in each profile's `config.yaml`:

```yaml
platforms:
  api_server:
    extra:
      port: <unique_port>
```

Port assignments:
- default: 8460
- publisher: 8461
- auditor: 8462

## Publisher Kimi Residual (2026-06-04)

Even after removing kimi-k2.6 from cron-worker, publisher's `auxiliary` model config may still reference it. Symptom: `Auxiliary title generation failed: HTTP 400 ... you passed kimi-k2.6`. This is non-blocking (title generation is cosmetic) but clutters logs. Fix: update publisher's `config.yaml` `auxiliary` section to use `deepseek-v4-pro` or `deepseek-v4-flash`.

## Diagnostic Commands

```bash
# Full swarm status
hermes kanban ls --status running
hermes kanban ls --status todo
hermes kanban ls --status done

# Worker progress
hermes kanban log <task_id> | tail -20

# Dispatcher health
hermes kanban dispatch  # Shows reclaimed/spawned counts
```
