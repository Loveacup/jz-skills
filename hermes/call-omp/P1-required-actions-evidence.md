# call-omp P1 — `required_actions` 契约 实证记录

> Slice：为 OMP audit verdict 增加**可选、机器可读的 `required_actions` 字段**，从单一规范契约（P1A）→ 生产者双写（P1B）→ 版本化外层判决 + 严格 gate（P1C1）。
> 本文档记录 P1A / P1B / P1C1 合并后的最终交付状态。
> 验收：supervisor 专项 42/42、全量 416/416、`call-omp-check` 0、`git diff --check` 0，均在所有 writer 停止后由 Hermes 复跑。

## 修改文件清单

| 路径 | 类型 | 用途 |
|---|---|---|
| `contracts/required-actions.schema.json` | 新增 | `required_actions` 的**唯一规范契约**（single source of truth）：验证器从 schema 派生允许的 `kind` 枚举与全部上限，不硬编码 |
| `scripts/required-actions-validate.py` | 新增 | 纯 stdlib 验证器：从 schema 派生枚举/上限；错误路径只在 stdout 输出一个 JSON 对象，不泄漏 traceback/usage |
| `scripts/gate/gate-verify.sh` | 修改 | 输出 gate：兼容缺字段的 legacy 判决，校验已提供的字段；v1 标记触发外层 allowlist + schema-valid actions + severity/action 一致性 |
| `templates/audit-prompt-template.md` | 修改 | 原始 audit 模板产出 `required_actions_contract: "call-omp.required_actions.v1"`，并约束 v1 只输出 allowlist 字段 |
| `scripts/omp-monitor.sh` | 修改 | 持久化 action 列表或 legacy 标记 |
| `scripts/omp-finish.sh` | 修改 | 双写：legacy `next_action` 与 schema-valid flow-style YAML/JSON `required_actions` |
| `tests/run-all.sh` | 修改 | 纳入 P1A/P1B/P1C1 回归，全量 416 |

## 交付契约（当前有效）

### P1A — 单一规范契约 + 加固验证器

- **规范契约唯一化**：`contracts/required-actions.schema.json` 是唯一真源。stdlib 验证器从 schema **派生**枚举（`kind ∈ revise|human_review|stop`）与所有 limits（`maxItems=8`、`reason ≤512`、`targets 1–16` 各 ≤256），不在代码里硬编码。
- **错误信封恰好一个 JSON 对象**：在以下情形下，stdout 恰好输出一个 JSON 错误对象，不泄漏 traceback / argparse usage：malformed actions、unknown key 内含**字面换行**、无 CLI 参数、malformed schema override。
- **输出 gate 的加法式校验**：gate 支持 legacy 缺字段（不阻断向后兼容），对已提供的字段执行校验；`pass` 判决**不得**携带非空 actions。

### P1B — 生产者双写（向后兼容 rollout）

- **prompt 索取 actions**：audit 模板要求产出 `required_actions`。
- **monitor 持久化**：monitor 持久化 action 列表，或在缺失时持久化 legacy 标记。
- **finish 双写**：finish 同时写 legacy `next_action` 与 schema-valid flow-style YAML/JSON `required_actions`。
- **安全回退映射**：对 malformed/legacy 数据有安全 fallback action 映射；**资源拒绝路径不合成 actions**（`resource_rejected` 不伪造修复指令）。

### P1C1 — 版本化外层判决 + 严格 gate

- **v1 标记**：新原始 audit 模板产出 `required_actions_contract: "call-omp.required_actions.v1"`（逐字，不得改写）。
- **marker-free 保持 legacy 兼容**：没有该标记的原始判决仍走 legacy 兼容路径，不受 v1 严格约束（迁移前）。
- **v1 严格化**：一旦带 v1 标记，强制外层 allowlist `{severity, summary, evidence, reject_instruction, confidence, required_actions_contract, required_actions}`、schema-valid actions、`pass=[]` 且**非 pass ≥1 action**。
- **`confidence` 是显式允许的既有字段**，不是 unknown key。

## 已验证本地结果

（以下命令在所有 writer 停止后由 Hermes 复跑）

```text
python3 -m py_compile scripts/omp-resource-supervisor.py   -> 0
bash tests/test-resource-supervisor.sh                     -> PASS=42 FAIL=0
bash tests/run-all.sh                                       -> PASS=416 FAIL=0
bash scripts/call-omp-check.sh                             -> 0
git diff --check                                           -> 0
```

## 真实 OMP verdict 状态 —— 无新增裁决

- P0 阶段一次真实 bundle-only Shell 审计（task `p0-final-audit-20260719`）raw 精确到达 20 MiB 硬 cap 被拒，**未产出可信 OMP verdict**——这是预期的熔断遏制证据，不是审计通过。
- P1 为纯契约/生产者/gate 层改动，**未产出任何新的 OMP verdict**。不得据 P1 声称存在一份最新的 OMP 审计通过。

## 已知边界 / 剩余限制

1. `required_actions` 为**可选**字段：legacy（marker-free）判决可完全不带该字段，gate 不阻断。严格化只对带 v1 标记者生效。
2. legacy `next_action` 作为兼容接口保留；`required_actions` 才是结构化指令。二者由 finish 双写，直到后续迁移收敛。
3. 资源 cap 拒绝路径不合成 actions；对被 `raw_cap`/`rate_fuse` 拒绝的 raw，**不得**手动补写 `required_actions` 再当成审计通过。
