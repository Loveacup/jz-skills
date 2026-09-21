---
name: call-omp
description: "通过受 gate 约束的 RPC / Shell / 实验性 ACP 通道调用 OMP，适用于独立代码审计、证据包裁决、受控执行和明确授权的治理任务。默认只读、默认 RPC、失败关闭。不要用于无 scope/rollback 的写入、危险发布、删除、密钥传递或递归 self-call。"
version: 0.9.0
---

# call-omp

把 OMP 当作**不可信执行者/审计者**：委派包先过 gate，输出重新取证，任何截断、非零退出或非终态 `stopReason` 都拒绝。

## 🚩 Red Flags

出现任一项立即停止自动链路，转人工或 `cc-tmux`：

- `task_id` 含 `/`、`..`、空白、控制字符，或超过 128 字符。
- `govern:clean|deep-clean|sql` 缺真实 scope、`risk.level=high` 或 rollback。
- 任何任务试图用废弃的 `--allow-write` 授权；写入只接受协调层显式签发的版本化 `capability_grant`。
- OMP 退出码非零、raw 为空、缺 `turn_end`，或最后 `stopReason != stop`。
- verdict 不是合法 JSON、`evidence=[]`、scope 越界、raw 无界增长。
- 要求发送密钥、改生产、推送、删除或绕过平台安全策略。
- 当前调用已经来自 OMP self-call；禁止递归。

## 什么时候使用

| 任务 | mode | 默认权限 |
|---|---|---|
| 独立代码/架构/安全审计 | `audit` | 只读 |
| 基于 evidence bundle 裁决 | `audit` + `bundle_only` | 只读 |
| 有边界的命令执行 | `execute` | 缺 grant 时只读；Shell 显式 grant 精确映射 OMP 原生能力 |
| 清理/深度清理/SQL 治理 | `govern:clean|deep-clean|sql` | 当前只允许规划/审计；自动写入已隔离停用 |

不使用：普通搜索、简单机械编辑、无验收条件的开放探索、不可逆外部发布。

## 兼容基线与通道

当前验证基线：OMP `16.3.2`。`omp --version` 只证明 CLI 版本，不证明 provider/model 可用。

通道策略：

1. **RPC（默认）**：持续 JSONL，会话内可多轮；`omp-start.sh` 默认 `channel=rpc`。
2. **Shell（降级）**：RPC 启动失败时的 bounded fallback；适合单轮。
3. **ACP（实验性）**：不是默认通道。先运行 `omp-acp-smoke.sh` / `omp-acp-probe.sh` 识别方言；当前 Hermes `delegate_task` 若无 ACP 参数，不得伪装为已支持。

协议细节按需读：[RPC / ACP notes](references/omp-rpc-acp-notes.md)。

## 四步闭环

所有命令在 skill 根目录运行。生产路径为 `scripts/`；gate 为 `scripts/gate/`。

### 1. START：建包并过 gate

优先使用 JSON 委派包；最小样例见 [package example](references/omp-audit-package-json-minimal-example.md)。

```bash
scripts/omp-start.sh \
  --mode audit \
  --task "审查目标与边界" \
  --criterion "criterion 1" \
  --criterion "criterion 2" \
  --task-id audit-001
```

`task_id` 必须匹配：

```text
[A-Za-z0-9][A-Za-z0-9._-]{0,127}
```

START 仅在 `gate-verify` 与 `gate-danger` 都通过后写 `status=gated`。

### 2. SEND：受控调用

```bash
scripts/omp-send.sh --state /tmp/omp-state-audit-001.json
```

默认工具白名单：`read,grep,glob,lsp,web_search`。Shell `mode=execute` 可携带 `call-omp.capability-grant.v1`，把明确授权的 tools/cwd/add_dirs/approval 精确映射到 OMP；完整合同见 [Capability Grant v1](references/capability-grant-v1.md)。

`--allow-write` 是废弃且模糊的布尔开关，继续隔离：

```bash
scripts/omp-send.sh --state /tmp/omp-state-clean-001.json --allow-write
```

所有 `--allow-write` 必须 exit 2。显式 grant 仅适用于 Shell `execute`，不得用于 audit/govern/bundle-only/RPC/ACP；每个 grant 必须绑定现存绝对 cwd，且 cwd/add_dirs 均被 scope 覆盖、denied_paths 为空。`allowed_paths` 不是 OS 沙箱，强隔离由上层 workspace/container/worktree 提供。任何写入都由当前 agent 独立验收。

### 3. MONITOR：失败关闭

```bash
scripts/omp-monitor.sh --state /tmp/omp-state-audit-001.json --json
```

接受条件：

- raw 非空且 JSONL 可解析
- 最后存在 `turn_end`
- 最后 `stopReason=stop`
- OMP 退出码为 0
- audit/govern verdict：`severity ∈ nit|concern|blocker|pass`、summary 非空、evidence 非空
- execute：允许非 verdict 文本，但退出码/stopReason/完整性规则完全相同

任何一项失败写 `status=rejected`；沉默、超时、截断不是通过。

### 4. FINISH：人工裁决

```bash
scripts/omp-finish.sh --state /tmp/omp-state-audit-001.json --accept
scripts/omp-finish.sh --state /tmp/omp-state-audit-001.json --reject --reason "缺证据"
scripts/omp-finish.sh --state /tmp/omp-state-audit-001.json --human-review
```

`--accept` 只允许 `status=reported`；`blocker`、rejected、非零退出不得接受。客观命令与 exit code 由当前 agent 重新运行验证，不采信 OMP 自报。

## Bundle-only 审计

先产出 evidence bundle，再让 OMP 只读 bundle，不暴露工作区：

```bash
scripts/omp-bundle-code-audit.sh --repo /abs/repo --out /tmp/bundle --scope src/module
```

必须检查：`manifest.json`、`file-list.txt`、`diff.patch`、命令输出与 exit code。中型 bundle 拆成独立 criterion；raw 快速增长或重复调用即停止。详见 [bundle gates](references/bundle-only-audit-gates.md) 与 [runaway policy](references/bundle-only-runaway-stop-policy.md)。

### P0：受资源监督的 bundle-only Shell

真正经由 Shell 执行的 bundle-only 审计（直连 Shell 与 RPC→Shell 回退两条路径）一律**强制异步且受 `scripts/omp-resource-supervisor.py` 监督**，不再有同步回退。supervisor 把 OMP 放在独立 session/pgrp，硬性执行 raw ≤ 20 MiB（child pre-exec 继承 `RLIMIT_FSIZE`，即使 `setsid` 逃逸后代仍持有 stdout FD 也守得住），并原子写脱敏 forensic state。

monitor 在解析 raw/verdict **之前**先认证资源 sidecar（规范化路径、拒 symlink/非常规文件、精确 v1 task/state/raw/pid 绑定、pid/pgid/session 交叉核对）；一旦 `resource_rejected`，先于任何 verdict 解析转 `rejected`。

**资源 cap 拒绝的正确处理**：保留 bounded 证据 → `omp-finish --reject` → 改用**重新划定范围、体积更小的证据包**，或转**人工复核**。**绝不**把资源 cap 拒绝改写成同步 shell 重跑，也**绝不**手动接受。（历史上「raw > 20MB 改同步重跑」的指引在 P0 后作废。）

## P1：`required_actions` 判决契约

audit verdict 可携带**可选、机器可读的 `required_actions`**（唯一真源 `contracts/required-actions.schema.json`，`kind ∈ revise|human_review|stop`）。操作约束：

- **新 audit prompt 必须产出 v1 标记** `required_actions_contract: "call-omp.required_actions.v1"`（逐字，不得改写）。带此标记即触发严格 gate：外层 allowlist `{severity,summary,evidence,reject_instruction,confidence,required_actions_contract,required_actions}`、schema-valid actions、`pass=[]` 且非 pass ≥1 action。
- **不要给 legacy 格式的判决贴 v1 标记**。marker-free 判决走 legacy 兼容路径；只有确为 v1 结构时才标记，否则严格 gate 会误判。
- **monitor legacy 标记**：`required_actions` 缺失时 monitor 持久化一个 legacy 标记，表示该判决未走结构化 action，不代表「无需动作」。
- **`next_action` 是兼容接口，`required_actions` 才是结构化指令**。finish 双写二者；消费方优先读 `required_actions`。
- **不要手动提升被拒的 raw-cap 审计**：资源拒绝路径不合成 actions，禁止手动补写 `required_actions` 把 `resource_rejected` 改写成审计通过。

详见 `P1-required-actions-evidence.md`。

## 错误处理

| 现象 | 动作 |
|---|---|
| `channel_unavailable` | 检查安装/PATH；不伪造结果 |
| RPC 不 ready | bounded Shell fallback；保留降级证据 |
| `toolUse` 结束、无 `stop` | rejected |
| execute exit code 非零 | rejected，禁止 finish accept |
| `resource_rejected`（raw_cap/rate_fuse） | supervisor 已熔断并 kill；保留 bounded 证据 → `--reject` → 换更小/重划范围的证据包或转人工。**禁止**改同步重跑或手动接受 |
| raw runaway / timeout | 受监督的 bundle-only 运行归 supervisor 所有，由硬 cap 处理，`--watch` **不得盲杀其 wrapper**；只有**非受监督**的运行才可用精确 PID 干预。保留 bounded 证据，reject，转更小/重划范围的 bundle 或人工 |
| round/reject 超限 | exit 20，停止自动循环 |
| gateway 救援 | 先读 [gateway rescue](references/sandbox-escape-gateway-rescue-20260629.md) |

## 验证

零 token、自包含测试：

```bash
python3 -m py_compile scripts/omp-resource-supervisor.py   # -> 0
bash tests/test-resource-supervisor.sh                     # -> PASS=42 FAIL=0
bash tests/run-all.sh                                       # -> FAIL=0（PASS 数随回归项增长）
bash scripts/call-omp-check.sh                             # -> 0
```

测试必须：

- 使用临时 `OMP_TMPDIR` 和 mock `OMP_BIN`
- 不移动真实 manifest、不改真实脚本权限、不使用宽泛 `pkill -f`
- 验证生产 hot-path 文件测试前后 hash 不变
- 覆盖 govern 三种合法写模式、非法 task ID、非零退出和非 `stop` 终态

真 token smoke 仅在用户授权且确有必要时运行，按 [shell smoke](references/omp-shell-smoke-test.md) 保存证据。

## Reference 路由

完整索引：[references/INDEX.md](references/INDEX.md)。

- 审计工作流：[omp-audit-workflow.md](references/omp-audit-workflow.md)
- scope 合同：[audit-scope-real-path-contract.md](references/audit-scope-real-path-contract.md)
- 平台适配：[platform-adapters.md](references/platform-adapters.md)
- gateway plist：[hermes-gateway-plist-env-fix.md](references/hermes-gateway-plist-env-fix.md)
- 历史记录：[historical-operations-and-pitfalls.md](references/historical-operations-and-pitfalls.md)（非当前合同）
- 更新记录：[CHANGELOG.md](CHANGELOG.md)

## ✅ Verification Checklist

- [ ] `task_id` 格式合法，scope 使用真实路径
- [ ] mode、channel、criterion 与任务匹配
- [ ] `--allow-write` 保持隔离；若有 grant，版本/模式/scope/cwd/add_dirs 与启动指纹均匹配
- [ ] 最后 `stopReason=stop`，OMP exit code=0
- [ ] evidence 是当前文件/命令的真实证据
- [ ] 当前 agent 已独立复跑关键命令
- [ ] `tests/run-all.sh` 与 `call-omp-check.sh` 全绿
