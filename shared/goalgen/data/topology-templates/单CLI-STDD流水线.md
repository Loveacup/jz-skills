# 拓扑模板：单 CLI 退化 — STDD 流水线（N=1）

> 角色槽位模板。单 CLI 可用（N=1）时 goalgen 退化为单 agent 内 STDD 流水线，角色靠**身份切换**轮转。对齐方法论 03 §3.3 / 04 §4.6。`driver_skill` 恒 null（自托管，无跨 CLI 驱动）。

## 元信息
- topology: `single-cli-stdd`
- role_bindings:（N=1，同一参与者担多角色，身份切换）
  - `{ "role": "executor", "cli": "<唯一CLI>", "model": "<model>", "effort": "<effort>", "work_mode": "<mode>", "driver_skill": null }`
  - `{ "role": "reviewer-auditor", "cli": "<同一CLI>", "model": "<可换更强model>", "effort": "<effort>", "work_mode": "<mode>", "driver_skill": null }`（AUDIT 阶段身份切换）
- gate_modes: `{ "gate_default": "<human|auto|hybrid>", "per_gate": { "audit": {...} } }`

## STDD 生命周期
`SPEC → RED → GREEN → REFACTOR → REPORT → AUDIT`，不得跳步；没有 RED 不进 GREEN；GREEN 只实现让当前测试通过的最小功能。

## Goal 骨架（19 字段）

```text
# Goal（单 CLI STDD）：<objective 一句话>

## roadmap_node（P7，必填）
<映射节点；映射不出来不得生成>

## 终止条件（P6）
AUDIT 三态（通过/有条件/阻断）通过且归档完成时本 goal 完成；同一单元打回2次→升级。

## STDD 阶段
1. SPEC：想清楚（定不出验收标准=Spec 不够清楚）；scope includes=<...>/excludes=<...>
2. RED：先写可验证证据（unit/CLI golden/JSON fixture/snapshot 之一），必须先红
3. GREEN：只实现让 RED 通过的最小功能，禁顺手做下一阶段
4. REFACTOR：边界内重构
5. REPORT：产可验证工件 + 证据句柄
6. AUDIT：身份切换为 auditor，只认证据，禁 inference-based approval，证据缺失=不通过

## acceptance_criteria（验收，每条三元组 P2）
- { criterion: "<可裁决判定>", verifier: "<test|review|demo|inspection>", threshold: "<阈值>" }

## 验证命令（P2，任何场景不可省）
<可粘贴的 bash 验证命令，逐项实跑全通过>

## forbidden（deny list P4/P9）
<不得 git commit/push/tag、不得改 scope 边界外文件、...>

## 确认门（gate_mode）
- audit 门：human=人裁 / auto=身份切换的独立 auditor 凭证据（单 CLI 内 auto 强度弱于跨实例对等评审，[I] 须标注）

## escalation（P6）
- mode: <human|auto>；triggers: <打回2次 / 验收不可验证 / 不可逆操作>
```

## live 锚定 / 边界
askills STDD 串行链（live `[C]`）；当前 Hermes Kanban 单 worker。单 CLI 内 AUDIT 身份切换是 P5 的最近似原语（同 model 仍有 anchoring 残留，强度弱于跨实例双审计，标 `[I]`）。
