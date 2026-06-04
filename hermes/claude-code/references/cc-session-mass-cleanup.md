# CC Session 批量清理

当多个 CC tmux 会话和 MCP 服务器进程长期累积时（例如多轮 agent team 测试后），一条命令全清。

## 症状

- `tmux list-sessions` 显示 10-20+ 会话（`hermes-cc-*` + 编号 session）
- `ps aux | grep claude` 显示多个 `claude --model` 进程，部分是 zombie
- 伴随 `chroma-mcp`、`exa-mcp-server`、`mcp-server-brave-search` 等 MCP 进程残留

## 清理命令（按顺序）

```bash
# 1. 杀光所有 tmux 会话
tmux list-sessions -F '#{session_name}' | xargs -I {} tmux kill-session -t {}

# 2. 砍 CC 主进程
pkill -f 'claude --model'

# 3. 砍 CC 基础设施
pkill -f 'chroma-mcp'
pkill -f 'worker-service.cjs'
pkill -f 'exa-mcp-server'
pkill -f 'mcp-server-brave-search'

# 4. 验证
ps aux | grep -iE 'claude|chroma-mcp|worker-service|exa-mcp|brave-search' | grep -v grep || echo 'ALL_CLEAN'
tmux list-sessions 2>&1 || echo 'ZERO_SESSIONS'
```

## 注意事项

- `chroma-mcp` 是 CC 的长期记忆存储（`.claude-mem`），清理后下次启动 CC 会自动重建
- `worker-service.cjs` 是 CC 插件市场的守护进程，随 CC 启动而创建
- 先杀 tmux session 再杀进程，避免进程变 zombie
- 如果清理后仍然存在网关绑定的 MCP server（随 Hermes gateway 启动），那是正常的，不要杀
