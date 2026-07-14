# OD-OMP-2 — ACP 交互式方言探测器

> **这是方言检测器，不是 ACP 默认通道启用器。**
> 本探测器以交互模式启动 `omp acp`：先发送 `initialize`，读取 `agentCapabilities.sessionCapabilities`，再按真实 capabilities 选择下一步探测方法。它只产出证据，不修改 call-omp 热路径。

## 探测目标

OD-OMP-1 已证明本机 OMP 16.3.2 能完成 `initialize`，但一次性 NDJSON 没有观测到 `session/new` / `session/prompt`。OD-OMP-2 的目标是进一步确认：OMP ACP 暴露的会话方言到底是什么。

核心策略：

1. 发送 `initialize`。
2. 解析 `result.agentCapabilities.sessionCapabilities`。
3. 如果 capabilities 包含 `list/fork/resume/close`，按 **OMP 16.3.x 方言**发送 `session/list`。
4. 如果 capabilities 包含标准 `new/prompt`，按 **standard session/new + session/prompt 方言**继续探测。
5. 如果只有 initialize，无 session capabilities，则记录为 `initialize_only`。

## 裁决状态

| 状态 | 语义 | 退出码 |
|---|---|---:|
| `dialect_detected` | 已根据 initialize capabilities 识别出可继续适配的 ACP 方言；不等于完整任务通道已可用 | 0 |
| `initialize_only` | initialize 成功，但未暴露可用 session capabilities | 2 |
| `protocol_incompatible` | 启动并返回内容，但 initialize 不合法或协议不符 | 2 |
| `failed_to_start_or_timeout` | OMP 不存在、进程失败、超时、stdout 为空等 | 3 |

## summary.json schema

```json
{
  "status": "dialect_detected",
  "reason": "omp_session_capabilities_detected",
  "protocol_version": 1,
  "agent_name": "oh-my-pi",
  "agent_version": "16.3.2",
  "dialect": "omp-session-capabilities",
  "initialize_ok": true,
  "capabilities_observed": true,
  "session_capabilities": ["close", "fork", "list", "resume"],
  "probe_methods_sent": ["initialize", "initialized", "session/list"],
  "probe_methods_succeeded": ["initialize"],
  "session_list_observed": false,
  "session_new_ok": false,
  "session_prompt_ok": false,
  "elapsed_sec": 1,
  "stdin_bytes": 284,
  "stdout_bytes": 503,
  "stderr_bytes": 0,
  "exit_code": 0,
  "mock": null
}
```

解释：`dialect_detected` 只表示“下一步该适配哪种 ACP 方言”已经有证据；如果 `session_list_observed=false`，下一刀仍需做事件循环/会话恢复适配，不能声称完整 ACP 热路径可用。

## 证据目录结构

`--out <dir>` 下固定 7 个文件：

| 文件 | 用途 |
|---|---|
| `summary.json` | 机器可读裁决与 schema |
| `result.md` | 人类可读报告 |
| `stdin.ndjson` | 实际发送给 `omp acp` 的 JSON-RPC 方法 |
| `stdout.ndjson` | `omp acp` 返回流 |
| `stderr.log` | stderr 抓取 |
| `timeline.ndjson` | spawn / send / receive / verdict 时间线 |
| `process.json` | omp 路径、版本、pid、退出码 |

## Mock 模式（零 token）

| Mock | 模拟场景 | 预期 |
|---|---|---|
| `--mock-omp1632` | OMP 16.3.2：capabilities=`list/fork/resume/close` | `dialect_detected`, `dialect=omp-session-capabilities`, 发送 `session/list` |
| `--mock-session-new` | 标准 `session/new` + `session/prompt` 方言 | `dialect_detected`, `dialect=standard-session-new-prompt` |
| `--mock-initialize-only` | 只有 initialize，无 session capabilities | `initialize_only` |
| `--mock-timeout` | 启动/超时失败 | `failed_to_start_or_timeout` |

## 真实探测命令

```bash
cd hermes/call-omp
OUT=/tmp/od-omp-2-acp-probe-$(date +%Y%m%d-%H%M%S)
bash scripts/omp-acp-probe.sh --out "$OUT" --timeout 20
jq . "$OUT/summary.json"
sed -n '1,20p' "$OUT/stdout.ndjson"
```

## 当前本机预期

对 OMP 16.3.2，预期不是 `session/new` 成功，而是：

```json
{
  "status": "dialect_detected",
  "dialect": "omp-session-capabilities",
  "session_capabilities": ["close", "fork", "list", "resume"],
  "probe_methods_sent": ["initialize", "initialized", "session/list"]
}
```

这说明下一步应实现 OMP ACP 方言适配（围绕 `session/list/resume/fork/close`），而不是继续假设 Open Design 的 `session/new/session/prompt` 标准序列。

## 非目标

- 不修改 `omp-start.sh` / `omp-send.sh`。
- 不把 ACP 自动切成默认可用热路径。
- 不运行真实审计任务、不烧长 token。
- 不实现 MCP / image / embeddedContext / 多轮 prompt。
- 不解决 OMP auth/model 配置。

## 集成位置

- 脚本：`scripts/omp-acp-probe.sh`
- 测试：`tests/run-all.sh` Group 20
- 上游探针：`references/OD-OMP-1-acp-smoke.md`
- 跨平台边界：`references/platform-adapters.md`
