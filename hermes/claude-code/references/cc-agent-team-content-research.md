# CC Agent Team for Content Research Briefings

> **When to read:** delegate_task or Kanban orchestration is blocked (kanban gate, profile isolation), and the task is a multi-lane parallel research → assembly workflow (e.g., morning news briefing, market research, competitive analysis).

## When to use this pattern

- `delegate_task` returns kanban_gate / permission denied
- The task requires 3+ parallel lanes of independent web research
- Each lane has distinct search queries and source requirements
- Output is a structured document (markdown briefing, report, analysis)

## Workflow

```
Phase 1: Prep (Hermes parent agent)
  ├── Create workspace directory with .gitignore
  ├── Write context file (context-for-cc.md) with:
  │   ├── Full task spec (sections, source counts, format rules)
  │   ├── Worker timeout rule (10min per worker)
  │   ├── Explicit extractor instructions (verbatim quotes, fetch URL)
  │   └── Output paths
  └── Launch CC tmux session + send task

Phase 2: Search (CC agent team, 3+ workers)
  ├── Worker A: Lane 1 search → write lane-a.json
  ├── Worker B: Lane 2 search → write lane-b.json
  └── Worker C: Lane 3 search → write lane-c.json
  Monitor: capture-pane every 60s, watch token counts

Phase 3: Assembly (CC Leader)
  ├── Read all lane JSON files
  ├── Deduplicate, structure, write analysis
  └── Output: final markdown briefing

Phase 4: Render (Hermes parent or CC print mode)
  └── CC print mode: markdown → HTML template → Playwright PDF
      claude -p 'Convert markdown to PDF using template' --max-turns 15

Phase 5: Deliver
  └── MEDIA: path to PDF
```

## Known Limitations

### 1. Verbatim quote extraction is unreliable
CC workers are good at finding sources and metadata (titles, URLs, dates) but tend to skip the `fetch → extract verbatim quote` step. The JSON output often has empty `verbatim_quotes` or `content` fields.

**Mitigation:** In the context file, write explicit extractor instructions:
```
Each source item MUST have:
- verbatim_quotes: array of 2-3 exact quotes from the fetched page
- Use web_extract or web_fetch to get full page content
- DO NOT summarize — copy exact sentences
```

If quotes are still missing, the parent agent supplements by doing direct MCP searches for key articles.

### 2. Worker stalls are common
See `references/worker-true-stall-no-disk-output.md`. ~30% chance a worker stalls at 60-80k tokens without writing output.

**Mitigation:** Timeout rule in context file + parent agent ready to fill gaps.

### 3. CC has no Hermes MCP tools
CC uses its own web_search/web_fetch, NOT `mcp_searxng_searxng_web_search`. Search coverage is narrower. For tasks requiring SearXNG multi-engine aggregation, the parent agent should run key searches itself as a supplement.

## Real-world case: morning-news-briefing 2026-05-28

- Task: Daily news briefing with 3 lanes (China 18 sources, Intl, Market 11 sources)
- delegate_task blocked by kanban gate
- CC agent team: 3 workers + Leader
- Lane A (China): ✅ 18 sources, 13KB JSON
- Lane B (Intl): ❌ Stalled at 65.1k tokens, no disk output → killed session
- Lane C (Market): ✅ 11 sources, 7.3KB JSON
- All verbatim_quotes fields empty — CC workers only collected titles/URLs
- Parent supplemented Lane B via direct SearXNG MCP searches
- Parent assembled final briefing from CC JSON + SearXNG results
- CC print mode rendered mobile PDF (430×932px) successfully
