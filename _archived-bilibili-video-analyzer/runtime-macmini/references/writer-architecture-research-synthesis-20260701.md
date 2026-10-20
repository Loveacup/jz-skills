# Writer 架构研究综合（学术 + 开源）

**日期**：2026-07-01  
**触发**：P2-D1 前调研"逐节 writer vs 全文一次性 writer"最优路径

## 学术结论（共识极强）

| 论文 | 年份 | 核心发现 |
|:--|:--|:--|
| Google DeepMind "Planning into Single-Turn Generation" | 2024 | 先计划再写作：auxiliary task 教 LLM 结构化推理 → +2.5% ROUGE-L，3.60 人类胜率 |
| STORM (Stanford, NAACL) | 2024 | 逐节生成 + 并行 + 去重拼接 → 组织性 +25%，覆盖度 +10% |
| WritingPath | 2024 | 显式 outline 引导 LLM → 用户意图在 outline 阶段编码 |
| Plan-and-Generate with Citations (ACL) | 2024 | Plan = 问题序列 → 引用准确率显著提升 |
| DOME | 2024 | 规划与写作融合 + 记忆模块防上下文冲突 |
| Segment-Level Diffusion | 2024 | 逐段 latent representation → autoregressive decode |
| MM-PAW (INLG) | 2024 | 先出 intermediate plan → 条件化生成 → 内容相关性/groundedness 大幅提升 |

> **核心共识**：plan → generate per-section → validate → concatenate。没有一篇支持一次性吐全文。

## 开源项目模式

| 项目 | 架构 | 质量 | 适用性 |
|:--|:--|:--|:--|
| **t2md** | 单次 LLM → 全文，prompt-first | ⭐⭐ | 简单但不控 |
| **jedireporter** | 三阶段（Fix→Create→Post），Create 仍是单 LLM | ⭐⭐⭐ | 有 LLM judge 无逐节控制 |
| **BodhiFlow** | 两阶段（提取→精炼），多 style 输出 | ⭐⭐ | 灵活但无质量闸 |
| **casestudypilot** ⭐ | Agent-driven + 逐节生成 + fail-fast 验证 + 多因子质量评分 | ⭐⭐⭐⭐ | 最接近目标架构 |
| **r2-mechanics** | 离线 ASR + LLM 分析 → 结构化 HTML | ⭐⭐⭐ | 离线方案但非开源代码 |

## 对本项目的启示

1. **已有 plan 层**（SectionSpec + build_writer_section_context）—— 学术界认为这是最关键资产
2. **逐节 LLM writer + 确定性 validator** 是工程最优解
3. **casestudypilot 的 fail-fast 验证**与本项目 `validate_section()` 同构
4. **DeepSeek V4 Pro** 作 provider，harness 质量 > 模型上限

## 决策
- ❌ 不继续确定性 writer（§3/§4/§7 需 LLM 综合判断）
- ❌ 不走全文一次性（学术/工程共识反对）
- ✅ **逐节 LLM writer + 确定性 validator + 跨节 coherence check**
