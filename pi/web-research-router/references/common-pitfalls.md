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
14. **Web-research-router copies diverge.** The default profile skill is authoritative, but profile copies are independent. Verify ALL profiles after updates: search for `### Red Flags` or `v3.2` in each profile's copy.
15. **GitHub URL blocked by `web_extract`.** `web_extract` blocks `github.com` / `raw.githubusercontent.com` / `gist.github.com` as "internal network." This is NOT a network block — it's a Hermes URL validator false positive. Bypass：`mcp_searxng_web_url_read`（SearXNG 抓页面，无内网误判）、`mcp_exa_web_fetch_exa`、或 `gh api` via `github` skill。

## Deep-Research Pitfalls（v3.2.0 新增）

下列陷阱专属于多轮 deep research loop / fetch-extract / forced-answer 流程，
对应 references/ 中的 `deep-research-loop.md` / `fetch-extract-pattern.md` / `anti-refusal-prompt.md`。

16. **Extractor 当 answerer 用。** fetch 一个页面后让同一次 LLM call 既"读页面"又"答用户问题" → 幻觉高发，引用错位。
    正确做法：fetch → extractor prompt 只产 verbatim quote → 综合答案是**后续独立**的 LLM call。详见 `fetch-extract-pattern.md`。
17. **没 token / iter budget 就开 deep loop。** Loop 默认配 `breadth=4, depth=2, max_iter=8, token_budget=30k`；
    缺一项就跑 → 实际等于无限循环，烧 token 也卡 deadline。详见 `deep-research-loop.md`。
18. **Reviewer 永远不接受 None。** gpt-researcher 的核心姿势是 "if draft meets guidelines, return None"，把"够了"判定外包给 LLM 自评。
    硬要跑满 max_iter = 浪费 + 越改越离谱。
19. **Section merge 时不 renumber citation。** 每个 section 内本地 `s1`/`s2` 编号；merge 时必须重新分配
    全局 `citation_id` 并更新 confirmed/inferences 中的引用，否则 "[s3]" 在最终报告里指向错误 source。
20. **滥用 forced-answer mode。** forced-answer ("a wrong answer is better than no answer") 仅对
    **有 ground truth 的 fact-recall**（端口号 / 版本号 / 日期 / 命名实体）适用。
    用于"哪个框架更好"/"该不该买"/伦理建议 = 强迫 LLM 编造。详见 `anti-refusal-prompt.md`。
21. **Hedge phrase 命中后无限重写。** anti-refusal pipeline 应当**最多重写一次**；二次仍 hedge → 输出"未找到/需 cross-check"。
    无限重写循环越改越离谱。
22. **Extracted_quotes 为空时仍走 forced-answer。** 没收集到 verbatim quote 就强答 = 凭空捏造。
    应当老实说"SearXNG fetch-extract 全员 NOT RELEVANT，无证据可答"。
23. **没拆 broad query 直接深 loop。** Broad 议题（"对比 X vs Y vs Z"）应先 `query-decomposition.md` 拆 sub-query，
    每个 sub-query 独立走 section research；硬塞整个 broad query 给 deep loop → section 严重交叉、quote 重复入库。
24. **Provider 字段没区分 SearXNG 来源。** SearXNG 命中的 source 必须 `provider: "searxng"`，
    后续 fetch 即使换工具也应在 notes 标 `fetched via exa/tavily`。不区分 → 复盘时无法定位"是哪个引擎漏了"。
25. **Inline citation 写裸 URL 而非 `citation_id`。** ✅ `[s3]` / ❌ "据 https://example.com..."。
    URL 在 source map 里查；正文用 stable `citation_id`，否则 merge / 跨 session 引用全部断链。

## Multi-engine Dedup / RRF

When the same query is sent to more than one engine, normalize URLs and merge duplicates.

Use the helper script:
```bash
python ~/.hermes/skills/research/web-research-router/scripts/dedup_rrf.py results.json
```

Accepted input: `{"exa": [...], "brave": [...]}`. Returns merged with `rrf_score`, `providers`, `source_ranks`, duplicate counts, and gap warnings.
