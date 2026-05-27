# Coordinator Credential Isolation (2026-05-25)

## Problem

`kanban-coordinator-poll.py` spawned `hermes -p regent chat ...` as a
subprocess. The regent profile's `config.yaml` had `model.provider:
openai-codex` (OAuth), which **overrides** any `--provider` CLI flag.
Result: every coordinator subprocess failed with "No Codex credentials
stored" even when `kimi-coding` API key was available and working.

The OAuth token was also in a broken state (device_code limbo), which
made Hermes abort before even trying other providers.

## Root Cause

When `hermes -p <profile>` is used, the profile's `config.yaml`
`model.provider` takes precedence over CLI `--provider`. The `-m` flag
sets model but NOT provider. So `-m kimi-coding/kimi-k2.6` with a
profile that has `provider: openai-codex` tries to serve kimi-k2.6
through the openai-codex OAuth endpoint — which fails.

## Fix

```python
# ❌ Before — profile config overrides --provider
cmd = ["hermes", "-p", "regent", "chat", "-q", prompt,
       "-m", "kimi-coding/kimi-k2.6", "--provider", "kimi-coding", ...]

# ✅ After — no -p flag, explicit provider (API key, not OAuth)
cmd = ["hermes", "chat", "-q", prompt,
       "--provider", "kimi-coding", "-m", "kimi-k2.6",
       "--skills", "kanban-orchestrator,hermes-agent", ...]
```

The coordinator does not need the regent profile's config — it needs:
1. Kanban board access (global, via BOARD_DB path)
2. Skills loaded explicitly via `--skills`
3. `HERMES_HOME` set to regent profile home (for state files)

## Anti-pattern: Catastrophizing Transient Errors

When the coordinator failed with OAuth, the Regent tested other
providers (minimax-cn, deepseek) and declared "all providers broken."
In reality:
- `kimi-coding`: actually worked (API key valid)
- `openai-codex`: just rate-limited (429), not permanently broken
- `deepseek`: API key expired (401), a separate fixable issue

**Rule**: test each provider in isolation before making global claims.
Do not prematurely delete credentials or change configs based on
transient errors.

## Recovery

```bash
# Verify credential pool
hermes auth list <provider>

# Test provider in isolation
hermes chat --provider kimi-coding -m kimi-k2.6 -q "test"

# Re-add OAuth if accidentally deleted
hermes auth add openai-codex  # interactive browser flow
```
