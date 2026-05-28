---
name: "pi-supermemory"
description: "Configure, debug, and maintain the pi-supermemory extension on Windows. Use when supermemory tool errors, 403, crashes, config changes, or extension source needs modification."
version: 2
created: "2026-05-29"
updated: "2026-05-29"
platforms: [windows]
---

## 🚨 Red Flags

| 你会想 | 现实 |
|--------|------|
| "403 而已，可能是临时网络问题" | **403 = container tag 未授权。检查 projectContainerTag。不会自动恢复。** |
| "改完代码就行，不用 rebuild" | **pi 加载 src/index.ts 直接执行，源码改动生效。但 dist/ 是给 npm publish 用的。** |
| "改个配置不用重启 pi" | **supermemory 配置在 session_start 时加载一次，必须重启。** |
| "日志没有 error 就是没问题" | **crash 时来不及写日志。addMemory: start 后无 follow-up = 已崩溃。** |
| "settings.update 返回 403 但 add 能用，忽略就行" | **它是 fire-and-forget，未 catch 的 rejection 在 Node.js 22 杀进程。必须 catch。** |

## 🔀 Decision Tree

```
supermemory 出问题 →
├── 403 错误？
│   └── → §Container Tags，检查 projectContainerTag
├── pi 直接退出/crash？
│   └── → §Crash Diagnosis，检查日志截断点
├── 工具调用后无响应？
│   └── → §Check Logs，看 ~/.pi-supermemory.log
├── 首次设置/更换 API key？
│   └── → §Quick Setup
├── 需要改扩展代码？
│   └── → §Architecture + §Rebuild
├── 搜索结果重复/混乱？
│   └── → §Container Tags，检查 user/project tag 是否相同
└── 通用 Supermemory 概念？
    └── → 参考 shared/supermemory-maintenance（通用参考）
```

## Architecture

```
pi agent (Windows, Node.js 22)
  └── pi-supermemory extension (~/pi-supermemory-fork/)
        ├── src/index.ts          ← tool 注册 + lifecycle hooks
        ├── src/services/client.ts ← Supermemory SDK (v4.21.1) 封装
        ├── src/config.ts         ← 配置加载
        └── dist/index.js         ← bun build 产物 (~11MB)
             │
             ▼
        Supermemory API (api.supermemory.ai)
          ├── POST /v3/documents  ← add
          ├── POST /v4/search     ← search (hybrid/memories/documents)
          ├── GET  /v3/documents  ← list
          ├── PATCH /v3/settings  ← settings.update (⚠️ fire-and-forget)
          └── POST /v4/profile    ← profile
```

## Quick Setup

```bash
# 1. 安装扩展
pi install /path/to/pi-supermemory-fork

# 2. 配置 API key (~/.pi/agent/supermemory.jsonc)
{
  "apiKey": "sm_...",
  "userContainerTag": "Pi",
  "projectContainerTag": "sm_project_cli"
}

# 3. 重启 pi
# /reload 或重新启动 pi agent
```

**验证**：重启后调用 `supermemory mode='search' query='test' scope='user'`，应返回 results 数组。

## Container Tags

| Scope | Tag | 用途 |
|-------|-----|------|
| user | `Pi` | 跨项目的偏好/画像 |
| project | `sm_project_cli` | 项目特定的配置/经验 |

**PITFALL**: tag 大小写敏感。`Cli` ≠ `cli`。本账户仅授权 `Pi` 和 `sm_project_cli`。

## Procedure

### Check Logs
```bash
cat ~/.pi-supermemory.log | tail -50
```
找：403、error、或截断的操作（`addMemory: start` 后无 success/error = crash 信号）。

### Crash Diagnosis
Node.js 22 中 unhandled promise rejection 是 fatal 的。
- 模式：日志在 `xxx: start` 处截断 → 操作执行期间进程被 kill
- 根因：fire-and-forget promise 未 catch（已知：settings.update）
- 修复：添加 `.catch()` handler

### 403 Fix
container tag 未授权 → 改 `~/.pi/agent/supermemory.jsonc` 的 `projectContainerTag`

### Rebuild
```bash
cd ~/pi-supermemory-fork
npx bun install    # 如果缺少 peer dependencies
npx bun run build  # 生成 dist/index.js
```
pi 加载 TS 源码直接执行，重启即生效。dist/ 供 npm publish 使用。

## Pitfalls

| 陷阱 | 说明 |
|------|------|
| SDK v4.21.1 CJS + .mjs shim | require 和 import 均可用，但 settings.update 可能独立 403 |
| 日志截断 = crash | 非网络超时，是进程被 kill |
| 配置不热加载 | 改 config 必须重启 pi |
| user/project 同 tag | 搜索结果重复，已用不同 tag 隔离 |
| 新记忆有延迟 | 写入后 status=`queued`，索引完成才能搜到 |

完整 pitfalls → `references/common-pitfalls.md`

## Known Fixes

| 日期 | 问题 | 修复 |
|------|------|------|
| 2026-05-29 | settings.update() unhandled rejection → crash | `src/services/client.ts` getClient() 添加 `.catch()` |
| 2026-05-29 | project scope 403 (tag `Cli` 未授权) | projectContainerTag 改为 `sm_project_cli` |

完整 changelog → `references/changelog.md`

## References

| 文件 | 何时读 |
|------|--------|
| `references/common-pitfalls.md` | 遇到未列出的错误时 |
| `references/changelog.md` | 查历史修复记录 |
| `shared/supermemory-maintenance/SKILL.md` | Supermemory 通用概念和 SDK API |
| `hermes/supermemory-hermes/SKILL.md` | Hermes 多 profile 记忆架构 |

## Verification

- [ ] 配置改动后重启 pi 并调用 supermemory 工具 → success:true
- [ ] 日志中操作有完整的 start → success/error 对
- [ ] rebuild 后 `dist/index.js` 存在，体积 ~11MB
- [ ] `supermemory mode='search' query='test' scope='user'` 返回非空结果
