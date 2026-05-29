# Academic Search / Research MCP GitHub References

Session-derived source map for adding an academic-search lane to Hermes research routing. Use as a starting point for future implementation/design work; re-check GitHub freshness before installing anything.

**Status as of 2026-05-26:** The Academic Lane routing layer is fully implemented in `web-research-router` v2, deployed to all 16 profiles, and tested end-to-end (arXiv→Semantic Scholar→Exa, GRPO test case). The GitHub MCP projects below remain as reference for future tool-layer decisions; none are installed. Current academic backend: arXiv API + Semantic Scholar API (direct curl, no MCP wrappers). Next priority for tool-layer: Semantic Scholar API → OpenAlex API → PubMed API, in that order.

## Recommended architecture lesson

Do **not** treat academic search as just another ordinary web engine. Model it as an Academic Lane that composes specialized sources:

- `arXiv`: fresh CS/AI/ML/math preprints and versioned PDFs.
- `Semantic Scholar`: citation graph, references, influential citations, recommendations, author profiles.
- `OpenAlex`: DOI/venue/institution metadata, broad bibliometrics, trends, collaboration networks.
- `PubMed/Europe PMC`: biomedical literature with MeSH/PICO/full-text conventions; keep as a biomedical sub-lane.
- `Zotero`: downstream library/archive layer, not the first discovery layer.
- Exa/Brave/Tavily: project pages, GitHub implementations, author blogs, conference pages, and mainstream/current cross-checking.

## High-signal projects found

### arXiv

- `blazickjp/arxiv-mcp-server` — https://github.com/blazickjp/arxiv-mcp-server
  - Mature arXiv-focused MCP server; search result showed ~2.7k stars.
  - Useful reference for arXiv MCP tool design, paper metadata schema, and paper download/cache behavior.

- `takashiishida/arxiv-latex-mcp` — https://github.com/takashiishida/arxiv-latex-mcp
  - Focuses on arXiv LaTeX sources for precise math/scientific interpretation.
  - Useful when PDF text extraction loses formulas.

### Semantic Scholar

- `zongmin-yu/semantic-scholar-fastmcp-mcp-server` — https://github.com/zongmin-yu/semantic-scholar-fastmcp-mcp-server
  - FastMCP server for Semantic Scholar API.
  - Reference for paper search, author info, citation networks, references, and related papers.

- `JackKuo666/semanticscholar-MCP-Server` — https://github.com/JackKuo666/semanticscholar-MCP-Server
  - Simpler Semantic Scholar MCP wrapper; useful for baseline tool shape.

### Multi-source academic search

- `Dianel555/paper-search-mcp-nodejs` — https://github.com/Dianel555/paper-search-mcp-nodejs
  - Node/TypeScript multi-source MCP: arXiv, PubMed, Google Scholar, bioRxiv, medRxiv, Semantic Scholar, IACR, Crossref, Web of Science, Scopus, etc.
  - Good for unified paper model ideas; avoid copying the “support everything shallowly” pattern without source-quality policy.

- `alisoroushmd/academic-research-mcp` — https://github.com/alisoroushmd/academic-research-mcp
  - Exa result described unified tools across OpenAlex, Semantic Scholar, Crossref, PubMed, arXiv, medRxiv/bioRxiv, Google Scholar, ORCID, Unpaywall.
  - Useful reference for systematic-review/PRISMA workflow support and source routing.

- `upascal/paper-search-mcp` — https://github.com/upascal/paper-search-mcp
  - Cloudflare Workers-oriented academic paper search MCP with Semantic Scholar, Crossref, OpenAlex, arXiv, PubMed, bioRxiv/medRxiv.
  - Exa result highlighted RRF fusion, date filtering, citation thresholds, and daily digests.

- `ICBME/paper-search-mcp` — https://github.com/ICBME/paper-search-mcp
  - Multi-source Python MCP with unified search/download, DOI extraction, deduplication, and download fallback.

### OpenAlex

- `oksure/openalex-research-mcp` — https://github.com/oksure/openalex-research-mcp
  - OpenAlex MCP for works, citations, trends, collaboration networks.

- `drAbreu/alex-mcp` — https://github.com/drAbreu/alex-mcp
  - Simple OpenAlex MCP server; useful for lean implementation reference.

- `benedict2310/Scientific-Papers-MCP` — https://github.com/benedict2310/Scientific-Papers-MCP
  - arXiv + OpenAlex MCP; useful for lightweight two-source composition.

### PubMed / biomedical lane

- `cyanheads/pubmed-mcp-server` — https://github.com/cyanheads/pubmed-mcp-server
  - PubMed/Europe PMC, full text, citations, MeSH terms, Unpaywall.

- `andybrandt/mcp-simple-pubmed` — https://github.com/andybrandt/mcp-simple-pubmed
  - Simple PubMed MCP server; useful for minimal wrapper reference.

- `u9401066/pubmed-search-mcp` — https://github.com/u9401066/pubmed-search-mcp
  - Professional biomedical literature MCP with PubMed, Europe PMC, CORE, OpenAlex, Semantic Scholar, NIH iCite, MeSH expansion, PICO analysis.
  - Keep this class separate from generic academic search because biomedical search has domain-specific evidence and vocabulary rules.

### Zotero / library layer

- `kujenga/zotero-mcp` — https://github.com/kujenga/zotero-mcp
  - Zotero API MCP server.

- `TonybotNi/ZotLink` — https://github.com/TonybotNi/ZotLink
  - Saves open preprints into Zotero with rich metadata and PDF attachments.

- `PiaoyangGuohai1/cli-anything-zotero` — https://github.com/PiaoyangGuohai1/cli-anything-zotero
  - CLI/MCP-like Zotero operations: search, import, PDF, BibTeX, notes.

### Workflow / skill inspiration

- `Imbad0202/academic-research-skills` — https://github.com/Imbad0202/academic-research-skills
  - Claude Code skill suite for research → write → review → revise → finalize.
  - Useful design inspiration for Material Passport, claim verification, academic pipeline orchestration, peer-review agents, and not reducing academic work to search alone.

## Implementation guidance for Hermes

Suggested phased path:

1. Patch `web-research-router` with an `academic` lane.
2. Strengthen the existing `arxiv` skill into a broader `academic-search` workflow before installing many MCP servers.
3. Use arXiv + Semantic Scholar API directly for v1; add OpenAlex for metadata/venue/institution normalization.
4. Treat PubMed/biomedical as a separate sub-lane.
5. Add Zotero only when the user wants persistent paper-library management or citation export.

Academic source map fields worth adding:

- `paper_id`
- `arxiv_id`
- `doi`
- `venue`
- `year`
- `citation_count`
- `influential_citation_count`
- `open_access_pdf`
- `code_url`
- `dataset_url`
- `method_family`
- `evidence_role`: `seminal | survey | sota | replication | critique`
