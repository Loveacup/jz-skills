# Academic Lane Policy

Full academic search policy. Loaded on-demand from SKILL.md `references/academic-lane.md`.

Use the academic lane as a knowledge-graph layer, not as a normal web-search replacement.

## Backend Responsibilities

- **arXiv:** fastest free discovery for AI/ML/CS/math/physics preprints; preserves arXiv IDs and version suffixes.
- **Semantic Scholar:** citation counts, influential citations, references, recommendations, author profiles. Treat counts as approximate and time-sensitive.
- **OpenAlex:** open scholarly graph for works, authors, institutions, concepts, venues, DOI-normalized metadata.
- **Crossref:** DOI and publisher metadata cleanup; useful for formal citations but weaker for discovery.
- **PubMed:** biomedical and clinical literature; prefer for medicine over arXiv/general web.
- **Papers with Code:** benchmark/code/dataset linkage; use after identifying canonical papers.
- **GitHub/Hugging Face/project pages:** implementation and adoption evidence; label third-party implementations clearly.

## Default Academic Workflow

1. **Clarify the target implicitly:** latest papers, seminal works, citation genealogy, implementation assets, or a review brief.
2. **Discover candidates:** arXiv for preprints; Semantic Scholar/OpenAlex/PubMed for broader coverage.
3. **Normalize identities:** keep arXiv ID, DOI, Semantic Scholar ID, title, first author, year, and version read.
4. **Assess signal:** venue/source, citation count, influential citations, author/institution, recency, benchmark relevance.
5. **Read selectively:** fetch abstracts first; full PDFs only for high-signal papers or when claims depend on details.
6. **Trace graph:** references for prerequisites; citations/recommendations for descendants and neighboring work.
7. **Map implementation:** project page, official code, Papers with Code, GitHub, Hugging Face, datasets, benchmarks.
8. **Report gaps:** missing full text, no official code, unclear venue, stale citation counts, conflicting claims.

## Academic Output Shapes

For quick Telegram answers: 结论 → 论文地图 (3–8 papers grouped by role) → 关键谱系 → 可复现资产 → 缺口.

For serious briefs: Problem definition → Method families → Seminal papers → Recent/SOTA → Surveys/tutorials → Benchmarks/datasets → Code/model availability → Open questions.

## Academic Verification Rules

- Do not call a paper "peer-reviewed" just because it is on arXiv.
- Preserve arXiv version if the specific PDF/version was read.
- Treat citation counts as approximate unless fetched live from Semantic Scholar/OpenAlex.
- Separate official code from third-party reproductions.
- For biomedical/clinical claims, prefer systematic reviews, RCTs, PubMed/journal sources, and label study type.
- For "first paper" or "SOTA" claims, require cross-checking.

## arXiv Rate Limiting

arXiv's public API enforces ~1 req / 3 seconds. If rate-limited (HTTP 429), do NOT retry immediately — wait 5+ seconds, or fall back to Semantic Scholar. Proven fallback chain: Semantic Scholar paper search → Exa for project/code pages → cross-check with Semantic Scholar citations.
