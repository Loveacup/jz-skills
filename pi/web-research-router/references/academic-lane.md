# Academic Lane (Full Reference)

> Load when academic mode is triggered and you need detailed routing and verification rules.

## When to Use Academic Lane
- Paper discovery, literature review, citation genealogy
- SOTA scanning, "who did what after this method"
- Author publication history, paper-to-code/data assets
- Method comparison, field mapping

## Routing Strategy

Pi has no direct arXiv/Semantic Scholar API. Uses Exa semantic search + Brave supplement:

| 需求 | 路径 |
|------|------|
| Paper discovery, literature search | Exa (neural search works well for academic) |
| Code/project page | Brave search GitHub / project page |
| Citation/influence signal | Exa search result citation info (if available) |
| Official paper page | fetch arXiv.org / proceedings |

**Search tips:**
- Exa query: include paper title, author, method name, arXiv ID
- Brave supplement: `{paper_title} github` or `{method} implementation`

## Paper Classification

- **Seminal**: Introduced or popularized the method or problem
- **Survey**: Maps the field, not necessarily original contribution
- **SOTA**: Current leaderboard or frontier claim
- **Implementation asset**: Code, data, model checkpoint
- **Critique/negative result**: Failure modes, limitations, benchmark disputes

## Verification Rules

- ❌ Don't call arXiv preprints "peer-reviewed"
- ❌ Don't blindly trust citation counts (vary across sources; signal only)
- ❌ Don't confuse preprints with formal publications
- ✅ Distinguish official code from third-party reproductions
- ✅ "First"/"SOTA" claims must be cross-validated (min 2 independent sources)
- ✅ Note publication year and venue
- ✅ If multiple versions, state which version was read
