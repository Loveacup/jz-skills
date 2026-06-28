# OMP Shell 通道冒烟测试记录

> 实测环境：omp **v16.2.2**（`/opt/homebrew/bin/omp`，macOS Darwin 25.5.0），默认 provider 路由到 **kimi-code**（cost=0）。jq `/usr/bin/jq`。测试日期 2026-06-28。
> 本记录是"待验证 → 已验证/已证伪"的真相归档。**草案里若干 prompt 协议在 v16.2.2 中不存在**，实现已按真实接口对齐。

## 1. 真实 CLI 接口（vs 设计草案）

| 草案假设 | v16.2.2 实测真相 | 实现采用 |
| --- | --- | --- |
| `omp -p "audit:..."` 内置 audit 协议 | ❌ **不存在** `audit:`/`govern:` prompt 协议 | 用 `--append-system-prompt`（templates/）约束 OMP 输出内层 JSON |
| prompt 里写 `output=json` | ❌ JSON 输出靠 **`--mode json`** flag | `omp -p --mode json` |
| `--mode json` 返回单个 JSON | ❌ 返回 **JSONL 事件流**（NDJSON，每行一事件） | monitor 用 jq 逐事件提取 |
| Advisor 是独立审查者 | ⚠️ `--advisor` 是 flag，语义是**被动 self-review 每轮**（审 OMP 自己，非审目标） | 默认不开；`omp-send --advisor` 透传，语义差异见 §5 |
| 超时未定义 | ✅ 内置 `--max-time <秒>`（macOS **无** `timeout` 命令！） | send 用 `--max-time` + perl alarm 双兜底 |
| scope 待验证 | ✅ `--cwd`（工作目录）+ `--tools`（白名单）+ `--approval-mode`/`--auto-approve` | 默认只读白名单 `read,grep,glob,lsp,web_search` |
| ACP delegate_task 待 Hermes #32401 | ⚠️ `omp acp` 子命令**已存在**（OMP 这端是 ACP server over stdio）；Hermes client 端仍待 #32401 | channel=acp 仍标待验证，send 拒发 |
| MCP 双向桥 | ⚠️ 未见 omp 直接 `mcp` server 子命令（有 acp/agents/plugin 等） | channel=mcp 标待验证，send 拒发 |

其它实测可用 flag：`--no-session`（ephemeral，审计用）、`--no-tools`、`--system-prompt`、`--thinking`、`--print-thoughts`、`--config`、`--profile`。

## 2. `--mode json` 的 JSONL 事件结构

一次 `omp -p --mode json` 的输出是按行的事件流，典型序列：

```
session → agent_start → turn_start
  → message_start(user) → message_end(user)
  → message_start(assistant) → message_update × N（流式 delta，thinking/text 逐块）
  → message_end(assistant) → turn_end → agent_end
```

- **`turn_end`** 是权威终结事件，含 `.message.stopReason`（正常=`stop`）与 `.message.usage`。
- **最终答案**在 assistant 的 `message_end` / `turn_end` 的 `.message.content[]`，取 `type=="text"` 的块（排除 `thinking` 块——它带超长 `thinkingSignature` base64）。
- `message_update` 极多（每个 delta 一条），导致**输出体积巨大**：见 §4。

### 双层解析（实现的核心）

```
传输层（omp JSONL）：jq slurp → 取最后一个 assistant text 的完整字符串
应用层（审计载荷）：从该 text 抠出内层 JSON（```json 围栏优先，否则首{…末}）→ jq 校验
```

OMP **不原生输出** `severity/evidence/summary`——这些靠 `templates/audit-prompt-template.md` 的 system prompt 约束 OMP 产出，再由 `omp-monitor.sh` / `gate-verify.sh` 双层抠取。

## 3. 输出体积警告（重要工程约束）

| 任务 | raw 大小 | 行数 |
| --- | --- | --- |
| "reply smoke-ok"（纯文本，--no-tools） | **122 KB** | 41 |
| 审计 10 行 login.js（含 1 次 read 工具） | **1.96 MB** | ~310 |

→ **monitor / finish 绝不能把 raw 打进对话上下文**，必须 jq 提取关键字段、raw 落盘 `/tmp/omp-raw-<id>.json`。这与 cc-tmux「大输出写文件」一致。

## 4. 冒烟用例

### 4.1 最小连通性（纯文本）
```bash
omp -p --mode json --no-tools --no-session --max-time 60 "Reply with exactly: smoke-ok"
# exit 0；assistant 最终 text = "smoke-ok"；stopReason=stop；provider=kimi-code cost=0
```

### 4.2 真实 audit 端到端（SQL 注入，**关键验证**）
目标：`src/login.js` 第 3 行字符串拼接用户输入构造 SQL。

```bash
omp-start.sh --mode audit --task "审查 src/login.js 是否存在 SQL 注入" \
  --cwd <repo> --allowed-path src --criterion "所有 SQL 必须参数化" --task-id smoke-real
omp-send.sh   --state <state> --max-time 70     # 真实 omp，17s，exit 0，raw 1.96MB
omp-monitor.sh --state <state>                  # → status=reported
```

OMP **严格遵守了 system-prompt 的 JSON 契约**，monitor 双层提取得到：
```json
{"severity":"blocker",
 "summary":"src/login.js 在第 3 行直接拼接用户输入构造 SQL，存在 SQL 注入漏洞，未使用参数化查询。",
 "evidence":[{"type":"file","ref":"src/login.js:3"}],
 "reject_instruction":"将 SQL 改为参数化查询，使用占位符…禁止直接拼接用户输入。",
 "confidence":"high"}
```
- `severity=blocker`（合法）· `evidence` 指向**真实文件+行号** · `stopReason=stop`
- `omp-finish --accept` → **exit 2 被拒**（blocker 红线生效）
- `omp-finish --human-review` → verdict YAML 完整，status=rejected+human_review=true

## 5. 验收红线的真实结果

| 承重墙 | 验证方式 | 结果 |
| --- | --- | --- |
| P1 可裁决 | 委派包缺 criterion → gate-verify | ✅ exit 1 |
| P3 可审计 | 全程 state/raw/verdict 落盘 + 归档 | ✅ |
| P7 溯源（evidence 非空） | 空 evidence 输出 → gate-verify | ✅ exit 10；真实 audit evidence 指真实行号 |
| P9 终止上限 | round 第4 / reject 第3 → gate-counter | ✅ exit 20 |
| 不采信自报 | blocker → finish --accept | ✅ exit 2 拒绝 |
| 默认只读 | --tools 白名单 read,grep,glob,lsp,web_search | ✅ omp 只 read 未写 |

`tests/run-all.sh`：**45/45 通过**（mock omp，零 token）。

## 6. 仍待验证（不得写成已实现）

- ✅ 通道：Shell + **RPC 均已真实端到端**（RPC 为过渡首选；协议/架构/证据见 [[omp-rpc-acp-notes]]）。
- ✅ `--advisor` 已探查：print/rpc 模式下不注入额外结构化事件、不干扰审计 JSON 提取（实测是 self-review，与草案"独立审查者"语义不同）→ 默认不开。
- ✅ `govern:inspect` 已真实端到端（生产配置巡检：severity=blocker、evidence=5、输出含 plan/rollback）。仍待：`clean/deep-clean/sql` 真实写执行（默认 dry-run/计划优先，未真跑破坏性写）；`evidence` 子模式同管道未单独跑。
- OMP MCP server 是否存在、tool schema、认证（未见对应子命令）。
- ACP：`omp acp` server 端已在，但 Hermes client 端 `delegate_task` 字段待 #32401（见 [[omp-rpc-acp-notes]]）。
- OMP 是否对 `--cwd` 外路径做硬隔离（当前 scope 由 prompt 级 + 工具白名单 + gate 三重软防，未验证 OMP 原生 path enforcement）。
- 大 raw（>2MB）在长审计下的 jq 解析耗时上界。
