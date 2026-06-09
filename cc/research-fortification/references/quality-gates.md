# 质量验证矩阵 G1–G4

> 四道门，按模式分档启用（见 modes.md）。Critique Utility 量化：以软处表为分母，`injected` 计数为分子，逐点判定。

## 门表

| 门 | 维度 | 检查项 | 通过判据 | 量化方式 |
|---|---|---|---|---|
| **G1** | 反幻觉门(焊前) | 每个软处批评点在基底原文是否有据 | `hallucinated` 点 **100% 被剔除**，不进 P4 | 幻觉剔除率 = hallucinated/N；**>40% 则回流 P1 重诊断**（洞察稿质量存疑） |
| **G2** | 逐点落地计数 | 每个 grounded 软处是否真焊入终稿 | **N/N 全落地**；`not-landed` 强制回流 P4 复焊 | Critique Utility =(injected+0.5×partial)/N；门槛 **Standard≥0.9，Deep=1.0** |
| **G3** | 宏观一致性二次检测 | 焊回后全文论旨/逻辑链是否自洽无新矛盾 | `conflict` 数 = 0；冲突点复焊 | 全文通读专测论旨连贯(非局部) |
| **G4** | additive 占比门槛 | 加固是否以增补承重论证为主 | additive 占比 **≥ 0.6**（Deep ≥ 0.7）；低于则判「新手式只换措辞」 | additive_ratio，**按承重段落体量加权，非裸点数** |

## G4 正确算法：按承重体量加权，而非裸点数

若按裸点数算，例如 additive 2 点 / 总 4 点 = 0.5 会**误判**不达标。G4 防的是「主力是否投在增补」——必须按**新增承重段落体量**计：两面整章承重墙的体量远超几处改词与标签替换，按体量加权 additive 占比常达 ≈ 0.85，主力明确在 additive，达标。

> 这条算法本身就是 G4 要教会评审的判读方式：别被点数欺骗，看承重段落的字数/篇幅占比。

## 分档启用（详见 modes.md）

| 模式 | 启用门禁 |
|---|---|
| Quick | G1 + G2 |
| Standard | G1 + G2 + **G4** |
| Deep | **G1+G2+G3+G4 全开**（G2=1.0, G4≥0.7） |

> 分档铁律①：**G1 反幻觉任何模式不可砍**（CLAIMCHECK 红线），否则会把幻觉批评焊进文档。

## 台账 = 门的物理载体

point-by-point 台账（见 soft-spot-schema.md）每行的 `claimcheck_status`(供 G1) / `critique_utility`(供 G2) / `macro_consistency`(供 G3) / `weld_strategy`+体量(供 G4) 即四门的逐点数据源。终稿附台账 = 四门可机检。
