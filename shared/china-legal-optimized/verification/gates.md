---
file: verification/gates.md
role: pipeline 编排总图 · 装配入口（控制流根 · 概念零依赖）
depends_on: []
orchestrates: [volatility-classes, source-tags, non-lawyer-gate, grill-framework, web-research-gate, version-schema, output-checklist, output-gate, anti-patterns]
consumed-by: [SKILL.md]
status: draft v0.1
last_reviewed: 2026-06-01
---

# 装配总图 · Gates（编排入口）

> SKILL.md 薄入口加载的第一份。本文件是**地图**——编排 9 个文件的加载与触发，但**不消费**它们的内部定义（控制流根，故概念零依赖、不构成环）。同时在此**裁定**三个跨文件挂账（#1 / #3 / #5）。

## 0. 装配总则（常驻 vs 条件触发）

| | 文件 | 时机 |
|---|---|---|
| 🟢 **常驻 8** | gates · volatility · source-tags · grill · non-lawyer-gate · output-checklist · anti-patterns · output-gate | 会话装配即加载 |
| 🔶 **条件 2** | web-research-gate | 断言判 **L2/L3** |
| | version-schema | 读 **knowledge/ 资料** |

## 1. Pipeline 编排总图（含数据流 · 解 #3）

```
SKILL.md 薄入口
   └─ 装配【常驻 8】
        │
        ▼
   闸门① grill ──── 确认 管辖地 / 时间线 ───┐
        │                                    │ 数据流（非依赖）
        ▼                                    │ #3 在此显式画出
   路由 → framework 领域模块                  │
        │                                    │
        ▼                                    ▼
   分析中 ──每断言──▶ volatility 判级
        │              ├─ L2/L3 ─▶ 🔶闸门② web-research ◀── 取 grill 的管辖地/时间 构造 query
        │              └─ 读资料 ─▶ 🔶version-schema 核 stale ──(stale)──▶ 闸门②
        ▼
   成稿 ─▶ 闸门③ output-gate（5 项 → 🔍 Gate Stamp）─▶ output-checklist（表达自检）─▶ 输出
        ╎
        └╌╌ anti-patterns 全程贯穿（负向约束）
```
> 实线 = 控制流；`◀──` = **运行时数据流**（grill→web 传参，由本编排层负责传递，非概念依赖边）。**#3 关闭** ✅

## 2. 触发对照表

| 触发条件 | 启动 |
|---|---|
| 任何分析开始 | 闸门① grill + 常驻协议 |
| 断言判 L2/L3 | 🔶 闸门② web-research |
| 读 knowledge 资料 | 🔶 version-schema |
| 资料 stale | version-schema → 闸门② |
| 成稿 | 闸门③ output-gate → Gate Stamp |
| 命中升级触发 | non-lawyer-gate 升级 |
| unknown 不可补 | provisional mode |
| 全程 | anti-patterns 负向约束 |

## 3. Gate Stamp 归属（防环说明）

Gate Stamp 的**格式定义在 [[output-gate]]**；本文件仅**引用**它。故 `gates ⇢ output-gate` 是控制流（虚线），非概念依赖——消解 gates⇄output-gate 潜在环（与装配图一致）。

## 4. 裁定 #1：标签 × 级别映射的单一数据源

> 挂账 #1：映射在 volatility §3 与 source-tags §3 重复（v1.0「8 处重复版本表」式漂移隐患）。
> **裁定**：以 **[[source-tags]] §3 为唯一数据源**；[[volatility-classes]] §3 已改为只判触发、不复制标签映射，并显式引用 source-tags §3。**#1 关闭** ✅

## 5. 裁定 #5：framework 层版本治理

> 挂账 #5：验证层自己的 10 文件（及 framework/ 方法论）有 status/version 但不走 stale。
> **裁定**：framework 层走**轻量复审**——绑定 skill 大版本（每次 vX.0 发布时人工过一遍）+ 半年兜底复审，**不**走 knowledge 的 stale 自动检索（方法论不会「数值过期」，只会随司法实践演进）。各文件 frontmatter 以 `last_reviewed` 字段记录最近复审日。**#5 关闭** ✅

## 6. SKILL.md 薄入口调用约定

```
SKILL.md（薄）：
  1. 加载 verification/gates.md（本图）
  2. 装配常驻 8
  3. 执行 pipeline（§1）：①grill → 路由领域 → 〔判级⇒②检索 / 读资料⇒version〕→ ③output-gate → checklist
  4. 领域 framework 模块由 §1 的「路由」步按 grill 识别结果挂载（不在本两层范围）
```

## 7. 十文件清单（落盘清单）

```
verification/
  gates.md              🟢入口   本图
  volatility-classes.md 🟢地基   L0–L3 判级（#1 后不再自带标签映射）
  web-research-gate.md  🔶闸门②  L2/L3 实时检索
  version-schema.md     🔶       资料 stale 判定
  output-gate.md        🟢闸门③  5 项硬核 + Gate Stamp 定义
cross-cutting/
  source-tags.md        🟢       三层标签 + 引用规范（#1 后为映射唯一源）
  grill-framework.md    🟢闸门①  事实确认块
  non-lawyer-gate.md    🟢       免责 / 升级 / provisional
  output-checklist.md   🟢       表达质量自检
  anti-patterns.md      🟢贯穿   10 红线
```

---

*draft v0.1 · last_reviewed 2026-06-01 — verification/gates.md*
