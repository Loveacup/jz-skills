# CC Stale Context / Task Mismatch

> 2026-06-27 实发：模型配置文档重构任务。cc-start + tmux_type 发送任务后，CC 实际在回应之前的博客文章任务，新任务 14+ 分钟未被消费。

## 症状

- `cc-start.sh` 成功，session 创建
- `tmux_type` + `Enter` 发送任务文本
- `cc-monitor` 显示 THINKING，token 增长
- 但实际抓屏发现 CC 在输出博客文章反馈，与模型配置文档完全无关
- Hermes 等了 14 分钟才意识到 CC 在做错误的事

## 根因

1. **Session 复用了旧上下文**：cc-start 创建的 session 可能继承了上一个 task 的对话历史（如果用了 `--topic` 或 session 未清理）
2. **CC 正在回应旧任务的最后一条消息**：新任务文本被 typed 进 pane 后，CC 先完成了对旧消息的响应（博客文章），新任务进入了队列但未被消费
3. **没有 pre-send 验证**：Hermes 没有在发送新任务前确认 CC 处于 IDLE 且无待处理输出

## 恢复步骤

1. 抓屏确认 CC 实际在做什么（不是看 monitor 状态，是看实际输出内容）
2. 如果 CC 在回应旧任务 → 等它完成或 `/clear`
3. `/clear` 后重新发送任务
4. 发送后等 CC 复述理解，确认它在做正确的事

## 预防

- **cc-start 后、发任务前**：`tmux_read` 确认 CC 处于 IDLE（❯ 空，无正在生成的输出）
- **如果 CC 在输出旧响应**：等它完成（看 ❯ 出现）再发新任务
- **发任务后**：等 CC 复述理解 + 抓屏确认，不要直接进入 wait 循环
- **优先用 `cc-send.sh`** 而非手动 `tmux_type`——前者自带存活验证
- **新任务用新 session**：避免 `--topic` 会话复用，除非确认旧上下文已清空

## 与 Pitfall #28 的区别

| | Pitfall #28 | 本问题 |
|--|-----------|--------|
| CC 在做的事 | 分析新任务（但冻结） | 回应旧任务（根本没收到新任务） |
| monitor 显示 | THINKING 长时间 | THINKING 长时间 |
| 判断方法 | 看 token/屏幕是否更新 | **看输出内容是否匹配任务** |
| 恢复 | C-c 缩小范围 | /clear 重新发送 |
