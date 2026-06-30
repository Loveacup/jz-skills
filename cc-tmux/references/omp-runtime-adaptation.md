# OMP (Oh My Pi) Runtime Adaptation

> 2026-06-27 关键发现：用户已从 PI 切换到 **OMP (Oh My Pi)**，cc-tmux 需要适配新运行时。

## OMP 与 PI 的区别

| 特性 | PI (pi-coding-agent) | OMP (Oh My Pi) |
|------|----------------------|----------------|
| 版本 | v16.2.0 (Windows) | v16.1.22 (MacBook) |
| 命令 | `pi` | `omp` |
| 路径 | Windows 7800x3d | `/opt/homebrew/bin/omp` |
| 内置工具 | `web_search` / `web_fetch` (WRR extension.ts) | `web_search` (内置，默认 Anthropic) |
| 扩展机制 | `ExtensionAPI` | `--hook` / `-e` / `--plugin-dir` |

## OMP 关键发现

### 内置 web_search 工具
- 默认使用 **Anthropic** provider
- 支持 `--provider` 切换：Exa / Brave / Perplexity / Tavily
- 环境变量：`EXA_API_KEY` / `BRAVE_API_KEY` / `TAVILY_API_KEY` / `PERPLEXITY_API_KEY`

### 扩展机制
```bash
# 加载 hook/extension 文件
omp --hook /path/to/hook.js

# 加载扩展文件
omp -e /path/to/extension.js

# 加载插件目录
omp --plugin-dir /path/to/plugin/

# 禁用扩展发现
omp --no-extensions
```

### 环境变量
- `OMP_PROFILE`：命名 profile
- `PI_CODING_AGENT_DIR`：session 存储目录（兼容 PI）
- `PI_SMOL_MODEL` / `PI_SLOW_MODEL` / `PI_PLAN_MODEL`：模型覆盖

## 适配策略

### 1. 运行时检测
```bash
# 检测 OMP
which omp > /dev/null 2>&1 && omp --version

# 或检查环境变量
env | grep OMP_PROFILE
```

### 2. WRR 适配
- WRR `extension.ts` 原注册到 `pi-coding-agent`
- 现在需要适配 OMP 的扩展机制
- 可能通过 `--plugin-dir` 或 `--hook` 加载

### 3. 工具注册
- OMP 已有内置 `web_search`，可能不需要额外注册
- 但 WRR 的 fallback 机制（exa → brave → searxng）需要移植

## 相关文档

- `references/runtime-adaptive-design.md` (WRR skill) — 运行时自适应改造设计
- `references/runtime-scope-clarification.md` (WRR skill) — 运行时范围澄清
