---
file: verification/output-gate.md
role: 输出闸门③ · Gate Stamp 总成（L4 汇聚点）
depends_on: [grill-framework, web-research-gate, source-tags, version-schema, non-lawyer-gate, volatility-classes]
consumed-by: [gates]
status: draft v0.1
last_reviewed: 2026-06-01
---

# 输出闸门 · Output Gate（闸门③ · Gate Stamp 总成）

> 验证层的**收口**。前面 6 份各产一个零件——grill 出确认块、web 出检索戳、source-tags 出标签、version 出 fresh 判定、nlg 出免责/升级、volatility 出判级——本闸门把它们**汇成一张 Gate Stamp**。这是「强制 = 可见化审计」的最终落地：**任一项 ❌ → MUST NOT 直接输出**。

## 0. 核心铁律

```
成稿后 → 逐项核 5 项硬核 → 生成 Gate Stamp（必打印）
   任一 ❌  →  回正文修正  或  显式降级声明（❌→⚠️）  或  删除该断言
   🔴 绝不「带 ❌ 输出」。
本闸门只管【事实正确性】；表达质量归 [[output-checklist]]（软、不阻断）。
```

## 1. 五项硬核

| # | 硬核项 | ✅ 判据 | ❌ 情形 | 验收的上游 |
|:--:|---|---|---|---|
| ① | **事实确认** | grill 确认块在场 + 无未响应 unknown | 缺确认块 / unknown 关键要素却给确定结论 | [[grill-framework]] |
| ② | **检索核验** | 每个 L2/L3 带 [检索·日期] 或合法降级 | 存在凭记忆的 L3 数值（无戳无降级） | [[web-research-gate]] |
| ③ | **法条溯源** | 每断言**有且仅有一个**标签；L2/L3 非 [模型知识]；条号现行或 [条号待核] | 无标签断言 / L2-L3 用 [模型知识] / 编造条号 | [[source-tags]] |
| ④ | **版本现行** | 所引资料 fresh 且 superseded_by=null | 引用 stale / 被取代资料而未重核 | [[version-schema]] |
| ⑤ | **免责升级** | 标准免责在场 + 已触发的升级已响应 | 缺免责 / 命中 HARD 却无警示 | [[non-lawyer-gate]] |

> **贯穿**：[[volatility-classes]] 判级决定 ②③④ 的**检查范围**（哪些断言是 L2/L3、哪些要查版本）。

## 2. 收口映射（5 项硬核 ← 6 个上游零件）

```
grill ──────────▶ ① 事实确认 ┐
web-research ───▶ ② 检索核验 │
source-tags ───▶ ③ 法条溯源 ├──▶ 🔍 Gate Stamp（一张可审计签章）
version-schema ▶ ④ 版本现行 │
non-lawyer-gate ▶ ⑤ 免责升级 ┘
volatility ─────▶ 贯穿（②③④ 的判级依据）
```

## 3. Gate Stamp 格式

**状态符号**：`✅` 通过 ｜ `⚠️` 通过含标注（assumed / 合法降级）｜ `❌` 未通过（**阻断**）｜ `N/A` 不适用 ｜ `🔴` 升级触发（⑤ 特有）。

**标准格式**（每次法律输出末尾 MUST 附）：
```
🔍 Gate Stamp
① 事实确认  ✅ 管辖地/时间/主体已确认（金额 ⚠️ assumed 已标注）
② 检索核验  ✅ 契税 1% [检索·2026-06-01·税务总局]
③ 法条溯源  ✅ 4/4 断言带标签，无 L2/L3 用 [模型知识]
④ 版本现行  ✅ 引 company-law-2024.md（fresh）   〔未引资料则 N/A〕
⑤ 免责升级  ✅ 标准免责在场                       〔触发则 🔴 + 警示〕
```

**含降级 / 升级的样例**：
```
🔍 Gate Stamp
① 事实确认  ⚠️ 管辖地 assumed=杭州（建议确认）
② 检索核验  ⚠️ 维修资金单价检索失败 → [未核验·需查证：杭州住建局]
③ 法条溯源  ✅ 3/3 带标签
④ 版本现行  N/A（未引 knowledge 资料）
⑤ 免责升级  🔴 触发 HARD（标的额重大）— 升级警示已置顶
```

## 4. ❌ 的处理（三条出路，绝不带病输出）

```
某项 = ❌
   ├─ 能修正？──是──▶ 回正文补全（追问 / 去检索 / 补标签 / 重核版本 / 加免责）→ 重新过闸 → ✅
   ├─ 不能修正 ──────▶ 显式降级声明（标 [未核验·需查证] + 告知用户局限）→ ❌ 转 ⚠️
   └─ 既不能修也不能合理降级 ──▶ 删除该断言 / 不给该结论
```
- **修正**（首选）= 真补全；**降级**（兜底）= 诚实标局限；**删除**（最后）= 宁缺毋错。
- `⚠️` 是**合法放行态**（已诚实标注）；`❌` **永不放行**。

## 5. 全流程

```
成稿
  ├─ 逐项核 5 项（①grill ②web ③src ④version ⑤nlg；volatility 定范围）
  ├─ 生成 Gate Stamp
  └─ 有 ❌？
       ├─ 是 ─▶ 修正 / 降级 / 删除 ─▶ 重新过闸
       └─ 否（全 ✅/⚠️/N/A）─▶ 附 Gate Stamp ─▶ 交 output-checklist（表达自检）─▶ 输出
```

## 6. 与 output-checklist 的边界（钉死 · 解 open-issue #6）

| | `output-gate`（本文件） | `output-checklist` |
|---|---|---|
| 维度 | 事实**存在性 + 合规性** | 表达**呈现质量** |
| 强度 | 硬 · **阻断** · 产 Stamp | 软 · 不阻断 · 可选行 |
| 顺序 | **先** | 后 |

> **③ 溯源 vs checklist ⑤ 溯源——最终边界**：本闸门 ③ 核「标签**在且合规**」（缺即 ❌ 阻断）；checklist ⑤ 核「标签**清晰可读、来源对读者透明**」（提醒级）。**同一对象（标签）的两个维度——存在合规 / 呈现质量——不重复**。

## 7. 依赖方向 + Gate Stamp 归属（防环）

- **依赖 6 个上游**（见 frontmatter），本文件是概念 DAG 的**汇点**，不被任何文件依赖（除 `gates` 编排）。
- **Gate Stamp 格式定义在本文件**；`gates` 仅**引用**它（虚线编排）——故 `gates ⇢ output-gate` 是控制流、非概念依赖，**消解 gates ⇄ output-gate 潜在环**（呼应装配图）。

## 8. 正例 / 反例（v1.0 实锚）

**反例 ❌**：v1.0 无统一输出验收 → 「契税 1–1.5%」「《民法典》512 条」「无免责」全部**带病输出**，用户无从判断可靠度。
**正例 ✅**：Gate Stamp ② 显 [检索·日期] 或 [未核验]、③ 显标签齐全、⑤ 显免责 / 升级 → 每次输出的可靠度**一眼可审计**。

---

*draft v0.1 · last_reviewed 2026-06-01 — verification/output-gate.md*
