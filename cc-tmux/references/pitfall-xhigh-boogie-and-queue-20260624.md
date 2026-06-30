# Pitfall #22-#23：xhigh Boogieing 黑洞 + CC 2.1.186 Queued Messages

> 2026-06-24 · cc-tmux v1.22.0 · CC v2.1.186–2.1.187

## #22：xhigh Boogieing 黑洞

### 症状
用 Opus 4.8 + xhigh effort 派发大型分析/审查任务时，CC 进入 "✻ Boogieing… (20m+)" 状态，零工具调用，然后回到 `❯` 提示符，没有任何产出。hook 心跳停在 THINKING/RECEIVED，实际 pane 已 idle。

### 根因
xhigh effort 触发 CC 的深度思考模式，可能：
1. 思考超 20 分钟后内部超时放弃
2. API 500 打断后状态损坏

### 修复
- **降 effort**：同类任务用 `high` 而非 `xhigh`（码审/分析 high 足够）
- **拆分**：大评估任务拆成 2-3 轮（如 Phase 1 代码审计 → Phase 2 架构审计）
- **已知 Pitfall #14/16** 已文档化"实现类优先 high，避冻结"，分析类同理

### 复现条件
- Opus 4.8 + xhigh
- 任务规模 >200 行 context
- 要求通读 10+ 文件

---

## #23：CC 2.1.186 "Press up to edit queued messages"

### 症状
通过 tmux send-keys 发送消息到 CC 后，CC 显示 "❯ Press up to edit queued messages" 而非处理消息。每次新消息都被追加到队列但不执行。

### 根因
CC 2.1.186 引入了消息队列 UI：当 CC 处于某种内部状态时，`Enter` 后的文本被入队而非提交。send-keys 直接注入的 Enter 可能触发此行为。

### 修复
1. **轻量**：`tmux send-keys C-c` 清空队列 + 重发
2. **彻底**：`cc-finish --kill-session` 杀 session 重建

### 检测信号
- pane 显示 "Press up to edit queued messages"
- 多次 send-keys 后 pane 不变化
- 心跳仍是上一状态
