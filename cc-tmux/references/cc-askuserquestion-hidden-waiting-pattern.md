# CC 隐藏等待输入模式 — 2026-06-28

## 症状
CC 状态显示 `STARTING` 或 `THINKING` 超过 10 分钟，无 turn-done marker，无 spinner 更新。用户质问"怎么没反应"。

## 实际原因
CC 不是冻结，而是在 pane 底部显示交互式选择菜单（AskUserQuestion / 执行策略选择 / 确认对话框），但：
- 菜单在 pane 底部，可能被 scrollback 遮挡
- `cc-monitor.sh` 的 6 状态机无法识别这种"等待用户输入"状态
- 心跳文件仍在刷新（hook 在运行），所以不触发冻结告警

## 诊断方法
1. `tmux capture-pane -t <session> -p -S -100 | tail -50` — 看 pane 底部是否有 `❯` 选择菜单
2. 检查是否有 `Enter to select · Tab/Arrow keys to navigate · Esc to cancel` 等提示
3. 检查 `cc-status-*.json` 的 state — 可能是 `BLOCKED` 或 `IDLE`

## 恢复方法
- 选项还在 → `send-keys "<n>" Enter`（选择第 n 个选项）
- 已超时消失 → `Escape` + 纯文本告知决策
- ❯ 后有残留排队 → `send-keys Enter`

## 预防
1. **Pre-send 约定**：context 末尾加「禁用 AskUserQuestion，有决策点直接用纯文本提问」
2. **每 2-3 分钟主动抓屏**：即使状态显示 THINKING，也要看 pane 底部是否有隐藏菜单
3. **监控脚本改进**：`cc-monitor.sh` 应检查 pane 底部是否有选择菜单提示（`Enter to select` / `❯` 后紧跟选项）

## 与冻结的区别
| 特征 | 隐藏等待输入 | 真冻结 |
|------|-------------|--------|
| spinner | 无（在等待输入） | 无（完全静止） |
| THINK_TIME | 不更新 | 不更新 |
| token | 可能显示 ? | 完全不动 |
| pane 底部 | 有选择菜单/提示 | 空白或旧输出 |
| 心跳 | 新鲜（hook 在运行） | 陈旧 |

## 实例
2026-06-28 WRR v4.0 重构：CC 卡在 STARTING 17 分钟，实际是在等用户确认执行策略（分支隔离 vs 逐步）。用户未看到提示，Hermes 未主动抓屏，导致长时间无响应。
