---
name: call-omp
description: >-
  通过 Shell 通道标准化调用 OMP v16.2.2（Oh My Pi）为 Hermes 提供独立审计、govern 治理与
  编码辅助能力面，全程可监控、可干预、可讨论。当任务需要：独立 Advisor 风格审查并得到
  nit/concern/blocker 级 verdict；结构化 JSON 审计报告；govern 的 inspect/clean/deep-clean/
  evidence/sql 治理；或 OMP 的 LSP/DAP/Hashline/浏览器/多搜索后端能力面时使用。触发词：
  OMP、Oh My Pi、omp 审计、独立审查、govern 治理、审计报告、Advisor。与 cc-tmux 互补
  （cc-tmux 管长会话编码委派，omp 管审计/治理/工具面）。
version: 0.3.0
type: autonomous-ai-agents
author: anyis (Hermes Agent Team)
license: MIT
---

# omp

Thin skill + fat scripts：本文件只讲**何时用、怎么调、边界、坑**；gate、状态、JSONL 双层解析、
计数、危险检测都在 `scripts/` 里（每个脚本有完整头注与 `--help`）。Hermes 负责目标拆解、风险裁决、
结果解释；OMP 负责审计/治理/工具执行；脚本负责把关。

> ⚠️ 实现按 omp **v16.2.2 实测接口**对齐，**不是**草案里的 `audit:`/`govern:` prompt 协议
> （那在 v16.2.2 不存在）。真实路径见 `references/omp-shell-smoke-test.md`。

## 触发条件

**使用**本 skill：
- 用户点名 OMP / Oh My Pi / `omp`。
- 需要独立审查者给 `nit`/`concern`/`blocker`/`pass` 级、**带证据**的 verdict。
- 需要结构化 JSON 审计报告（`audit` 模式）。
- 需要 govern 治理：`inspect`/`evidence`（只读优先）、`clean`/`deep-clean`/`sql`（高危，需 rollback）。
- 需要 OMP 能力面：Hashline、LSP、DAP、浏览器、搜索后端、子代理编排。
- 与 cc-tmux 互补：cc-tmux 跑实现，omp 做独立审计/治理。

**不使用**：普通文件读取/简单 shell/本地解释；用户禁止外部 CLI；任务要读密钥/token/密码/.env；
要求绕过 gate/scope/轮次/证据。

## 核心原则（与 cc-tmux 对齐）

**协作三原则**（灵魂）：
1. **持续监控** — 调 OMP 后必须 `omp-monitor` 跟状态，不是 fire-and-forget。长任务用 `--async` + 轮询。
2. **可及时干预** — async 模式记 pid，任何时候 `kill <pid>` 可中断；状态权威文件随时可查。
3. **可讨论** — 执行前（dry-run 看渲染 prompt）、中（monitor 看进度）、后（verdict）都可与 Hermes/CC 讨论。

**四条红线**（脚本硬卡，不可绕过）：
- **不采信自报** — OMP 的自然语言总结不能单独作完成证据；只认结构化 verdict + evidence。
- **不空证据** — accept 必须有 evidence（gate-verify `exit 10`）。
- **不越界** — 所有任务必须有 scope；危险任务无 scope/rollback 即拦（gate-danger `exit 10`）。
- **硬终止** — round > 3 或 reject > 2 强制停（gate-counter `exit 20`）。

## 调用接口（优先级：ACP ＞ RPC ＞ Shell）

三通道输出同构 **JSONL 事件流**（非单 JSON），由 `omp-monitor` 双层解析；一切调用先过三 gate
（verify/danger/counter），输出同一 verdict schema。默认只读工具白名单 `read,grep,glob,lsp,web_search`，
放开写需 `omp-send --allow-write`（仅 govern 写类）。

### 1. ACP delegate_task（终局首选，已实现）
`delegate_task(acp_command='omp')`——OMP 这端 `omp acp`（server over stdio）已存在。
使用方式：
```bash
# omp-send 渲染 prompt 后 status=pending_acp，Hermes 读取 state 文件调用：
delegate_task(acp_command='omp', goal=<PROMPT 内容>, context=<背景>)
```
- `omp acp` 启动 ACP server，`delegate_task` 将其作为子代理 spawn。
- 结果通过 `delegate_task` 回调返回，由 `omp-monitor` 写入同一 state/verdict schema。
- 子代理隔离最干净，无 daemon 状态管理负担。

### 2. RPC 通道（过渡备选，已实测可用）
`omp --mode rpc` 持续连接（NDJSON stdio）：daemon 常驻、fifo 发 prompt、stdout 落盘。
```bash
omp --mode rpc --no-session --tools <白名单> [--cwd <scope>] [--advisor] \
    --append-system-prompt <templates/模板>            # 启动 daemon → 输出 {"type":"ready"}
echo '{"type":"prompt","message":"<任务正文>"}' > <fifo>    # 发一轮（对 .message 做 / 分流）
```
- 天然异步：`omp-send` 启动 daemon 发 prompt 后立即返回，`omp-monitor` 轮询 + daemon 心跳。
- 一个 prompt 常产生**多 turn**（toolUse turn + 最终 `stopReason=stop` turn）；完成判定看 **stop**。
- 复用连接省启动开销；可干预（`kill <daemon pid>`）；holder 进程保持 fifo 写端兼超时。

### 3. Shell 通道（快速单次降级，已实测可用）
`omp -p --mode json` 单次进程。**RPC 启动/就绪失败时 `omp-send` 自动降级到此**（记 `degraded_from`）。
```bash
omp -p --mode json --no-session --max-time <N> --tools <白名单> [--cwd <scope>] \
    --append-system-prompt <templates/模板> "<任务正文>"
```
适合短审计；`--async` 可后台 + 轮询。
## 操作流程（start → send → monitor → finish）

### Step 1 · start —— 生成委派包 + 过 gate
```bash
# 方式 A：完整委派包 JSON（推荐，Hermes 用 jq 生成；schema 见 templates/delegation-package-template.md）
echo '<JSON>' | scripts/omp-start.sh --package-json -
# 方式 B：便捷参数
scripts/omp-start.sh --mode audit --task "审查 auth 模块" \
  --cwd /path/repo --allowed-path src/auth --criterion "SQL 参数化" --criterion "路由校验 session"
```
→ 过 gate-verify + gate-danger，写状态文件，`status=gated`。gate 失败 `exit 2`；omp 缺失 `exit 3`(channel_unavailable)。

### Step 2 · send —— 渲染并调用 omp

```bash
scripts/omp-send.sh --state <状态文件>                      # 按委派包 channel（默认 acp（终局首选），rpc 失败降级 shell，shell 失败 rejected）
scripts/omp-send.sh --state <状态文件> --channel shell      # 强制 shell 单次（短任务）
scripts/omp-send.sh --state <状态文件> --channel shell --async  # shell 后台 + 轮询
scripts/omp-send.sh --state <状态文件> --channel acp        # ACP 委托（delegate_task）→ status=pending_acp
scripts/omp-send.sh --state <状态文件> --dry-run            # 只看渲染 prompt + 将执行的命令，不烧 token
```
→ gate-counter 计一轮（超限 `exit 20`），渲染 prompt（templates/），按通道调 omp，raw JSONL 落盘，`status=running`。
  RPC：启动 daemon + fifo 发 prompt，立即返回（异步轮询）；Shell：单次进程（同步/--async）。

### Step 3 · monitor —— 持续监控 + 双层校验
```bash
scripts/omp-monitor.sh --state <状态文件>            # 完成→校验；async 进行中→报进度
# async 轮询：循环调用直到 phase != running；干预：kill <pid>
```
→ 校验 JSONL 完整、内层 severity/summary/evidence、severity∈{nit,concern,blocker,pass}。
全过 `status=reported`；任一失败 `status=rejected`（空证据 `exit 10`）。

### Step 4 · finish —— 转 verdict + 裁决
```bash
scripts/omp-finish.sh --state <状态文件> --accept         # status=accepted + 归档
scripts/omp-finish.sh --state <状态文件> --reject         # status=rejected + 计 reject（可能 exit 20 停）
scripts/omp-finish.sh --state <状态文件> --human-review   # 升级人工（不占 reject 配额）
```
→ 输出 Hermes verdict YAML（severity/evidence/reject_instruction/next_action）。
**accept 红线**：status 须 reported、severity≠blocker、evidence 非空，违反则 `exit 2` 拒绝。

## 状态机（7 态）

`created`（生成委派包）→ `gated`（gate 全过）→ `running`（RPC/Shell 执行中）/ `pending_acp`（ACP 已渲染，待 Hermes delegate_task）→ `reported`（已校验）→
`accepted`（接受+归档）/ `rejected`（拒绝/超限/人工复核）。状态是 skill 侧约定，非 OMP 原生。

## verdict / 委派包 schema（与 cc-tmux 兼容）

- 委派包共享 `task / criterion / threshold / risk / auditor / independence_level`（见 templates/）。
- verdict 共享 `severity / evidence / reject_instruction`，附 `summary / next_action`。

## 与 cc-tmux 的分工边界

| 维度 | omp skill | cc-tmux skill |
| --- | --- | --- |
| 核心对象 | OMP v16.2.2 | Claude Code CLI |
| 通道 | `omp --mode rpc`（首选）/ `-p`（降级） | tmux 会话 |
| 强项 | 独立审计、govern 治理、LSP/DAP/Hashline/浏览器/搜索 | 长会话编码、交互式 CLI、tmux 监控 |
| 监控/干预 | 状态文件 + rpc/async daemon pid + `kill` | tmux pane + watcher + heartbeat |
| 协作 | 输出 verdict/evidence，Hermes 裁决 | 输出进展/结果，Hermes 验收 |

典型链路：Hermes → cc-tmux 实现 → omp 审计 → Hermes 裁决（blocker 不直接触发 cc-tmux 改，先裁决）。

## 常见坑（Pitfalls）

- **把 OMP 自然语言总结当证据** → 必拒；只认 evidence。
- **`--mode json` 当单 JSON 解析** → 它是 **JSONL 事件流**；用 `omp-monitor` 提取，别 `jq .` 当单对象。
- **raw 体积巨大**（一次审计可达 **1.96 MB**）→ 绝不打进上下文，raw 落盘、只提取关键字段。
- **macOS 无 `timeout`** → 用 omp 内置 `--max-time` + 脚本的 perl alarm 兜底。
- **bash `set -u` + 中文紧邻变量名**（`$RL、` 会炸）→ 脚本里一律 `${RL}、`；改脚本时注意。
- **clean/deep-clean/sql 缺 rollback** → gate-danger `exit 10` 拦。
- **忘了轮次/reject 上限** → gate-counter 硬终止；别在 stop 后自动重试。
- **委派包夹带密钥/token/.env** → gate-danger 拦（只标记不回显，防二次泄露）。
- **blocker 直接 accept** → finish `exit 2` 拒；按 evidence reject 或转 cc-tmux 修复。
- **RPC 一个 prompt 多 turn** → 完成看 `stopReason=stop`（最终文本 turn），不是首个 `turn_end`（那常是 toolUse turn，提不到审计文本）。
- **RPC daemon 后台进程 fd** → 必须 `</dev/null` + 重定向 stdout/stderr，脱离父管道；否则被 `… | grep` 调用时 holder 持管道写端，上游卡到超时。
- **ACP 通道需 delegate_task 支持** → `omp-send --channel acp` 后 status=pending_acp，Hermes 须调用 `delegate_task(acp_command='omp')` 完成。不要当 fire-and-forget。

## 待验证清单

详见 `references/omp-shell-smoke-test.md` §6。要点：`--advisor` 真实语义（实测是 self-review，非草案的
独立审查者）、govern 五模式真实执行（目前仅 audit 真实端到端）、MCP/ACP 可用性、OMP 原生 path
enforcement。**待验证项不得在输出中写成已实现事实。**

## 测试

`bash tests/run-all.sh` —— 自包含套件（mock omp，零 token），覆盖 gate 硬卡 + 四步状态机 +
async 监控/干预 + ACP delegate_task + 红线。当前 **55/55 通过**。

## 版本历史

### v0.3.0（2026-06-28）— ACP 审查驱动安全加固

基于 ACP delegate_task 对 `omp-send.sh` 的深度代码审查（15+ 问题，P0 2 项），修复：

| 级别 | 修复 | 描述 |
|:---:|------|------|
| P0 | RPC daemon 复用权限泄露 | 复用前校验 `rpc_tools`/`rpc_auto_approve` 与当前配置一致，不一致则重启 |
| P0 | heredoc 命令替换风险 | `$(...)` 替换为 `printf` + 字符串拼接，消除维护者误引入注入的风险 |
| P1 | gate-counter 静默错误 | `2>/dev/null` → `2>"$C_ERR"`，失败时 cat stderr |
| P1 | 关键字段空值校验 | `TASK`/`MODE_FULL` 空值→exit 3；`RL`/`JL` 非数字→默认 3 |
| P2 | MAXTIME 数值校验 | 非正整数→exit 3 |
| P2 | 变量展开引号 | dry-run 输出 `${CWD:+--cwd "$CWD"}` |

### v0.2.0（2026-06-28）— ACP 升为默认通道

- 优先级 RPC > Shell > ACP → **ACP > RPC > Shell**
- `omp-send.sh` 默认 channel `rpc` → `acp`
- 三通道 smoke test 全部通过（RPC ✅ / Shell ✅ / ACP ✅）

### v0.1.0（2026-06-28）— 初始发布

- 三通道 RPC / Shell / ACP 实现
- 7 态状态机
- 三 gate（verify/danger/counter）
- 55/55 单元测试
