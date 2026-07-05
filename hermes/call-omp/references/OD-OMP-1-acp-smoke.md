# OD-OMP-1 — ACP 真实探针规范

> **这是证据产出探针，不是 ACP 通道启用判定器。**
> 本探针只记录 `omp acp` 真实行为（启动、协议兼容性、stderr、耗时、字节数），
> 产出结构化证据包。**ACP 不会成为默认通道，除非真实证据通过且明确配置。**

## 探针目标（OD-OMP-1）

验证 call-omp 能否真实调用 `omp acp`（ACP server over stdio），并记录完整交互证据。
**不改 call-omp 默认通道行为**——即使探针通过,ACP 也不自动启用,仍需显式配置。

## 裁决三态

| 状态 | 语义 | 退出码 |
|---|---|---|
| `compatible_smoke_passed` | `initialize` 返回 `protocolVersion=1`，且观测到 session/prompt 或 `session/update` 响应 | 0 |
| `started_but_protocol_incompatible` | 进程启动并可响应 JSON-RPC，但未满足完整 OD-OMP-1 序列 | 2 |
| `failed_to_start_or_timeout` | 进程启动失败、崩溃、超时、或 stdout 为空 | 3 |

**零 token 测试路径（mock 模式）**：
- `--mock-pass` — 伪造 `compatible_smoke_passed`（不启 omp）
- `--mock-incompatible` — 伪造 `started_but_protocol_incompatible`
- `--mock-timeout` — 伪造 `failed_to_start_or_timeout`

## 证据目录结构

探针产出 7 个文件（`--out <dir>`，缺省临时目录）：

| 文件 | 内容 | 用途 |
|---|---|---|
| `summary.json` | 裁决状态、耗时、字节数、退出码 | 机器判定 |
| `result.md` | 人类可读报告（状态 + 文件清单 + 裁决说明） | 人工复核 |
| `stdin.ndjson` | 发给 `omp acp` 的 JSON prompt（单行） | 复现/调试 |
| `stdout.ndjson` | `omp acp` 返回的完整 NDJSON 流 | 协议分析 |
| `stderr.log` | stderr 抓取（可能含进度/警告，非致命） | 错误诊断 |
| `timeline.ndjson` | 时间轴事件（spawn/stdin_sent/stdout_line/exit） | 性能/序列分析 |
| `process.json` | 进程元信息（omp 路径、版本、pid、退出码） | 环境记录 |

## 探针工作流

1. **查找 omp 二进制**（PATH / `/opt/homebrew/bin/omp` / `/usr/local/bin/omp`）
2. **准备最小 ACP JSON-RPC 序列**（NDJSON over stdin）：
   ```json
   {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientInfo":{"name":"call-omp-acp-smoke","version":"0.1.0"},"capabilities":{}}}
   {"jsonrpc":"2.0","method":"initialized","params":{}}
   {"jsonrpc":"2.0","id":2,"method":"session/new","params":{"cwd":".","mcpServers":[]}}
   {"jsonrpc":"2.0","id":3,"method":"session/prompt","params":{"sessionId":"call-omp-smoke-session","prompt":[{"type":"text","text":"Reply with exactly: smoke-ok."}]}}
   ```
3. **启动 `omp acp`**（stdin 管道、stdout/stderr 分流、超时护栏 30s）
4. **裁决协议兼容性**：
   - `initialize` 响应 `protocolVersion=1` 且观测到 session/prompt 或 `session/update` → `compatible_smoke_passed`
   - `initialize` 成功但 session/prompt 未观测 → `started_but_protocol_incompatible`（当前 OMP 16.3.2 实测状态）
   - 超时 / 非零退出 / stdout 为空 → `failed_to_start_or_timeout`
5. **写 7 个证据文件**

## 当前本机观测（OMP 16.3.2）

本机真实运行 `bash scripts/omp-acp-smoke.sh --timeout 10` 的当前结论：

```json
{"status":"started_but_protocol_incompatible","reason":"initialize_ok_but_session_prompt_unobserved","initialize_ok":true,"session_observed":false,"prompt_or_update_observed":false}
```

`stdout.ndjson` 中 OMP 返回了 JSON-RPC initialize result，包含：

```json
{"protocolVersion":1,"agentInfo":{"name":"oh-my-pi","title":"Oh My Pi","version":"16.3.2"},"agentCapabilities":{"loadSession":true,"promptCapabilities":{"embeddedContext":true,"image":true},"sessionCapabilities":{"list":{},"fork":{},"resume":{},"close":{}}}}
```

因此：**OMP ACP server 可启动并完成 initialize 握手；但当前一次性 NDJSON 探针尚未观测到 session/prompt/update 完整序列。** 后续若要推进，需要实现交互式 ACP client，而不是把 initialize 成功误判为 full compatibility。

## 使用示例

### 真实探针
```bash
bash scripts/omp-acp-smoke.sh --out /tmp/acp-evidence
# → 退出码 0/2/3，证据在 /tmp/acp-evidence/{summary.json,result.md,...}
```

### Mock 测试（零 token）
```bash
bash scripts/omp-acp-smoke.sh --mock-pass --out /tmp/mock-pass
# → 退出 0，/tmp/mock-pass/summary.json: "status":"compatible_smoke_passed"

bash scripts/omp-acp-smoke.sh --mock-incompatible --out /tmp/mock-inc
# → 退出 2，"status":"started_but_protocol_incompatible"

bash scripts/omp-acp-smoke.sh --mock-timeout --out /tmp/mock-to
# → 退出 3，"status":"failed_to_start_or_timeout"
```

## 与 ACP 通道启用的关系

**探针通过 ≠ ACP 自动启用。**

即使 `omp-acp-smoke.sh` 退出 0（`compatible_smoke_passed`），call-omp 的默认通道仍是
**优先 ACP > 降级 RPC > 再降级 Shell**（v0.2.0 起，SKILL.md § 调用接口）。
真实启用 ACP 需：
1. 本探针 `compatible_smoke_passed`（证据充分）
2. Hermes 支持 `delegate_task(acp_command='omp')`（目前 v0.6.8 已可用，见 SKILL.md）
3. 用户/配置明确启用 ACP 通道（通过 `omp-send.sh --channel acp`）

**本探针的价值**：产出证据包供人工/自动判定，不自动变更 call-omp 行为。

## 集成位置

- **探针脚本**：`scripts/omp-acp-smoke.sh`
- **规范文档**：`references/OD-OMP-1-acp-smoke.md`（本文件）
- **测试覆盖**：`tests/run-all.sh` Group 19（mock 三路径 + 证据文件完整性）
- **SKILL.md 引用**：版本历史 v0.6.9 / Package D slice 3

## 参考

- `scripts/call-omp-smoke.sh` — 跨平台 mock-only 冒烟（不启 omp）
- `references/platform-adapters.md` — 两类冒烟严格区分
- `references/omp-shell-smoke-test.md` — 真 token Shell 通道冒烟
- `SKILL.md` § 调用接口 1. ACP delegate_task — ACP 通道 4 步状态机
