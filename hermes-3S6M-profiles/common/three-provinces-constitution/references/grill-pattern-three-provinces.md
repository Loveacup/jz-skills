# Grill 模式在三省六部中的落地

吸收自 mattpocock/skills: [grill-me](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) + [grill-with-docs](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs)

## grill-me → 监国太子承旨后

> Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree.

映射到三省六部：**中书拟制前必须 grill 父皇**。

触发条件（任一满足即 grill）：
- 需求术语模糊（"评估一下"——评估什么维度？）
- 边界不清（"整个项目链路"——包括哪些组件？）
- 验收标准未定（"完成了通知我"——什么叫完成？）
- 多解并存（可以有 A/B/C 三种理解）

操作：
1. 承旨复述后，识别歧义点
2. 逐问题向父皇追问，一问一答，不跳步
3. ≥2 轮确认不嫌烦
4. 共识达成 → 拟制

反面教材（2026-05-25 第7次纠正）：
- 父皇说"看板项目完成后主动跟我说" → 孤理解为"对话时查板" → 父皇纠正为"不对话时主动推送"
- 若当时 grill 追问一句"主动的意思是每次对话时查板，还是看板清空时推送消息？" → 少一轮返工

## grill-with-docs → 门下封驳

> Challenge against the existing domain model, sharpen terminology, update documentation inline.

映射到三省六部：**门下封驳时用制度/CONTEXT/ADR 拷问方案**。

操作：
- 用 three-provinces-constitution、kanban-orchestrator、各 profile SOUL.md 拷问
- 术语冲突立即标记（"你的方案说'直派工部'，但宪法要求尚书省必介入"）
- 模糊语言要求精确（"'合适的时候' → 请指定触发条件"）

## 已知陷阱

- **grill ≠ 犹豫不决**：grill 是澄清需求，不是反复讨论方案
- **grill ≠ 拒绝执行**：追问完确定边界后立即执行
- **grill 过度**：父皇明确说"直接做""不用问"时，不 grill
