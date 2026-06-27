# Worker Stall Detection · CC Agent Team

## Pattern

When cc spawns parallel workers (3+ agents for multi-file tasks), workers frequently complete file writes but the completion notification never reaches the orchestrator. The orchestrator gets stuck in `Waiting for N background agents` forever.

**Hit rate this session:** 3 occurrences / ~6 worker spawns ≈ 50%.

## Detection Recipe

```bash
# Step 1: Monitor tokens. If same count in 2 consecutive captures (30s apart):
# → likely stalled. Check files.

# Step 2: ls -la the expected output
ls -la <path/to/expected/output.md>

# Step 3: If file exists AND >0 bytes → tell cc immediately
tmux send-keys -t hermes-claude-longterm \
  'Worker X is done. <filename> on disk at <N> bytes. Continue.' Enter
```

## Session Examples (2026-05-28)

| Worker | Stuck | File | Time Saved |
|--------|-------|------|------------|
| agent3-query-refusal | 12m, 75.8k tokens | anti-refusal-prompt.md (7835B) | ~5min |
| worker-c-keyword-sources | 5m34s, 66.6k tokens | keyword-expansion-dict.md (7791B) | ~3min |
| worker-c-fact-check | 9m36s, 75.5k tokens | anti-refusal-prompt.md | ~3min |

## Key Insight

**Don't wait 2 minutes.** 60s of stalled tokens + file on disk = worker done. The completion-notification mechanism is unreliable; file writes are atomic. Every extra minute waiting is wasted context window.

---

## ⚠️ Deep Thinking ≠ Stalling (2026-05-31)

**Symptom:** Worker tool count unchanged for 2-4 minutes, but token count still growing.

**Diagnosis:** This is normal deep analysis, NOT a stall. LLM is processing large context, comparing files, or reasoning through complex logic.

**Discrimination table:**

| Signal | Deep Thinking (normal) | True Stall (needs intervention) |
|--------|:----------------------:|:-------------------------------:|
| Token count | Growing steadily | Completely frozen >3min |
| Tool count | May be unchanged | Unchanged |
| Shell count | May be unchanged | Unchanged |
| Wait before acting | Wait 5+ min | Act after 2-3min of frozen tokens |

**Rule:** If tokens are growing → continue waiting and report normally. If BOTH tokens AND tool count are frozen >5min → treat as stall.

> **2026-05-31 case:** 3 lens workers all completed within 8min timeout. During execution, tool count stayed at 1 for 2-3min stretches while workers deep-read and analyzed files. Token count grew from ~10.8k to ~46k during these \"quiet\" periods. All workers finished successfully — no stalling, just thinking.
