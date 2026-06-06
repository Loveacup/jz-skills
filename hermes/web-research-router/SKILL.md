---

name: web-research-router
description: "Searches the web, finds papers, explores GitHub source code, verifies facts, and runs multi-step deep-research loops using Exa/Brave/web_search/Tavily/SearXNG (5 engines) plus local knowledge (Supermemory/qmd/Obsidian/CodeGraph). Includes verbatim-quote extraction (anti-hallucination), query decomposition, and forced-answer fact-recall. Use when the user needs to 搜索, 检索, 查找, 调研, 核实, 深挖, 出报告, 找资料, 找项目, search, research, deep-research, find, look up, or verify information. Routes GitHub source code tasks to github. Do NOT use for local file ops."
type: routine
version: 3.9.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [search, research, router, searxng, exa, tavily, brave, academic, papers, citations, sources, mcp, deep-research, verbatim-quote, anti-refusal, wechat, sogou]
    related_skills: [source-search, exa-research, source-reader, source-verification, content-source-workflow, qmd, obsidian, native-mcp, github, scrapling]

---

# Web Research Router v3.9

> 🆕 **v3.9 (2026-06-02)**: 🆕 集成 Sogou/微信公众号搜索 via weixin-search-mcp (PyPI v0.2.1)。搜索 + 加密链接解密 + 正文提取完整链路，Scrapling CLI stealthy-fetch 作为内容抓取 fallback（张睿 2026-06-01 验证）。新增 `references/sogou-wechat-source.md`。

> 🆕 **v3.7 (2026-05-29)**: 🔥 跨平台交叉验证后的路由大改。regent(macOS) + pi(Windows) 同日实测确认 **SearXNG 实例本身已损坏**（Google 失效 / Bing 降级 / DDG CAPTCHA，换 MCP 客户端无救）。SearXNG 从「默认起手」降级为「兜底 + 抓取专用」，Exa/Brave 升为双主力，Tavily 为深度调研专用。新增 MCP Configuration & Deployment 章节、Step 0 强制四步本地检查、Output Contract 强制 `[s<id>]` inline citation + 三分栏、common-pitfalls 新增 4 条（含 fetch 类工具 `urls:[...]` 数组参数陷阱）。

> 🆕 **v3.6 (2026-05-29)**: 引擎全量可用。Brave/Tavily API key 已配置，测试满分/Brave 9/9、Tavily 8/9。路由表升级为 5 引擎全矩阵，SearXNG 降级为广撒网后备。Quick Reference 重写。

> 🆕 **v3.5 (2026-05-28)**: 引擎可用性大修。第一轮流测揭示 SearXNG/Tavily/Brave MCP 缺失。路由表更新为 `web_search` 起手+Exa 精准。tool-names.md 重写。16 profile MCP 全量同步。

> 🆕 **v3.4 (2026-05-28)**: 基于好伴AI深度研究案例 RCA，新增 3 条 deep loop Red Flag 与 4 条质量验证清单（事实解耦/Claim 溯源/补搜回路/口径确认）。详见 `references/deep-research-loop.md` 与 `references/deep-loop-verification-pattern.md`。

> ⚙️ **Tuning:** `CROSS_CHECK_DEPTH=1` (fast, single-source) to `3` (thorough, triple-verify). Default: `2`.

---

## 🚨 Red Flags: DO NOT SKIP THIS ROUTER

Before calling ANY search tool, check this table. If any excuse below sounds familiar, **STOP — you are about to violate the decision tree.**

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "This is a simple query, I'll just use `web_search`" | `web_search` is a generic fallback. The router picks the best engine per query type. Even "simple" factual queries benefit from multi-engine cross-check (web_search + Exa)。 |
| "I already know the answer" | Training data is stale. Current facts need current search. |
| "I already loaded the skill, that's enough" | Loading ≠ following. Loading tells you WHAT to do; you still need to DO it. |
| "The loaded skill / context already has info on this — I can answer from that" ★ | **2026-06-01 真实违规。用户追问"你搜索了吗"。** 加载了 claude-code skill 后，基于 skill 内容和先验知识直接回答了 CC agent team 模型选择机制——但这是关于外部产品当前能力的 factual 问题。skill 里的信息可能过期、不完整或被后续更新推翻。**任何外部事实/版本/能力/当前状态的问题，即使已加载的 skill 看似覆盖了该领域，也必须走 Step 0 + 公网搜索。skill 是工作流指南，不是事实权威来源。** |
| "The decision tree is too complicated for this" | It's 4 branches. Pick one. Takes 5 seconds. |
| "I'll cross-check later" | Cross-checking after the fact is twice the work. Do it in the right order now. |
| "我直接 Exa 单引擎一次到位" | 单引擎容易遗漏独立索引盲区（Exa 的神经索引 vs Brave 的独立爬虫覆盖不同源）。默认双主力 Exa + Brave 交叉，web_search 广扫兜底。 |
| "我不会 deep research / 单轮就够了" | 议题维度 ≥3、需可引用报告、单轮 source map 覆盖 <70% → 升级 deep loop（`references/deep-research-loop.md`）。不升级 ≠ 答得对；只是把幻觉藏起来。 |
| "fetch 完直接综合答案就行，省一步" | fetch + 综合答案放一次 LLM call → 幻觉高发。正确：fetch → extractor（verbatim quotes only） → 独立 call 综合。详见 `references/fetch-extract-pattern.md`。 |
| "section 写完就行，facts.jsonl 太麻烦" ★ | **fetch-write 耦合是 deep loop 80% 偏差的根因。** 营销话术一旦被叙事化（"已有1亿用户、竞争压力巨大"），REFLECT 看到的是流畅叙事而非原子事实卡片，无法回头推翻。SECTION 阶段必须先产 `facts.jsonl`（指标/口径/来源/可信度/原始URL），write 读卡片不读原始页面。详见 `references/deep-research-loop.md` Step 2。 |
| "REFLECT 过一遍就够了，不用再做 Claim 溯源" ★ | REFLECT 是同一 Agent 在相同上下文做自审 → 只能发现"段落间逻辑矛盾"，无法发现"整个上下文 based on 一个错误前提"。含"第一/最/突破/领先/超过/首家"或带规模数字的 claim **必须独立 search 溯源**，由独立 LLM call 在新上下文中验证。详见 `references/deep-loop-verification-pattern.md`。 |
| "中文搜索词够了，议题是国内的" ★ | 跨语言盲区是**系统性**的——中文 query 几乎召不回英文公告（Anthropic Claude for Healthcare 案例）。MERGE 前必须有"盲区检视 → 反向假设（'国际玩家最近做了什么'）→ 跨语言补搜"回路。详见 `references/deep-research-loop.md` Step 4。 |
| "本地能回答的问题别上公网 / I'll just hit the web, it's faster" ★ | **跳过 Step 0 是 v3.6 测试 P1 缺陷的根因。** Supermemory/session/qmd/CodeGraph 已沉淀过往结论、verbatim quote、user-validated facts —— 跳过 = 重新付一遍 token + 把已验证事实降级为"再次查证"。公网召回的还可能与本地结论矛盾，反而引入冲突。**强制 4 步本地检查（Supermemory → session_search → qmd/Obsidian → CodeGraph），全部 miss 才上公网。** 不查本地 ≠ 答得快；只是把 token 账单和幻觉风险一起放大。 |

**If you caught yourself thinking any of these → re-read the decision tree below and start over.**

---

## 🔀 Routing Decision Tree (ALWAYS RUN THIS FIRST)

### Step 0: Local knowledge first — MANDATORY 4-STEP SEQUENCE

> 🛑 **STOP.** Before ANY public search engine call, you MUST run all 4 local checks below in order. Each step is one tool call. Skipping = router violation.

- **Step 0.1 — Supermemory (cross-session memory)**
  - check: 过往 session 是否已问过同一议题，是否已有结论 / source map / facts.jsonl 可复用
  - tool: `supermemory_search`
  - skip only if: 议题明显是实时性新闻（今日股价、刚发生的事件）且 < 24h
  - escalate to public if: 命中 < 2 条 OR 命中结论已过期（> 90 天且涉及版本 / 价格 / 排名）
- **Step 0.2 — session_search (this session context)**
  - check: 本轮对话上文是否已 fetch 过相关页面、抽过 verbatim quote、用户是否已给原文 / 截图
  - tool: in-context scrollback / session transcript search
  - skip only if: 新议题与本轮上文零重叠（首条用户消息即新主题）
  - escalate to public if: 本轮上文未覆盖该子问题 OR 上文 source 不足以下结论
- **Step 0.3 — qmd / Obsidian (knowledge base)**
  - check: 本地知识库（qmd 向量库、Obsidian vault、个人 wiki）是否已有该主题笔记 / 卡片
  - tool: `qmd search` / Obsidian search / `mcp_obsidian_*` query
  - skip only if: 议题为外部公司 / 产品 / 最新动态，本地不可能有
  - escalate to public if: 命中 0 条 OR 命中笔记 > 180 天且涉及变动信息
- **Step 0.4 — CodeGraph (local code & repos)**
  - check: 若问题涉及本地代码、内部仓库、接口定义、函数实现，先查 CodeGraph / `gh search code` 本地索引
  - tool: `mcp_codegraph_*` / `serena` / 本地 `rg` / `gh api`（本地 repo）
  - skip only if: 议题与代码 / 仓库零相关（纯事实、纯新闻、纯背景）
  - escalate to public if: 本地仓库无相关实现 OR 需要对比外部上游版本

**只有以上 4 步全部"已查 + 未命中或不足"，才允许调用 web_search / Exa / Brave / Tavily / SearXNG。** 在最终回答的 Verification Checklist 中必须显式声明这 4 步的执行结果（命中 / 未命中 / 跳过+原因）。

### Step 1: Is this a GitHub source code task?
- "看看 X 项目源码" / "这个函数怎么实现" → load `github`.

### Step 2: Pick the search mode and engine

> ⚠️ **引擎可用性声明（2026-05-29 v3.7 跨平台交叉验证后）：**
> ✅ **Exa 9/9 + Brave 9/9 满分** → 升为双主力（语义精准 + 独立索引交叉）。
> ✅ Tavily 8/9 → 深度调研专用（含 `tavily_extract` 结构化抽取）。
> ✅ web_search 13/15 → 广扫兜底 + 通用查询。
> 🔧 **SearXNG 实例本身已损坏**：Google 完全失效 / Bing 严重降级 / DDG CAPTCHA — 跨平台系统性缺陷，**换 MCP 客户端无效**。
> ⛔ `mcp_searxng_searxng_web_search` 仅作**最后兜底**；`mcp_searxng_web_url_read` 仅作**抓取通道**保留。
>
> **默认路由：web_search 广扫 → Exa 语义精准 → Brave 独立交叉 → Tavily 深度调研 → SearXNG 兜底。**

#### 五模式路由（保留 v3.6 mode 名称，更新 engine 序列）

- **discovery** — 背景调研 / landscape / "有没有相关项目"
  - Primary: `web_search` 广扫 → `Exa` 语义精准
  - Cross-check: `Brave`（独立索引交叉）
  - Fallback: `SearXNG`（仅当前三家命中 <3 条）

- **grounding** — 日期 / 数字 / 价格 / claim / 新闻核实
  - Primary: `Exa` + `Brave`（双引擎并行，独立索引交叉）
  - Cross-check: `web_search`（通用兜底）
  - Fallback: `Tavily`（结构化抽取数字 / 口径）

- **research** — 实质 brief / 决策备忘 / 市场扫描
  - Primary: `Exa` + `Brave`（双主力并行）
  - Cross-check: `Tavily`（深度结构化 + `tavily_extract` 抽事实卡）
  - Fallback: `web_search` 广扫补盲区；SearXNG 不再参与
  - 🆕 **补充源:** 主链路跑完后，对 §不稳定高质量源 做 pre-flight check → 可用则追加搜索（权威源互补覆盖）

- **academic** — 论文 / 引用 / SOTA / arXiv / DOI
  - Primary: `Exa` + `arXiv`（curl / `scripts/search_arxiv.py`，见 `references/arxiv-semantic-scholar.md`）
  - Cross-check: `Brave`（学术域名独立交叉）
  - Fallback: `web_search`（SearXNG **不**推荐——学术信源被实例噪声淹没）

- **recovery** — 死链 / 迁移源 / 缺失材料
  - Primary: `web_search` + `Brave`（双引擎广扫候选）
  - Cross-check: `Exa Fetch`（`mcp_exa_web_fetch_exa` 抓 cache / mirror）
  - Fallback: `mcp_searxng_web_url_read`（仅作抓取通道；**不**用 SearXNG 搜索）

> 🔁 **何时升级到 deep-research loop？** 议题维度 ≥ 3 / 需可引用结构化报告 / 单轮 source map 命中 <70% / 用户显式说"深挖" → 进入
> `references/deep-research-loop.md` 的 plan → section research（含 `fetch-extract-pattern.md` extractor） → reflect → merge 循环。
> Deep loop **不替换**上述 5 mode；它是 `research` mode 的可选升级路径。

Detailed mode instructions: `references/research-modes.md`

### Step 3: Cross-check only when warranted (respect `CROSS_CHECK_DEPTH`)
Cross-check when: numbers, dates, prices, legal claims, attribution, SOTA claims, financial decisions, fast-changing news, suspicious claims. At depth 1, skip cross-check. At depth 2 (default), cross-check one source. At depth 3, triple-verify.

### Step 4: Fetch discipline
Search first, fetch second. Fetch 1–3 high-signal URLs only. Prefer primary/official sources.

---

## 🧭 Quick Reference: Which Engine When

> ⚠️ **实际可用性标记（2026-05-29 v3.7 跨平台验证）：**
> ✅ = 主力可用 | ⚙️ = 后备 / 受限场景 | 🔧 = 实例损坏，仅保留特定通道

### 引擎清单（按推荐顺序）

- **Exa** ✅ 🥇 主力 #1
  - status: 满分 9/9（regent + pi 双平台）
  - best-for: 语义精准、技术 / 研究 / 对比类查询、跨语言召回
  - tool: `mcp_exa_web_search_exa`
  - params: `query: string, numResults?: number=3`

- **Brave** ✅ 🥇 主力 #2
  - status: 满分 9/9，API key 已配置
  - best-for: 独立索引交叉验证、新闻 / 时效类、绕开 Google 重排
  - tool: `mcp_brave_search_brave_web_search`
  - params: `query: string, count?: number=5`

- **Tavily** ✅ 🥈 深度调研专用
  - status: 8/9，API key 已配置
  - best-for: 结构化抽取、deep loop facts.jsonl、数字 / 口径核对
  - tool (search): `mcp_tavily_tavily_search` — params: `query: string, max_results?: number=5`
  - tool (extract): `mcp_tavily_tavily_extract` — params: `urls: string[]`（**数组**，非单字符串）

- **web_search** ✅ 🥉 广扫兜底
  - status: 13/15，Hermes 内置 100% 在线
  - best-for: 通用查询、broad scan、Exa / Brave 命中不足时补盲
  - tool: `web_search`
  - params: `query: string, limit?: number=5`

- **Exa Fetch** ✅ 抓取主力
  - status: 唯一可靠 GitHub / HTTPS 抓取通道
  - best-for: URL → markdown，含 GitHub raw / blob
  - tool: `mcp_exa_web_fetch_exa`
  - params: `urls: string[]`（**数组**！非 `url: string`）

- **SearXNG MCP search** ⚙️ 仅兜底 / fallback only
  - status: 🔧 实例 Google 失效 / Bing 降级 / DDG CAPTCHA
  - best-for: **只在前 4 家全部命中 <3 条时启用**；高噪声需人工过滤前 5-10 条
  - tool: `mcp_searxng_searxng_web_search`
  - params: `query: string, language?: string='en'`
  - 警告: 默认**不**调用；30% 导航噪声 + 跨平台系统性缺陷

- **SearXNG URL Read** ⚙️ 仅抓取通道 / fetch channel only
  - status: 可用但 5000 字符截断 + 30% 导航噪声
  - best-for: Exa Fetch 失败时的 URL → markdown 备胎
  - tool: `mcp_searxng_web_url_read`
  - params: `url: string`
  - 警告: Tavily Extract 在内容质量上完胜，优先用 `mcp_tavily_tavily_extract`

- **arXiv + Semantic Scholar** ✅ 学术专用
  - status: 在线
  - best-for: CS / AI / ML 预印本 + 引用 / 相关 / 作者数据
  - tool: `scripts/search_arxiv.py` + Semantic Scholar API（见 `references/arxiv-semantic-scholar.md`）

- **gh CLI** ✅ GitHub 代码
  - status: 在线
  - best-for: GitHub 代码搜索
  - tool: `terminal` → `gh search code`

## 🔀 不稳定高质量源（Auxiliary Sources）

> 🛑 **不在主链路。** 以下引擎不稳定（可能未安装/未认证/额度耗尽），**必须先做 pre-flight check 再调用**。仅作为主链路 Exa/Brave/Tavily/web_search/SearXNG 跑完后、需要额外权威验证时的加分项。

### Pre-flight check（每次使用前强制执行）

```bash
# Claude Code — 检查 CLI 是否可用
which claude && claude --version 2>/dev/null || echo "UNAVAILABLE"

# Codex — 检查 CLI + 认证状态
which codex && codex login status 2>/dev/null || echo "UNAVAILABLE"
```

**规则：**
- ❌ pre-flight 失败 → 不调用，不报错，静默跳过
- ⚠️ 调用成功但返回空 → 视为额度耗尽 / 限流，该 session 不再重试
- ✅ 启用场景：
  - **research 模式** — 主链路跑完后，pre-flight OK 则追加搜索，结果作为互补源合并
  - **grounding 模式** — 主链路命中 <3 条 + 需要权威源交叉验证时
  - **deep-research loop** — SECTION 阶段作为额外源参与 facts.jsonl 采集（见 `references/deep-research-loop.md`）
  - **日常 discovery** — 不启用（成本/收益不划算）

### 引擎

- **Claude Code WebSearch** 🔶 不稳定高质量
  - status: 🆕 v3.8，本地 CLI wrapper（`scripts/claude-web-search.sh`）
  - pre-flight: `which claude && claude --version`
  - contract: JSON stdin/stdout（pi-web-providers custom provider 兼容）
  - best-for: 权威源验证（anthropic.com/github.blog）
  - cost: ~$0.30–0.66/query
  - ⚠️ 可能未安装 / 额度耗尽 / 限流。不接主链路。

- **Codex WebSearch** 🔶 预留（未就绪）
  - pre-flight: `which codex && codex login status`
  - status: CLI 已安装 (v0.135.0)，需 `codex login` 认证
  - ⚠️ 当前不可用，等待认证后激活

- **weixin-search-mcp** 🔶 中文微信专用（新）
  - status: 🆕 v0.2.1，2026-06-02 实测通过
  - pre-flight: `uv pip install --python 3.12 weixin-search-mcp` + `python -c "from weixin_search_mcp.tools.weixin_search import sogou_weixin_search; print(len(sogou_weixin_search('测试')))"`
  - contract: Python import（非 MCP stdio——协议兼容性待解决，直接用 Python API）
  - best-for: 微信公众号文章搜索 + 加密链接解密 + 正文提取
  - cost: Free（硬编码 Cookie，可能随时失效）
  - fallback: Scrapling CLI `stealthy-fetch` 直接抓 `mp.weixin.qq.com`
  - ⚠️ 仅用于中文 + 微信/公众号相关 query；不接主链路
  - 详见 `references/sogou-wechat-source.md`

- **Sogou WeChat Search** 🔶 微信专用 🆕
  - status: v0.2.1 实测通过（搜索 + 加密链接解析 + 正文提取），唯一可索引微信公众号的搜索引擎
  - pre-flight: `python3 -c "from weixin_search_mcp.tools.weixin_search import sogou_weixin_search; print(len(sogou_weixin_search('test', page=1)))"` — 返回 >0 即正常
  - tool: `weixin-search-mcp` PyPI 包（需 Python 3.12+）
  - best-for: 中文 + 微信/公众号视角的 discovery/research；社交媒体信源补充
  - ⚠️ Cookie 硬编码，可能随时过期；建议每周冒烟测试
  - 详细文档: `references/sogou-wechat-source.md`

### 选型口诀 (v3.8)

> **Exa 精准 + Brave 交叉 → Tavily 深研 → web_search 广扫 → SearXNG 仅兜底 / 仅抓取。**
>
> 🔶 不稳定高质量源（Claude Code / Codex）**不接主链路**——pre-flight check 可用时才作为额外权威验证，失败静默跳过。
>
> 默认双主力 = Exa + Brave；研究类加 Tavily；SearXNG **不再**作为起手引擎。

### 参数陷阱速查（pi-report 教训吸收）

- 🪤 `mcp_exa_web_fetch_exa` 需 `urls: ["url"]` **数组**（非 `url: "..."` 字符串）
- 🪤 `mcp_tavily_tavily_extract` 需 `urls: ["url"]` **数组**
- ✅ 搜索类工具（exa_search / brave / tavily_search / web_search / searxng_search）用 `query: string` **字符串**
- ✅ 抓取类工具（exa_fetch / tavily_extract）用 `urls: string[]` **数组**
- ⚠️ 区分原则: search = string query；fetch / extract = array urls

Full tool list: `references/tool-names.md`

---

## ⚙️ MCP Configuration & Deployment

> v3.7 把 SearXNG 降为后备 / 抓取专用后，Exa / Brave / Tavily 三家 API key 是主力路径的生命线。本节给出最小可跑配置 + key 申请 + 同步 + 自检四件套。完整旧版同步流程仍见 `references/deployment.md`。

### MCP Server config (config.yaml `mcp_servers` snippet)

最小可跑的 4 引擎 `mcp_servers` 段，粘到 `~/.hermes/profiles/<profile>/config.yaml` 即可。Key 走 `${ENV_VAR}` 注入，**不要**把明文 key 写进 yaml。

```yaml
mcp_servers:
  exa:
    command: npx
    args: ["-y", "exa-mcp-server"]
    env:
      EXA_API_KEY: ${EXA_API_KEY}
  brave:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: ${BRAVE_API_KEY}
  tavily:
    command: npx
    args: ["-y", "tavily-mcp"]
    env:
      TAVILY_API_KEY: ${TAVILY_API_KEY}
  searxng:
    command: npx
    args: ["-y", "mcp-searxng"]
    env:
      SEARXNG_URL: ${SEARXNG_URL}
```

### API Key acquisition (`.env` template + links)

复制到 `~/.hermes/profiles/<profile>/.env`，逐行填值。Brave / Tavily 都有免费额度，日常 deep loop 够用。

- **EXA_API_KEY**: `your-exa-key` — 申请: https://exa.ai （注册即送试用额度）
- **BRAVE_API_KEY**: `your-brave-key` — 申请: https://brave.com/search/api/ （免费 2000 次/月）
- **TAVILY_API_KEY**: `your-tavily-key` — 申请: https://tavily.com （免费 1000 次/月）
- **SEARXNG_URL**: `http://127.0.0.1:32080` — 自建本地实例，无需 key

> 🔐 `.env` 必须加进 `.gitignore`。换 profile 时**只**复制 yaml，不复制 `.env`，key 每台机器独立维护。

### All-profile sync command

一键把 `~/.hermes/skills/...` 下的 source-of-truth 推到所有 profile，带时间戳备份。

```bash
SRC=~/.hermes/skills/research/web-research-router
TS=$(date +%Y%m%d_%H%M%S)
for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
  dst=~/.hermes/profiles/$prof/skills/research/web-research-router
  if [ -d "$dst" ]; then
    mkdir -p ~/.hermes/profiles/$prof/backups
    cp -r "$dst" ~/.hermes/profiles/$prof/backups/web-research-router-$TS
    rm -rf "$dst"
  fi
  mkdir -p "$(dirname "$dst")"
  cp -r "$SRC" "$dst"
  echo "synced → $prof"
done
```

### Verification

跑完上面三步后，按顺序确认 gateway / 实例 / 引擎都活着：

```bash
# 1. MCP 服务已加载（应看到 exa / brave / tavily / searxng 四行）
hermes mcp list

# 2. SearXNG 本地实例存活（应返回 SearXNG 首页 HTML <head>）
curl -s http://127.0.0.1:32080/ | head -5

# 3. 各引擎冒烟测试（任选一条 query，每个引擎跑一次）
hermes mcp test exa     --query "claude 4.7 release notes"
hermes mcp test brave   --query "claude 4.7 release notes"
hermes mcp test tavily  --query "claude 4.7 release notes"
hermes mcp test searxng --query "claude 4.7 release notes"
```

预期：Exa / Brave / Tavily 各回 5-10 条相关结果；SearXNG 回 30+ 条含噪声（正常，按 v3.7 路由表只做后备 / `web_url_read` 抓取）。任一引擎报 `401 / invalid api key` → 回 API Key 段重申。

---

## 📋 Output Contract v3.7

> Telegram-friendly：禁用宽表，使用 `key: value` bullet 行。所有 `research` 模式输出必须满足下列硬约束。

### 必填字段（每次回答顶部）

- **Mode:** `discovery` / `grounding` / `research` / `recovery` / `academic`（必填，单选）
- **结论:** 1–2 行，结论先行；含引用必须用 inline `[s<id>]` 形式，禁止裸 URL / 裸标题
- **来源:** 每条一行，格式 `[s<id>] domain — why it matters — URL`（URL 行内允许，但结论段不允许裸 URL）

### 强制三分栏（research 模式必填，其它模式建议填）

- **已确认 (Confirmed):** 有 ≥1 条 verbatim quote 直接支撑、且 `citation_ids` 可映回 source map 的事实
- **推断 (Inference):** 基于已确认事实的判断 / 外推；每条须标 `基于 [s<id>][s<id>]` 说明依据
- **冲突缺口 (Conflicts & Gaps):** 来源相互矛盾、口径不一致、覆盖率不足的条目；每条标 `冲突 / 缺口` 类型与涉及 `[s<id>]`

### Inline citation 硬规则

- 正文 / 结论 / 分栏内**只能**写 `[s1]` / `[s2]` 这种 `[s<数字>]` 形式
- 禁止：裸 URL（`https://...`）、裸 domain（`anthropic.com 说...`）、`(source: ...)`、`见上文`
- 每个 `[s<id>]` 必须能在 **来源** 段映射到一条 source_map 条目（含 title / url / extracted_quote / fetched_at）

### 格式示例（照抄即可）

- **Mode:** `research`
- **结论:** Claude for Healthcare 于 2026-05 进入 GA，主打 HIPAA 合规与临床总结 workflow [s1]；与同期 OpenAI Health API beta 形成正面竞争 [s2][s3]。
- **来源:**
  - `[s1] anthropic.com — 官方 GA 公告，含合规声明与定价 — https://anthropic.com/news/claude-healthcare-ga`
  - `[s2] openai.com — Health API beta 文档，对照功能集 — https://platform.openai.com/docs/health`
  - `[s3] statnews.com — 第三方报道，含分析师评论 — https://statnews.com/2026/05/...`
- **已确认 (Confirmed):**
  - Claude for Healthcare 2026-05 GA，HIPAA BAA 可签 — `[s1]`
  - OpenAI Health API 同期处于 beta，未承诺 HIPAA BAA — `[s2]`
- **推断 (Inference):**
  - 短期内 HIPAA 合规将成为企业医疗采购的硬门槛 — 基于 `[s1][s3]`
- **冲突缺口 (Conflicts & Gaps):**
  - 缺口：未找到 Google MedLM 同期更新公告（跨语言 / 跨厂商盲区）
  - 冲突：`[s3]` 引述价格区间与 `[s1]` 官方定价不一致，需以 `[s1]` 为准

### Source Map 字段映射

每个 `[s<id>]` 背后的 source_map JSON 条目须含：`id` / `title` / `url` / `domain` / `fetched_at` / `extracted_quotes[]` / `confidence` / `citation_id`。完整 schema 见 `references/source-map-schema.md`。

---

## 📦 Progressive Disclosure Reference Map

| When you need... | Read... |
|-----------------|---------|
| Detailed mode instructions (default paths, examples) | `references/research-modes.md` |
| Query patterns for common tasks | `references/query-patterns.md` |
| Academic lane policy (arXiv, Semantic Scholar, PubMed, etc.) | `references/academic-lane.md` |
| **arXiv / Semantic Scholar 操作细节**（API 语法 / BibTeX / 引用数据 / 限流降级 / `search_arxiv.py`） | `references/arxiv-semantic-scholar.md` |
| Vertical domain → engine mapping (finance, security, health, etc.) | `references/vertical-domains.md` |
| Full Source Map Schema JSON（含 `citation_id` / `extracted_quotes` / `budget` 字段） | `references/source-map-schema.md` |
| MCP tool names by profile | `references/tool-names.md` |
| **MCP 配置与部署**（config.yaml + .env + 同步 + 验证四件套） | 本文 §MCP Configuration & Deployment |
| Deployment & Sync instructions (legacy) | `references/deployment.md` |
| **抓页面后如何抽 verbatim quote**（防幻觉最大杠杆）★ | `references/fetch-extract-pattern.md` |
| **多轮 deep research loop SOP v3.4**（plan → section(facts.jsonl) → CoV验证 → merge(盲区补搜) → 颗粒度Gate） | `references/deep-research-loop.md` |
| **Deep loop 质量缺陷 + CoV 验证模式**（fetch-write耦合、REFLECT天花板、跨语言盲区 — 2026-05-28 案例RCA） | `references/deep-loop-verification-pattern.md` |
| **broad 议题如何拆 sub-query**（TEMPORAL/NUMERICAL/NAMES/ENTITY/CONCEPTUAL 五类） | `references/query-decomposition.md` |
| **🆕 实用模型选型指南**（实测+公开评测+curl 示例，非专业测试的"什么模型做什么事"方法论） | `references/practical-model-selection-guide.md` |
| **fact-recall 时 LLM 死活不答如何破**（8 hedge phrase + forced-answer prompt） | `references/anti-refusal-prompt.md` |
| **🔬 5 引擎质量实测报告（2026-05-28）**（web_search/Exa/SearXNG/Brave/Tavily 全量对比） | `references/engine-quality-report-20260528.md` |
| **Claude Code WebSearch wrapper**（JSON stdin/stdout，pi custom provider 兼容） | `scripts/claude-web-search.sh` |
| **🆕 Claude Code WebSearch benchmark（2026-05-30）**（pi-web-providers 内置 provider，$0.66/query，权威性满分但成本不可持续） | `references/claude-code-websearch-benchmark.md` |
| **🆕 Sogou 微信搜索源**（搜索 + 解密 + 抓取完整链路 — weixin-search-mcp v0.2.1 + Scrapling CLI） | `references/sogou-wechat-source.md` |
| **🆕 Sogou/微信搜索源（2026-06-02）**（weixin-search-mcp v0.2.1 — 搜索+解密+抓取完整链路，Scrapling CLI fallback） | `references/sogou-wechat-source.md` |
| **🆕 新闻管线抓取断裂根因（2026-06-02）**（web_extract SSRF 守卫 → 伪引用 → 模型脑补 → 产出不可信 — 三省六部早新闻案例诊断） | `references/news-pipeline-extraction-failure.md` |
| **Telegram 客户端差异排查**（PC 可见但 iOS 不可见的 topic typing indicator：先分离 API 正确性 vs 客户端渲染） | `references/telegram-client-specific-topic-typing.md` |

---

## ⚠️ Common Pitfalls (Top 9)

1. **SearXNG SNR 陷阱。** SearXNG MCP 每次返回 140+ 条，其中大量 spam/钓鱼/词典释义/无关条目。信噪比 ~67%。**必须取前 5-10 条人工过滤**，不可直接把全量结果当有效信息源。
2. **Brave/Tavily 假在线。** MCP server 显示 enabled 但搜索返回空——因为 API key 失效。先检查 key 状态：`echo $BRAVE_API_KEY` / `echo $TAVILY_API_KEY`，缺失则去官网申请免费 key。
3. **Extractor 当 answerer 用** ★ 同一次 LLM call 既 fetch 又综合答案 → 幻觉高发。fetch → verbatim quote 抽取 → 后续独立 call 综合。详见 `references/fetch-extract-pattern.md`。
4. **搜索引擎并发堆叠。** 不必每次调 5 个引擎——`web_search` + Exa 两步覆盖 95% 场景，省 token 且质量高。
5. **Skipping local truth.** Check Supermemory/qmd/CodeGraph before public web.
6. **Conflating discovery with evidence.** Search results are candidates; fetched/extracted sources are evidence.
7. **GitHub `web_extract` trap.** `web_extract` 对所有 URL 均拦截（环境网络策略），不仅 GitHub。**已弃用** —— 抓取主力用 `mcp_exa_web_fetch_exa` 或 `mcp_tavily_tavily_extract`（`urls: string[]` 数组）；`mcp_searxng_web_url_read` 仅作两者失败时的备胎。
8. **Exa 语义漂移。** Exa 语义搜索偶尔跑偏（"React release date" 召回 GTA 6）。对精确事实类 query 优先 `web_search`。
9. **Cron job model pinning.** Always pin model explicitly in cron jobs — default model may be rate-limited.
10. **Client-specific behavior ≠ backend failure.** If the user reports “works on PC/Desktop but not iOS/mobile” (or vice versa), immediately split the investigation into API/backend correctness vs client rendering/metadata behavior. Search with explicit client terms (`iOS`, `Android`, `Desktop`, version) and avoid declaring the server-side fix failed when one client already renders correctly. For Telegram topic/DM typing indicators, PC visibility plus iOS invisibility strongly suggests client-rendering limitations; keep native API calls as ground truth and treat visible placeholder fallbacks as opt-in only.

Full pitfalls (33 items, 含 v3.4 新增 deep loop 质量 8 项): `references/common-pitfalls.md`

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] **Local first?** Supermemory/session/qmd/CodeGraph 都查过再上公网。
- [ ] **Step 0 四步全跑过？** Supermemory / session_search / qmd-Obsidian / CodeGraph 四项是否在回答中显式声明"已查 + 命中 / 未命中 / 跳过原因"？— 未声明视同未跑（v3.6 P1 Local-first 缺陷）。
- [ ] **Mode + engine?** 选定 discovery/grounding/research/academic/recovery，或升级 deep loop；按 v3.7 表用对 primary engine（默认 Exa+Brave 双主力，SearXNG 仅兜底）。
- [ ] **Extractor not answerer?** 每个 fetched 页面跑过 extractor、verbatim quote 入 source map，**不是**让单次 LLM call 又 fetch 又综合答案。
- [ ] **Citation 用 `citation_id`?** 综合答案中 inline citation 写 `[s3]`，不写裸 URL；`confirmed[i].citation_ids` 全部映得回 source map。
- [ ] **Inline 引用全部 `[s<id>]` 形式？** 正文 / 结论 / 三分栏内是否 100% 使用 `[s1]`/`[s2]` 等 `[s<数字>]` 引用，零裸 URL、零裸 domain、零"见上文"？每个 `[s<id>]` 都能在 **来源** 段映回 source_map 条目？— 任一裸引用即失败。
- [ ] **Cross-check + budget?** 重要 claim 按 `CROSS_CHECK_DEPTH` 交叉；走 deep loop 时 `max_iter` / `token_budget` / `stop_reason` 都有值。
- [ ] **Fetch discipline?** Fetched ≤3 high-signal URLs；fetch 类工具记得用 `urls: [...]` **数组**参数；GitHub URL 用 `mcp_exa_web_fetch_exa` / `mcp_tavily_tavily_extract` / gh api（**不**用 `web_extract`，SearXNG URL Read 仅作备胎）。
- [ ] **Confirmed vs inference 分开?** 报告中事实与判断必须分栏，conflicts/gaps 单列。
- [ ] **三分栏显式分开？** 回答是否同时包含 **已确认 (Confirmed)** / **推断 (Inference)** / **冲突缺口 (Conflicts & Gaps)** 三块独立 bullet，且每块至少一行（无则写"无"）？— 缺任一栏视同未分栏（v3.6 P1 Output Contract 缺陷）。

### Deep-loop 专属（如果用了 deep-research loop，以下 4 条必须勾过）★

- [ ] **事实解耦？** deep loop 的 SECTION 阶段 fetch 后是否先产 `facts.jsonl`（字段：指标/口径/来源/可信度/原始URL）再 write_section？— 防止 fetch-write 耦合（80% 偏差根因）。
- [ ] **Claim 溯源？** 含 `"第一/最/独家/突破/领先/超过/首家/首个"` 或带数字规模/benchmark/排名 的 claim，是否每条都做了独立 search 验证（新上下文、跨信源、跨语言）？— 防 REFLECT 自审天花板。
- [ ] **补搜回路？** MERGE 前是否做了"盲区检视 → 反向假设（'国际玩家/跨语言信源遗漏什么？'）→ 跨语言补搜"？— 防跨地域/跨语种召回失败。
- [ ] **口径确认？** 涉及数字（用户量/MAU/DAU/累计/GMV）是否区分了"累计 vs 月活 vs 日活 vs 截至某月"？涉及政策/排名是否标注了原始项目名/数量/信源等级？— 防颗粒度坍缩与营销口径误读。

**Every box must honestly pass before returning results. If unchecked, go back.**

---

> 🔄 Deployment & Sync: `references/deployment.md`
