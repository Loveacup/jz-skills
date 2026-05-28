# Worker True Stall (No Disk Output) Recovery

> **When to read:** worker token count frozen >2min + `ls -la` shows NO output files on disk. This is the "hard stall" variant — not just UI lag.

## Diagnosis

```bash
# 1. Check disk first — this is the decision point
ls -la <workspace>/search/ <workspace>/output/

# 2. If files exist → soft stall, tell CC "Agent is done, continue" (standard protocol)
# 3. If files DON'T exist → hard stall, proceed below
```

## Why standard recovery fails

When CC is in `Waiting for N background agents` state, the main thread blocks on the worker promise. `send-keys` text input appears at the prompt but is **not processed** — CC is not in an input-accepting state. Sending Enter, Ctrl+C, or messages has no effect.

Confirmation: `capture-pane` shows your message text on screen but no `●` tool call follows within 30s.

## Recovery for hard stall

**Only option:** Kill the tmux session and take over manually.

```bash
tmux kill-session -t <session-name>
```

Then evaluate what completed work is usable, supplement missing pieces, and finish manually.

## Prevention (Critical)

In the context file given to CC, add a timeout clause:

```
## Worker Timeout Rule
Each worker has 10 minutes. If a worker has not produced output to disk by
the 10-minute mark, the Leader MUST:
1. Accept the completed lanes as-is
2. Do NOT wait for the stalled worker
3. Fill gaps with Leader's own research if needed
4. Proceed to assembly immediately
```

This prevents the Leader from blocking indefinitely on a dead worker.

## Real-world case: morning-news-briefing 2026-05-28

- Lane B (US/Intl) worker stalled at 65.1k tokens, 10m 50s
- `ls -la` showed no `lane-b.json` on disk
- `send-keys` recovery message appeared at prompt but was never processed
- Resolution: killed cc session, manually did Lane B search via SearXNG, assembled briefing directly
- Lane A (18 sources) and Lane C (11 sources) were usable
