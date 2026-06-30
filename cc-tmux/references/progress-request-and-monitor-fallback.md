# Progress request + monitor fallback pattern

Context: During long CC-driven documentation/architecture tasks, the user may ask “进度？/你没监控吧？” while Hermes is waiting on `cc-wait-marker.sh`. Treat this as a first-class progress request, not as commentary.

## Rule

When the user asks for progress mid-task:

1. Stop waiting for the next planned interval.
2. Read current CC state immediately.
3. Send a visible 📡 progress block with:
   - elapsed time / last known state
   - what CC is editing or thinking about
   - what is already done
   - Hermes judgement: continue / intervene / correct
4. Then resume waiting.

## If `cc-monitor.sh` fails

Do not report “monitor failed” as if the CC task failed. Fall back to direct tmux inspection:

```bash
tmux capture-pane -t <session> -p -S -60
```

Interpret pane signals:

- visible diff / Write / Edit output → CC is actively changing files
- spinner + token counter moving → thinking normally
- `❯` prompt empty + turn-done marker exists → complete; read artifacts
- `❯` prompt with residual text → queued input / Enter not consumed; send Enter or Escape according to Pitfall #18/#22

When falling back, tell the user explicitly:

```text
📡 monitor 脚本报错，我已切到 tmux 抓屏。
  当前：...
  Hermes 判断：...
```

## Anti-patterns

- Continuing to wait silently after a user asks for progress.
- Returning an empty response after tool calls.
- Letting a monitor script error hide real CC progress visible in tmux.
- Saying “I’m monitoring” without showing a concrete state block.
