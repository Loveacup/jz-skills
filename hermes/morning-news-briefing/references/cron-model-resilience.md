# Cron Model & Provider Resilience

> Discovered: 2026-06-04 morning-news-briefing 08:00 run failure cascade.

## Failure Chain (08:00 run)

```
08:09:30  deepseek-v4-pro → RemoteProtocolError (connection drop)
          ↓ retry
08:10:18  deepseek-v4-pro → HTTP 400 Content Exists Risk (safety filter)
          ↓ Hermes auto-fallback to kimi
08:10:19  kimi-k2.6        → HTTP 404 (model deprecated)
08:10:22  kimi-k2.6        → HTTP 404 (retry 2/3)
08:10:27  kimi-k2.6        → HTTP 404 (retry 3/3) → Job FAIL
```

## Root Causes

1. **kimi-k2.6 deprecated**: The model was removed from kimi's endpoint (`api.kimi.com/coding`). Any cron job with this model will fail with 404.
2. **DeepSeek safety filter**: News content can trigger `Content Exists Risk` (HTTP 400). Usually transient — retry succeeds.
3. **No `tts` in enabled_toolsets**: `text_to_speech` tool invisible to agent → TTS never runs.

## Fixes Applied (2026-06-04)

1. **Model**: Changed cron job model from `kimi-k2.6` → `deepseek-v4-pro`
2. **Credential pool**: Removed kimi from pool (`hermes auth remove kimi-coding 1`) — prevents auto-fallback to dead model
3. **TTS toolset**: Added `tts` to `enabled_toolsets`
4. **Prompt**: Changed from "严格按 SKILL.md 执行" to explicit imperative tool-call instructions (write_file → terminal render → text_to_speech) — agent was reading skill as reference and summarizing instead of executing
