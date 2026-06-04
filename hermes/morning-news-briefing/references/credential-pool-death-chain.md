# Credential Pool Death Chain — 2026-06-04

## Failure Sequence

```
08:00 cron trigger → deepseek-v4-pro
  ├── API call #1-2: OK (skill loading, initial search)
  ├── API call #3: HTTP 400 "Content Exists Risk" (news safety filter)
  │   └── Hermes auto-fallback → kimi-coding pool
  └── kimi-k2.6: HTTP 404 × 3 → Job failed
```

## Root Cause

kimi-k2.6 was removed from the kimi API (`api.kimi.com/coding`), but it was still in the Hermes credential pool. When DeepSeek's safety filter rejected news content, Hermes automatically fell back to the dead kimi model — 3 retried → job failure.

## Fix

```bash
# 1. Remove dead model from credential pool
hermes auth remove kimi-coding 1

# 2. Ensure cron job model is pinned to a live provider
cronjob(action="update", job_id="...", model={"model": "deepseek-v4-pro", "provider": "deepseek"})
```

## Lessons

- **Never leave dead models in credential pool** — they become silent fallback targets that cascade a temporary 400 into a fatal 404.
- **`hermes auth list` should be part of periodic maintenance** — check for deprecated models.
- **DeepSeek 400 Content Exists Risk is transient** — the same content often passes on retry. Don't treat it as a permanent model issue.
