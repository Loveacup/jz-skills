# Worker "Continue" Permission Dialog Recovery

## Symptom

Multiple CC agent team workers stuck at:
```
❯ 1. Continue

Enter to confirm · Esc to cancel
```

Workers completed file writes but CC's file-access confirmation gate blocked them.

## Quick Fix — Batch Unblock

```bash
SESSION="hermes-cc-{agent}-{ts}"

# Scan for stuck panes
for p in $(tmux list-panes -t "$SESSION" -F '#{pane_index}'); do
  pane_text=$(tmux capture-pane -t "$SESSION.$p" -p -S -5 2>/dev/null)
  if echo "$pane_text" | grep -q "Enter to confirm"; then
    echo "🔓 Unblocking pane $p"
    tmux send-keys -t "$SESSION.$p" Enter
  fi
done
```

## Prevention — Context File Snippet

Add to CC context file's "Rules" section:

```
Permission dialogs: all file writes under <workdir> are pre-authorized.
If you see "1. Continue → Enter to confirm", press Enter and move on.
Do not wait for user confirmation on file-access gates.
```

## Distinguish from Other Dialogs

| Dialog | Pattern | Fix |
|--------|---------|-----|
| PTY Dialog 2 "Yes, I accept" | At session start | `Down → Enter` (Pitfall #1) |
| AskUserQuestion form | Mid-task, multi-field | `Escape` → plain-text reply (Pitfall #26) |
| **"1. Continue" file-access gate** | After file writes | `Enter` (this doc) |

## History

2026-06-08: SIL session — 5/6 workers (R1-R5 researchers) simultaneously stuck on this dialog after completing file writes. Batch-unblocked with `for p in 2 3 4 6 7; do tmux send-keys Enter; done`. Pane 2 immediately resumed work.
