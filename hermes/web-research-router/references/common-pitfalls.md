# Common Pitfalls

Full pitfalls list. Top 5 are in SKILL.md. Loaded on-demand.

1. **Search-engine maximalism.** SearXNG 注册 245 个引擎 ≠ 245 个都能用。此环境实测仅 **bing**(10r)、**baidu**(9r)、**arxiv**(10r)、**wikipedia**(1r) 稳定返回；brave/duckduckgo/google/startpage 全 0。选 `engines=bing`（英）或 `engines=bing,baidu`（中），务必设 `language` 参数。**先单测每个引擎，确认可用再组合。** 详见 `references/searxng-engine-diagnostics.md`。
2. **单引擎依赖 + 烂引擎组合。** `engines=bing,brave,google,duckduckgo` 中仅 bing 有结果 → 大量 0r 稀释信号。直接用 Exa 单刷也容易遗漏。正确做法：`web_search` 起手广扫 → Exa 精准补强 → SearXNG HTTP(bing+baidu) 做中文交叉。**⚠️ Qwant 引入 spam（lj.im 等垃圾域名），禁用。**
3. **SearXNG MCP vs HTTP 混淆。** 当前环境 SearXNG **搜索仅作为独立 HTTP 服务**运行（`127.0.0.1:32080`），`mcp_searxng_searxng_web_search` 搜索通道不存在，用 `curl` + `format=json` 调 HTTP API（且实例已损坏，仅作最后兜底）。**URL 抓取主力 = Exa Fetch（`mcp_exa_web_fetch_exa`）+ Tavily Extract（`mcp_tavily_tavily_extract`）**；`mcp_searxng_web_url_read` 仅作两者都失败时的备胎。
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
15. **`web_extract` 全局拦截（已弃用）。** 在此 sandbox 环境中，`web_extract` 拦截**所有** HTTPS URL（包括 `github.com`、`obsidian.md`、甚至 `example.com`），统一返回 "private/internal network"。这不是 GitHub 特有问题——是环境网络策略，故 `web_extract` 已弃用、禁止推荐为抓取工具。**替代抓取方案**：Exa Fetch（`mcp_exa_web_fetch_exa`，含 GitHub 页面）/ Tavily Extract（`mcp_tavily_tavily_extract`）为主力；`mcp_searxng_web_url_read` 仅作两者都失败时的备胎。

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
    应当老实说"fetch-extract（Exa Fetch / Tavily Extract）全员 NOT RELEVANT，无证据可答"。
23. **没拆 broad query 直接深 loop。** Broad 议题（"对比 X vs Y vs Z"）应先 `query-decomposition.md` 拆 sub-query，
    每个 sub-query 独立走 section research；硬塞整个 broad query 给 deep loop → section 严重交叉、quote 重复入库。
24. **Provider 字段没区分 SearXNG 来源。** SearXNG 命中的 source 必须 `provider: "searxng"`，
    后续 fetch 即使换工具也应在 notes 标 `fetched via exa/tavily`。不区分 → 复盘时无法定位"是哪个引擎漏了"。
25. **Inline citation 写裸 URL 而非 `citation_id`。** ✅ `[s3]` / ❌ "据 https://example.com..."。
    URL 在 source map 里查；正文用 stable `citation_id`，否则 merge / 跨 session 引用全部断链。

## SearXNG Engine Diagnostics（2026-05-28 实测新增）

26. **不测引擎就直接用多引擎组合。** SearXNG 注册 245 个引擎，但 brave/duckduckgo/google/startpage 在此环境全 0 结果。先逐引擎单测 `curl .../search?q=test&engines=<engine>` 确认可用，再用 `engines=bing,baidu` 组合。详见 `references/searxng-engine-diagnostics.md`。
27. **忘设 `language` 参数。** 不设 `language=en` 或 `language=zh-CN` 时，SearXNG 返回跨语言噪音（日文词典、游戏结果）。每次 SearXNG HTTP 调用必须带 `&language=<code>`。
28. **Qwant 引擎引入垃圾域名。** 实测 Qwant 返回 lj.im 等 spam 域名，污染结果集。禁用它。
29. **MCP 配置是 per-profile 的。** 每个 profile 的 `config.yaml` 中 `mcp_servers` 段独立管理。当前 regent 仅有 codegraph + exa。default（小黄）无 config.yaml → 仅有内置工具。加 MCP server 只改目标 profile 的 config。

When the same query is sent to more than one engine, normalize URLs and merge duplicates.

Use the helper script:
```bash
python ~/.hermes/skills/research/web-research-router/scripts/dedup_rrf.py results.json
```

Accepted input: `{"exa": [...], "brave": [...]}`. Returns merged with `rrf_score`, `providers`, `source_ranks`, duplicate counts, and gap warnings.


## v3.7 新增陷阱（2026-05-29 跨平台交叉验证）

30. **Array-format 参数陷阱（fetch 类工具统一坑）。** `mcp_exa_web_fetch_exa` 与 `mcp_tavily_tavily_extract` **均要求 `urls` 字段为 JSON 数组**，传裸 string 会被工具层拒绝，且报错文案晦涩（"validation error" / "expected array"），极易被误判为"工具坏了"而切换其它路由浪费 budget。同类 fetch 工具（如未来接入的 Firecrawl/Jina Reader）多遵循同一约定，**默认按数组传参**。
    - ✅ 正确：`mcp_exa_web_fetch_exa(urls=["https://example.com/page"])`
    - ✅ 正确：`mcp_tavily_tavily_extract(urls=["https://example.com/a", "https://example.com/b"])`
    - ❌ 错误：`mcp_exa_web_fetch_exa(urls="https://example.com/page")` → 直接失败
    - ❌ 错误：`mcp_tavily_tavily_extract(url="https://example.com/page")` → 字段名也错
    遇到 fetch 工具首调失败时，**先检查参数是否包成数组**，再考虑换工具。

31. **SearXNG 实例跨平台系统性缺陷（换 client 无救）。** 2026-05-28 ~ 05-29 期间，regent（macOS）+ pi（Windows）两个独立 profile 同日实测：**Google 后端完全失效（0 结果或 502）/ Bing 严重降级（结果质量崩塌、相关性骤降）/ DuckDuckGo 持续 CAPTCHA 阻断**。**根因在 SearXNG 实例本身的上游后端**——不是 MCP 客户端、不是 profile 配置、不是网络抖动。换 `mcp_searxng_*` → 直 HTTP curl → 换另一台 MCP server 全部无改善，因为打的是同一个坏掉的实例。v3.7 路由表据此把 SearXNG 从"默认起手广扫"降级为"后备 + 抓取专用"，Exa/Brave/Tavily 上升为主力搜索。**修复路径**：要么修上游实例的 engine settings.yml（需运维介入），要么完全弃用其搜索能力。

32. **抓取主力 = Exa Fetch + Tavily Extract，SearXNG URL Read 仅备胎，且绝不当搜索引擎主力。** v3.9 起抓取主力是 **Exa Fetch（`mcp_exa_web_fetch_exa`）+ Tavily Extract（`mcp_tavily_tavily_extract`）**；`mcp_searxng_web_url_read` 在沙箱 `web_extract` 全局拦截下仍可读取部分公网页面，**仅作前两者都失败时的兜底**。**绝不要**把 `mcp_searxng_searxng_web_search` 作为 primary discovery —— 见 #31 的系统性缺陷。2026-05 实测排序：**Tavily Extract（结构化提取、噪声最低）> Exa Fetch（覆盖广、含 GitHub）> SearXNG web_url_read（兜底，30% 导航噪声 + 5000 字符截断）**。Extraction 任务默认走 Exa Fetch / Tavily，SearXNG URL Read 仅在前两者都失败时尝试。

33. **跨平台双 profile 同症 = 路由表必须改（一票配置，两票系统）。** 当**两个独立 profile / 不同 OS** 同一时间窗口报同一个引擎缺陷时，按"systemic defect"处理，**立刻更新 routing table**，不要再花时间排查本地配置。判定规则：
    - **单 profile 报问题** = 配置 / 网络 / API key 问题 → 先排查本地，不动路由表
    - **两 profile + 不同 OS 报同问题** = 引擎 / 上游实例 / API provider 系统性缺陷 → 直接降级该引擎在路由表中的位置，附测试日期 + 两 profile 名作为证据
    - **三 profile 以上 + 跨网络环境** = 全局降级 / 标记 deprecated
    本次 v3.7 的 SearXNG 降级正是 regent(macOS) + pi(Windows) 同日交叉验证的产物，证据链写入 references/common-pitfalls.md #31 与 routing 章节，避免下次复盘时"为啥降的级"无据可查。
