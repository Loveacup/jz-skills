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
