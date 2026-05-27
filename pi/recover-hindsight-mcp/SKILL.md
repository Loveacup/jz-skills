---
name: recover-hindsight-mcp
description: "恢复 Pi → SSH隧道 → Mac Mini hindsight MCP 连接。当 pi 报错 'SSE error: TypeError: fetch failed: read ECONNRESET' 且目标为 hindsight 时使用。不要用于非 ECONNRESET 错误、其他 MCP 服务器故障、或一般网络问题。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  tags: [mcp, hindsight, ssh, tunnel, recovery, pi-config]
---

# Recover Hindsight MCP for Pi

恢复 Pi（Windows）通过 SSH 隧道连接 Mac Mini 上的 hindsight MCP 服务（26 个工具）。

---

## 🚨 Red Flags: 别跳过诊断

| 你的第一反应 | 为什么不对 |
|--------------|------------|
| "重启 Pi 就行" | 根因在 Mac Mini 端。重启 Pi 属于浪费时间 |
| "hindsight 应该随 gateway 自动启动" | hermes gateway 和 hindsight-local-mcp 是 **两个独立进程**。gateway 跑着不代表 MCP 在线 |
| "换个端口就行了" | 换端口必须同步改 `~/.pi/agent/mcp.json`。改了不验证 = 白改 |
| "Mac Mini 上之前好好的" | hindsight 收到 SIGTERM/sleep 后不会自动重启 |

**如果你刚才心里冒出了上面任何一句 → 停止，按下面决策树一步步来。**

---

## 🔀 诊断决策树

### Step 1: Mac Mini 还活着吗？

```bash
ssh <user>@<mac-mini-ip> echo ok
```

❌ 连不上 → 检查 Mac Mini 是否开机、网络是否通、SSH 密钥是否配置。

### Step 2: Mac Mini 上 hindsight 在跑吗？

```bash
ssh <user>@<mac-mini-ip> "lsof -i :<mcp-port> | grep LISTEN"
```

❌ 没有 LISTEN → 启动（替换 `<hermes-root>` 为 hermes 安装路径）：

```bash
ssh <user>@<mac-mini-ip> "cd <hermes-root>/hermes-agent && HINDSIGHT_PROFILE_NAME=<profile> nohup ./venv/bin/hindsight-local-mcp --port <mcp-port> --host 127.0.0.1 > /tmp/hindsight-mcp.log 2>&1 &"
```

### Step 3: Windows 本地端口可用吗？

```bash
netstat -ano | grep "LISTENING" | grep 9177
```

✅ 没有输出 → 用 9177，跳到 Step 4。
❌ 有 LISTENING 但 `taskkill` 失败（僵尸占用）→ 用 **9178**。

### Step 4: 建 SSH 隧道

```bash
ssh -f -N -L <本地端口>:localhost:<mcp-port> <user>@<mac-mini-ip>
```

### Step 5: 更新 Pi MCP 配置

编辑 `~/.pi/agent/mcp.json`：

```json
"url": "http://localhost:<端口>/mcp/hermes-default/"
```

> 详细信息见 [references/connection-config.md](references/connection-config.md)

### Step 6: 验证连通

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:<端口>/mcp/hermes-default/
```

---

## 速查表

| 项目 | 值 |
|------|-----|
| Mac Mini | `<mac-mini-ip>` / `<user>` |
| hermes profile 端口 | `<mcp-port>` (默认 9177) |
| hindsight 二进制 | `<hermes-root>/hermes-agent/venv/bin/hindsight-local-mcp` |
| Pi MCP 配置 | `~/.pi/agent/mcp.json` |
| SSH 认证 | 密钥免密 |

---

## 验证清单

- [ ] `curl` 返回 200
- [ ] Pi 的 `mcp connect hindsight` 返回 **26 tools**
- [ ] `hindsight_recall` 可正常搜索记忆
