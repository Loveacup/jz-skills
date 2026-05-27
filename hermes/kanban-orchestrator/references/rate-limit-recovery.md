# Rate-Limit Recovery in Kanban Workflows

Reference for orchestrators and operators handling Kanban tasks that crash due to provider rate limits or usage caps.

## Symptom

Task status flips `running` → `crashed` with log showing:
```
RateLimitError [HTTP 429]
The usage limit has been reached
plan_type: plus, resets_at: <timestamp>
```

## Why reclaim alone doesn't work

The dispatcher's default retry (`max_retries`, usually 2) will spawn a new worker with the **same profile + same model + same provider**. If the rate limit hasn't reset, the new worker fails identically. After `max_retries` exhausted, the task goes `blocked`.

## Recovery steps

1. **Read the crash log** to confirm it's a rate limit, not a code bug:
   ```bash
   hermes kanban log <task_id>
   ```

2. **Switch the profile's model/provider** (do NOT reclaim yet):
   ```bash
   hermes -p <profile> model
   # pick a different provider or model with available quota
   ```

3. **Then reclaim** so the dispatcher spawns with the new config:
   ```bash
   hermes kanban reclaim <task_id>
   ```

4. **If no alternative provider is configured**, the operator must either:
   - Wait until `resets_at` (check the error details for timestamp)
   - Add a new provider credential (`hermes auth add` or edit `~/.hermes/.env`)

## Orchestrator notification pattern

When a task is blocked due to rate limits, the orchestrator should report to the user with:
- Task ID and profile name
- Provider/model that hit the limit
- Reset time (if known from error)
- Suggested alternative providers on this setup
- Ask: switch model, wait, or add new provider?

## Prevention

- For long-running or multi-task workflows, check provider quota health before fan-out
- Consider setting `--max-runtime` conservatively so rate-limited tasks fail fast rather than burning retries over minutes
- Use `hermes auth list` to see which providers have pooled credentials
