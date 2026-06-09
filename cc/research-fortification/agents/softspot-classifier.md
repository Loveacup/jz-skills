# Agent: softspot-classifier（R1·P2 弱点分类）

## 输入（Leader 注入）
- 全部 lens-diagnostician 的软处候选（已合并去重；若多透镜有重叠软处，合并为一条并保留各视角证据锚）

## 动作
给每个软处打分类标，写满 schema 的 P2 字段：
- `fw_surface_meaning ∈ {表层, 意义}` — Faigley-Witte 纵轴。改的是字面/表述=表层；改的是命题真值/论证=意义。
- `fw_micro_macro ∈ {微观命题, 宏观论旨}` — 横轴。只动单点=微观；动摇全文论旨=宏观。
- `revision_polarity ∈ {additive, corrective}` — additive=增补承重论证（注入新墙）；corrective=改写/纠正既有（换措辞/降调）。

## 分类启发
- backing缺失 / 论证断层 / 证据缺位 → 多为 意义×宏观 → additive
- warrant缺失(微观) / 措辞含糊/失准 → 表层↔意义×微观 → corrective
- 口径过强 / 反例未防御 → 意义 → corrective(防御)

## 输出（task I/O 返回）
分类后软处表（每条补齐 fw_*、revision_polarity，sid 全程不变）。

## 约束
- 合并重叠软处时**可增不可漏**：多透镜都点到的承重点优先级最高。
- timeout 10min。
