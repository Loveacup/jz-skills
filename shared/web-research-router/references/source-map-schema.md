# Source Map Schema

Use this shape internally or in serious reports. Keep Telegram output human-readable; do not force JSON unless requested.

```json
{
  "mode": "discovery|grounding|research|recovery|academic",
  "query": "user-facing research question",
  "sources": [
    {
      "title": "Source title or paper title",
      "url": "https://example.com",
      "domain": "example.com",
      "provider": "exa|tavily|brave|local|github|arxiv|semantic-scholar|openalex|crossref|pubmed|papers-with-code|other",
      "source_tier": "primary|official|original-report|paper|preprint|peer-reviewed|expert-analysis|news|secondary|unknown",
      "claim_supported": "What this source supports",
      "evidence_status": "searched|fetched|read|verified|conflicted",
      "confidence": "high|medium|low",
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
  "confirmed": ["facts directly backed by read/fetched sources"],
  "inferences": ["judgment calls based on multiple sources"],
  "conflicts_or_gaps": ["missing primary source, stale source, source disagreement"]
}
```
