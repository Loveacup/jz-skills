# 团队编排：2-run DAG + 审定门协议 + 数据契约

> 仿 strategic-insight-longform v5.0 的 CC Leader 自编排，但切成**两段 team + 中间 Hermes 自核审定门**——这是本方法论红线② 强制、SI 纯生成流水线没有的适配。

## 1. 三铁律（数据契约）

1. **阶段内中间件走 task I/O 不走盘**：Insight Units、软处候选、分类表等由 Leader 切片注入下游 prompt，禁落 json/md 中间件。
2. **依赖全显式 blockedBy**：每个下游 Task 声明它 blockedBy 哪些上游。
3. **审定门三件套 + 成稿 + 台账落盘**（对 SI「只最终落盘」的**有意偏离**）：人类门是磁盘中介交接点、point-by-point 追溯要落盘。落盘清单 = `洞察稿.md` / `软处指令表.md` / `冲突报告.md` / `W清单.md` / `焊接成稿.md`（含台账）。

## 2. RUN-1 诊断 DAG

```
TeamCreate("rf-diag-{topic}")
  lens-distiller        [blockedBy: ∅]        (仅有外部洞察源时)
  lens-diagnostician×N  [blockedBy: distiller] 并行·互盲 barrier
  softspot-classifier   [blockedBy: 全部 diagnostician]
  evidence-anchor       [blockedBy: classifier]   ← G1 claimcheck + gate-prep
→ Leader 落盘 4 件（洞察稿/软处指令表/冲突报告/草稿W清单）→ TeamDelete
```

## 3. 审定门协议（Hermes 自核 + 重大上报）

RUN-1 的 evidence-anchor 已给每条软处预打 `escalation`。Hermes 门口动作 = **机械执行**（不需读深规则）：

```
读 冲突报告.md：
  auto 区   → 直接采纳每条 default（措辞纠偏/口径降格/grounded微观additive）
  上报区    → 仅 escalation=user 的项摆给用户逐条拍板（采纳/驳回/改判）
回填草稿 W清单.md 的 PENDING 项 → 定稿 W清单.md
若上报区有 PENDING 未获应答(headless 无人在环) → 停，不得静默放行要害项
```

### escalation 判据（RUN-1 据此打标，= 治理护栏）

| escalation = user（必上报） | escalation = auto（自核·采纳 default） |
|---|---|
| 证伪一条**宏观**承重论点（反转全文结论）| 措辞纠偏（corrective）|
| backing缺失 × 宏观 → 大体量整章注入 | 口径降格（claimcheck 已证 over-claim）|
| `claimcheck = needs-external` | grounded × 微观 additive |
| 洞察 ↔ 基底 **双方有据的直接矛盾** | ~~hallucinated~~（G1 已自动剔除，非决策项）|
| Deep 模式所有宏观 additive 注入 | |
| 命中用户预设敏感清单 | |

> 护栏①：打标拿不准 → 归 user。护栏②：W清单是 RUN-2 唯一指令源，无论某条是 Hermes 自核还是用户拍板，焊接一视同仁，不得绕过 W 直读洞察稿。

## 4. RUN-2 焊接 DAG

```
TeamCreate("rf-weld-{topic}")   ← 全新 team，welder ≠ 任何 diagnostician（B→C 隔离）
  welder            [blockedBy: ∅]        入 {基底, 洞察稿, W清单, mode}
  landing-verifier  [blockedBy: welder]   G2 +(Std)G4 +(Deep)G3
  ├ not-landed / gate-fail → SendMessage→welder 复焊 (max 1)
→ Leader 落盘 焊接成稿.md(+台账) → Skill("humanizer-zh") → TeamDelete
```

## 5. 角色分工（CC Leader vs Hermes）

| 角色 | 职责 |
|---|---|
| **CC Leader** | 两段 team 内的全部自编排（建 Task DAG、派遣、收 task I/O、落盘、回流复焊、TeamDelete）。**只路由不代笔**：诊断/焊接全派 subagent。 |
| **Hermes** | thin：kickoff RUN-1 → 审定门机械核定（auto 采纳 + 上报区转发用户）→ kickoff RUN-2 → 最终验收入库。不产血肉与钢筋。 |

## 6. kickoff 参数

```
execute(base_path,            # 基底文档（已存在；不存在先 SI/web-research 产）
        insight_source=None,  # 可选外部洞察源（SI长文/专家稿/red-team/运行实证）；无则 lens-diagnostician 直接产
        mode="Standard")      # Quick | Standard | Deep → 见 references/modes.md
```

> 透镜外置可插拔插槽：洞察源 ∈ {本 skill 多透镜自产 | SI长文 | 专家稿 | red-team | 运行实证}，任选其一但软处必过 IC-1..5（见 references/doc-type-matrix.md）。
