# CC Blank Pane / Task Injection Fallback

> 2026-06-27 实发：Phase 8 Slice 1、Phase 7 roadmap alignment、Phase 7 Slice 9 等多个 CC session。`cc-start.sh` 成功创建 session，但 pane 显示空白输入框（只有 ❯ 提示符，无 CC 启动输出），`cc-send.sh` 或 `tmux_type` 发送的任务文本不被消费。

## 症状

- `cc-start.sh` 成功，session 创建，tmux ls 可见
- `cc-monitor.sh` 显示状态为 IDLE 或 STARTING
- `tmux capture-pane` 显示 pane 几乎空白，只有 ❯ 提示符
- 发送任务文本后，CC 不消费、不启动、无 spinner
- 等多久都不变化

## 根因

1. **Claude Code 启动时卡在权限对话框**：CC v2.1.178 启动时可能显示 `⏵⏵ bypass permissions on (shift+tab to cycle)` 权限对话框，tmux `send-keys` 无法交互（见 Pitfall #26）。`--allow-dangerously-skip-permissions` 已加但可能未生效或版本差异。
2. **CC 进程启动异常**：`claude` CLI 在 tmux PTY 下初始化失败，进程存在但无 TUI 渲染。
3. **任务文本 typed 时 CC 尚未就绪**：send-keys 在 CC 启动完成前到达，被 shell 消费而非 CC 消费。

## 恢复步骤

**方法 A：tmux load-buffer + paste-buffer（最可靠）**

```bash
# 1. 将任务文件加载到 tmux buffer
cat /tmp/cc-task.md | tmux load-buffer -b cc-task -

# 2. 粘贴到目标 pane
tmux paste-buffer -t '<session>:1.1' -b cc-task

# 3. 发送 Enter
sleep 2
tmux send-keys -t '<session>:1.1' Enter

# 4. 验证：抓屏确认 CC 开始消费
sleep 3
tmux capture-pane -t '<session>:1.1' -p -S -50 | tail -20
```

**方法 B：直接 send-keys 重新注入（如果 pane 有响应但任务未消费）**

```bash
# 先清可能残留
tmux send-keys -t '<session>:1.1' C-c Enter
sleep 1

# 重新发送任务
tmux send-keys -t '<session>:1.1' "$(cat /tmp/cc-task.md)"
tmux send-keys -t '<session>:1.1' Enter
```

**方法 C：kill 重建（如果 pane 完全无响应）**

```bash
cc-finish.sh --session '<session>' --kill-session --force
cc-start.sh --target '<target>' --effort high --task '<task>'
# 然后重新用方法 A 注入
```

## 预防

- **cc-start 后必做启动验证**：不是看 `cc-start.sh` exit 0，而是 `tmux capture-pane` 确认 pane 有 CC 启动输出（`Ionizing…` / `Composing…` / `Julienning` 等 spinner）
- **如果 pane 空白 → 不直接 send-keys**，先尝试 load-buffer/paste-buffer 注入
- **发任务后抓屏确认消费**：看 pane 底部是否有 CC 的 spinner 或工具调用输出，不是只看 monitor 状态
- **优先用 `cc-send.sh`**：它自带回读校验，但如果 pane 空白，cc-send 也会失败，需 fallback 到手动注入

## 与 Pitfall #26 的区别

| | Pitfall #26 | 本问题 |
|--|-----------|--------|
| 症状 | 权限对话框可见，send-keys 无效 | pane 完全空白，无对话框 |
| 根因 | CC 权限对话框阻塞 | CC 未启动或启动异常 |
| 恢复 | `--allow-dangerously-skip-permissions` | load-buffer/paste-buffer 注入 |
| 判断 | 抓屏看到 `⏵⏵ bypass` | 抓屏几乎空白 |

## 与 Pitfall #29 的区别

| | Pitfall #29 | 本问题 |
|--|-----------|--------|
| 症状 | CC 在输出旧任务内容 | pane 空白，无输出 |
| 根因 | 旧上下文未清理 | CC 未启动 |
| 恢复 | `/clear` 后重发 | 手动注入或 kill 重建 |
