# delegate_task async checkpoint monitoring for CC

## 背景

Hermes v0.17 的顶层 `delegate_task` 默认以后台异步方式运行：调用后立即返回 handle，子 agent 完成后通过 async delegation completion queue 注入回原 gateway 会话（Telegram 等持久平台支持；stateless API 路径会同步 fallback）。

这可以用于 cc-tmux 长任务的**会话内 checkpoint 唤醒**，但不能替代主会话对 CC 的控制权。

## 正确定位

`delegate_task` checkpoint worker 是「到点巡检员 / 回叫闹钟」，不是「自动驾驶」。

主会话（Hermes/小黄）仍是驾驶员，必须负责：

- 判断 CC 是否走偏
- 是否需要 `Escape` / 补 `Enter` / 发纠偏指令
- 是否需要 C-c 中断（高风险，通常先汇报用户）
- 读取产物、审核、决定下一轮指令

checkpoint worker 只做一次取证并返回 verdict，完成后让结果注入回当前 Telegram 会话，唤醒主会话继续判断。

## 推荐分层

### 1. 起步阶段：必须 in-turn control loop

刚发 context 后不要立刻退场。必须先确认：

- `cc-send.sh` 已被 CC 消费，不是 ❯ 后残留文字
- CC 读对了路径 / 项目 / vault
- CC 理解任务没偏
- 没有 AskUserQuestion / queued input
- 已进入正常 THINKING / TOOL / 明确等待确认状态

### 2. 稳态阶段：可切 checkpoint delegate

当 CC 已稳定工作且方向正确，但预计还需 10–30 分钟时，可以派 one-shot checkpoint worker：

- 等 120–180 秒
- 读取 `/tmp/cc-status-<session>.json`
- 读取 `/tmp/cc-heartbeat-<session>`
- 检查 `/tmp/cc-turn-done-<session>`
- 检查 `/tmp/cc-freeze-<session>`
- 必要时 `tmux capture-pane -t <session> -p -S -80`
- 输出结构化 verdict 后结束

### 3. 异常/完成：主会话接管

如果 checkpoint 返回以下任一状态，不要继续自动派 checkpoint；主会话必须接管：

- `DONE`
- `BLOCKED`
- `SUSPICIOUS`
- `ERROR`
- AskUserQuestion
- queued input / ❯ 后残留文字
- IDLE but no turn-done
- freeze 告警

## checkpoint worker prompt 模板

```text
你是 cc-tmux checkpoint worker。

目标：
等待 150 秒后检查 CC session: <SESSION> 的状态，并返回结构化 verdict。
不要长期循环；只做一次检查后立刻结束，让结果注入回主会话。

允许读取：
- /tmp/cc-status-<SESSION>.json
- /tmp/cc-heartbeat-<SESSION>
- /tmp/cc-turn-done-<SESSION>
- /tmp/cc-freeze-<SESSION>
- tmux capture-pane -t <SESSION> -p -S -80

默认禁止：
- 不要 kill session
- 不要 C-c
- 不要替用户选择 AskUserQuestion
- 不要发送语义指令给 CC

唯一允许的机械修复：
- 如果 pane 明确显示 ❯ 后有残留文字且无 spinner，说明 Enter 没生效，可以只补一次 Enter。
- 如果显示 queued messages，可以只发 Escape 清队列，然后报告。

输出：
1. status: OK / DONE / BLOCKED / SUSPICIOUS / ERROR
2. evidence: 关键文件 mtime、capture-pane 末尾信号
3. suggested_action: main Hermes 下一步应该做什么
4. if DONE: 提醒主会话读取产物并验收
```

## 禁止模式

- 用 cron 监控 CC：cron 不能稳定注入回当前会话控制流。
- 一个 delegate 永久循环监控：delegate_task 不是 durable supervisor。
- 子 agent 做高风险干预：子 agent 无用户交互权，且缺少主会话上下文。
- 只挂 `notify_on_complete` 后沉默：完成通知不是持续可干预监控。

## 一句话

`delegate_task(background)` 适合做 **会话内 checkpoint 唤醒 + 取证巡检**；不适合做 CC 主控。主会话仍必须保留 observe → decide → intervene/report 的驾驶舱职责。
