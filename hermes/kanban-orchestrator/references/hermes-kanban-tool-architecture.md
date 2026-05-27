# Hermes Kanban 工具函数架构 — 对 governance gate 的影响

> 发现于 2026-05-19 · kanban_gate CLI → SOUL.md 集成三次被驳回的根因

## 核心事实

**Hermes Kanban workers 使用工具函数（tool functions），不使用 CLI。**

```
Agent 调 kanban_create(...)  →  Python 工具函数  →  kanban_db SQLite
Agent 调 kanban_complete(...)  →  Python 工具函数  →  kanban_db SQLite
```

Agent **从不** shell out 到 `hermes kanban create ...`。

官方文档确认：
> "Workers do not shell out to `hermes kanban`."
> "The dispatcher spawns each worker with these tools already in its schema; the model reads its task and hands work off by calling them directly."

## 对 governance gate 的影响

| 拦截方式 | 可行性 | 原因 |
|----------|--------|------|
| CLI wrapper（kanban_gate.py） | ❌ | Agent 不走 CLI |
| SOUL.md 替换 CLI 引用 | ❌ | SOUL.md 中没有 CLI 引用 |
| pre_tool_call hook | ✅ | 工具函数调用前触发，可阻断 |
| custom_tools override | ⚠️ | Issue #11049，未合并 |
| system_prompt 注入规则 | ⚠️ | 软约束，靠 Agent 自觉 |

## 已知可行方案：pre_tool_call hook

Hermes 已有 `pre_tool_call` hook（Issue #359 阻断能力已合入 main）。

```
Agent 调 kanban_create → pre_tool_call hook → gate 校验
  ├─ 通过 → 放行
  └─ 拒绝 → 返回 block 消息
```

**局限**（Issue #12922）：`memory`, `todo`, `session_search`, `clarify`, `delegate_task` 等内置工具走 `run_agent.py` 短路径，不经过 `handle_function_call()`，因此 `post_tool_call` hook 对它们不触发。但 `pre_tool_call` 对这些工具仍然有效（通过 `get_pre_tool_call_block_message`）。待验证 kanban 工具是否也走短路径。

## 错误路径（已废弃）

以下路径在本会话中被验证不可行：
1. **用 kanban_gate.py CLI 替换 hermes kanban CLI** → Agent 不走 CLI
2. **在 SOUL.md 中修改 CLI 引用** → SOUL.md 中没有 CLI 引用
3. **用 kanban_gate.py 作为 CLI wrapper + prompt 自检** → 两层都弱
