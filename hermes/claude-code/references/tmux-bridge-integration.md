# tmux-bridge MCP — Hermes ↔ CC 实时双向通道

> created: 2026-06-08 | version: 1.0.0
>
> 让 Hermes 通过 MCP 原生工具直接读写 CC 的 tmux pane，替代 `terminal("tmux capture-pane/send-keys")` 的断裂模式。支持同一 session 内「监控 → 干预 → 讨论」闭环。

## 问题

cli-code skill 的红线①（`capture-pane → 📡 汇报`）要求 Hermes 持续监控 CC。但当前实现靠 Hermes 在 `terminal()` 里裸调 `tmux capture-pane`，读和写是两次独立 terminal 调用：

- `tmux capture-pane` → 返回 pane 文本 → Hermes 分析
- `tmux send-keys` → 往 pane 里发命令 → 需要精确的目标和序列

两个操作无法在同一逻辑链中快速切换——读完后想干预，需要另起一轮 tool call。发现 CC 卡死/跑偏时，干预链路断裂。

## 方案

[tmux-bridge-mcp](https://github.com/howardpen9/tmux-bridge-mcp)（MIT, v0.3.0）是一个独立 MCP server，把 tmux 的 `capture-pane`/`send-keys`/`list-panes` 封装成 9 个标准 MCP 工具。

| 工具 | 作用 |
|------|------|
| `tmux_list` | 列出所有 pane（session:window.pane + 进程名 + 标签） |
| `tmux_read` | 读 pane 最后 N 行（满足 read guard） |
| `tmux_type` | 往 pane 里打字（不按 Enter，需先 read） |
| `tmux_message` | 发消息（自动加 `[tmux-bridge from:...]` 前缀） |
| `tmux_keys` | 发送特殊键（Enter / Escape / Ctrl-C，需先 read） |
| `tmux_name` | 给 pane 贴标签（如 "cc"） |
| `tmux_resolve` | 按标签查 pane ID |
| `tmux_id` | 当前 pane 的 tmux ID |
| `tmux_doctor` | 诊断 tmux 连通性 |

## 安装

### 前置条件

- tmux ≥ 3.2
- Node.js ≥ 18
- `npx` 可用

### Hermes MCP 配置

在 `~/.hermes/config.yaml` 的 `mcp_servers` 段添加：

```yaml
mcp_servers:
  tmux-bridge:
    args:
    - -y
    - tmux-bridge-mcp
    command: npx
    connect_timeout: 30
    timeout: 60
```

> ⚠️ **关键坑：`args` 必须是 YAML 数组，不能用 JSON 字符串。** `hermes config set mcp_servers.tmux-bridge.args '["-y", "tmux-bridge-mcp"]'` 会把 args 存成 JSON 字符串 `'["-y", "tmux-bridge-mcp"]'`（类型 str），而非 YAML 列表（类型 list），导致 MCP server 启动时 `1 validation error for StdioServerParameters args`。**必须用 Python + yaml 库直接编辑 config.yaml**，或手动编辑。

### 验证

```bash
# Hermes MCP 连接测试
hermes mcp test tmux-bridge
# 预期：Connected, 9 tools discovered

# 裸 JSON-RPC 测试
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | npx -y tmux-bridge-mcp
```

> ⚠️ **Mid-session 新增 MCP 不会生效。** 需要在 MCP server 配置完成后再启动新 session（或 `/reset`）。

## read-act-read 工作流（核心模式）

tmux-bridge 强制「先读后写」的 guard 机制：`tmux_type`、`tmux_keys`、`tmux_message` 在调用前必须先 `tmux_read` 目标 pane。

```
1. tmux_read(target, lines=30)   → 看 CC 当前状态
2. 判断：需要干预？
3. tmux_type(target, "消息")      → 往 CC pane 打字
4. tmux_read(target, lines=5)     → 读 guard + 确认字打上去了
5. tmux_keys(target, ["Enter"])   → 提交
6. sleep 等待 CC 处理
7. tmux_read(target, lines=30)   → 看 CC 回复
8. 继续讨论或发下一轮指令
```

### 完整的监控-干预-讨论循环（Hermes↔CC）

```python
# 伪代码：Hermes session 内执行
target = "cc_aidali_wechat_20260608:0.0"  # CC pane

# 监控循环
while task_running:
    output = tmux_read(target, lines=30)
    if "❯" in last_line(output) and "●" not in output:
        # CC idle — 检查是否完成
        if task_complete_marker in output:
            break
    elif "Error" in output or "Traceback" in output:
        # 发现问题 → 干预
        tmux_read(target, lines=5)   # guard
        tmux_type(target, "你这里报错了，检查一下 X 模块")
        tmux_read(target, lines=5)   # guard
        tmux_keys(target, ["Enter"])
    sleep(30)

# 完成 — 读取最终结果
final = tmux_read(target, lines=100)
```

## 实测数据（2026-06-08）

| 测试项 | 结果 | 详情 |
|---|---|---|
| 环境 | ✅ | macOS 26.2, tmux 3.6b, Node 26, npx v0.3.0 |
| Hermes MCP 接入 | ✅ | `hermes mcp test tmux-bridge` → Connected, 9 tools (1445ms) |
| tmux_list | ✅ | 正确列出所有 pane（CC session + 测试 pane） |
| tmux_read 真实 CC | ✅ | 读出 `❯` idle + `Not logged in · Run /login` 状态 |
| tmux_type + tmux_keys | ✅ | 文字打入 cat 进程 pane，正确回显 |
| read-act-read 双向循环 | ✅ | 多轮「读→判断→写→读回复」无失败 |
| tmux_message | ⚠️ | 送达但 `[tmux-bridge from:...]` 前缀在 zsh 下被 glob 拦截 → 对 CC REPL 无影响 |

## 局限性

- CC 必须在 tmux 中运行（当前 claude-code skill 的默认模式，不是问题）
- Mid-session 新增 MCP 需新 session
- 无跨机器支持（tmux 在同一台机器上）
- `tmux_message` 前缀含方括号，zsh 下会触发 glob → 建议用 `tmux_type` + `tmux_keys` 组合

## 集成路线

1. ✅ Hermes MCP 配置完成（config.yaml）
2. ✅ 工具可用性验证通过（9 tools）
3. ⬜ claude-code skill 接入：将 read-act-read 循环写入 Core Rules 或独立 reference
4. ⬜ 全 profile 部署：cron-worker / lane-* 等 profiles 同步 tmux-bridge MCP 配置
