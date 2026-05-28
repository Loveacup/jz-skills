---
name: "pi-supermemory"
description: "Configure, debug, and maintain the pi-supermemory extension on Windows. Use when supermemory tool errors, 403, crashes, config changes, or extension source needs modification."
version: 1
created: "2026-05-29"
updated: "2026-05-29"
platforms: [windows]
---

## 🚨 Red Flags

| 你会想 | 现实 |
|--------|------|
| "403 而已，可能是临时网络问题" | **403 = container tag 未授权。检查 projectContainerTag。不会自动恢复。** |
| "改完代码就行，不用 rebuild" | **pi 加载 src/index.ts 直接执行，源码改动生效。但 dist/ 是给 npm publish 用的，保持同步。** |
| "改个配置不用重启 pi" | **supermemory 配置在 session_start 时加载一次，必须重启。** |
| "日志没有 error 就是没问题" | **crash 时来不及写日志。addMemory: start 后无 follow-up = 已崩溃。** |
| "settings.update 返回 403 但 add 能用，忽略就行" | **它是 fire-and-forget，未 catch 的 rejection 在 Node.js 22 杀进程。必须 catch。** |

## When to Use
Use when: (1) supermemory tool returns errors (403, 401, timeout). (2) pi crashes when calling supermemory. (3) Changing container tags, API keys, or config. (4) Modifying the pi-supermemory extension source code. (5) Debugging extension behavior (hooks, compaction, memory injection). (6) Understanding the architecture (SDK, API endpoints, auth flow). (7) Building/reinstalling the extension.

Do NOT use for: (1) Routine add/search/list/forget operations — those are the tool itself, not maintenance. (2) General memory strategy discussions — use shared/supermemory-maintenance for that.

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
          ├── POST /v4/search     ← search (hybrid)
          ├── GET  /v3/documents  ← list
          ├── PATCH /v3/settings  ← settings.update (⚠️ fire-and-forget)
          └── POST /v4/profile    ← profile
```

## Quick Reference

| 文件 | 用途 |
|------|------|
| `~/.pi/agent/supermemory.jsonc` | 配置文件（API key, container tags） |
| `~/pi-supermemory-fork/src/index.ts` | 扩展主逻辑（tool 注册 + hooks） |
| `~/pi-supermemory-fork/src/services/client.ts` | Supermemory SDK 封装 |
| `~/pi-supermemory-fork/src/config.ts` | 配置加载 |
| `~/.pi-supermemory.log` | 运行日志 |
| `~/.supermemory-pi/credentials.json` | OAuth 凭据 |

**Allowed container tags**: `Pi`, `sm_project_cli`

## Procedure
1. **Check logs**: `cat ~/.pi-supermemory.log | tail -50` — 找 403、error、或截断的操作（crash 信号）
2. **Verify config**: `cat ~/.pi/agent/supermemory.jsonc` — apiKey、projectContainerTag、userContainerTag
3. **Check source**: `~/pi-supermemory-fork/src/` — index.ts（tool+hooks）、services/client.ts（SDK）、config.ts（配置）
4. **Crash diagnosis**: Node.js 22 中 unhandled rejection 是 fatal 的。找未被 catch 的 promise
5. **403 fix**: container tag 未授权 → 改 projectContainerTag
6. **Rebuild**: `cd ~/pi-supermemory-fork && npx bun run build`
7. **Restart pi** 使改动生效

## Pitfalls
- pi 加载 TS 源码（`pi.extensions: [./src/index.ts]`），源码改动重启即生效，不依赖 dist/
- supermemory SDK v4.21.1，CJS + .mjs ESM shim，require 和 import 均可用
- settings.update() (PATCH /v3/settings) 可能 403 即使 add/search 正常。必须 catch
- 日志中 `addMemory: start` 后无 success/error = 操作期间 crash
- user scope 固定走 `Pi`，project scope 走配置的 tag。同 tag = 搜索结果重复
- tag `Cli` 未授权，已废弃

## Known Fixes
- **2026-05-29**: getClient() 中 settings.update() 未 catch 导致 unhandled rejection → Node.js 进程退出。修复：添加 `.catch()` handler

## Verification
1. 改配置后重启 pi，调用 supermemory 工具返回 success:true，不 403
2. 代码修复后日志显示操作完成（success 或 error），不截断
3. rebuild 后 `dist/index.js` 存在，体积 ~11MB
4. `supermemory mode='search' query='test' scope='user'` 返回结果数组
