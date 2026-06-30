# CC 空闲会话堆积阻塞新任务 · 2026-06-27 实发

## 症状

`cc-start.sh` exit 3：「其他活跃 CC」，列出一长串 `THINKING` 状态的 session，拒绝启动。

```
hermes-cc-default-ai-mud-rp-dice-final-0625-1150 — THINKING   (实际 IDLE, age=108256s)
hermes-cc-default-aimud-a0-playable-loop-0626-2308 — THINKING   (实际 IDLE, age=65373s)
hermes-cc-default-aimud-action-affordance-v04-0627-1217 — THINKING (实际 IDLE, age=18525s)
... 共 10 个
```

## 根因

cc-start 的全量 scan 用 `cc-monitor` 的 6 状态机抓屏判定——但 hook 在 CC 真正停掉后可能不再更新 `cc-status-*.json`，导致 `last_state` 仍为 `THINKING`/`TOOL`（虽心跳已被 watcher 刷新）。scan 看到 `THINKING` → 判为活跃 → exit 3。

实际：这些 session 早已 IDLE，只是 hook 写入的状态文件未反映最新状态（CC 进程已死但 tmux session 未清理）。

## 诊断方法

不要只看 scan 报告的表面状态，直接检查所有 session 的 `cc-status-*.json` + 心跳年龄：

```bash
for session in $(tmux ls | grep "hermes-cc" | cut -d: -f1); do
  status="/tmp/cc-status-$session.json"
  hb="/tmp/cc-heartbeat-$session"
  state=$(jq -r '.state // "?"' "$status" 2>/dev/null)
  age=$(($(date +%s) - $(stat -f '%m' "$hb" 2>/dev/null || echo 0)))
  echo "$session state=$state age=${age}s"
done
```

判据：`heartbeat_age > 3600s` 且 `state != TOOL` → 可安全 kill。

## 恢复步骤

```bash
# 1. 杀掉所有判定为闲置的 session
for session in $(tmux ls | grep "hermes-cc" | cut -d: -f1); do
  tmux kill-session -t "$session"
done

# 2. 清理残留的锁/心跳/状态文件
rm -f /tmp/cc-heartbeat-hermes-cc-* \
      /tmp/cc-status-hermes-cc-*.json \
      /tmp/cc-turn-done-hermes-cc-* \
      /tmp/cc-lock-* \
      /tmp/cc-freeze-hermes-cc-*

# 3. 杀残留 watcher
pkill -f "cc-watcher.sh" 2>/dev/null || true

# 4. 重试 cc-start.sh（此时无冲突）
```

## 预防

1. **每次 cc-finish 必须 `--kill-session`**：不及时 kill → session 残留 → 堆积。除非用户明确要求保留 session 做后续交互。
2. **定期跑 `cc-gc.sh --mode gc --apply`**：清理僵尸孤儿文件（死 session 的锁+state）。
3. **cc-start 前习惯性检查**：若 scan 报告大量「活跃」session 但任务间隔 >1h → 按上述诊断方法确认真实状态后再决定是否 `--ack-active`。
4. **不要默认 `--ack-active`**：先诊断、再清理、最后才并发启动。
