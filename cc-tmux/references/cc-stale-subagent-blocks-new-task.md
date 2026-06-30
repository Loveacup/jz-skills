# CC Stale Sub-Agent Blocks New Task · 2026-06-29 实发

## 症状

- CC session 存活、心跳新鲜、monitor 显示 TOOL 或 IDLE
- 旧 sub-agent（如 Phase 1 的 `academic-researcher`）仍在 toolbar 显示，运行时间 >1h
- `cc-send.sh` 成功但新任务不被消费
- `tmux capture-pane` 显示 ❯ 空提示符 + 旧 sub-agent，无新任务响应
- 等多久 CC 都不处理新任务

## 根因

CC 主 agent 在等 stale sub-agent 返回结果——即使 sub-agent 已经冻结或永远不会返回。
`send-keys` 把新任务文本 typed 进 pane，但 CC 的 readline 线程被 sub-agent wait 阻塞，
不读取新输入。

## 恢复步骤

```bash
# 1. 发送 Escape 取消 sub-agent wait
tmux send-keys -t <session> Escape
sleep 1

# 2. 确认 CC 回到正常 IDLE（❯ 提示符，无 sub-agent 阻塞）
tmux capture-pane -t <session> -p -S -5 | tail -5

# 3. 如果 CC 仍不响应 → /clear 清空旧上下文
tmux send-keys -t <session> "/clear" Enter
sleep 2

# 4. 重新发送任务
cc-send.sh --session <session> --context <task-file>

# 5. 发后抓屏确认 CC 已开始消费（spinner 或工具调用）
```

## 预防

- **复用 session 前必查 pane**：`tmux capture-pane` 看是否有 stale sub-agent（toolbar 显示 ◯ <name> 且运行时间异常）
- **有 stale sub-agent → 先 Escape 清理**，再发新任务
- **不同 Phase 之间的 session 复用**：如果上轮有长时间 sub-agent，先 `/clear` 或 kill 重建
- **长生命周期 sub-agent 完成后及时 `/agents` 查看并 remove**：CC 的 `/agents` 命令可列出/移除子 agent
