# Source Map Schema & Dedup Rules

## Source Map Template

Output for every research task. Mandatory, not optional.

```
## Source Map

**Mode:** (discovery|grounding|research|recovery|academic)
**Query:** (user-facing research question)

| # | Title | URL | Provider | Tier | Evidence | Confidence |
|---|-------|-----|----------|------|----------|------------|
| 1 | ... | ... | exa/tavily/brave | primary/official/paper/preprint/expert/news | searched/fetched/read/verified | high/medium/low |

**For GitHub mode:** Use permalinks in URL column.

**For Academic mode, add:** Year, Venue, Evidence Role, Code URL

**Confirmed:** Facts directly backed by read/fetched sources
**Inferences:** Judgment calls based on multiple sources
**Conflicts & Gaps:** Missing primary source, stale source, contradictions

**Dedup:** Exa N | Tavily N | Brave N → unique N | overlap N
```

## Dedup Rules

1. Merge same-URL hits across engines, label `providers: ["exa", "brave"]`
2. URL normalization: strip `utm_*`, `?ref=*`, `#fragment`
3. `www.example.com/a` = `example.com/a`
4. Multi-engine hit ≠ verified, but means source is discoverable
5. Output stats: per-engine count, unique count, overlap count
