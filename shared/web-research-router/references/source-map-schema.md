# Source Map Schema

> **Read when:** 输出正式报告 / 调用方需要程序化处理 source map / 走 deep-research loop。
> Telegram 输出仍保持人读，不强制 JSON。

Use this shape internally or in serious reports. Keep Telegram output human-readable; do not force JSON unless requested.

```json
{
  "mode": "discovery|grounding|research|recovery|academic|platform|deep",
  "query": "user-facing research question",
  "sources": [
    {
      "citation_id": "stable, citation-ready short id (e.g., 's1', 's2'); used in inline citations and survives merge across deep-loop sections",
      "title": "Source title or paper title",
      "url": "https://example.com",
      "domain": "example.com",
      "provider": "searxng|exa|tavily|brave|local|github|arxiv|semantic-scholar|openalex|crossref|pubmed|papers-with-code|agent-reach|other",
      "platform": "optional, platform-mode only: twitter|reddit|bilibili|xiaohongshu|youtube|v2ex|xueqiu|xiaoyuzhou|rss|null",
      "source_tier": "primary|official|original-report|paper|preprint|peer-reviewed|expert-analysis|news|social|secondary|unknown",
      "claim_supported": "What this source supports",
      "evidence_status": "searched|fetched|read|extracted|verified|conflicted",
      "confidence": "high|medium|low",
      "extracted_quotes": [
        {
          "text": "verbatim quote from the page (copied exactly — numbers, names, dates unchanged)",
          "focus": "the sub-query / focus string used when extracting",
          "char_offset": "optional offset in fetched markdown, integer or null"
        }
      ],
      "paper_id": "optional stable ID such as Semantic Scholar paperId",
      "arxiv_id": "optional arXiv ID",
      "doi": "optional DOI",
      "venue": "optional journal/conference/workshop/preprint server",
      "year": "optional publication year",
      "citation_count": "optional integer or null",
      "influential_citation_count": "optional integer or null",
      "open_access_pdf": "optional PDF URL",
      "code_url": "optional canonical or third-party code URL",
      "dataset_url": "optional dataset URL",
      "method_family": "optional method/topic family",
      "evidence_role": "seminal|survey|sota|replication|implementation|critique|background|unknown",
      "notes": "caveats, dates, conflicts, or why selected"
    }
  ],
  "confirmed": [
    {
      "claim": "fact directly backed by extracted quotes",
      "citation_ids": ["s1", "s3"]
    }
  ],
  "inferences": [
    {
      "claim": "judgment call based on multiple sources",
      "citation_ids": ["s2", "s4"],
      "reasoning": "why this inference follows from those quotes"
    }
  ],
  "conflicts_or_gaps": ["missing primary source, stale source, source disagreement"],
  "budget": {
    "breadth": 4,
    "depth": 2,
    "max_iter": 8,
    "iter_used": 0,
    "token_budget": 30000,
    "token_used": 0,
    "stop_reason": "reviewer_none|all_pass|max_iter|token_exhausted|no_progress|n/a"
  }
}
```

## 字段说明

- **`citation_id`** —— 短而稳定的引用 ID（`s1` / `s2` …）。在 deep-loop 的 section research 阶段
  各 section 内本地编号；merge 阶段统一 renumber，但保留 provenance 关系（哪个 section 原产）。
  调用方在 confirmed / inferences / 综合答案的 inline citation 中只用 `citation_id` 引用，不复述 URL。
- **`extracted_quotes`** —— 来自 `fetch-extract-pattern.md` 的 verbatim quote 数组。
  `focus` 字段记录抽取时用的 sub-query，便于追溯"为什么这条 quote 入选"。
  没跑 extractor / extractor 返 `NOT RELEVANT` → 该 source 的此字段为 `[]`，
  对应 `evidence_status` 不应升到 `extracted`。
- **`budget`** —— deep-loop 的预算账本（参考 `deep-research-loop.md`）。
  非 deep mode 时 `budget` 字段可省略；deep mode 必填。
  `stop_reason` 必填，告诉 caller 为什么停（`reviewer_none` = LLM 自评够了；
  `max_iter` / `token_exhausted` = 强制停；`no_progress` = 连续 2 轮无新 quote）。
- **`provider` 保留 `searxng`** —— 命中自 SearXNG 兜底通道的结果在 provider 字段标 `searxng`（v3.9：SearXNG 仅作最后兜底，非默认起手）。
  原本由 SearXNG 命中、但 fetch 阶段又被 Exa fetch 抓的 source 标 `searxng` + `notes: fetched via exa`。
- **`provider: agent-reach` + `platform` + `source_tier: social`（v3.10 platform mode）** —— 经 platform mode 通过 Agent-Reach CLI 取得的社交/视频/论坛/RSS 信源：
  `provider` 标 `agent-reach`，`platform` 标具体平台（`twitter`/`reddit`/`bilibili`/`xiaohongshu`/`youtube`/`v2ex`/`xueqiu`/`xiaoyuzhou`/`rss`），`source_tier` 标 **`social`**（UGC/社交信源，区别于 primary/official/news）。
  社交单方说法 / 高赞推文默认 `confidence: low|medium`，仅当多平台一致或经 Exa/Brave 公网 cross-check 才升 `high` 并把 `evidence_status` 提到 `verified`。
  互动数据（点赞/回复/播放）写 `notes`，是代表性信号不是事实。详见 `references/platform-mode.md`。
- **`evidence_status` 新增 `extracted`** —— 比 `fetched` 进一步：已跑过 extractor、拿到 verbatim quote。
  排序：`searched` < `fetched` < `extracted` < `verified`（多源交叉过）；`conflicted` 与上述维度正交。

## 与 inline citation 的衔接

最终综合答案中：
- ✅ "Hermes A2A 默认端口为 8945 [s3]." —— `s3` 即 `citation_id`
- ❌ "据 https://example.com 报道..." —— 不应裸写 URL；URL 在 source map 里查
- ✅ confirmed[i].citation_ids 全部能映回 sources 中存在的 `citation_id`，否则报错"dangling citation"

---

## SOURCE_QUALITY —— `source_tier` → quality_weight（v3.11 新增）

> **Read when:** 多源融合排序需要权重（喂 `dedup_rrf.py --weights`）；或同一 claim 多源不一致需要 tie-break。
> **来源:** last30days `signals.py` 的 editorial SNR 常量（Reddit 0.6 / HN 0.8 / X 0.68 / Polymarket 0.5）——但 WRR 是 **authority-first**，故把它**换形**成「按 `source_tier` 的权威度权重」，而非按平台 engagement 打分。

WRR 不做连续分层评分（last30days 那套），但需要一张**确定性的权威度权重表**作为 RRF 融合权重与 tie-break 依据。下表是 `source_tier` 枚举 → `quality_weight ∈ [0,1]` 的单一映射：

| `source_tier` | quality_weight | 说明 |
|---|:--:|---|
| `primary` / `official` | 1.00 | 一手 / 官方（changelog、官网公告、招股书、API 一手数字） |
| `original-report` / `peer-reviewed` | 0.95 | 原始调查报告 / 同行评审 |
| `paper` | 0.90 | 正式论文 |
| `preprint` | 0.80 | 预印本（未评审） |
| `expert-analysis` | 0.78 | 署名专家深度分析 |
| `news` | 0.70 | 权威媒体报道（二手但有编辑把关） |
| `secondary` | 0.60 | 一般二手聚合 / 转述 |
| `social` | 0.50 | 社交 / UGC（platform mode 信源，恒为此档上限） |
| `unknown` | 0.40 | 来源不明 |

### 🛑 红线（与 CQI §14.6 一致）：weight 不抬 tier

- **`social` 档的 weight 永远 ≤ 非 social 档**——一条 5 万赞但断言错误的推文，`quality_weight` 仍是 0.50，**不得**因 engagement 高而越过官方 changelog（1.00）。
- engagement（点赞/回复/播放/赔率）**只在 `social` 档内部**做次级排序，写进 `notes`，**绝不**抬升 `source_tier`，**绝不**单独把 weight 推过 0.50。
- 平台级 social 次权重（仅在 `source_tier: social` 内部细分代表性，参考 last30days editorial SNR）：HN 0.80 · X/Twitter 0.68 · Reddit 0.60 · Polymarket 0.50——**这些只调 social 档内的相对顺序，封顶仍受 0.50 约束**。

### 用法

1. **RRF 融合**：把 `quality_weight` 作为 per-provider/per-source 权重传给 `dedup_rrf.py --weights`（见该脚本 `--weights` 说明），`score = weight / (k + rank)`。
2. **tie-break**：两条 claim 冲突且 rank 接近时，`quality_weight` 高者优先进 Confirmed，低者降级到 Inference / Conflicts。
3. **与 intent 权重叠加**：本表是「源权威度」基线；mode/intent 的「时效/语义」偏好（SKILL.md Step 2 intent 权重）作为乘子叠加——`final_weight = quality_weight × intent_multiplier`。

> 🔧 **wrr-core 收口**：本表是 prompt/doc 层 spec。wrr-core 阶段 1 将其迁入 `constants.json`（§3.5 单一真源第 2 条），由 `route()` 在融合前注入 `--weights`；迁移 ≠ 推翻——表值与红线不变，仅改存放位置。
