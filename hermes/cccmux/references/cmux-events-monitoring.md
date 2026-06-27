# cmux 事件驱动监控（替代盲轮询）

> **核心范式转移：** tmux 没有事件，所以 raw-tmux 版只能「每 30-60s 盲抓屏 + 人肉汇报」当心跳。cmux 有真正的事件总线 `cmux events`（NDJSON，可重连、可重放）+ `~/.cmuxterm/workstream.jsonl` 审计 + 每会话 lifecycle。**监控的根因（看不见）被消除，capture-pane 退化为「事件不够用时的取证手段」。**

## 1. 订阅命令（发任务后立即起，常驻）

```bash
cmux events \
  --category agent \
  --category feed \
  --category surface \
  --category notification \
  --cursor-file ~/.cache/cmux/cccmux.seq \
  --reconnect
```

- **NDJSON 帧**，非 SSE。每帧带单调递增 `seq` + `boot_id`（cmux 重启会变）。
- `--cursor-file`：把 last seq 持久化，断线/重启用它续传，**不丢事件**。
- `--reconnect`：永久重连并自动从最后 seq 续。
- 内存 replay buffer 上限 **4096 帧**；单帧 16 KiB，超出置 `payload_truncated:true`；订阅落后会被 `slow_consumer` 踢。
- `ack` 帧里 `resume.gap=true` → cursor 太旧，需用 `cmux tree` / `cmux list-workspaces` / `occupancy-scan.sh` 重新快照对齐。
- 同样的事件也落盘 `~/.cmuxterm/events.jsonl`（16 MiB 轮转），可事后 `--after <seq>` 回放。

## 2. ack 帧与 event 帧结构（实测）

```json
{"type":"ack","protocol":"cmux-events","version":1,"boot_id":"…","subscription_id":"…",
 "heartbeat_interval_seconds":15,"replay_count":0,
 "resume":{"after_seq":null,"requested_after_seq":333,"oldest_seq":1,"latest_seq":333,"next_seq":334,"gap":false},
 "filters":{"names":[],"categories":["agent","feed"]}}

{"type":"event","seq":336,"id":"<boot_id>-336","name":"notification.created","category":"notification",
 "source":"notification.store","occurred_at":"2026-06-11T14:33:02.338Z",
 "workspace_id":"…","surface_id":"…","pane_id":null,"window_id":null,
 "payload":{"notification_id":"…","redacted_fields":["title","subtitle","body"],"delivery":"store"}}
```

- **heartbeat 每 15s**：事件稀疏时也有心跳证明流活着；heartbeat 丢失 >2min = 流异常。
- **隐私 redact**：`surface.input_sent`、通知 title/body、browser.input 等文字字段默认 redact，只给 `*_length`。监控靠的是**事件类型/lifecycle**，不靠偷看内容。

## 3. 关键事件清单（写 skill 要订阅的）

### `agent` 类 — `agent.hook.<HookEventName>`（CC 原生 hook 经 cmux 转发）
source = agent 名（`claude`）。payload 含 `session_id` / `hook_event_name` / `tool_name` / `phase`。

| HookEventName | 含义 | orchestrator 动作 |
|---|---|---|
| `PreToolUse` / `PostToolUse` | CC 正在/刚用某工具 | 汇报「CC 正在 {tool_name}」 |
| `Stop` | 回合结束（leader 空闲） | 汇报结果 + **触发磁盘校验**（Core #12） |
| `SubagentStart` / `SubagentStop` | teammate 启停 | 更新 worker 树状态 |
| `Notification` | CC 要权限/空闲提示 | 见 feed 类 |
| `SessionStart` | 会话起来 | 确认 team 已启动 |

### `feed` 类 — 决策点（详见 `cmux-feed-decision-points.md`）

| event name | 含义 | 动作 |
|---|---|---|
| `feed.item.received` | Feed 归档项；可能是阻塞决策点,也可能只是 SessionStart/UserPromptSubmit/Stop 等 hook 归档 | **先分类**:Permission / ExitPlanMode / AskUserQuestion / lifecycle=`needsInput` 才立即转发用户；普通归档项只记录 |
| `feed.item.completed` | hook 拿到决定/超时/归档完成 | 记录结果；若前序是决策点则汇报已解决 |
| `feed.item.resolved` | 一次 Feed 回复解决了某决策点 | 汇报已解决 |

### `surface` 类 — 屏幕活动
`surface.selected` / `surface.focused`（被切到/收键盘焦点）、`surface.created`（teammate split 出新 surface 时）。

### `notification` 类
`notification.created`（title/body redacted，只给长度）。

## 4. lifecycle 占用状态（不靠事件流也能查）

`~/.cmuxterm/claude-hook-sessions.json`：每个 CC 会话一条，关键字段 `agentLifecycle`：

| 值 | 含义 |
|---|---|
| `running` | 忙（在思考/调工具） |
| `idle` | 空闲（回合结束） |
| `needsInput` | 等决策点（权限/提问） |
| `unknown` | 未知 |

外加 `workspaceId` / `surfaceId` / `cwd` / `pid` / `transcriptPath` / `launchCommand`（脱敏）。
`activeSessionsByWorkspace.{wsId}.sessionId` 标出每个 workspace 当前活跃会话。

→ 占用检测脚本 `occupancy-scan.sh` 直接读这个文件的 `agentLifecycle`，**取代 raw-tmux 版的 emoji grep**。

## 5. 兜底：事件不够用时回退 capture-pane

事件流断连、heartbeat 丢失、或要看具体屏内容时，回退到 tmux 兼容读屏：

```bash
cmux capture-pane --workspace workspace:N --surface surface:M --lines 60
```

- 输出 = 纯渲染可见文本（含 Claude TUI 的 `❯`、`⏵⏵ bypass permissions on`），**无行号、无 ANSI**。
- 底层 = `cmux read-screen`（`surface.read_text`），与 `capture-pane` 逐字节相同。
- 这是**兜底**，不是主监控手段——别退回 raw-tmux 那种「每次 capture 都 1:1 汇报」的噪音。

## 6. 自定义状态推送（给用户可视化）

orchestrator 可把自己算出的 worker 树/进度推成 cmux 侧栏状态，发 `sidebar.*` 事件：

```bash
cmux set-status cccmux "3/5 workers done"
cmux set-progress 0.6
cmux log "Worker C 假死,ls 校验中"
```
