# 奏报官 / Kanban Watcher 详细设计

## 监听事件

### 应监听
- completed
- blocked
- gave_up
- crashed
- timed_out
- ready 任务长时间没人领（stale ready）
- running 任务长时间无 heartbeat（stale running）
- 父任务完成，子任务被推广为 ready（dependency ready）
- 根任务 / 汇总任务完成

### 不应监听
- 每条 comment / heartbeat
- 普通叶子任务完成
- 普通状态变化

## 通知对象

### 太子频道（regent）
接收较多事件：blocked, completed, crashed, dependency ready, stale running

### 父皇（user）
只接收高价值事件：
- 总任务完成
- 需要父皇裁决
- 任务失败/阻塞超过阈值
- 成本/权限/外部动作需要确认

## Watcher 脚本实现要点

1. 通过 `hermes kanban list --json` 获取当前全板状态
2. 维护 `~/.hermes/kanban-watch/last-state.json` 记录上次已知状态
3. 对比新旧状态，检测：
   - 新任务创建
   - 状态变更（尤其是 blocked, crashed, timed_out, gave_up）
   - 长时间无心跳的 running 任务
   - 过期 ready 任务
4. 根据事件分级决定输出内容
5. 空输出 = 静默，cron 不发送通知
6. 使用 `no_agent=True` 脚本模式

## 状态文件格式

```json
{
  "last_check_at": "2026-05-20T03:30:00+08:00",
  "known_task_ids": ["t_abc123", "t_def456"],
  "known_statuses": {"t_abc123": "running", "t_def456": "done"},
  "last_heartbeat": {"t_abc123": "2026-05-20T03:25:00+08:00"},
  "notified_events": []
}
```

## notify-subscribe 用法

```bash
# 订阅根任务事件，通过 regent gateway 推送到太子 Telegram DM
hermes kanban notify-subscribe <task_id> \
  --platform telegram \
  --chat-id <regent_telegram_chat_id> \
  --notifier-profile regent

# 查看当前订阅
hermes kanban notify-list

# 取消订阅
hermes kanban notify-unsubscribe <task_id>
```

## 项目看板查询

```bash
# 全板统计
hermes kanban stats --json

# 按状态/assignee 列出
hermes kanban list --json | jq '.[] | {id, title, status, assignee}'

# 特定任务事件日志
hermes kanban log <task_id>
hermes kanban runs --json <task_id>
```
