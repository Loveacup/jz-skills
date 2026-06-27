# Swap 危机 → Gateway 崩溃模式

> 记录于 2026-05-30 swap 危机事件。当 mac-doctor 发现 swap >5GB 时，应主动检查 gateway 存活状态。

## 崩溃链路

```
swap 打满 (>90%)
  → 系统 OOM 压力
  → launchd 发送 SIGTERM 给 gateway 进程
  → gateway 退出，Telegram 断连
  → 自动重启失败（端口冲突 + Telegram 会话未释放）
  → 持续离线直到 swap 缓解
```

## 诊断命令

```bash
# 1. 确认 swap 状态
sysctl vm.swapusage
ls -lt /System/Volumes/VM/swapfile* | head -10

# 2. 检查 gateway 崩溃日志
grep "SIGTERM\|Shutdown context" ~/.hermes/logs/agent.log | tail -10
# 关键字段：loadavg_1m — 如果 <5 仍然 SIGTERM，不是 swap 导致

# 3. 确认 gateway 是否重连 Telegram
grep "telegram c\|Gateway running" ~/.hermes/logs/agent.log | tail -5
# ✓ telegram connected + Gateway running with 1 platform(s) = 正常
# 只有 Gateway running without ✓ telegram = Telegram 未连上

# 4. 常见重启失败原因
grep -E "conflict|already in use|keepalive failed" ~/.hermes/logs/gateway.error.log | tail -10
```

## 常见故障模式

| 症状 | 日志特征 | 原因 | 修复 |
|------|---------|------|------|
| Telegram 断连 | `Gateway running with 1 platform(s)` 但无 `✓ telegram` | .env 中 `TELEGRAM_BOT_TOKEN` 被注释 | 取消注释 → `kill -TERM <pid>` 重启 |
| 端口冲突 | `Port 8460 already in use` | 多个 gateway 实例抢同一端口 | 各 profile 分配唯一端口（8460/8461/8417） |
| kanban.db 损坏 | `kanban.db is not a valid SQLite database` | swap 危机中 SQLite 文件损坏 | `mv kanban.db kanban.db.bak && hermes kanban init` |
| MCP 全部掉线 | 多个 `keepalive failed` 同一秒 | gateway 进程 hang 或网络抖动 | 等自动重连或重启 gateway |

## 恢复验证

```bash
# 确认三个 gateway 都在跑
ps aux | grep "hermes_cli.main gateway run" | grep -v grep

# 预期输出（3 个 profile）：
#   default   → PID xxx (小黄)
#   cron-worker → PID xxx (影分身)
#   regent    → PID xxx (太子)
```

## 经验

- swap >5GB 时主动查 gateway 存活，提前预警
- 不要只依赖 `Gateway running` 日志 — 要确认 `✓ telegram connected`
- .env token 被注释是常见陷阱（迁移/重构遗留）
- `parent_pid=1` 的 SIGTERM = launchd 发送（系统压力/重启触发）
