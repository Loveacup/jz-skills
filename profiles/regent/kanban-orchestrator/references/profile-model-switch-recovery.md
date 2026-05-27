# Switching Profile Model/Provider for Kanban Recovery

When a Kanban task crashes due to rate limits or model issues, you may need to switch the assigned profile to a different model/provider. Here are the exact commands.

## Via hermes config set (fast, non-interactive)

```bash
# Switch default profile to moonshot + kimi2.6
hermes -p default config set model.provider moonshot
hermes -p default config set model.default kimi2.6

# Verify
cat ~/.hermes/config.yaml | grep -A3 "^model:"
```

**Note:** `hermes config set` without `-p <profile>` writes to the **current active profile** (which may be `regent` if you're running as regent). Always use `-p <profile>` to target the specific profile assigned to the Kanban task.

## Via interactive model picker

```bash
hermes -p default model
```

## Common pitfalls

1. **Forgetting `-p` flag** — writes to wrong profile's config
2. **Config path confusion** — `~/.hermes/config.yaml` is the base config; profiles use `~/.hermes/profiles/<name>/config.yaml`. The `-p` flag handles this automatically.
3. **Reclaim before switching model** — reclaim spawns a new worker with the OLD config. Always switch first, then reclaim (or unblock + dispatch).
4. **Reclaim on blocked tasks** — `hermes kanban reclaim` only works on `running` tasks. For `blocked` tasks (e.g. after max retries), use `unblock` first.

## Full recovery sequence (rate limit → new model)

```bash
# 1. Check the crash log
hermes kanban log <task_id>

# 2. Switch the profile's model (example: to moonshot/kimi2.6)
hermes -p default config set model.provider moonshot
hermes -p default config set model.default kimi2.6

# 3. Unblock the task (if it was auto-blocked after crashes)
hermes kanban unblock <task_id>

# 4. Trigger dispatch
hermes kanban dispatch

# 5. Verify it's running
hermes kanban list | grep <task_id>
```
