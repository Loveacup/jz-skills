# 中书省 cc Agent Team 接入 (2026-05-25)

## 背景

中书省 (planner profile, kimi-k2.6) 在处理多文件规划任务时频繁耗尽
90/90 迭代预算——逐文件读取消耗大量轮次。Claude Code agent team 可承担
深度探索/取证工作，中书省只做下达任务→收产物→整合方案。

## 配置

### planner config.yaml 追加

```yaml
mcp_servers:
  claude_octopus:
    command: npx
    args:
    - -y
    - claude-octopus@latest
    env:
      CLAUDE_SERVER_NAME: claude-octopus
      CLAUDE_TOOL_NAME: cc
      CLAUDE_DESCRIPTION: Claude Code agent via Claude Octopus
    timeout: 300
    connect_timeout: 90
```

### system_prompt 追加指令

```
## Claude Code Agent Team（优先使用）
凡涉及以下任务，不要自己逐文件读取。立即调用 cc agent team：
- 多文件代码库分析（>5 文件）
- 源码级架构理解 / 依赖梳理
- 多方案对比评估需跨文件取证
- 复杂制度/流程设计需跨仓库取证

调用规范：
cc(prompt="清晰任务描述", maxTurns=8, maxBudgetUsd=0.5, permissionMode="plan")
```

## Sandbox 隔离问题

Claude Code 的 `~/.claude/` 目录受 Kanban worker sandbox HOME 隔离影响。
若 cc 报告 "claude /login 阻塞"，可能是 worker 的 sandboxed home 中缺少
Claude Code 认证文件。此时 cc MCP 仍可连接（MCP 层正常），但内部
`claude` 子进程需认证文件。

## 验证

```bash
# regent 端验证 cc 可用
hermes --profile regent mcp test claude_octopus
# → Connected ✓, 5 tools

# 新会话后测试 planner cc
hermes -p planner chat -q "调用 cc 分析小任务，验证是否可用"
```
