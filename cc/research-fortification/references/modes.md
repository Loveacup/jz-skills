# 模式分级表

> 比 strategic-insight（16/9/5 agent）**更轻量**。分级主轴 = **门禁开关数 + 软处规模**，agent 数控制在 3-9。

## 模式 → subagent 映射（软编排：mode 决定 Leader 派几个 teammate + 开哪些门）

| 模式 | 透镜数 | 估时 | 软处 N | RUN-1 诊断 agents | RUN-2 焊接 agents | 启用门禁 | 总 agent |
|---|:--:|---|:--:|---|---|---|:--:|
| **Quick 速焊** | 1 | 4-6 min | 6-10 | 蒸馏+诊断合 1 · 分类+锚定合 1 | welder + verifier | G1 + G2 | ~3 |
| **Standard 标准**〔默认〕 | 1 | 8-12 min | 10-18 | distiller · diagnostician · classifier · evidence-anchor | welder + verifier | G1+G2+**G4** | ~5 |
| **Deep 深焊** | 2-3 | 15-20 min | 18-30 | distiller + diagnostician×2-3(互盲并行) + classifier + 独立 claimcheck | welder + verifier + G3 宏观二次检测 | **G1+G2+G3+G4 全开**(G2=1.0, G4≥0.7) | ~9 |

> Quick 把 P0+P1 与 P2+P3 各合一个 agent（distiller 无外部源时直接由 diagnostician 起）；Deep 把 claimcheck 独立成 agent、P1 多透镜互盲并行、P5 加 G3 宏观专项 + 回流复焊循环。比 SI（16/9/5）更轻，agent 数 3-9。

## N=1（Quick/Standard 单透镜）选哪个 lens —— 按基底体裁先验（doc-type-matrix）

单透镜**绝不能乱选**：选错就整片漏掉该体裁的主力软处。按 doc-type-matrix 的体裁→主力软处映射定：

| 基底体裁 | N=1 选 lens | 因为主力软处是 |
|---|---|---|
| 技术/战略分析稿 | 证据审查者 | 证据缺位 + 口径过强 |
| CQI 清单/问题日志 | 因果桥审查者 | warrant/backing 缺失（根因凭直觉）|
| 方法论/文献综述 | 因果桥审查者 | 缝合处无论证 |
| 规范文档(SKILL.md类) | 反例猎手 | 反例未防御 |

> Deep（N=2-3）按体裁取主力 lens + 1-2 个补充 lens（如分析稿配「反例猎手」压测）。

## 分级三铁律

1. **G1 反幻觉任何模式不可砍**（CLAIMCHECK 红线），否则会把幻觉批评焊进文档。
2. **P0 蒸馏 + P5 验证全模式保留**（即使合并）：剪枝纯化与落地验证是本方法论区别于「粗暴 merge」的本质，砍了就退化。
3. Deep 的「多透镜并行」是透镜外置的强形式（PerFine 多 profile），但仍远轻于 SI 的 16-agent。

## 选档先验

软处地基越松、对外风险越高 → 越靠 Deep。
- 四点全覆盖三策略 + 全套 CoV 附录 + 多透镜对抗的高风险技术稿 → **Deep**。
- 只补几处的扎实基底 → **Quick**。
- 拿不准 → **Standard**（默认）。
