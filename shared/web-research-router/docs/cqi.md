# WRR 持续质量改进（CQI）与诊断

记录运行中发现的质量问题、根因判定与处置。仅登记**结论与可执行动作**，
不维护时间线 / phase。

---

## CQI-001 · SearXNG MCP 子进程泄漏（判定：Hermes 核心问题，非 WRR）

**状态**：已定性 / 等待 Hermes 侧修复 · **严重度**：中（资源泄漏，非功能性）
· **发现日**：2026-06-28

### 现象
系统残留多个 `mcp-searxng` 进程（每个为 `npm exec mcp-searxng` → `node .../mcp-searxng`
两进程一对），跨多次 gateway 重启累积，日志无 cleanup 报错。

### 关键澄清：这不是 WRR 的进程
- 泄漏的是 **Hermes 内置 `searxng` MCP server**，配置在
  `~/.hermes/config.yaml` 的 `mcp_servers.searxng`（`command: npx` / `args: [-y, mcp-searxng]`），
  作为"MCP 备份工具"（`mcp_searxng_*`）存在。
- **WRR 自身的 SearXNG 路径不涉及该进程**：`wrr/engines/searxng.py` 的 `SearxngEngine`
  直接用 `httpx` 调 `SEARXNG_URL`（`http://127.0.0.1:32080/search`），不 spawn 任何子进程。
- 因此 WRR 的 `plugin.yaml` / 代码对该泄漏无控制权。

### 根因（基于源码与进程树取证）
泄漏 = **Hermes 网关生命周期缺口**，而非进程跟踪或清理逻辑本身的缺陷：

1. **清理逻辑是正确的，但只挂在"优雅关闭"路径上**
   - `tools/mcp_tool.py` 的 `_kill_orphaned_mcp_children()`（L4602）通过 `os.killpg`
     向 spawn 时记录的 pgid 发 SIGTERM→（2s）→SIGKILL，能正确连带回收 npm+node。
   - PID 跟踪在 macOS 上经 `psutil`（已确认 venv 内 `psutil 7.2.2` 可用）正常工作，
     spawn 的子进程会被记入 `_stdio_pids` / `_stdio_pgids`（L1796–1827）。
   - 子进程由 MCP SDK 以 `start_new_session=True` 启动，**自成会话/进程组**
     （取证确认：`npm exec` 进程 `stat=Ss`、`pgid==自身 pid`）。所以
     `killpg(子进程pgid)` 不会误杀 gateway —— 清理是安全且有效的。

2. **但回收只在 `shutdown_mcp_servers()` 中触发，而它位于关闭流程的最末端**
   - `gateway/run.py:17878` 在 `await runner.wait_for_shutdown()`（L17849，完整 drain）
     **之后**才调 `shutdown_mcp_servers()` → `_stop_mcp_loop()` →
     `_kill_orphaned_mcp_children(include_active=True)`。
   - `atexit` 只注册了 `remove_pid_file` / `release_gateway_runtime_lock`（L17776–17777），
     **没有注册 MCP 回收**。

3. **`--replace` 重启会绕过该末端回收**
   - 新 gateway 以 `gateway run --replace` 启动时，向旧实例发 SIGTERM；若旧实例
     未在期限内退出，**升级为 SIGKILL**（`run.py:17467`："Old gateway did not exit
     after SIGTERM, sending SIGKILL"）。
   - SIGKILL 不可捕获、不跑 atexit ⇒ `shutdown_mcp_servers()` 永不执行 ⇒
     该 gateway 名下的 npm+node 成为孤儿。
   - 进程树取证显示泄漏对分别挂在 **三个不同 profile 的 gateway** 名下
     （`default` ppid=86441 / `cron-worker` ppid=72212 / `regent` ppid=72384），
     与"每个 profile 各自起一份 searxng MCP、各自在被替换/强杀时泄漏"完全吻合。

> 注：执行包中"进程无 setsid 包装、与 gateway 共享 pgid"的假设**与取证相反**——
> 子进程恰恰因 `start_new_session=True` 自成进程组，`killpg` 本可奏效；真正的缺口
> 在"强杀路径不触发回收"。

### 处置

**WRR 侧（本仓库可做）——已完成本登记。** 该问题不在 WRR 代码范围，不做代码改动。

**监控建议（可选，低成本）**：把下列巡检纳入例行健康检查，发现累积即手动清理或重启收敛：
```bash
# 统计残留的 mcp-searxng 对；>2 即提示泄漏累积
ps -ax -o pid,ppid,pgid,stat,command | grep -c '[m]cp-searxng'
# 一键清理（按进程组，安全连带 node 子进程）
pkill -f 'mcp-searxng'
```

**根治选项（二选一，均需用户决策，非 WRR 改动）**：
- **选项 A（推荐，配置级，零代码）**：在 `~/.hermes/config.yaml` 关闭
  `mcp_servers.searxng`。理由：WRR v4 的 `SearxngEngine` 已用直连 HTTP 覆盖 SearXNG
  搜索能力，内置 `searxng` MCP 仅作冗余备份（`mcp_searxng_*`）。关闭即根除泄漏源，
  功能损失仅"MCP 备份工具菜单里少一项 searxng"。
- **选项 B（Hermes 核心修复）**：见下方 issue 摘要。

### 给 Hermes 提 issue 的事实摘要
> **标题**：stdio MCP 子进程在 `gateway run --replace` 强杀路径下泄漏
>
> - **环境**：macOS（darwin 25.5.0），Hermes venv `psutil 7.2.2`，Python 3.12。
> - **复现**：配置任一 stdio MCP（如 `searxng: npx -y mcp-searxng`）→ 反复
>   `gateway run --replace`（或令旧实例 drain 超时被 SIGKILL）。
> - **现象**：每次强杀残留 `npm exec` + `node` 一对孤儿，跨重启累积。
> - **根因**：MCP 子进程回收（`tools/mcp_tool.py:shutdown_mcp_servers` →
>   `_kill_orphaned_mcp_children`）仅在 `gateway/run.py:17878` 的优雅关闭末端调用；
>   `atexit`（run.py:17776-77）未注册 MCP 回收；`--replace` 的 SIGKILL 升级
>   （run.py:17467）绕过全部回收。
> - **回收逻辑本身正确**：`killpg` 打到子进程自有 pgid（`start_new_session=True`，
>   pgid==自身 pid），psutil 跟踪在 macOS 正常——**缺的是触发时机**。
> - **建议修复方向**：① 为 SIGTERM 关闭路径在更早、更可靠处（或 `atexit`）补一次
>   `_kill_orphaned_mcp_children(include_active=True)`；② `--replace` 在 SIGKILL 旧
>   gateway **之后**，由新 gateway 兜底按 pgid 回收旧实例遗留的 stdio MCP 组；
>   ③ 或缩短 drain 期限/延长 SIGKILL 宽限，让优雅回收有机会跑完。
>
> 取证细节见 `/tmp/cc-output/hermes-cc-default-wrr-p2-p3-0628-1850/`（进程树、源码行号引用）。
