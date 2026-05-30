# Enhanced Progress Reporting — Visual Agent Team Status

> **何时读取：** 每次向 CC tmux 发送任务后，汇报进度时参考本文模板。
> **设计原则：** Telegram 原生格式（无表格），emoji 状态映射，渐进式信息密度。

---

## 状态 Emoji 映射

| CC 状态 | Emoji | 含义 |
|---------|:-----:|------|
| `●` 工具调用中 | ⚡ | CC 正在执行操作 |
| `❯` 等待输入 | 💤 | CC 空闲，可发新指令 |
| Worker 完成 | ✅ | Worker 成功返回 |
| Worker 运行中 | 🔵 | Worker 仍在执行 |
| Worker 假死 | 🟡 | UI 显示 running 但文件已写盘 |
| Worker 真死 | 🔴 | 无磁盘产出，需手动接管 |
| Fact-Forcing Gate | 🛡️ | 安全门，正常流程 |
| Error / Traceback | ❌ | 出错 |
| Shell stall | 🐚 | 后台 shell 卡死 |
| Rate limit | ⏳ | 限流等待中 |

---

## 模板一：标准 Agent Team 进度（推荐）

```
📡 CC Agent Team [12min]
  ⚡ Leader: 汇总 3 workers → /tmp/output.md
  ├─ ✅ Worker A: 数据采集 (8s, 2.4k tokens)
  ├─ ✅ Worker B: 格式转换 (12s, 3.1k tokens)
  └─ 🔵 Worker C: 验证 (running, 1.8k tokens so far)
  📊 Token: 7.3k / 200k · 🛡️ Gate: 1 次
```

## 模板二：单任务进度

```
📡 CC 进度 [5min]
  ⚡ Write(/path/to/file.ts) — 重构 auth 模块
  ✅ 已完成: src/auth/login.ts (142 行)
  🔵 进行中: src/auth/middleware.ts
  📊 Token: 12.4k · 💰 ~$0.18
```

## 模板三：Worker 异常

```
📡 CC 进度 [18min] ⚠️
  ⚡ Agent Team: 3 workers
  ├─ ✅ Worker A: Done (5min)
  ├─ 🟡 Worker B: 假死检测 — ls 确认文件已写盘 (2.1KB)
  │   → 已发 "Agent B is done. Continue."
  └─ 🔴 Worker C: 真死 — 无磁盘产出，已 kill-session 手动接管
```

## 模板四：等待/限流

```
📡 CC [22min] ⏳
  💤 等待输入 — 上一轮已完成，可发新指令
  上次: 生成 3 份参考文档 (47k tokens, ~$0.70)
```

---

## 汇报节奏控制

| 计时点 | 动作 |
|--------|------|
| 发送任务后 15s | 首次 capture-pane |
| 30-60s 间隔 | 持续轮询 |
| 发现关键信号 | 立即汇报 |
| 沉默 >2min | **绝对不可**，即使无事也要汇报 |
| Agent Team worker 变更 | 每完成/新增 worker 立即更新树 |

## 信息密度原则

- **第 1 行**：总览（耗时 + 当前操作）
- **第 2-N 行**：Worker 树（缩进 + emoji + 关键指标）
- **最后 1 行**：Token/成本/异常汇总

## Token 与成本估算

```
📊 Token: <used> / <limit> · 💰 ~$<estimate>
```

CC token 成本参考（approximate）：
- claude-sonnet-4-6: ~$3/M input, ~$15/M output
- 每次 agent team 任务通常 20-80k tokens → ~$0.30-1.20

---

## 参考资料

- [CLI UX Best Practices: Progress Displays](https://evilmartians.com/chronicles/cli-ux-best-practices-3-patterns-for-improving-progress-displays) — spinner, X/Y, progress bar
- [tmux-agent-indicator](https://github.com/accessd/tmux-agent-indicator) — tmux plugin for agent state visualization
- [agent-view](https://github.com/doyled-it/agent-view) — multi-agent terminal dashboard
- [claude-tmux-dashboard](https://github.com/ybouhjira/claude-tmux-dashboard) — live dashboard via `~/.claude/dashboard.json`
- [claude-tmux-orchestration](https://github.com/primeline-ai/claude-tmux-orchestration) — worker state machine with heartbeat
