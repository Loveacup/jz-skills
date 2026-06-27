# Claude Code WebSearch — Engine Quality Benchmark

> 2026-05-30. pi-web-providers comparison session. Tested as the "built-in local" provider that Claude Code uses for `web_search`.

## Test Setup

- **Query:** "Claude 4.7 Opus release date 2026 key features"
- **Tool:** Claude Code CLI v2.1.153, `claude -p "..." --max-turns 3`
- **Under the hood:** Claude Code's built-in `WebSearch` tool, executed by Haiku 4.5 (1 request), results synthesized by Opus 4.7
- **Cost:** $0.66 total ($0.63 Opus cache creation + $0.03 Haiku search)

## Raw Results

9 results, all high-authority:
1. anthropic.com — What's new in Claude Opus 4.7 (official docs)
2. anthropic.com — Introducing Claude Opus 4.7 (official announcement)
3. wikipedia.org — Claude (language model)
4. github.blog — Claude Opus 4.7 is generally available
5. finout.io — Pricing analysis
6. scriptbyai.com — Claude Timeline
7. findskill.ai — Release Tracker
8. hidekazu-konishi.com — Model Release Timeline
9. llm-stats.com — Benchmarks, Pricing & Context Window

## Scoring vs Other Engines

| Dimension | Claude Code | Exa | Brave | Tavily | web_search |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Relevance | 5 | 5 | 4 | 4 | 4 |
| Authority | 5 | 5 | 4 | 4 | 4 |
| Content richness | 3 | 5 | 3 | 5 | 4 |
| Diversity | 5 | 4 | 4 | 5 | 3 |
| Cost | 1 | 5 | 5 | 5 | 5 |
| Speed | 3 | 5 | 5 | 4 | 5 |
| **Composite** | **3.7** | **4.8** | **4.2** | **4.5** | **4.3** |

## Key Findings

1. **Highest authority, worst cost.** Claude Code WebSearch consistently returns official sources (anthropic.com, github.blog, wikipedia) that other engines sometimes miss. But at $0.66/query it's ~100x more expensive than API-based engines.

2. **Cache economics are broken for single queries.** The $0.63 cache creation (99K tokens of system prompt + tool definitions) dominates the cost. Batch queries would amortize this, but pi-web-providers doesn't batch — each `web_search` call is a fresh Claude Code session.

3. **Not suitable for cron/batch.** At $0.66/query × 96 ticks/day = $63/day. Compare: Exa at ~$0.005/query × 96 = $0.48/day.

4. **Best use case: critical fact verification.** When you need the highest-authority source and cost is irrelevant (legal, compliance, one-off executive brief). Use as a last-resort fallback when Exa + Brave + Tavily all fail to return a primary source.

## Integration Notes

- Requires Claude Code CLI installed (`brew install claude-code` or npm)
- Uses local Claude auth (no separate API key needed)
- pi-web-providers wraps this as the `claude` provider for `web_search` and `web_answer`
- Our router does NOT currently route to Claude Code — this benchmark confirms that's the right call for 99% of queries
- If added to router: treat as "premium fallback" behind Exa → Brave → Tavily → web_search → SearXNG
