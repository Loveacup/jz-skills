# Hermes Deck Routing vs cc-tmux — Comparison Notes

> 2026-06-16 分析 hermes-deck (TNJ2026/hermes-deck) 源码后的对照笔记。
> hermes-deck Kanban: `t_628789c3`（Agent 自动路由方案设计，待讨论）

## Hermes Deck 协作机制摘要

三个核心机制：

1. **Primer 注入** — 每次 `session.create` 时以 system 角色注入路由约定（格式 + 目标列表），agent 通过 in-context learning 学会委派，不依赖 skill 安装。
2. **AgentRouting 块** — agent 输出 ` ```AgentRouting\n@target prompt\n``` `，Deck 客户端解析后自动转发。四道安全校验（闭合 fence + 正确 info + @开头 + 单目标），保证"永不误路由"。
3. **客户端编排** — 并行 fan-out → 收集回复 → framed 拼接回传源 agent。一次性格式纠错。

## 与 cc-tmux 的关键差异

| 维度 | hermes-deck | cc-tmux |
|------|-------------|---------|
| 会话模式 | 无状态请求-响应（一次 @mention = 一次 prompt → reply） | 有状态长会话（CC 在 tmux 里持续运行） |
| 通信界面 | 干净 API（JSON-RPC / ACP / CLI stream） | 脏界面（send-keys + capture-pane） |
| "回复"语义 | 明确的 messageComplete 事件 | 无明确"回复"——需监控判断"完成" |
| 多 agent 协调 | Deck 客户端并行 fan-out + close-the-loop | CC 内部 agent team（同 tmux pane） |
| 路由本质 | 客户端编排的请求-响应 | 人/agent 发起的持续对话 |

## 兼容性判断

- **Primer 注入：完全兼容** — gateway 层面，与 CC 后端无关
- **Session 注入机制：完全兼容** — `session.create` 的 `messages` 现成
- **自动路由：部分兼容** — 不应抄 hermes-deck 的请求-响应模式，应基于 cc-tmux 脚本封装编排层
- **close-the-loop：语义不匹配** — CC 无 reply 事件，需重新定义"完成"信号

## SOUL.md 采用的折中

不追求纯自动路由，采用 human-in-the-loop 变体：
- 用户明确指令 → 直接执行
- agent 自主判断 → 报告理由 → 等确认
- 讨论先行 → 执行 → 产物审核 → 有问题先汇报再退回

## 相关文件

- 源码：`/tmp/hermes-deck/`（TNJ2026/hermes-deck clone）
- 设计文档：`hermes-deck/docs/AgentRoutingPrimer.zh-CN.md`
- 核心模块：`AgentRoutingPrimer.swift`, `ChatStore+Routing.swift`, `ChatModels.swift`（`AgentMentionRouteParser`）
- Agent 客户端：`RoutingAgentClient.swift`, `ClaudeCLIClient.swift`, `ACPAgentClient.swift`, `AgyClient.swift`
- Obsidian 笔记：`00-Inbox/SOUL.md Claude Code 调用规则优化_20260616.md`
