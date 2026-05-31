# 战略洞察长文质量闸门体系（quality-gates）

> 替代旧 `quality-checklist.md`。从"人工 ✅/❌ 填空"升级为**硬指标 + 自动判定 + Leader API**。
>
> v5.0 起：所有质检火力全开（无 mode 分支）。Red Flags 顶部预拦截，L1-L4 四层闸门串行执行，neat-freak 独立闸门，任何 Gate 不死锁。

---

## 0. 🚨 Red Flags 8 条预拦截（Stage 0 之前 / Leader 自查）

> 命中任一红旗，立即 **STOP** 或强制回炉到指定节点。**不进入正常 pipeline**。

| # | 触发条件 | 处置 | 阻断级别 |
|---|---------|------|---------|
| 1 | 用户主题 < 8 字且未上传素材 | 强制调用 `question-refiner`，补足后才放行 | 软阻断 |
| 2 | 素材单一来源 + 主题预测性强（如"X 公司明年股价"） | **STOP**，回提示用户补来源或改题 | 硬阻断 |
| 3 | `knowledge-enricher` 返回 qmd=0 且 Exa=0 | **STOP**，信息真空告警，要求用户补素材 | 硬阻断 |
| 4 | CoV Layer 1 引用覆盖率 < 60% | 全量回炉到 3 个 researcher，**不进入 Stage 4** | 软阻断（max 1 轮）|
| 5 | CoV Layer 2 URL 死链率 > 40% | 同上 + 来源降级标记 | 软阻断（max 1 轮）|
| 6 | `longform-writer` 字数 < 2500 或 > 30000 | 直接 reject，回写者调字数 | 软阻断（max 2 轮）|
| 7 | 主标题与正文核心论点偏离度 > 50% | 回 `output-finalizer` 重提炼标题，**不进入 6.5 美化** | 软阻断（max 1 轮）|
| 8 | 主题命中政治敏感词 / 内容合规高风险词 | **STOP**，提示用户改写或转私域 | 硬阻断 |

**Red Flags 输出 verdict（统一 Schema）**：

```
<verdict>
{
  "gate": "RedFlags",
  "pass": true,
  "score": null,
  "subscores": {
    "topic_length": 24,
    "source_count": 3,
    "qmd_exa_total": 7,
    "title_alignment": null
  },
  "blocking": [],
  "next_action": "proceed_to:topic-preprocessor"
}
</verdict>
```

---

## 1. L1 硬性规则闸门（output-finalizer 首段）

> 命中阈值 = **0**。任何一条不通过即回炉。

引用黑名单详见 [`anti-ai-blacklist.md`](anti-ai-blacklist.md)。

| 指标 | 阈值 | 检测方法 | 失败处置 |
|---|---|---|---|
| AI 词汇黑名单命中数 | = 0 | grep `anti-ai-blacklist.md` 全表 | 回 `longform-writer` 局部段落重写（max 2 轮）|
| 教科书开头命中数（"近年来" / "随着 X 的发展" / "在 X 背景下"等）| = 0 | grep 首段 + 每章节首段 | 同上 |
| 连续 3+ 破折号段落数 | = 0 | 段内 `—{3,}` 或 `——.*——.*——` | 同上 |
| YAML frontmatter 字段完整性 | = 100% | 检查 status / type / aliases / tags / created / modified | 回 `output-finalizer` 补字段 |
| 禁止标点连用（中文`,,` / `。。`）| = 0 | regex 扫描 | 同上 |

**L1 verdict 示例**：

```
<verdict>
{
  "gate": "L1",
  "pass": false,
  "score": 0.6,
  "subscores": {
    "blacklist_hits": 3,
    "textbook_openers": 1,
    "dash_clusters": 0,
    "yaml_completeness": 1.0,
    "forbidden_punct": 0
  },
  "blocking": ["blacklist_hits=3 > 0", "textbook_openers=1 > 0"],
  "next_action": "send_back_to:longform-writer:local_rewrite"
}
</verdict>
```

---

## 2. L2 风格一致性闸门（longform-writer 内部自检 / Stage 5 末段）

> 控制节奏感、避免段落 monoton、保证伏笔回收。

| 指标 | 阈值 | 计算方法 | 失败处置 |
|---|---|---|---|
| 段长方差 / 段长均值 | ≥ 0.40 | `np.var(段长) / np.mean(段长)` | 回 writer 局部重写（max 2 轮）|
| 连续短句段落比（每段 ≥ 4 句 且 每句 < 15 字）| ≤ 10% | 章节统计 | 同上 |
| 连续长句段落数（每段 ≥ 3 句 且 每句 > 50 字）| = 0 | 全文扫描 | 同上 |
| 伏笔回收率（前文出现 + 后文呼应 / 前文出现）| ≥ 70% | 关键概念交叉检索 | 标记低置信度，不阻断 |

**L2 verdict 示例**：

```
<verdict>
{
  "gate": "L2",
  "pass": true,
  "score": 4.1,
  "subscores": {
    "para_length_cv": 0.48,
    "short_sentence_para_ratio": 0.07,
    "long_sentence_para_count": 0,
    "callback_recovery_rate": 0.78
  },
  "blocking": [],
  "next_action": "proceed_to:L1_gate"
}
</verdict>
```

---

## 3. L3 内容质量闸门（output-finalizer 中段 + source-manager 早期触发）

> 整合原 CoV 三层、论点-证据-结论链、HKR Resonance、引用密度。

### 3.1 早期触发（Stage 3.5 / source-manager 内）

仅校验 **CoV 致命异常**：
- CoV Layer 1 覆盖率 < 60% → 触发 Red Flag 4
- CoV Layer 2 死链率 > 40% → 触发 Red Flag 5

### 3.2 终审（output-finalizer 中段）

| 指标 | 阈值 | 计算方法 | 失败处置 |
|---|---|---|---|
| 论点-证据-结论链覆盖率 | ≥ 90% | 章节内识别 claim → evidence → conclusion 三元组 / 总论点数 | 回 `insight-synthesizer`（max 1）|
| CoV 引用完整性（Layer 1 / 来源标注率）| ≥ 95% | (有标注引用数 / 总引用数) | 回 `source-manager`（max 1）|
| CoV URL 可达率（Layer 2）| ≥ 85% | HEAD 请求成功率 | 同上 |
| CoV 交叉验证通过率（Layer 3）| ≥ 70% | 多源一致性 / 总核查项 | 同上 |
| HKR Resonance（Happy + Knowledge + Resonance 三维平均）| ≥ 3.5/5 | 综合主观 + 启发性评分 | 回 `longform-writer`（max 1）|
| 引用密度 | 1 条/400 字 ±30% | (引用条数 / 全文字数) × 400 → 落入 [0.7, 1.3] | 详见 [`source-citation-guide.md`](source-citation-guide.md) §"引用密度阈值" |

**L3 verdict 示例**：

```
<verdict>
{
  "gate": "L3",
  "pass": false,
  "score": 3.4,
  "subscores": {
    "argument_chain_coverage": 0.85,
    "cov_citation_completeness": 0.95,
    "cov_url_reachability": 0.62,
    "cov_cross_verification": 0.72,
    "hkr_resonance": {"happy": 3.8, "knowledge": 4.2, "resonance": 3.5, "avg": 3.83},
    "citation_density": 0.92
  },
  "blocking": ["cov_url_reachability=0.62 < 0.85"],
  "next_action": "send_back_to:source-manager"
}
</verdict>
```

---

## 4. L4 活人感闸门（output-finalizer 最末）

> 软违规 → 自动调 `Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")` 改写；硬违规 → 回炉 writer。

| 指标 | 阈值 | 软/硬 | 计算方法 |
|---|---|---|---|
| AI 味词汇密度 | ≤ 0.3 / 千字 | 软 | (黑名单命中数 / 全文字数) × 1000 |
| 破折号密度 | ≤ 1 / 800 字 | 软 | (`—` + `——` 总数 / 全文字数) × 800 |
| 三段式 "不是 X 而是 Y 更是 Z" 出现次数 | ≤ 2 处 / 全文 | 硬 | regex 扫描全文 |
| 否定排比（"不是…不是…不是…"）次数 | ≤ 1 处 / 全文 | 硬 | regex 扫描全文 |

**处置流程**：

1. **软违规**：Leader 调用 `Skill(skill="de-slop", args="检测并改写以下文本的AI味：{problematic_segment}")` 自动改写，改写后回 L4 复检。复检仍 fail → 标记低置信度放行 + 综合评分 -0.3
2. **硬违规**：回 `longform-writer` 局部重写（max 1 轮）。仍 fail → 综合评分 -0.5 放行

**L4 verdict 示例**：

```
<verdict>
{
  "gate": "L4",
  "pass": false,
  "score": 3.7,
  "subscores": {
    "ai_word_density": 0.45,
    "dash_density": 1.6,
    "triple_pattern_count": 4,
    "negative_parallelism_count": 0
  },
  "blocking": ["ai_word_density=0.45 > 0.3 (soft)", "dash_density=1.6 > 1.0 (soft)", "triple_pattern_count=4 > 2 (hard)"],
  "next_action": "auto_call:Skill(de-slop) for soft + send_back_to:longform-writer for hard"
}
</verdict>
```

---

## 5. neat-freak 闸门（output-finalizer 末段 / 与 L4 并行）

> 控制信息密度，避免"长文虚高"。

| 指标 | 阈值 | 计算方法 | 失败处置 |
|---|---|---|---|
| 膨胀比（最终字数 / 核心洞察字数）| ≤ 5.0 | `wc(final-article.md) / wc(core-insights.md)` | 回 `longform-writer` 精简（max 1）|
| 单章节占比 | ≤ 35% | 任一 H2 章节字数 / 全文字数 | 同上 |

**neat-freak verdict 示例**：

```
<verdict>
{
  "gate": "NeatFreak",
  "pass": true,
  "score": 4.5,
  "subscores": {
    "inflation_ratio": 4.2,
    "max_chapter_ratio": 0.28
  },
  "blocking": [],
  "next_action": "proceed_to:final_scoring"
}
</verdict>
```

---

## 6. 统一 Verdict JSON Schema（Leader API）

每个 Gate 强制输出包裹在 `<verdict></verdict>` 标签里的 JSON。Leader 用 regex 提取 + `json.loads` 解析 + `next_action` 路由。

### 字段定义

```typescript
interface Verdict {
  gate: "RedFlags" | "L1" | "L2" | "L3" | "L4" | "NeatFreak" | "FinalScore";
  pass: boolean;                              // true=通过 false=回炉
  score: number | null;                       // 0-5 综合评分（RedFlags 为 null）
  subscores: Record<string, number | object>; // 各子指标原始值
  blocking: string[];                         // 阻断原因列表（人类可读 "metric=value < threshold"）
  next_action: string;                        // "proceed_to:<gate>" / "send_back_to:<agent>" / "auto_call:Skill(...)" / "STOP" / "retry"
}
```

### Leader 端解析伪代码

```python
import re, json
m = re.search(r"<verdict>\s*(\{.*?\})\s*</verdict>", agent_output, re.DOTALL)
if m:
    verdict = json.loads(m.group(1))
    action = verdict["next_action"]
    if action.startswith("send_back_to:"):
        target_agent = action.split(":", 1)[1]
        # SendMessage / TaskCreate 回炉
    elif action.startswith("auto_call:Skill"):
        # Skill(...) 调用
    elif action == "STOP":
        # 终止 pipeline
    elif action.startswith("proceed_to:"):
        # 进入下一 Gate
```

---

## 7. 失败回路图（ASCII）

> 任何 Gate 累计回炉到 max 轮后 **不死锁**，标记低置信度放行 + 综合评分扣分 + 报告告警。

```
[用户输入]
    │
    ▼
┌──────────────────────────────────────┐
│  🚨 Red Flags 8 条预拦截              │
└──────────────────────────────────────┘
    │
    ├─[命中 1/3/8: 硬阻断]──→ STOP
    ├─[命中 2: 硬阻断]──→ 提示补来源 → STOP
    ├─[命中 4/5: 软阻断 max 1]──→ researchers / source-manager
    │      └──→ 仍 fail → 标记低置信度放行
    ├─[命中 6: 软阻断 max 2]──→ longform-writer 调字数
    ├─[命中 7: 软阻断 max 1]──→ output-finalizer 重提炼标题
    │
    ▼ (全部通过 / 软阻断已放行)
[Stage 1-5 正常 pipeline]
    │
    ▼
┌──────────────────────────────────────┐
│  Stage 3.5 L3 早期（仅 CoV 致命）    │
└──────────────────────────────────────┘
    │
    ├─[CoV Layer 1 < 60%]──→ Red Flag 4
    ├─[CoV Layer 2 死链 > 40%]──→ Red Flag 5
    │
    ▼
[Stage 5 末段]
    │
    ▼
┌──────────────────────────────────────┐
│  L2 风格一致性闸门 (writer 内自检)   │
└──────────────────────────────────────┘
    │
    ├─[fail max 2]──→ writer 局部重写
    │      └──→ 仍 fail → 标记低置信度放行
    │
    ▼ (pass)
[Stage 6 output-finalizer 开始]
    │
    ▼
┌──────────────────────────────────────┐
│  L1 硬性规则闸门 (最先)              │
└──────────────────────────────────────┘
    │
    ├─[fail max 2]──→ writer 局部重写
    │      └──→ 第 3 轮 fail → 标记放行 + 评分 -0.5
    │
    ▼ (pass)
┌──────────────────────────────────────┐
│  L3 内容质量闸门 (中段终审)          │
└──────────────────────────────────────┘
    │
    ├─[论证链 < 90%]──→ insight-synthesizer (max 1)
    ├─[Resonance < 3.5]──→ longform-writer (max 1)
    ├─[CoV 引用/URL/交叉 不达标]──→ source-manager (max 1)
    │      └──→ 任一仍 fail → 标记放行 + 评分 -0.5
    │
    ▼ (pass)
┌──────────────────────────────────────┐
│  L4 活人感闸门 (最末)                │
└──────────────────────────────────────┘
    │
    ├─[软违规]──→ Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")
    │      └──→ 复检仍 fail → 标记放行 + 评分 -0.3
    ├─[硬违规 max 1]──→ writer 局部重写
    │      └──→ 仍 fail → 标记放行 + 评分 -0.5
    │
    ▼ (pass / 已放行)
┌──────────────────────────────────────┐
│  neat-freak 闸门 (与 L4 并行)        │
└──────────────────────────────────────┘
    │
    ├─[膨胀比 > 5.0]──→ writer 精简 (max 1)
    ├─[单章 > 35%]──→ writer 精简 (max 1)
    │      └──→ 仍 fail → 标记放行 + 评分 -0.3
    │
    ▼
┌──────────────────────────────────────┐
│  综合评分 ≥ 4.0 准入                 │
└──────────────────────────────────────┘
    │
    ├─[< 4.0]──→ writer 全文修订 (max 1)
    │      └──→ 仍 fail → 强制放行 + 标记 "需人工复审"
    │
    ▼ (pass / 已放行)
┌──────────────────────────────────────┐
│  Stage 6.5 obsidian-md-ac 美化       │
└──────────────────────────────────────┘
    │
    ▼
[最终输出 战略洞察-*.md]
```

---

## 8. 综合评分（保留原 9 维加权 + 闸门扣分）

| 维度 | 权重 | 分数来源 |
|---|---|---|
| 结构完整性 | 15% | L1 YAML + 章节数量符合复杂度 |
| 三轴/双轴覆盖 | 15% | framework-builder verdict |
| 洞察价值 | 25% | L3 HKR Resonance |
| 数据支撑 | 15% | L3 CoV 综合分 |
| 文风质量 | 15% | L2 综合分 |
| 知识集成与关联 | 15% | wikilinks 有效率 + qmd 引用数 |
| **基础总分** | — | 加权求和 |
| 闸门扣分 | — | L1 放行 -0.5 / L3 放行 -0.5 / L4 放行 -0.3 / NeatFreak 放行 -0.3 / 综合放行 -1.0 |
| **最终总分** | — | 基础总分 - 闸门扣分 |

### 发布标准

| 最终总分 | 建议 |
|---|---|
| 4.5-5.0 | 优秀，可直接发布 |
| 4.0-4.4 | 良好，可发布 |
| 3.5-3.9 | 合格，建议小修后发布 |
| 3.0-3.4 | 需较大修改 |
| < 3.0 | 需重写 |

---

## 9. 保留自原 checklist 的有用条目（结构 / 三轴 / 内容 / 数据 / 逻辑 / Wikilinks）

> 不再是人工 ✅/❌，全部融入上方各 Gate 的 subscores。下表仅作"指标到 Gate 的反查表"。

| 原 checklist 条目 | 归属 Gate | 自动化指标 |
|---|---|---|
| 全息摘要 200 字内、有三轴融合 | L1（字数） + L3（论证链）| `len(abstract)` + `triaxial_keywords_count` |
| 章节标题观点化 | L2 | `headline_assertion_ratio` |
| 三轴覆盖（空间/时间/领域）| L3 论证链 | `axis_coverage_rate` |
| 章节有论点+论据+推论 | L3 论证链 | `argument_chain_coverage` |
| 核心问题覆盖 ≥ 80% | L3 | `key_question_coverage` |
| 数据有来源标注 | L3 CoV Layer 1 | `cov_citation_completeness` |
| 多源验证 | L3 CoV Layer 3 | `cov_cross_verification` |
| 二阶 / 三阶推论 | L3 论证链 | `second_order_count` / `third_order_count` |
| S×T / S×D / T×D 交叉洞察 | L3 论证链 | `cross_dim_insight_count` |
| Wikilinks 有效性 | L3 | `wikilink_validity_rate` |
| Wikilinks 自然嵌入 | L2 | `wikilink_naturalness_score` |
| AI 幻觉防范 | L3 CoV | `cov_url_reachability` + `cov_cross_verification` |
| 长句不超过 50 字 | L2 | `long_sentence_para_count` |
| 形容词过度使用 | L4 | `ai_word_density`（含修辞词）|
| 无口语残留 | L1 | 黑名单含口语词 |
| 政治敏感避免 | Red Flag 8 | 敏感词扫描 |

---

> **提醒**：本文档是 Leader 与所有 agent 共享的"API 契约"。任何 agent 输出 verdict 时必须严格遵守 Schema；任何指标阈值调整必须同步更新本文档 + config.json 的 `quality_gates` 节。
