---
file: verification/version-schema.md
role: 资料时效元数据规范 + 过期判定（L3 · 条件触发）
depends_on: [volatility-classes, web-research-gate]
consumed-by: [output-gate, anti-patterns]
status: draft v0.1
last_reviewed: 2026-06-01
trigger: 仅当本次分析读取了 knowledge/ 资料文件时启动
---

# 资料时效规范 · Version Schema（条件触发）

> v1.0 的 8 个文件**没有任何「最后核验日」**——契税过期了也没人知道。本文件给 `knowledge/` 每份资料装 `VERSION.yaml` 保质期标签：读取时先查 **stale**，过期就**自动触发** [[web-research-gate]] 重新核验。**仅在读 knowledge 资料时启动**（条件触发，非常驻）。

## 0. 核心铁律

```
knowledge/ 每份资料 MUST 带 VERSION.yaml 头。
读取资料时 MUST 先判 stale：
   stale → 触发闸门② 重新核验，禁止直接引用过期内容（= anti-pattern ⑨）
无 VERSION.yaml 的资料 → 一律视为 stale。
```

## 1. VERSION.yaml 字段规范

```yaml
# ── 必填 ──
file:          knowledge/company-law-2024.md      # 自描述路径
legal_version: 公司法 2023修订（2024-07-01施行）   # 所依据的法律版本
content_cutoff: 2026-05-01      # 内容反映的法律状态截止日（ISO 8601）
last_verified:  2026-06-01      # 最近一次确认「仍现行有效」的日期
verify_cycle:   半年            # 核验周期（枚举，见 §3）
volatility:     L1              # 主挥发级（L0–L3，取自 volatility-classes）
superseded_by:  null            # 被取代？null 或「取代它的法规/文件」

# ── 可选 ──
sources:        [flk.npc.gov.cn/...]   # 官方源，便于复核
notes:          含 88 条股权转让补充责任
maintainer:     <最后更新者>
```

**字段类型**：日期一律 `YYYY-MM-DD`；`volatility ∈ {L0,L1,L2,L3}`；`verify_cycle` 见 §3 枚举；`superseded_by` 为 `null` 或字符串。

> **`content_cutoff` vs `last_verified`（易混，务必分清）**：
> - `content_cutoff` = 内容的**知识时点**（「写的是截至这天的法律」）
> - `last_verified` = 最近一次**体检日**（「这天有人确认它没过期」）
> - **过期判定用 `last_verified`，不是 `content_cutoff`**——一份资料可以内容较旧但最近核验过、确认仍有效。

## 2. 过期判定（stale）

**主判据**：
```
now − last_verified > verify_cycle   →   stale
```

**其他强制 stale**：
- 无 `VERSION.yaml` 或缺 `last_verified`
- `superseded_by ≠ null`（已被取代）
- 手动标记（发现新法 / 新解释）

**stale 触发动作**：
```
stale → 调 [[web-research-gate]] 重新核验
          ├─ 仍有效 → 更新 last_verified = now（续命）
          └─ 已变化 → 标 superseded_by + 触发资料更新，本次引用走检索结果
```

## 3. verify_cycle 取值（与 volatility 挂钩）

挥发性越高、核验越勤——这是本规范与 [[volatility-classes]] 的内在一致：

| volatility | verify_cycle | 理由 |
|:--:|---|---|
| **L0** 静态 | `年度`（近永久） | 原则几乎不变 |
| **L1** 慢变 | `半年` | 修法才动 |
| **L2** 修法 | `季度` | 司法解释更新频繁 |
| **L3** 数值 | `实时`（= 不缓存） | 数值随时变 |

> 🔑 **关键决断：L3 数值不进 `knowledge/`。** 它的 `verify_cycle=实时` 意味着「任何缓存当即 stale」——所以 L3 干脆**不落库**，每次走闸门②实时检索。这正是方案原则②「资料最小化、详细走实时检索」的落地。
> ⟹ **`version-schema` 实际服务 L1/L2**（有缓存价值、需周期核验）；L0 近乎免管，L3 不缓存。

## 4. 读取流程

```
读取 knowledge/X.md
   │
   ├─ 有 VERSION.yaml？──否──▶ 视为 stale ─▶ 闸门②
   ├─ superseded_by ≠ null？──是──▶ stale ─▶ 闸门② + 标更新
   ├─ now − last_verified > verify_cycle？
   │      ├─ 是 ─▶ stale ─▶ 闸门②（仍有效→续命 last_verified；已变→标 superseded_by）
   │      └─ 否 ─▶ fresh
   └─ fresh 也 MUST 按 volatility 标 source-tag（fresh ≠ 免标签：L1 仍标 [法条原文]）
```

## 5. 示例

**L1/L2 资料（缓存 + 周期核验）**
```yaml
file: knowledge/civil-procedure-core.md
legal_version: 民事诉讼法 2023修正（2024-01-01施行）
content_cutoff: 2026-05-01
last_verified: 2026-06-01
verify_cycle: 季度          # 诉讼程序近年频调 → 取季度（就高）
volatility: L2
superseded_by: null
```

**L3 数值（演示「不落库」）**
```yaml
# ❌ 不应存在 knowledge/local-deed-tax.md 这类 L3 静态文件
# 契税率属 L3 → verify_cycle=实时 → 任何缓存即 stale
# 正解：契税在使用时由 web-research-gate 实时检索，不建静态资料
```

## 6. 依赖方向（钉死）+ 适用边界

- **上游依赖**：[[volatility-classes]]（volatility 字段取值域）+ [[web-research-gate]]（stale 触发检索）。
- **适用边界**：本规范**只管 `knowledge/` 资料层**。`framework/`（含本验证层 10 文件）的版本走各自 frontmatter 的 `status` / `last_reviewed`，**不走 stale 自动核验**——方法论不像数值会「过期」，但会随司法实践演进（裁定 #5：绑定大版本 + 半年兜底复审）。

## 7. 正例 / 反例（v1.0 实锚）

**反例 ❌**：v1.0 法律版本表分散 8 文件、无核验日、无 stale → 契税过期内容**静默存活**，无人察觉。
**正例 ✅**：每份资料带 `VERSION.yaml`，季度到期**自动触发**核验；L3 数值不落库、强制实时。

## 8. 下游接口约定

| 下游 | 取用本文件的什么 |
|---|---|
| `output-gate` | Gate Stamp 第④项：核所引资料 fresh、superseded_by=null |
| `anti-patterns` | 红线 ⑨（用过期版本）引用本文件的 stale 判定 |

---

*draft v0.1 · last_reviewed 2026-06-01 — verification/version-schema.md*
