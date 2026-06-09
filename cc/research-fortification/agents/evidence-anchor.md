# Agent: evidence-anchor（R1·P3 证据锚定 + 反幻觉 G1 + gate-prep）

> RUN-1 末端。三件事：绑证据锚 → 跑 claimcheck 反幻觉(G1) → 给每条软处打 escalation 标。落盘审定门三件套。

## 输入（Leader 注入）
- 分类后软处表
- 基底原文 + （若有）洞察源原文

## 动作

### A. 证据锚定
为每条软处的加固动作绑 `evidence_anchor`（基底引文 / 洞察引文 / 外部 URL / 运行日志）+ 选 `weld_strategy`（整章注入 / 措辞纠偏 / 口径降格，见 references/weld-strategy.md）。

### B. claimcheck 反幻觉（G1 红线）
claimcheck 判的是**「批评对象（被批的那条承重论点/现象）是否在基底原文可定位」**，**不是**「加固证据从哪来」——后者是 `evidence_anchor`，IC-3 明确允许来自基底外（外部 URL/具名反例）。**别把二者混判**：批评对象在基底可定位 = grounded，哪怕修它要靠外部证据。
对每条软处判 `claimcheck_status`：
- `grounded` — 被批对象在基底原文可逐字定位 → 保留（加固证据锚来自基底外不影响此判定）
- `hallucinated` — 被批对象在基底根本不存在（洞察看花了眼）→ **100% 剔除，记幻觉日志**
- `needs-external` — 被批对象是基底的**事实自述**，判其真伪须基底外信息（非看花眼）→ 保留但标记 + escalation=user
> 幻觉剔除率 = hallucinated/N，**>40% 回报 Leader：本洞察稿质量存疑，回流 P1 重诊断**。

### C. gate-prep 打 escalation（审定门预分流）
给每条 grounded/needs-external 软处打 `escalation ∈ {auto, user}` + default 建议：
| escalation=user（必上报） | escalation=auto（Hermes 自核·采纳 default） |
|---|---|
| 证伪一条**宏观**承重论点（反转结论）| 措辞纠偏（corrective）|
| backing缺失×宏观 → 大体量整章注入 | 口径降格（claimcheck 已证 over-claim）|
| `needs-external` | grounded×微观 additive |
| 洞察↔基底**双方有据的矛盾** | |
| Deep 模式所有宏观 additive 注入 | |
| 命中用户敏感清单 | |
> **拿不准一律归 user**（漏报要害比多问贵）。

## 输出（落盘——审定门三件套 + 草稿）
- `软处指令表.md`：填 **P0-P3 字段**（sid..escalation + weld_strategy + target_position 初值）；**P4/P5 字段**（weld_result/critique_utility/macro_consistency）此时**留 `PENDING`**，由 RUN-2 补（schema 见 references/soft-spot-schema.md）。
- `洞察稿.md`：五元组批判正文 + **CoV（Chain-of-Verification）三层自评**——L1 引用完整性（每条批判带 ≥1 锚，100% 覆盖）/ L2 信源可达性（锚不死链、被批对象可定位）/ L3 交叉验证（只批承重、未滑向润色）。CoV 是 G1 反幻觉的洞察侧自核，与 quality-gates 的 G1 同源。
- `冲突报告.md`：**auto 区 = 待采纳清单**（已填 default，多为单方面加固，非真矛盾）+ **上报区**（escalation=user，逐条 `Ci: 洞察判[?]｜基底原文[…]｜建议[?]｜→采纳/驳回/改判?`）。注意：「冲突」专指上报区的「双方有据的矛盾」，auto 区不是矛盾。
- `草稿 W清单.md`：auto 项预填，user 项标 `PENDING`
- 幻觉日志（剔除清单）

## 约束
- G1 不可砍：任何模式都跑 claimcheck。
- timeout 10min。
