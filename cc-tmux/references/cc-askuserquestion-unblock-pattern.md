# CC AskUserQuestion 阻塞 & 解除 Pattern

> 2026-06-24 · CC v2.1.186+ · cc-tmux 实战中反复出现

## 症状

CC 在执行中弹出 `AskUserQuestion` 交互式选择题，Hermes 未及时响应 → CC 状态卡 `BLOCKED`，askuserquestion 窗口可能超时关闭，但 CC 仍在 ❯ 提示符等待，不继续执行。

**具体表现**：
- `cc-status` 显示 `state=BLOCKED, last_tool=AskUserQuestion`
- pane 不再显示选项 UI，只显示 CC 的分析文本
- ❯ 提示符存在但为空
- 心跳持续但无工具调用

## 解除方法

### 方法 A：选项仍在时直接选
```
tmux send-keys -t "<session>" "<选项号>" Enter
```
适用于 pane 仍显示 `Enter to select · Tab/Arrow keys to navigate` 的情况。

### 方法 B：选项已消失（超时关闭）
```
# 1. 先 Escape 清残留
tmux send-keys -t "<session>" Escape
sleep 2

# 2. 纯文本告知决策
tmux send-keys -t "<session>" "拍板：<决定>。继续执行。" Enter
```
适用于选项 UI 已消失、CC ❯ 空闲的状态。

### 方法 C：CC 卡在 queue 模式（"Press up to edit queued messages"）
```
tmux send-keys -t "<session>" C-c
sleep 2
tmux send-keys -t "<session>" Escape
tmux send-keys -t "<session>" "<新的纯文本指令>" Enter
```

## 预防

- **effort 选 high 而非 xhigh**：xhigh 在实现任务上易陷入 >10min 深度思考 + Boogieing 黑箱 + 不调工具 → AskUserQuestion 概率升高
- **Hermes 主动巡检**：等 turn-done 期间，每 3-5 分钟查一次 `cc-status` 的 state 字段，`BLOCKED` 立即响应
- **避免 "Press up to edit"**：不在 CC 的 ✻/✽ 思考态发送消息

## 本 session 实例

2026-06-24 · CC Opus 4.8 · cc-tmux P1 三项任务：
- 第 1 次：cron 配置方式选择 → Hermes 选 2 后 CC 继续
- 第 2 次：用量告警判据选择 → Hermes 选 1 → 选项超时消失 → Escape + 纯文本决策 → CC RECEIVED 继续
