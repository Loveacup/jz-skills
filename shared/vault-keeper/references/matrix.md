# 速查：矩阵 · R 级 · 阈值 · 取证卡

> 渐进披露：需要判定细节时才读本文件。权威定义在 vault `GOVERNANCE.md`。

## 风险 × 置信矩阵（gate.py 路由）

| | conf < low(0.6) | low–high(0.6–0.85) | ≥ high(0.85) |
|---|---|---|---|
| **R1 低** | 退回(20) | 自动晋升+抽样(0) | 自动晋升+抽样(0) |
| **R2 中** | 退回(20) | 人工(10) | 自动+高抽样(0) |
| **R3 高** | 退回(20) | 人工(10) | 人工(10) |

退出码：`0`自动晋升 · `10`人工队列 · `20`退回加工 · `30`矛盾裁决（冲突触底，绕过矩阵）。

## R 级定义

- **R2（任一触发）**：晋升常青 / 改写权威 claim / 丢信息合并 / 枢纽页(入链≥`hub_inlink_threshold`,默认8) / 元知识区(`20_Obsidian方法论`·`02-Plan&CQI`) / 项目交付区(`10-Projects`)。
- **R3（人工红线）**：对外发布候选 / 改治理规则（`GOVERNANCE.md`/`ROUTER.md`/skill engine）。
- **R1**：其余 core 操作（30-Resources/一般 20-Areas 新增、additive 更新、补链、打标签）。

## 复合置信度（confidence.py）

```
confidence = 0.35·源数量信号 + 0.20·信息密度 + 0.20·连接度 + 0.25·AI自评
源数量: ≥2→0.35 / =1→0.15 / 0→0   信息密度: body>400字→0.20 否则0.10
连接度: 0.20·min(双链数/5,1)        AI自评: frontmatter `_ai_self`(缺省0.6)
冲突 → 0.0（强制进裁决）
```

## 硬门槛（gate.py 第一层，任一不过即退回）

- sources ≥ `min_sources`（默认1，溯源不变量）
- 双链 ≥ `min_links`（默认3）
- frontmatter 含 `lifecycle_state/status/type/created`
- 无断链（指向不存在的页）

## 阈值表（vault GOVERNANCE.md，改=R3）

| key | 默认 | 含义 |
|---|---|---|
| `promote_conf_low` | 0.6 | 矩阵低阈 |
| `promote_conf_high` | 0.85 | 矩阵高阈 |
| `sample_rate_R1` | 0.15 | R1 抽样率（地板0.05） |
| `sample_rate_R2` | 0.40 | R2 自动带抽样率 |
| `hub_inlink_threshold` | 8 | 枢纽页入链阈 |
| `stale_days` | 180 | Lint 陈旧阈 |
| `min_links` / `min_sources` | 3 / 1 | 硬门槛 |

## 矛盾裁决取证卡模板（写入 88-审计/adjudication/ADJ-YYYYMMDD-NNN.md）

```markdown
# 矛盾裁决卡 ADJ-20260614-001
- 实体: [[页名]]  锚点: ^claim-N
- 旧 claim: "..." | 源: SRC-.. (日期)
- 新 claim: "..." | 源: SRC-.. (日期)
- 差异点: ...
- AI 倾向: 采纳新 / 保留旧 / 并存（附理由）
- 裁决: [ ]采纳新 [ ]保留旧 [ ]并存 [ ]打回   裁决人: __ 日期: __
```
铁律：裁决前旧 claim 不删不覆盖；超时默认「保留旧+并存」；被取代 claim 归档不删。
