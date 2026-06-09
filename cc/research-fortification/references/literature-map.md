# 设计决策 → 文献支撑速查（最低优先级，溯源用）

> 本 skill 每个设计落点都锚定顶会/顶刊文献。下表供需要追问「这条规则凭什么」时溯源。

| 设计落点 | 文献/框架 | 标识符 |
|---|---|---|
| 透镜外置（元原则①、P1、Quick 不可省、Deep 多透镜） | Constitutional AI (Anthropic 2022) / PerFine | arXiv:2212.08073 / arXiv:2510.24469 |
| 五步加固骨架（Pipeline 主轴） | Flower, Hayes et al. Detection-Diagnosis-Strategy-Operation (1986) | DOI 10.2307/357381 |
| 弱点四象限分层（schema 字段、§5 落点、G3） | Faigley & Witte, Analyzing Revision (1981) | DOI 10.58680/ccc198115887 |
| additive/corrective 操作化（元原则②、§5、G4） | IteraTeR (ACL 2022) / Sommers (1980) | arXiv:2203.03802 / EJ240356 |
| 证据锚定 verify-then-correct（P3、G1） | CRITIC (ICLR 2024) | arXiv:2305.11738 |
| 反幻觉校验红线（G1、决策树剔除分支） | CLAIMCHECK (EMNLP 2025) | arXiv:2503.21717 |
| Critique Utility 量化（G2、P5） | RCO / Training LM to Critique (ACL 2025) | arXiv:2506.22157 |
| 剪枝纯化（P0 蒸馏、N 取舍） | Revisiting Knowledge Injection Frameworks (2023) | arXiv:2311.01150 |
| 类型→动作映射（§5 策略表、ODC 骨架） | ODC (IEEE TSE 1992) / CWE→Mitigation | DOI 10.1109/32.177364 / cwe.mitre.org |
| 落地验证 + 强制 Follow-up（P5、G2/G3） | Fagan Inspection (IBM 1976) | — |
| point-by-point 可追溯（sid 链、G2 台账） | Response-to-Reviewers 协议 | PMC10917605 |
| 命名查证（Research Fortification 无撞名） | Food Fortification（语义无关，撞名排除） | GHSP 2021 |

## 辅助术语体系（skill 内部命名，论证理论无人占用）

- `load-bearing claim identification` 承重论点识别（P1 一级操作）
- `adversarial lens review` 对抗视角审查（区别于 BMAD adversarial review）
- `dialectical synthesis` 辩证合成

## ⚠️ 待人工复核项

以下 2026 年/较新预印本编号为检索所得，落地引用前再核验链接有效性：
- WriteBack-RAG (arXiv:2603.25737)
- PerFine (arXiv:2510.24469)
- SCRPO (arXiv:2512.05387)
- SPA (arXiv:2603.22213)

> 完整来源索引见设计方案全文 `research-fortification-skill-方法论方案`（OB `02-Plan&CQI/`）附录。
