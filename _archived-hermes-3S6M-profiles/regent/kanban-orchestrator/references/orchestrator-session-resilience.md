# Orchestrator Session Resilience

How the 监国太子 (regent/orchestrator) avoids self-inflicted failures.

## Context explosion → API timeout

### Symptom

```
ERROR root: API call failed after 3 retries. Request timed out.
provider=openai-codex model=gpt-5.5 tokens=~119,710
```

The Telegram session accumulates tool output (kanban monitoring, web research, config dumps, skill files) over many turns until the context (~80k–120k tokens) exceeds the model backend's timeout.

### Root cause (two factors)

1. **Telegram as primary interface** — every tool output, even kanban monitoring logs, enters the conversation context. No side-channel for operational noise.
2. **Orchestrator doing everything in one turn** — dispatching tasks, monitoring them, fetching research, reading configs, and patching prompts all in the same conversation window.

### Fix patterns

**Immediate:** Switch to a model with better large-context handling.
```bash
hermes model  # pick deepseek-v4-pro, kimi-k2.6, or another high-context model
```
This recovers the session immediately without losing state.

**Structural (prevent recurrence):**
1. **Split work across Kanban, not inline.** Long research, analysis, or synthesis should be a Kanban task (planner → reviewer), not done by the regent in the main conversation.
2. **Background monitoring, not inline polling.** Use `terminal(background=True, notify_on_complete=True)` for kanban task monitors instead of blocking the main loop.
3. **Report summaries, not raw output.** When kanban tasks complete, the regent reads only the summary, not the full workspace. The full artifacts live in workspace files.
4. **New session for heavy work.** If the regent must do multi-step work itself (rare, but sometimes unavoidable), start a fresh session with `/new` first to clear context.

### When to switch models vs when to compress

| Situation | Action |
|-----------|--------|
| Single timeout, context < 60k tokens | Wait and retry (transient) |
| Repeated timeouts, context > 80k tokens | Switch model/provider |
| Session still functional but slowing down | `/compress` or `/new` |
| Session unusable, no `/compress` available | Switch model, then `/new` after recovery |

### Compression diagnosis (session 20260518)

Compression **does** trigger and works — the problem is re-expansion velocity:

```
15:48:22  Compression triggered: 137,311 tokens (gpt-5.5 threshold: 136,000 = 50% of 272k)
15:48:56  Compression done: 306→293 messages, 137,311→103,026 tokens
15:50:43  Session split: 20260518_102507 → 20260518_154856

// Within 8 minutes of the new session:
15:54:41  Timeout #1: tokens=~119,710 (re-expanded from 103k→120k)
15:59:48  Timeout #2: tokens=~119,710
16:02:24  Timeout #3: tokens=~72,829 (smaller after context compaction summary injection)
```

Key insight: Compression reduced context by only 25% (137k→103k), below the configured 50% target because 20% of messages resist compression. The new session immediately accumulated kanban monitoring logs, raw skill file content (grill-with-docs SKILL.md 3500 chars + README.md 11000 chars), and profile config dumps, hitting the timeout ceiling before the next compression cycle could fire.

### Known-good fallback

gpt-5.5 @ openai-codex → deepseek-v4-pro @ deepseek: works for 100k+ token contexts in Telegram sessions. The DeepSeek API handles large message arrays more reliably than the Codex backend for sustained multi-turn conversations.

### Prevention checklist

After a timeout/recovery:
- [ ] Was raw file content (skill SKILL.md, README.md, config dumps) pasted into the conversation? → Next time: reference paths, not content.
- [ ] Were kanban monitoring loops polling every 20s? → Next time: use background processes with `notify_on_complete=true`.
- [ ] Did the orchestrator do research/analysis inline instead of via Kanban? → Next time: create planner task.
- [ ] Is the main channel SOUL.md updated with slimness rules? → See `主频道瘦身` section in the regent's SOUL.md.
