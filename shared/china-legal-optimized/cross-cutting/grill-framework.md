---
file: cross-cutting/grill-framework.md
role: 输入闸门① · 分析前强制事实确认（L1）
depends_on: [non-lawyer-gate]
consumed-by: [output-gate, anti-patterns]
status: draft v0.1
last_reviewed: 2026-06-01
---

# 事实确认 · Grill Framework（闸门①）

> 法律结论高度依赖「在哪、何时、谁对谁、多少钱、到哪一步」。**MUST 在任何实质分析前，先输出一个事实确认块**，把五要素标 `confirmed / assumed / unknown`；`unknown` 的关键要素 **MUST 追问**，禁止静默假设。拿不到就降级 → [[non-lawyer-gate]] provisional mode。

## 0. 核心铁律

```
任何领域分析开始前：
   先输出【事实确认块】（五要素 × 三态）
   ├─ 有 unknown 关键要素 → 追问；追问不到 → provisional mode
   └─ assumed 项 → MUST 显式标注，不得当 confirmed 用
🔴 MUST NOT 跳过本块直接分析（= anti-pattern ⑦）
🔴 MUST NOT 把推断（assumed）伪装成已确认（confirmed）
```

## 1. 五要素 · 「地 · 时 · 人 · 额 · 程」

| 要素 | 为何关键（影响什么） | unknown 时追问 |
|---|---|---|
| **管辖地** | 决定**地方性法规 + 地方标准**（社平、维修资金、契税执行、管辖法院）→ 多为 L3。*不问就套地方法规 = property 浙江教训* | 「涉及哪个省 / 市？（影响适用的地方法规与标准）」 |
| **时间线** | 决定**适用法律版本**（新法 / 旧法）、**时效**、期限是否届满 → 多为 L2。*2024 前后公司法不同、民法典前后不同* | 「关键事件发生在什么时间？（影响适用版本与时效）」 |
| **主体** | 决定**资格 / 适格 / 责任方式**（自然人 / 法人 / 个体户、消费者 / 经营者、劳动者 / 用人单位、一人公司） | 「涉及哪些主体？各是个人还是公司？」 |
| **金额** | 决定**管辖级别**、诉讼费、是否触发**重大利益升级**（接 [[non-lawyer-gate]] HARD #4）、补偿计算 | 「涉及金额大约多少？（影响管辖、费用与方案）」 |
| **程序状态** | 决定**可用手段 + 紧迫性**、是否**已涉诉**（接 non-lawyer-gate HARD #5） | 「目前到哪一步？协商 / 已起诉 / 已开庭 / 已判决？」 |

## 2. 三态标注规则

| 态 | 标记 | 含义 | 处理 |
|---|:--:|---|---|
| **confirmed** | ✅ | 用户明确提供 / 材料可确证 | 直接作分析基础 |
| **assumed** | ⚠️ | 从上下文**合理推断**，未经确认 | **MUST 显式标注**；若影响重大结论 → 追问确认 |
| **unknown** | ❓ | 缺失且影响分析 | **MUST 追问**；不得静默假设 |

## 3. 事实确认块格式（闸门①的强制可见产物）

```
📋 事实确认
| 要素     | 状态           | 内容 |
|----------|----------------|------|
| 管辖地   | ✅ confirmed   | 浙江·杭州 |
| 时间线   | ⚠️ assumed     | 假设签约于 2024-07 后（适用新公司法）|
| 主体     | ✅ confirmed   | 甲=自然人，乙=有限公司 |
| 金额     | ❓ unknown     | 待补：标的额 |
| 程序状态 | ✅ confirmed   | 协商中，未起诉 |

❓ 需补全：标的额大约多少？（影响管辖法院与诉讼费）
⚠️ 假设提示：若签约在 2024-07 前，适用旧公司法，结论可能变化。
```

> 此块是闸门①的「留痕」——`output-gate` 第①项核它是否在场（缺块 = 未过闸）。

## 4. unknown 处理：追问 vs provisional 分流

```
事实确认块完成
   │
   ├─ 五要素无 unknown（全 ✅/⚠️）──▶ 进入分析（⚠️ assumed 项全程显式标注）
   │
   └─ 有 unknown 关键要素 ──▶ 能追问吗？
            ├─ 能（多轮交互）──────▶ 追问 → 等补全 → 重判三态
            └─ 不能（用户明确无法提供 / 单轮）──▶ provisional mode
                                                  （non-lawyer-gate §3：
                                                   方向性分析 + 显式假设 + 假设性免责）
```
**追问是首选，provisional 是兜底。** MUST NOT 在能追问时直接跳 provisional 偷懒。

## 5. 依赖方向 + 与闸门②的数据流（钉死 · 防环）

- **上游依赖**：本文件 depends_on [[non-lawyer-gate]]——unknown 不可补时调其 provisional mode。
- **对闸门②的供给**：确认后的**管辖地 / 时间线**是 [[web-research-gate]] 构造精准 query 的输入（查「杭州·契税」需城市、查适用法律需时间）。
  > ⚠️ 这是**运行时数据流**（由 `gates` 编排传递），**不是**概念依赖——web-research-gate 的依赖仍是 volatility + source-tags，装配图无新增边、无环。

## 6. 正例 / 反例（v1.0 实锚）

**反例 ❌**
- property.md 不问管辖地、直接套浙江法规 — **管辖地 unknown 当 confirmed**
- 经济补偿不确认离职日 / 社平地就给数字 — **时间线 + 管辖地双 unknown**
- 直接假设「你是劳动者」不确认劳动关系 — **主体 assumed 当 confirmed**

**正例 ✅**
- 先出确认块，管辖地 ❓ → 追问「哪个市」
- 时间线 ⚠️ assumed（新法）→ 显式标「假设适用 2024 新公司法」
- 金额 ❓ 且涉管辖 → 追问标的额

## 7. 下游接口约定

| 下游 | 取用本文件的什么 |
|---|---|
| `output-gate` | Gate Stamp 第①项：核「事实确认块在场 + 无未响应的 unknown」 |
| `anti-patterns` | 红线 ③（地方法规想当然 = 管辖地未确认）、⑦（跳过 grill 静默假设）引用本文件 |
| `web-research-gate` | 运行时取确认的**管辖地 / 时间线**构造 query（数据流，见 §5） |

---

*draft v0.1 · last_reviewed 2026-06-01 — cross-cutting/grill-framework.md*
