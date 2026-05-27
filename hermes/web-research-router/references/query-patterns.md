# Query Patterns

Common search query patterns. Loaded on-demand from SKILL.md.

## Current factual lookup

Primary: Tavily. Cross-check with Brave if important.

```
<entity/topic> latest official announcement pricing release date 2026
```

Output: concise answer + citations + uncertainty if sources disagree.

## Semantic source discovery

Primary: Exa.

```
high signal sources about <topic> official docs reports practitioner analysis 2026
```

Output: source map, not a raw result dump.

## Company / market scan

Primary: Exa; Brave for coverage; Tavily extract for selected pages.

```
<company/category> competitors pricing product positioning enterprise adoption 2026 official pages
```

Prefer official sites, docs, pricing, changelogs, investor materials, credible interviews.

## Technical docs / API lookup

Primary: Exa for discovery; fetch official docs. Use CodeGraph first for local repo behavior.

```
<language/framework/package version> <API/error> official docs examples issue
```

## Academic paper / literature lookup

Primary: arXiv for fresh CS/AI/ML/math/physics preprints; Semantic Scholar for citations.

```
<topic/method> recent papers survey related work SOTA citations code benchmark 2024 2025 2026
```

Output: paper map grouped by role: seminal / survey / SOTA / implementation / critique.

## Citation and research genealogy

Primary: Semantic Scholar; supplement with OpenAlex/Crossref for metadata.

```
paper: <arxiv_id|doi|title> citations references influential citations related papers
```

Output: predecessor works, descendant works, citation count, influential citation count.

## Paper-to-code / reproducibility lookup

Primary: Papers with Code, GitHub, Hugging Face, project pages.

```
<title or arxiv_id> code github project page benchmark dataset huggingface
```

Output: canonical code URL, third-party implementations labeled, datasets/models/benchmarks.

## Biomedical literature

Primary: PubMed, then Semantic Scholar/OpenAlex, then journal/PMC/full text.

```
<condition/intervention/biomarker> systematic review randomized trial PubMed 2024 2025 2026
```

Output: publication type, human/animal/in-vitro distinction, journal/source, clinical caveats.

## Website structure / docs crawl

Primary: Tavily map/crawl.

Use when the task is "what pages exist under this docs/site/pricing area?" or when a single page is insufficient.
