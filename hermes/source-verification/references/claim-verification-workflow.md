# Claim 核验工作流 v1.0

> **Read when:** source-verification Step 1–4 执行时。本文档定义 claim 怎么抽、两路证据怎么取、置信度怎么判、结果怎么落盘。
> **依赖:** web-research-router v3.9（路 B 外部核验经它取数）。

---

## 0. 核心原则

- **只核高风险 claim**：价格/数字、政策/法规、排名/序数、具名声明。叙述句、推理句、过渡句**不进队列**。
- **外部核验必须换源**：路 B 不复用草稿原始 URL，否则等于自证（同一篇错稿核不出错）。
- **唯一硬阻塞是 contradicted**：not found 软标注保留，不删、不阻塞。

---

## 1. Step 1 — Claim 抽取

从草稿正文逐段扫描，命中以下任一模式即入队（按风险排序，取 top-≤10）：

| 类型 | 识别模式 | 例 |
|---|---|---|
| 价格/数字 | 货币符号 / `%` / 涨跌幅 / 单位量词 | `$78.3/桶`、`GDP 增长 5.2%`、`市值 3.1 万亿` |
| 政策/法规 | 「X 部」「自…起施行」「税率」「禁令」「新规」 | `央行 6 月起降准 0.5 个百分点` |
| 排名/序数 | 「第一」「最大」「首次」「史上」「唯一」 | `全球最大单笔融资` |
| 具名声明 | 「X 表示/宣布/称」+ 主体 | `OpenAI 宣布 GPT-X 发布` |

产出：

```json
{
  "id": "c01",
  "text": "国际油价 Brent 收于 $78.3/桶,日内 +1.2%",
  "type": "price",
  "citation_id": "mixed-003",
  "char_offset": 1820
}
```

> 抽样上限 ≤10 条/版。叙述层（"市场情绪谨慎""分析人士认为")**不抽**——那是推理层，归 de-slop / analysis-format 管，不归核验。

---

## 2. Step 2 — 两路证据取证

每条 claim 同时跑两路：

### 路 A — 内部比对（回 source_map）

```
1. 用 claim.citation_id 定位 source_map 里对应 article
2. 在 article.extracted_quotes[] 找直接支撑的 verbatim quote
3. 命中 → 记 evidence.internal = {quote_text, char_offset}
   未命中 → evidence.internal = null（不代表假,等路 B）
```

### 路 B — 外部二次核验（仅价格/数据/政策类）

```
1. 构造 grounding query（换源,不复用原 URL）：
   价格   → "Brent crude price {date}"          → Tavily grounding
   政策   → "{政策关键词} 官方 {date}"            → Brave 双源（官媒 vs 通讯社）
   数据   → "{实体} {指标} {date}"               → Exa 语义 + Tavily 交叉
2. 取 web 返回的对应数值/表述
3. 记 evidence.external = {source, value, url}
```

> 具名声明类（"X 宣布 Y"）只走路 A + 路 B 的存在性核验（该声明是否真出现在权威源），不做数值比对。

---

## 3. Step 3 — 置信度判定

```
路 A 命中 verbatim quote 直接支撑
  └─ 且（无路 B 或 路 B 数字 ±2% 内一致）       → verified
路 A 间接支撑 / 口径不同（约、左右、单位/时点差） → partial
路 B 与草稿数字超 ±2% 冲突 / 两源互斥           → contradicted
路 A null 且 路 B 查无支撑                       → not found
```

**±2% 容差**（价格/比率类）：

```
|web_value - draft_value| / web_value ≤ 0.02  → verified
否则                                          → contradicted（取中位值 + 标"数据冲突"）
```

---

## 4. Step 4 — 门禁动作 + 落盘

| label | action |
|---|---|
| verified | `pass` |
| partial | `annotate:📎部分验证` |
| contradicted | `delete + reassemble`（hard 阻塞，回退重写该段） |
| not found | `annotate:⚠️未验证`（保留，不阻塞） |

落盘 `verification-{date}.json`：

```json
{
  "date": "{date}",
  "draft": "morning-news-{date}.md",
  "degraded": false,
  "claims": [
    {
      "id": "c01",
      "type": "price",
      "label": "verified",
      "evidence": {
        "internal": {"quote_text": "Brent settled at $78.3", "char_offset": 1820},
        "external": {"source": "Tavily", "value": "78.31", "url": "..."}
      },
      "action": "pass"
    }
  ],
  "summary": {"verified": 6, "partial": 2, "contradicted": 0, "not_found": 1},
  "gate": "pass"
}
```

> `gate`: `pass`（无 contradicted）/ `block`（有 contradicted 待回退重写后复核）。

---

## 5. 降级矩阵

| 故障 | 降级 | 标记 |
|---|---|---|
| source_map 损坏/缺失 | 仅路 B（纯 web 核验） | `degraded: true` + `verification-degraded` |
| web_search 全超时 | 仅路 A（内部比对）；无外部交叉的 claim 降 partial | `verification-internal-only` |
| 单条 claim web 查无 | 该条标 not found，不影响其它 | — |
| 全 claim not found | 不阻塞，日志 `WARN: zero-verified` | — |
| 抽不出高风险 claim | 跳过核验，通过 | `no-verifiable-claims` |

---

## 6. 常见错误

- ❌ 全篇逐句核（应只核高风险 claim，≤10 条/版）
- ❌ 路 B 复用草稿原 URL 自证（必须换源交叉）
- ❌ contradicted 软标注留着（必须删 + 回退重写）
- ❌ not found 当假删掉（误伤推理层；应软标注保留）
- ❌ source_map 损坏就整体跳过（应降级走路 B）
- ❌ 价格类无容差死判（应 ±2% 容差，超了才 contradicted）
