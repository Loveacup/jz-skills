# Common Pitfalls

Full pitfalls list. Top 5 are in SKILL.md. Loaded on-demand.

1. **Search-engine maximalism.** More engines are not better; they are only better when they reduce uncertainty.
2. **Skipping local truth.** User notes, local repos, and past sessions can outrank the public web for user-specific questions.
3. **Conflating discovery with evidence.** Search results suggest sources; fetched/read primary sources support claims.
4. **Treating arXiv as peer review.** arXiv is a preprint server; label venue/review status separately.
5. **Over-trusting citation counts.** Citation counts differ across Semantic Scholar/OpenAlex/Google Scholar and change over time; use them as signal, not truth.
6. **Mixing official and third-party code.** Always label official project/code versus reproductions, forks, and tutorials.
7. **Over-fetching.** Large fetched pages burn context; choose sources like a sniper, not a trawler.
8. **No conflict handling.** If sources disagree, say so and label the most authoritative source.
9. **Credential leakage.** Keep API keys in `.env`; config should use `${ENV_VAR}` substitution only.
10. **arXiv rate limiting.** arXiv's public API enforces ~1 req / 3 seconds. If rate-limited (HTTP 429), do NOT retry immediately — wait 5+ seconds, or fall back to Semantic Scholar for discovery.
11. **Cron job model pinning.** When creating cron jobs that call the LLM, always pin the model explicitly — never rely on the default. The default model may be rate-limited, and a cron job will silently fail.
12. **Web-research-router copies diverge.** The default profile skill is authoritative, but profile copies are independent. Verify ALL profiles after updates: search for `### Red Flags` or `v3.0` in each profile's copy.
13. **GitHub URL blocked by `web_extract`.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` / `gist.github.com` as "internal network." This is NOT a network block — it's a Hermes URL validator false positive. Bypass: use `mcp_exa_web_fetch_exa` or `gh api` via `github-code-explorer` skill.

## Multi-engine Dedup / RRF

When the same query is sent to more than one engine, normalize URLs and merge duplicates.

Use the helper script:
```bash
python ~/.hermes/skills/research/web-research-router/scripts/dedup_rrf.py results.json
```

Accepted input: `{"exa": [...], "brave": [...]}`. Returns merged with `rrf_score`, `providers`, `source_ranks`, duplicate counts, and gap warnings.
