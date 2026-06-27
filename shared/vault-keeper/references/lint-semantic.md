# 语义 lint 规程（agent 判断，engine 不做）

> `engine/lint.py` 只做**结构 lint**（断链 / 孤立 / 缺源 core / 陈旧 / 缺字段——确定性，谁跑都同结果）。
> **语义 lint 需 LLM 判断，由本规程驱动**（Hermes cron 周期触发 CC）。对应方法论 §二十四 B。

## 扫 core 区各页，判断：
1. **矛盾**：与其他 core 页的 claim 级冲突 → 送 §二十五 裁决。
2. **陈旧 / 过时**：claim 是否被更新的源推翻（不只看 `modified` 日期，看内容是否被新证据取代）。
3. **无源外推**：claim 是否超出其 `sources` 支持范围 → 接 `references/fidelity.md`，触发 confidence 触底。
4. **AI 腔 / 华丽空洞**：是有判断力的合成，还是堆砌套话（承 v1.7 资产保证度「华丽假图 = 保证度为零」）。

## 输出
追加到 `engine/lint.py` 生成的 `88-审计/lint-YYYY-MM-DD.md` 的"语义"小节，记 `lint` 日志。结构 lint 与语义 lint 同报告、分两节。
