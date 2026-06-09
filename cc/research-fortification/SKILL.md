---
name: research-fortification
description: |
  以独立洞察为透镜，对「信息完备但论证松散」的基底文档做 additive-first 加固：保留血肉、在承重论点软处熔入钢筋，区别于「合并」。CC Leader 自编排两段 team（诊断 → 焊接），中间一道 Hermes 自核审定门，多透镜 subagent 实现透镜外置。
  Use when / Triggers: 研究加固, 加固这份(研究稿/技术方案/方法论综述), CQI清单→SKILL.md, 把洞察焊进基底, 用运行实证给设计文档打钢筋, fortify research, weld insights into.
  DO NOT use for: 单纯合并两份对等文档(≠fortify), 措辞润色/校对, 从零写新稿/新研究, 单次事实问答.
version: 2.0.2
author: CC (regent) + Hermes
license: MIT
metadata:
  last_updated: 2026-06-09
  related_skills: [strategic-insight-longform, humanizer-zh, cqi-plan-writer]
---

# Research Fortification — 研究加固 v2.0 · 2-run 软编排

> 把独立洞察当**诊断透镜**，读出基底的承重论点软处，逐点打钢筋焊回去。血肉(基底)＋钢筋(洞察)→ 焊接成稿，**意义层为主、增补优先**，区别于「合并」。
> 一条 Leader + 两段 team 跑完：**RUN-1 诊断 →【Hermes 自核审定门】→ RUN-2 焊接**。

## 🚨 Red Flags（Leader / teammate 执行前默念）

| 若你想… | 现实检验 |
|---|---|
| 「把基底和洞察 merge 一下」 | **merge ≠ fortify**。merge 替换/并列血肉；本 skill 保血肉、只在软处熔钢筋。 |
| 「Leader 顺手把诊断/焊接做了」 | **越权代笔 = 透镜外置崩坏**。Leader **只路由**：诊断派 lens-diagnostician，焊接派 welder。 |
| 「一个 lens 扫一遍够了」 | Deep 单透镜弱化外置。多透镜**互盲并行**才是强外置（PerFine 多 profile）。 |
| 「这条批评看着对，直接焊」 | 跳过 **G1 claimcheck 红线**。批评点本身可能无据，先判 grounded/hallucinated。 |
| 「全文重写更干净」 | 违 **additive 优先**。骨架保留 ≈90%+，推倒重来 G4 不达标。 |
| 「auto/user 拿不准先归 auto」 | **拿不准一律归 user**。漏报要害比多问一句贵。 |
| 「中间软处表写 json 传下游」 | **禁落盘中间件**，走 task I/O。仅审定门三件套 + 成稿 + 台账落盘。 |
| 「上报区没人应答，先焊了」 | headless **不得静默放行要害项**。上报区有 user 项无应答 = 停。 |

## 🔀 决策树

```
要不要用 research-fortification？
├─ 有「信息完备但论证松散」的基底 + 一个独立透镜源 → ✅ 用
├─ 只是合并两份对等文档 / 润色措辞 / 从零写新稿     → ❌ 不用（见 Red Flags）
└─ 基底还不存在 → 先用 strategic-insight / web-research-router 产基底，再回来

选档（详见 references/modes.md）：扎实补几处→Quick；常规有明显软处→Standard〔默认〕；高风险对外发表→Deep
```

## 两不变量 ＋ 一红线（任何档不可破）

1. **透镜外置**：诊断由 fresh-context subagent 做，基底是**外部输入**（不在本 session 产）→ 天然没写过它；焊接 subagent 是 RUN-2 另一 fresh Task，只收制品看不到诊断推理。**会话隔离 → subagent 隔离**，不变量不变。
2. **additive 优先**：保叙事骨架(≈90%+)，钢筋注入而非推倒重来；纯措辞 corrective 降为收尾。
3. **G1 红线**：焊回前剔除「批评点本身无据」的幻觉软处，100% 不进 RUN-2。**不可砍。**

## 工作流（Stage DAG · 单 session · 2 team）

```
RUN-1 诊断   TeamCreate("rf-diag-{topic}") → Task DAG(显式 blockedBy) → 落盘 → TeamDelete
  P0 蒸馏    lens-distiller        外部洞察源 → Insight Units（无外部源则跳过）        [串行]
  P1 诊断    lens-diagnostician×N  N 视角并行·互盲（证据/反例/口径/因果桥审查者）      [并行 barrier]
  P2 分类    softspot-classifier   Faigley-Witte 四象限 + additive/corrective + type     [串行]
  P3 锚定    evidence-anchor       绑证据锚 + claimcheck(G1 剔幻觉) + gate-prep 打 escalation [串行]
  → 落盘 洞察稿.md + 软处指令表.md + 冲突报告.md(auto区/上报区) + 草稿 W清单.md

【审定门 · Hermes 自核】 auto 区直接采纳 default；上报区(escalation=user)交用户拍板（红线②收窄至此）
                        → 定稿 W清单.md（RUN-2 唯一指令源）

RUN-2 焊接   TeamCreate("rf-weld-{topic}") → 落盘 → TeamDelete
  P4 焊接    welder            W清单唯一指令源；weld 决策树；additive 铁律(整章注入→口径降格→措辞纠偏) [串行]
  P5 验证    landing-verifier  G2 +(Std)G4 +(Deep)G3；not-landed/fail → 回流复焊 max1     [串行]
  → 落盘 焊接成稿.md + 文末台账 → Skill(humanizer-zh) 去 AI 痕迹
```

**编排与数据契约见 `references/team-orchestration.md`（三铁律：阶段内中间件走 task I/O 不走盘 / 依赖全显式 blockedBy / 审定门三件套+成稿+台账落盘）。**

## 执行逻辑（精简）

```python
def execute(base_path, insight_source=None, mode="Standard"):
    topic = extract_topic(base_path)
    n_lens = {"Quick":1, "Standard":1, "Deep":3}[mode]; N = mode_N(mode)

    # ── RUN-1 诊断 ──
    TeamCreate(f"rf-diag-{topic}")
    units = Task("lens-distiller", {insight_source, base_path}) if insight_source else None
    spots = parallel([ Task("lens-diagnostician", lens=L, inputs={base_path, units})
                       for L in pick_lenses(n_lens) ])          # barrier，互盲
    cls  = Task("softspot-classifier", {spots})                 # blockedBy 透镜
    anch = Task("evidence-anchor", {cls, base_path})            # G1 claimcheck + gate-prep escalation
    write("洞察稿.md", anch.insight); write("软处指令表.md", anch.directives)
    write("冲突报告.md", anch.conflicts); write("W清单.md", anch.draft_W); TeamDelete()

    # ── 审定门（Hermes 自核 + 重大上报）──
    W = hermes_adjudicate("冲突报告.md")   # auto 采纳 default；user 项交用户；拿不准→user
    if not W.finalized: return             # 上报区未回填则停（不静默放行要害项）

    # ── RUN-2 焊接（welder ≠ 任何 diagnostician）──
    TeamCreate(f"rf-weld-{topic}")
    weld = Task("welder", {base_path, "洞察稿.md", "W清单.md", mode})         # P4
    ver  = Task("landing-verifier", {weld, "软处指令表.md", mode})            # P5 + gates_for(mode)
    if ver.unlanded or ver.gate_fail: weld = Task("welder", {...})            # 回流 max1
    write("焊接成稿.md", ver.final + ledger); Skill("humanizer-zh", "焊接成稿.md"); TeamDelete()
```

> 派遣统一 `Task(subagent_type="general-purpose", team_name="rf-{run}-{topic}", name="{agent}")`；上游结构化产物由 Leader 切片注入下游 prompt，不落盘。

## Agent 列表（6 个）

| Run·Stage | Agent | 职责 |
|---|---|---|
| R1·P0 | lens-distiller | 蒸馏外部洞察源 → Insight Units（去冗/概念化/按承重排序）|
| R1·P1 | lens-diagnostician | 参数化视角独立扫基底定位承重软处（互盲并行）|
| R1·P2 | softspot-classifier | Faigley-Witte 四象限 + additive/corrective + softness_type |
| R1·P3 | evidence-anchor | 绑证据锚 + claimcheck(G1) + gate-prep 打 escalation 标签 |
| R2·P4 | welder | 按 W清单焊接（weld 决策树 + additive 铁律）|
| R2·P5 | landing-verifier | G2/G3/G4 门 + not-landed 回流复焊 |

## 🚪 审定门 · Hermes 自核 + 重大上报（详见 references/team-orchestration.md）

RUN-1 已给每个软处预打 `escalation = {auto | user}`。Hermes 门口动作 = 机械执行：
- **auto 区**（措辞纠偏 / 口径降格 / grounded 微观 additive）→ 直接采纳 default。
- **上报区**（证伪宏观承重论点 / backing缺失大体量整章注入 / needs-external / 双方有据矛盾 / Deep 宏观注入 / 用户敏感清单）→ 交用户拍板。

> 两护栏：① 打标拿不准 → 归 user（漏报要害比多问贵）。② W清单是 RUN-2 唯一指令源，无论谁定的，焊接不得绕过 W 直读洞察稿。

## 📊 模式分级（详见 references/modes.md）

| 模式 | 透镜数 | RUN-1 agents | RUN-2 agents | 门禁 | 总 agent |
|---|:--:|---|---|---|:--:|
| **Quick** | 1 | 蒸馏+诊断合1 · 分类锚定合1 | welder + verifier | G1+G2 | ~3 |
| **Standard**〔默认〕 | 1 | distiller·诊断·分类·锚定 | welder + verifier | G1+G2+G4 | ~5 |
| **Deep** | 2-3 | distiller + 2-3透镜 + 分类 + 独立claimcheck | welder + verifier + G3宏观 | G1-G4 全开 | ~9 |

> 三铁律：① G1 任何档不可砍 ② P0 蒸馏 + P5 验证全档保留 ③ Deep 多透镜互盲 = 透镜外置强形式。

## 📦 References（按需 Read）

| 文件 | Read when |
|---|---|
| `references/team-orchestration.md` | 2-run DAG / blockedBy / task I/O 铁律 / 审定门协议 + escalation 判据 / Hermes 角色 |
| `references/pipeline-stages.md` | P0-P5 每阶段输入/动作/产出 + 2-run 切分 |
| `references/soft-spot-schema.md` | 软处 14 字段（含 escalation）/ point-by-point 台账 |
| `references/weld-strategy.md` | P4 选策略：warrant/backing 分流全决策树 + 适配表 |
| `references/quality-gates.md` | G1-G4 公式/阈值/回流/G4 加权算法 |
| `references/doc-type-matrix.md` | 基底矩阵 + 洞察源矩阵 + IC-1..5 契约 |
| `references/modes.md` | 选档 + 每档 subagent 数映射 |
| `references/literature-map.md` | 设计决策文献溯源（最低优先）|

## ✅ 验证清单（Leader 跑完自检，全 yes 才算完成）

- [ ] Leader 只路由没代笔？诊断派了 lens-diagnostician、焊接派了 welder？
- [ ] 基底是外部输入（非本 session 产）？Deep 的 P1 多透镜互盲并行？
- [ ] G1：hallucinated 100% 剔除并记日志？（剔除率 >40% 回流 P1 重诊断）
- [ ] 审定门：auto 区已采纳 + 上报区 PENDING 全回填？无残留 PENDING 进 RUN-2？
- [ ] welder ≠ 任何 diagnostician（RUN-2 全新 team）？W清单是唯一指令源？
- [ ] G2 每个 grounded 软处落地（Std≥0.9/Deep=1.0）？G4 按承重体量加权 ≥0.6（Deep≥0.7）？
- [ ] 终稿附 point-by-point 台账？中间件零落盘（仅审定三件套 + 成稿）？已 TeamDelete？

**任一项未过 → 回到对应阶段，不得交付。**

---

> 📋 设计方案全文：`research-fortification-skill-方法论方案`（OB `02-Plan&CQI/`）｜ v2.0 = 从 Hermes-编排(v1) 转 CC 2-run 软编排
