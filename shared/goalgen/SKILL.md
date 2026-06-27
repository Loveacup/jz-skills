---
name: goalgen
description: |
  把模糊任务意图编译成一条可裁决、可验证、可移植的结构化 goal 指令（多 CLI，兼容单 CLI）。
  逐角色询问/可裁决提议 {cli, model, effort, work_mode}，capability-match 校验，9 承重墙 + 25 检查点自审，
  按 gate_mode（human / auto=AI 互相确认）接线确认门，输出 19 字段 goal。
  Use when: 用户要「生成/写一条 goal 指令」「给任务编军令状」「组队派工」「多 agent 协作 goal」。
  Triggers: 生成 goal, 写 goal 指令, goalgen, 编 goal, 给任务写军令状, 组队派工, multi-cli goal, goal generator
  DO NOT use for: 直接执行任务 / 单条工具调用 / 非任务编排的创作。goalgen 只产出 goal 指令，绝不执行、不拉起/驱动其他 CLI。
version: 0.1.0
author: Loveacup
license: MIT
---

# goalgen — 多 CLI 通用 goal 指令生成器

> **纯生成器**：把模糊意图编译成「不会在长程运行中失稳」的可裁决 goal，产出 goal 文本/文件——**绝不亲自执行、不驱动其他 CLI**。方法论权威源：Obsidian `20-Areas/20_技术项目/多Agent协作 goal 方法论/`（00–05）。

## 🚨 Red Flags：别绕过 goalgen 的硬规则

| 你脑子会冒出的借口 | 为什么错 |
|---|---|
| 「任务简单，直接写个 goal 就行，不走流程」 | 简单 ≠ 可裁决。不走 capability-match/自审，goal 会在运行时失稳。该退化到单 CLI-STDD 模板，**仍走 19 字段 + 验收三元组**。 |
| 「用户没说目标 CLI/模型，我猜一个」 | 🚫 禁猜。target_cli/绑定按可裁决规则提议或问用户；猜 = 违反 P1 可裁决。 |
| 「验收标准写『正确完成』就够了」 | 「正确完成」不可裁决。必须 `criterion/verifier(test\|review\|demo\|inspection)/threshold` 三元组（P2）。 |
| 「目标 CLI 能不能干这活应该没问题」 | 必须 capability-match（P9）。未声明能力/model/effort/驱动 skill = **拒绝生成**，不是生成后失败。 |
| 「roadmap_ref 可有可无」 | 必填（P7 溯源）。映射不出来 = 拒绝生成。 |
| 「我顺手把这条 goal 执行了」 | goalgen 是纯生成器。只产出 goal，**绝不执行/驱动 CLI**。 |
| 「auto 确认门让 producer 自己说『过了』就行」 | 🚫 auto = 对抗式 AI 互相确认（producer≠reviewer + 只认证据 + 证据缺失=block），**绝非自证**。 |

**若你冒出以上任一念头 → 停，按下面流程走。**

## 🔀 决策树：要不要用 goalgen

```
用户要「生成/写 goal 指令 / 编军令状 / 组队派工 / 多 agent 协作 goal」?
├── YES → 走 goalgen 流程（下方 7 步）
└── NO（要直接执行任务 / 单条工具调用 / 非任务编排的创作）→ ❌ 不用 goalgen
```

## 流程（7 步）

`采集 → 组队绑定 → capability-match → 接确认门 → 填模板 → 自审 → 输出`

1. **采集**：`task_intent`（必填）、`roadmap_ref`（必填）+ 可选 `participants`/`topology`/`gate_mode`。缺必填 → fail-closed 拒绝并报缺什么。
2. **组队/角色绑定**：逐角色定 `{cli, model, effort, work_mode, driver_skill?}`——human 模式问用户；auto 模式可裁决自动提议。候选取自 `data/cli-registry.json` 的 `execution_options`；被驱动绑定（跨 CLI）从 `cross_cli_drivers` 取 `driver_skill`，并在 goal 里要求编排者加载该 skill。
3. **capability-match（P9，三类预校验门）**：① 能力/角色门 ② effort 跨宿主映射门（CC `low..max` ↔ Codex `minimal..xhigh` 不可线性，须回落）③ 驱动-skill 门 + 默认态门（agent-team/dynamic-workflow 需 env+版本）。未声明/不在目录/不可注入 → 拒绝或降级 Bash。
4. **接确认门（gate_mode）**：每类门（binding/audit/termination/escalation/publish/install）按 `data/gate-policy.json` 接 human 或 auto。auto = 对抗式 AI 互相确认（非自证）；不可逆门 full-auto 走最强档 N票多透镜 + 留痕 + 单点发布权隔离 + block-on-uncertainty。
5. **填模板**：用 `data/topology-templates/`（星型 / 单CLI-STDD流水线）角色槽位模板填 19 字段。
6. **自审**：25 检查点（`data/pillars-checklist.json`，安全红线唯一硬阻断）+ 9 承重墙。**自审 = producer 视角，auto 门真正放行须独立 auditor**。
7. **输出**：19 字段 goal + `role_bindings` + `gate_modes` + `schema_version`，可复现（稳定排序 + 可注入时钟/run_id）。

## 数据层（CLI 无关、可插拔；读 `data/`）
- `cli-registry.json` — 15 字段 CLI 能力卡 + `cross_cli_drivers`（驱动矩阵）+ `execution_options`。
- `goal-schema.json` — 19 字段输出契约 + `role_bindings` + `gate_modes`。
- `pillars-checklist.json` — 25 检查点（5 维 × 5）。
- `gate-policy.json` — gate_mode 默认 + 6 类门 + 风险→确认强度。
- `topology-templates/` — 星型 / 单CLI-STDD流水线 角色槽位模板。

详尽机制（承重墙逐条、capability-match、gate_mode、驱动-skill）见 `references/methodology-pointer.md` → Obsidian 方法论 00–05。

## 校验
`python3 scripts/validate_data.py` — 校验数据层完整与合法（exit 0 = GREEN）。

## ✅ 验证清单（返回 goal 前必跑）

- [ ] `task_intent` 与 `roadmap_ref` 都有？缺则拒绝（不猜）。
- [ ] 每个 `role_bindings` 的 model/effort/work_mode/driver_skill 都过 capability-match（在该 CLI `execution_options`/`cross_cli_drivers` 内）？
- [ ] `acceptance_criteria` 每条都是 criterion/verifier/threshold 三元组？
- [ ] `gate_modes` 已接线（human/auto），不可逆门补偿控制齐？
- [ ] 非 publisher 角色的 `forbidden` deny-list 已注入？
- [ ] 输出过 `goal-schema.json` 校验？
- [ ] 我**只生成了 goal**，没有亲自执行/驱动任何 CLI？

**任一未打勾 → 回去补。**

## 状态
MVP M0（SKILL.md 指令 + 数据层）。M1 生成逻辑脚本（intake/binding/capability-match/emit）待建。
