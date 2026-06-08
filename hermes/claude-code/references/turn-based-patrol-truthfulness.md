# Turn-Based Patrol Truthfulness

Use this when a user challenges "you are not automatically patrolling / intervening" during a Claude Code tmux session.

## Problem

In Telegram / turn-based Hermes, a statement like "I will automatically patrol" is false unless the agent actually performs the next `capture-pane → 📡` cycle in the same interaction flow. A background completion notice, Kanban status check, or a promise at the end of a message is not user-visible patrol.

## Required recovery

1. **Stop explaining first.** First action is `tmux capture-pane` for the active CC session.
2. **Immediately emit a full `📡 CC Agent Team [Xmin · 距上次 Xs]` block** in the current conversation.
3. **If the pane is stuck in the same state for multiple captures**, intervene in the same turn:
   - `Ctrl+C` if max-effort thinking is frozen / unchanged;
   - clear queued input if needed (`C-u` / `Escape`);
   - send one short atomic instruction, preferably file-backed if more than one sentence is needed.
4. **Do not say "automatic patrol" unless a durable automation was explicitly created and verified.** In ordinary Hermes turns, call it "manual patrol" or "next patrol cycle".
5. **Do not use Kanban as proof of CC monitoring.** Kanban can show task state, but CC monitoring evidence is the captured tmux pane plus user-visible 📡 interpretation.

## Bad patterns

- "I will keep monitoring" → final answer, no next tool call.
- `sleep 30 && capture-pane` hidden inside one tool call, then no visible 📡 until much later.
- Reading a background capture file and summarizing without the required template.
- Checking `hermes kanban list` and treating that as CC patrol.

## Good pattern

```text
capture-pane now → 📡 full block → if stuck, Ctrl+C / short atomic intervention → capture again → 📡 full block
```
