# Research Modes

Detailed mode instructions for web-research-router. Loaded on-demand from SKILL.md.

## Mode Selection

> 🌐 **跨模式默认起手：Exa + Brave 双主力。**（语义精准 + 独立索引交叉）`web_search` 广扫兜底，
> Tavily 做深度调研 / 数据 grounding。看清 landscape 后再按下表选模式、按各模式 Default path 决定精深方向。
> 🔧 **SearXNG 实例已损坏**（Google 失效 / Bing 降级 / DDG CAPTCHA），`mcp_searxng_searxng_web_search`
> 从"默认起手"降为**最后兜底**——仅当 Exa/Brave/web_search 前几家命中 <3 条时才启用。
> 这不是省钱省 token——是因为单引擎遗漏太常见,默认双主力交叉再精挖比从一开始就走窄漏斗更可靠。

**Auto-detect vs. ask:** Deterministic scenarios → auto-select. Uncertain scenarios → ask the user.

**When to ask (8 scenarios):**

| Scenario | Ask |
|----------|-----|
| Intent is ambiguous (quick overview vs. deep research?) | "是要快速了解还是深度调研？" |
| Topic is too broad with no specific need | "你关注哪个维度？" |
| Multi-engine results contradict each other | "结果有矛盾，要深挖吗？" |
| Search terms have multiple meanings | "你指的是哪种含义？" |
| Answer likely already in local knowledge (Supermemory/qmd) | "本地好像有，要先查本地吗？" |
| Not clear if user wants full-text fetch vs. summary | "要抓原文细读还是先看摘要？" |
| Academic search scope unclear (time range, include preprints?) | "时间范围和是否包含预印本？" |
| GitHub exploration depth unclear (L1 quick look vs. L4 full analysis) | "快速看实现还是全面分析？" |

---

## `discovery` — find high-signal sources

Use when the user asks for background, landscape, competitors, examples, docs, projects, or "有没有相关资料/项目".

Default path:
1. **web_search 广扫**（`web_search`）—— 一次拿到通用引擎结果，看清整个 landscape。
2. Exa 做语义精准——基于广扫的初探结果定义更精确的语义查询。
3. Brave 独立索引交叉 if Exa looks narrow or 需要本地化 / 新闻补强。
4. Fallback: SearXNG（`mcp_searxng_searxng_web_search`）—— 仅当前三家命中 <3 条时才启用；高噪声需人工过滤前 5-10 条。
5. Fetch 1–3 canonical sources only（抓取用 Exa Fetch / Tavily Extract）。

Good sources: official docs, GitHub repos, maintainer posts, primary reports, credible practitioner analysis.

---

## `grounding` — verify claims

Use when the task depends on dates, numbers, prices, authorship, identity, legal/regulatory facts, current news, or financial/investment claims.

Default path:
1. **Exa + Brave 并行交叉**（`mcp_exa_web_search_exa` + `mcp_brave_search_brave_web_search`）—— 两个独立索引同时返回，一致 → 高置信；分歧 → 进入深核流程。
2. web_search 通用兜底——双主力命中不足或需要 mainstream 视角时补盲。
3. Tavily 深核——目标是最新动态 / 结构化抽取数字 / 口径时调用（`mcp_tavily_tavily_extract`）。
4. Fallback: SearXNG（`mcp_searxng_searxng_web_search`）—— 仅当上述各家命中 <3 条时兜底。
5. Fetch/read the primary source before asserting（抓取用 Exa Fetch / Tavily Extract）。

Output must separate confirmed facts, inference, conflicts, and gaps.

---

## `research` — build a source-backed brief

Use when the user wants a substantive answer, source map, decision memo, market scan, technical recommendation, or long-form research.

Default path:
1. **Exa + Brave 双主力并行**（`mcp_exa_web_search_exa` + `mcp_brave_search_brave_web_search`）—— 语义精准 + 独立索引交叉，把全景拉满（公司、产品对比、深度博文 + 新闻视角）。
2. Tavily 深研——事实核验 / 结构化抽取原文与事实卡（`mcp_tavily_tavily_extract`）。
3. web_search 广扫补盲区；SearXNG 不再参与主链路（仅当上述全部命中 <3 条时才作最后兜底）。
4. Fetch only the highest-signal URLs（抓取用 Exa Fetch `mcp_exa_web_fetch_exa` / Tavily Extract；`mcp_searxng_web_url_read` 仅作两者失败时的备胎）。
5. Hand off to `source-reader`, `content-source-workflow`, `source-verification`, or a domain skill when the source map is built.

---

## `academic` — papers, citations, and research genealogy

Use when the user asks for papers, literature reviews, arXiv, citations, references, SOTA, surveys, academic sources, DOI/venue metadata, author profiles, research lineage.

**Full academic lane policy: `references/academic-lane.md`**

> 🎓 **学术模式默认起手 = Exa + arXiv skill。** Exa 语义精准召回论文 / project pages / blog 上下文，`arxiv` skill 深刷预印本；
> Brave 做学术域名独立交叉。**SearXNG 不推荐**——实例已损坏，学术信源会被实例噪声淹没。
> 专项图谱（引用、作者档案、PubMed 生物医学）仍需 Semantic Scholar / OpenAlex / PubMed 单刷。

Quick default paths by domain:
1. **AI/ML/CS/math/physics:** Exa 语义精准 + load `arxiv` 深刷预印本 → Semantic Scholar 拉引用图谱 → Brave 学术域名交叉、找 project pages 与 blog 上下文（SearXNG 不推荐）。
2. **Biomedical/clinical:** PubMed/Europe PMC first → Semantic Scholar/OpenAlex → journal full text。SearXNG 不覆盖 PubMed，跳过。
3. **Published metadata / DOI:** OpenAlex/Crossref 单刷补全 → publisher page → Semantic Scholar（SearXNG 实例损坏，不再作 Crossref 入口）。
4. **Reproducibility:** Papers with Code, GitHub, Hugging Face after canonical paper identified.

Output should distinguish: seminal / survey / SOTA / implementation / critique.

---

## `recovery` — recover missing, moved, or hard-to-find material

Use when a URL is dead, a source moved, a title is known but the link is missing.

Default path:
1. **web_search + Brave 双引擎广扫候选**（`web_search` + `mcp_brave_search_brave_web_search`），带 exact title/URL fragments 与 `site:` operators——两个独立索引并发，命中概率最高。某一引擎漏掉的快照，另一引擎可能还留着。
2. Exa for semantically similar pages or remembered titles（标题模糊时尤其有用）。
3. Exa Fetch（`mcp_exa_web_fetch_exa`）抓 cache / mirror / GitHub 页面；其次 Tavily Extract（`mcp_tavily_tavily_extract`）if candidate URLs are found.
4. Fallback: SearXNG（`mcp_searxng_searxng_web_search` 搜索仅当上述命中 <3 条时兜底；抓取失败时 `mcp_searxng_web_url_read` 仅作 Exa Fetch / Tavily Extract 的备胎）。
5. Report whether the recovered source is canonical, mirrored, archived, or uncertain.

---

## `platform` 🔌 — social / video / forum / RSS（v3.10 新增，补充模式）

Use when the query targets content **inside a platform that the 5 public engines can't reach**: Twitter/X 口碑、Reddit 讨论、B站/小红书/YouTube 内容、V2EX/雪球垂直社区、小宇宙播客、RSS。调用 Agent-Reach 的多后端通道。

> 🔌 **platform mode 是五模式之外的第 6 个补充模式，不替换 Exa/Brave/Tavily 主链路。** 它解决的是"公网索引覆盖不到平台原生内容"的结构性盲区，而非"换个更好的公网引擎"。
> **完整通道速查 / 触发映射 / 输出映射 / 交互环境标注 / DO·DON'T: `references/platform-mode.md`**

Default path:
1. **Step P0 先体检（强制）**：`agent-reach doctor --json` —— 按各平台 `active_backend` 选命令组；`status: off` 的通道（当前 linkedin / exa_search）静默跳过不报错。
2. **路由到对应通道**：
   - Twitter/X 口碑 → `opencli twitter search "query" -f yaml`（⚠️ 交互环境）
   - Reddit 讨论 → `opencli reddit search "query" -f yaml`（⚠️ 交互环境）
   - B站 → `bili search "query" --type video -n 5`（免登录）+ `opencli bilibili subtitle BVxxx`（字幕需桌面）
   - 小红书 → `opencli xiaohongshu search "query" -f yaml`（⚠️ 交互环境 + xsec_token）
   - YouTube → `yt-dlp --dump-json "ytsearch5:query"` + 字幕；无字幕 `agent-reach transcribe`
   - V2EX → `curl .../api/topics/hot.json`（免登录，最稳）
   - 雪球 / 小宇宙 / RSS → 公开 API / transcribe.sh / feedparser
3. **Cross-check**：口碑/评价类默认多平台交叉（Twitter ↔ Reddit）；社交数字/单方说法的关键 claim 用 Exa/Brave 公网佐证。
4. **Fallback**：通道不可用 → 回退 `web_search site:平台域名`（如 `site:reddit.com`）搜公开索引。
5. **管线收口**：CLI 原始信源 **必须** 经 extractor → source map（`provider: agent-reach` / `platform: <name>` / `source_tier: social`）→ 三分栏。社交口碑默认进「推断」或「冲突缺口」，**非「已确认」**（除非已被公网一手源 cross-check）。

Output discipline:
- 社交信源标 `source_tier: social`，与 primary/official/news 区分；互动数据（点赞/回复/播放）放 `notes`，是代表性信号不是事实。
- 凡用了「需要交互环境」的通道（OpenCLI 类），结论或 notes 必须标注——否则 cron/headless 复跑会静默失败。

---

## 薄源重试（Thin-Source Retry）— 切引擎前先简化重试同引擎 🆕 v3.11

> 偷自 last30days `pipeline.py` 的 thin-source retry：某引擎命中过少，常因 query 带太多修饰词而过窄，**不是该引擎没这个源**。切引擎前先给同引擎一次"简化重试"机会。

**规则（套在每个 mode 的 Fallback 步之前）：**

1. 某引擎命中 **<3 条** → **先**用 **core-subject 简化 query**（≤3 词，剥离 intent modifier，复用 `query-decomposition.md` 的 **NAMES** 类提取）**重试同一引擎一次**。
   - 例：`"Kanye West album sales Billboard performance 2026"` 命中 1 条 → 简化为 `"Kanye West"` 重试 Exa。
2. 简化重试仍 **<3 条** → **再**按该 mode 的 Fallback 切下一引擎 / SearXNG 兜底。

**边界：**
- 每引擎只薄重试 **一次**（防循环）；
- 简化 query 与原 query 的结果在喂 `dedup_rrf.py` **前先 dedup**（避免重复污染 RRF）；
- core-subject = 最显著的 NAMES 实体，≤3 词，不重新展开成多 sub-query（那是 decomposition 的活，不是 retry）。

> 🔧 **wrr-core 收口：** 当前是各 mode fallback 的 prompt 前置；wrr-core 阶段 1 把它放进 `route()` 的 fallback 链——作为"切下一引擎"前的一跳，由 registry `modes.*.fallback` 序列驱动。

---

## Cost / Noise Discipline

- Do not use all engines by default.
- Start with 5–8 results.
- Fetch/extract sparingly.
- Prefer one strong primary source over five weak summaries.
- For recurring monitoring, use silent cron/script watchdogs; notify only on meaningful deltas.
- If a query can be answered from local KB/code/session memory, avoid paid/public APIs.
