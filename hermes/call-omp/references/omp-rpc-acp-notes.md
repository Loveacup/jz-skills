# OMP RPC / ACP 通道：实测协议与设计

> 配套 `references/omp-shell-smoke-test.md`（Shell 通道）。本文档记录 **RPC 通道**（过渡首选）的
> 真实协议与封装设计，以及 **ACP 通道**（终局预留）的定位。全部基于 omp **v16.2.2** 本机实测。

## 0. 通道优先级（最新设计决策）

`RPC（过渡首选）＞ Shell（快速单次降级）＞ ACP（终局首选（默认））`

- RPC 启动/就绪失败 → `omp-send` 自动降级 Shell（状态记 `degraded_from=rpc`）。
- ACP 当前不实现，channel=acp 拒发（exit 3），架构预留接口位。

## 1. RPC 协议（实测）

### 1.1 启动（server→client）
`omp --mode rpc <flags>` 启动后立即输出 NDJSON：
```
{"type":"ready"}
{"type":"extension_ui_request","id":"…","method":"setWidget","widgetKey":"autoresearch"}
{"type":"available_commands_update","commands":[ … slash 命令清单 … ]}
```
然后阻塞等 stdin。`{"type":"ready"}` 是「可发指令」信号。

### 1.2 发指令（client→server）
stdin 写**一行** NDJSON：
```json
{"type":"prompt","message":"<文本>"}
```
- omp 对 `.message` 做 `startsWith('/')` 分流：`/` 开头 = slash 命令；否则 = 一次 prompt turn。
- 字段名实测确认：`type` 必须是已知命令（`prompt` 有效；`parse`/`input` → `Unknown command`）；
  prompt 的载荷字段是 **`message`**（`text`/`content`/`value`/`prompt` 均报 `A.startsWith` undefined）。
- system prompt 在**启动时** `--append-system-prompt` 注入（全局，对所有 turn 生效），实测能让 OMP
  稳定按审计 JSON 契约输出。

### 1.3 输出：一个 prompt → 多 turn（关键）
一个 prompt 常产生**多个 turn**：
```
turn_start → … tool_execution_* … → turn_end(stopReason=toolUse, content:[thinking,toolCall])   ← 中间 tool turn
turn_start → message_end(content:[thinking,text]) → turn_end(stopReason=stop)                     ← 最终文本 turn
```
- **完成判定 = 出现 `stopReason=="stop"` 的 turn_end**（最终回答）。只看首个 `turn_end` 会停在
  toolUse turn，此时 assistant 还没输出最终文本 → 提取为空 → 误判 rejected。
- 最终审计 JSON 在最后一个 assistant `message_end` 的 `content[].text`（双层解析同 Shell）。
- daemon 处理完一个 prompt 后**不退出**，回到等待 stdin（持续连接，可发下一个 prompt 复用）。

## 2. RPC 通道封装（实现）

```
omp-send（channel=rpc）
  ├─ mkfifo                                  /tmp/omp-rpc-<id>.fifo
  ├─ holder:  ( sleep MAXTIME > fifo 2>/dev/null ) </dev/null &   # 保持 fifo 写端 + 兼超时
  ├─ daemon:  ( omp --mode rpc <flags> < fifo > raw 2> err ) &    # 常驻；记 rpc_pid/holder_pid
  ├─ 等 ready（轮询 raw；daemon 早死立即降级，不空等）
  ├─ turn_start_line = wc -l raw            # marker：只看本轮
  └─ echo {"type":"prompt","message":…} > fifo   # 发 prompt，立即返回（异步）

omp-monitor（channel_used=rpc）
  ├─ rpc_turn_done(raw, marker)?  →  本轮出现 stopReason=stop 的 turn_end？
  │     是 → 完成校验（gate-verify + 双层提取，与 shell 通用）→ reported
  │     否 + daemon 活 → running（报进度，可重复轮询）
  │     否 + daemon 死 → rejected（崩溃/超时）
  └─ 干预：kill <rpc_pid>

omp-finish / omp-gc：rpc_stop（kill daemon+holder、rm fifo），幂等
```

### 2.1 两个致命坑（已修，有回归测试）
1. **后台进程 fd 继承父管道**：holder/daemon 若不 `</dev/null` + 重定向 stderr，当 `omp-send` 被
   `2>&1 | grep` 之类管道调用时，holder 继承管道写端并持有 MAXTIME，导致上游 grep/tail 不结束 →
   整条命令卡到超时。修复：所有后台进程切断 stdin + 重定向 stdout/stderr。
2. **流式 raw 末行不完整**：daemon 持续写，monitor 读时末尾可能半行。`jq .`（整体解析）/`jq -rs`
   （slurp）会整体失败。改为 `grep turn_end` + 逐行 `jq -c`（容忍坏末行），提取最后一个完整 text。

## 3. 真实 RPC 端到端证据

目标：含 SQL 注入的 `src/login.js`。`omp-start`（channel=rpc）→ `omp-send` → 轮询 `omp-monitor` → `omp-finish`。
```
send 1–3s 返回（启动 daemon + 发 prompt，异步）
monitor 轮询：running×4 → reported（约 8–10s）
内层审计 JSON：{"severity":"blocker","evidence":[{"type":"file","ref":"src/login.js:3"}], …}
finish --human-review：status=rejected、daemon 已停、fifo 已清
```
`tests/run-all.sh` 含 mock-daemon 回归（toolUse+stop 双 turn、降级、acp pending_acp），全套 **55/55 通过**。

## 4. ACP 通道（终局路径，已实现）

- OMP 这端：`omp acp`（子命令实测存在）= 「Run Oh My Pi as an ACP server over stdio」。
- Hermes client 端：`delegate_task(acp_command='omp')` 依赖 **#32401**，当前 Hermes v0.17.0 未合入。
- 本 skill 实现：`omp-send --channel acp` 渲染 prompt → 写 `status=pending_acp` → Hermes 读取 state 调用 `delegate_task`。
- #32401 合入后：ACP 子代理结果回调映射进同一 6 状态机与 verdict schema，gate 不变。

## 5. 仍待验证

- RPC 跨 finish 的 daemon 复用（当前 finish 关 daemon，下轮 send 新建；未做长连接跨轮复用）。
- RPC 多 prompt 在同一 daemon 上的 turn 边界（marker 方案已支持，但未压测多轮累积 raw）。
- ACP delegate_task 实际回调结果（`omp-send` 已实现状态写，待 Hermes 端触发实测）。
- `--advisor` 在 rpc 下的增益（实测 print/rpc 均不注入额外结构化输出）。
