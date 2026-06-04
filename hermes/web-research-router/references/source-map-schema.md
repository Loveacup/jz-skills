# Source Map Schema

> **Read when:** 输出正式报告 / 调用方需要程序化处理 source map / 走 deep-research loop。
> Telegram 输出仍保持人读，不强制 JSON。

Use this shape internally or in serious reports. Keep Telegram output human-readable; do not force JSON unless requested.

```json
{
  "mode": "discovery|grounding|research|recovery|academic|deep",
  "query": "user-facing research question",
  "sources": [
    {
      "citation_id": "stable, citation-ready short id (e.g., 's1', 's2'); used in inline citations and survives merge across deep-loop sections",
      "title": "Source title or paper title",
      "url": "https://example.com",
      "domain": "example.com",
      "provider": "searxng|exa|tavily|brave|local|github|arxiv|semantic-scholar|openalex|crossref|pubmed|papers-with-code|other",
      "source_tier": "primary|official|original-report|paper|preprint|peer-reviewed|expert-analysis|news|secondary|unknown",
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
- **`evidence_status` 新增 `extracted`** —— 比 `fetched` 进一步：已跑过 extractor、拿到 verbatim quote。
  排序：`searched` < `fetched` < `extracted` < `verified`（多源交叉过）；`conflicted` 与上述维度正交。

## 与 inline citation 的衔接

最终综合答案中：
- ✅ "Hermes A2A 默认端口为 8945 [s3]." —— `s3` 即 `citation_id`
- ❌ "据 https://example.com 报道..." —— 不应裸写 URL；URL 在 source map 里查
- ✅ confirmed[i].citation_ids 全部能映回 sources 中存在的 `citation_id`，否则报错"dangling citation"
