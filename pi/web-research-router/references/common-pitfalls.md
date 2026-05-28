# Common Pitfalls

Full pitfalls list. Top 5 are in SKILL.md. Loaded on-demand.

1. **Search-engine maximalism.** More engines are not better; they are only better when they reduce uncertainty。SearXNG 已聚合 6+ 引擎，一次广扫足够，不需要再叠 Exa+Tavily+Brave 三路并发。
2. **单引擎依赖症（over-relying on a single engine）.** 直接用 Exa 或 Tavily 单刷会漏掉其他引擎独家收录的页面。SearXNG 同时跑 Bing/Brave/Qwant/Mwmbl/DDG/Startpage 等 6+ 通用引擎，一次拿到 100+ 候选源，先广扫再精挖比从一开始就走窄漏斗更可靠。
3. **SearXNG 的 search vs URL read 混淆.** `mcp_searxng_searxng_web_search` 返回搜索结果（标题/URL/snippet 列表）；`mcp_searxng_web_url_read` 输入一个 URL、返回该页 markdown 全文。前者用于发现源，后者用于读取已知源——不要把它们当同一个工具。
4. **Skipping local truth.** User notes, local repos, and past sessions can outrank the public web for user-specific questions.
5. **Conflating discovery with evidence.** Search results suggest sources; fetched/read primary sources support claims.
6. **Treating arXiv as peer review.** arXiv is a preprint server; label venue/review status separately.
7. **Over-trusting citation counts.** Citation counts differ across Semantic Scholar/OpenAlex/Google Scholar and change over time; use them as signal, not truth.
8. **Mixing official and third-party code.** Always label official project/code versus reproductions, forks, and tutorials.
9. **Over-fetching.** Large fetched pages burn context; choose sources like a sniper, not a trawler.
10. **No conflict handling.** If sources disagree, say so and label the most authoritative source.
11. **Credential leakage.** Keep API keys in `.env`; config should use `${ENV_VAR}` substitution only.
12. **arXiv rate limiting.** arXiv's public API enforces ~1 req / 3 seconds. If rate-limited (HTTP 429), do NOT retry immediately — wait 5+ seconds, or fall back to Semantic Scholar for discovery.
13. **Cron job model pinning.** When creating cron jobs that call the LLM, always pin the model explicitly — never rely on the default. The default model may be rate-limited, and a cron job will silently fail.
14. **Web-research-router copies diverge.** The default profile skill is authoritative, but profile copies are independent. Verify ALL profiles after updates: search for `### Red Flags` or `v3.1` in each profile's copy.
15. **GitHub URL blocked by `web_extract`.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` / `gist.github.com` as "internal network." This is NOT a network block — it's a Hermes URL validator false positive. Bypass：`mcp_searxng_web_url_read`（SearXNG 抓页面，无内网误判）、`mcp_exa_web_fetch_exa`、或 `gh api` via `github` skill。

## Multi-engine Dedup / RRF

When the same query is sent to more than one engine, normalize URLs and merge duplicates.

Use the helper script:
```bash
python ~/.hermes/skills/research/web-research-router/scripts/dedup_rrf.py results.json
```

Accepted input: `{"exa": [...], "brave": [...]}`. Returns merged with `rrf_score`, `providers`, `source_ranks`, duplicate counts, and gap warnings.
