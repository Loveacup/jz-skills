---
name: pi-hermes-setup
description: "理解 Pi（Windows）与 Hermes（Mac Mini）联动架构、排查跨机器 MCP 连接问题。当用户问 'pi和hermes怎么连的'、'MCP 架构'、'为什么连不上hermes'、或需要新增 MCP 服务器时使用。不要用于单一 MCP 故障 — 用 recover-hindsight-mcp。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  tags: [pi, hermes, architecture, mcp, ssh, cross-machine, diagnosis]
---

# Pi ↔ Hermes 联动架构

Pi 在 Windows，Hermes 在 Mac Mini，通过 SSH 隧道 + MCP 协议联动。

---

## 🚨 Red Flags: 排查别乱猜

| 你的第一反应 | 为什么不对 |
|--------------|------------|
| "连不上就是 SSH 隧道断了" | 也可能是 Mac Mini 端服务挂了 |
| "所有 MCP 出问题都是同一原因" | hindsight/codegraph/utools 各有不同故障模式 |
| "重启 Pi 能解决" | Pi 只是客户端，根因通常在 Mac Mini 端 |
| "直接改端口就行" | 需要同步改 mcp.json，否则配置不一致 |

---

## 🔀 故障诊断决策树

### 症状 → 原因 → 操作

| 症状 | 最可能原因 | 操作 |
|------|-----------|------|
| hindsight `ECONNRESET` | Mac Mini 上 hindsight 挂了 | 用 `recover-hindsight-mcp` |
| hindsight `ECONNREFUSED` | SSH 隧道断了 | 重建隧道 |
| codegraph 工具不可用 | npx 未安装或路径问题 | `npx @colbymchenry/codegraph serve --help` |
| 所有 MCP 都连不上 | 网络问题 | `ssh <user>@<mac-mini-ip> echo ok` |
| hindsight 返回空结果 | profile 不匹配 | 检查 `HINDSIGHT_PROFILE_NAME` |

---

## 架构速览

```
Windows (Pi)                          Mac Mini (Hermes)
┌────────────────────┐               ┌────────────────────────┐
│ ~/.pi/agent/       │               │ ~/.hermes/             │
│ ├── mcp.json       │               │ ├── hermes-agent/      │
│ └── skills/        │               │ │   └── venv/bin/      │
│                    │               │ │       ├── hindsight-*│
│ MCP Clients:       │               │ │       └── hermes     │
│ hindsight → :本地───┼──SSH tunnel──→│ hindsight-local-mcp    │
│ codegraph → npx    │               │   :<port> (bank)      │
│ utools    → :3501  │               │                        │
└────────────────────┘               │ PostgreSQL (pg0)       │
                                     │   :<port> (db)        │
                                     └────────────────────────┘
```

> 完整架构图见 [references/architecture.md](references/architecture.md)

---

## MCP 配置参考

Pi 的三个 MCP 服务器配置在 `~/.pi/agent/mcp.json`：

```json
{
  "mcpServers": {
    "hindsight": { "type": "http", "url": "http://localhost:<隧道端口>/mcp/<bank-id>/", "lifecycle": "eager" },
    "codegraph": { "command": "npx", "args": ["-y", "@colbymchenry/codegraph", "serve", "--mcp", "--path", "."] },
    "utools":    { "type": "http", "url": "http://127.0.0.1:3501/mcp" }
  }
}
```

---

## Skills 清单

Pi 当前加载的 skills（`~/.pi/agent/pi-hermes-memory/skills/`）：

| Skill | 用途 |
|-------|------|
| web-research-router | 搜索路由 |
| edge-tts | 文本转语音 |
| hyperframes | 视频/动画 |
| obsidian-cli-* | Obsidian 笔记 |
| pi-grill | 设计拷打 |
| skill-creator | Skill 创作 |
| ui-ux-pro-max | UI/UX 设计 |
| recover-hindsight-mcp | hindsight 恢复 |

> 完整清单见 [references/skills-catalog.md](references/skills-catalog.md)

---

## 验证清单

- [ ] `ssh <user>@<mac-mini-ip> echo ok` — Mac Mini 可达
- [ ] 三个 MCP 服务器全部 `connect` 成功
- [ ] `mcp connect hindsight` 返回 26 tools
- [ ] `hindsight_recall` 可正常搜索
