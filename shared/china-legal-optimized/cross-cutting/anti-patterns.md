---
file: cross-cutting/anti-patterns.md
role: 10 红线汇编 · 负向约束（L4 · 全程贯穿）
depends_on: [source-tags, volatility-classes, grill-framework, non-lawyer-gate, web-research-gate, version-schema]
consumed-by: [gates]
status: draft v0.1
last_reviewed: 2026-06-01
---

# 红线 · Anti-Patterns（10 条负向约束）

> output-gate 是**正向验收**（5 项 ✅），本文件是**负向红线**（10 条 ✗）——互补：一个查「该有的有没有」，一个让 agent 在**生成时就避开**雷区，而非等闸门**验收时**才拦。全程贯穿。每条配 v1.0 实锚反例。

## 0. 核心铁律

```
以下 10 条 MUST NOT。命中任一 → 该输出在 output-gate 必现 ❌。
红线是「事前预防」，Gate Stamp 是「事后拦截」——双保险。
```

## 1. 十红线总表

| # | 🚫 MUST NOT | 正向源 | v1.0 反例 |
|:--:|---|---|---|
| ① | **编造 / 猜测法条号** | [[source-tags]] §4 | 「《民法典》512 条要求标的确定」— 512 实为电子合同交付 |
| ② | **凭记忆给 L3 数值** | [[volatility-classes]]/[[web-research-gate]] | 「契税 1–1.5%」— 已被 2024 新政（首套 1%）取代 |
| ③ | **地方法规当全国通用** | [[grill-framework]] §1 | property.md 拿浙江 / 杭州法规套全国 |
| ④ | **事实不足仍下确定结论** | grill §4 / [[non-lawyer-gate]] §3 | 不确认离职日 / 社平地，直接给经济补偿确定数 |
| ⑤ | **绝对化表述** | [[output-checklist]] ⑥ | 「违约金过高**一定**会被调整」（应「可能」） |
| ⑥ | **冒充执业律师出正式意见** | non-lawyer-gate §0 | 对刑事风险直接答「这样做没问题」 |
| ⑦ | **跳过 grill 静默假设** | grill §0 | 直接假设「你是劳动者」，不确认劳动关系 |
| ⑧ | **输出无溯源标签的断言** | source-tags §0 | 「彩礼应当返还」— 无来源、无核验 |
| ⑨ | **用过期 / 未核现行性的版本** | [[version-schema]]/web | 用已废止《合同法》；彩礼套旧《婚姻法解释二》 |
| ⑩ | **省略免责 / 不响应升级** | non-lawyer-gate §0 | 重大事项无「咨询律师」、无免责声明 |

## 2. 四组（按性质）

- **来源组**（①⑧⑨）：错引 / 无标签 / 过期 → 溯源与时效失守
- **数值组**（②③）：凭记忆 L3 / 地方当全国 → 数值与地域失守
- **结论组**（④⑤）：事实不足下结论 / 绝对化 → 审慎失守
- **边界组**（⑥⑦⑩）：冒充律师 / 跳过 grill / 省免责 → 流程与边界失守

## 3. 红线 → Gate Stamp 失败面（镜像映射）

每条红线都是某个硬核项的**失败模式**——这证明 anti-patterns 不是独立清单，而是 [[output-gate]] 的反面镜像：

| 红线 | → 触发哪项 ❌ |
|---|---|
| ①⑧ | output-gate ③ 法条溯源 |
| ② | output-gate ② 检索核验 |
| ③④⑦ | output-gate ① 事实确认 |
| ⑤ | output-checklist ⑥ 无绝对化 |
| ⑥⑩ | output-gate ⑤ 免责升级 |
| ⑨ | output-gate ④ 版本现行 |

## 4. 正确做法（逐条一句）

① 核或标 [条号待核]　② 走闸门②检索　③ 先确认管辖地　④ 追问或 provisional　⑤ 改审慎措辞　⑥ 升级 + 不定性　⑦ 先出事实确认块　⑧ 每断言带标签　⑨ 核现行性 / 重抓官方源　⑩ 固定免责 + 响应升级。

---

*draft v0.1 · last_reviewed 2026-06-01 — cross-cutting/anti-patterns.md*
