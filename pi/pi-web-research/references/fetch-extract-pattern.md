# Fetch-Extract Pattern · 抓页面 → 抽 verbatim quote

> **Read when:** 调用方刚拿到搜索结果、要决定如何"读"一个 URL；或者要写综合答案前需要先沉淀
> 可引用的原文片段；或者怀疑 LLM 在编造时。
> **Source:** `~/research-tmp/ldr-circuit/` (local-deep-research, 95% SimpleQA winner) + `~/research-tmp/odr/` + `~/research-tmp/gptr/`
> **Sibling refs:** `source-map-schema.md`（extractor 输出落在 `extracted_quotes[]` 字段）· `deep-research-loop.md`（section research 阶段调用本 pattern）
> **Leverage:** ★ 最大杠杆——这一招在 local-deep-research 的 95% 归因里贡献 5-10pts。

## 核心原则：Extractor ≠ Answerer

把"读一个 URL"和"回答用户问题"切成两个独立的 LLM 调用。fetch 阶段的 LLM 不知道也不需要知道
最终答案，它的唯一任务是从页面里**逐字抄出**和 focus 相关的片段。综合答案的活儿留给
orchestrator 在所有 quotes 都收齐之后一次性做。

为什么这样能抗幻觉：
- LLM 一旦被允许"回答问题"，它会用自身知识脑补缺失信息；逼它只能 copy 原文，就堵死了这条路。
- 一行一 quote，天然形成 citation 锚点：综合答案的每一句话都能追溯到某个 URL 的某段原文。
- 失败安全：页面没料 → 输出 `NOT RELEVANT`，orchestrator 自动跳过，不会被噪声污染。
- 模型尺寸友好：extractor 这种 narrow task 小模型（qwen3、gpt-oss）也能稳定做对。

## 默认 fetch 工具

`mcp_searxng_web_url_read` — SearXNG 自带 URL→markdown 抓取，没有 web_extract 把 GitHub
issue/wiki 误判为内网的问题，适合配合 verbatim 抽取。备选：`mcp_exa_web_fetch_exa`（贵但稳）/
`mcp_tavily_tavily_extract`（有时返回为空）。

## 抽取 prompt（verbatim 从源码抄）

### Prompt 1: extractor 主力（每次 fetch 后跑）

源：`~/research-tmp/ldr-circuit/src/local_deep_research/advanced_search_system/tools/fetch/prompts.py:40-61`

```
You are a content-extraction step inside a multi-step research agent.

Your role in the pipeline:
- The agent has already run web searches and decided this specific page is worth reading more carefully than its snippet allowed.
- Your output is returned to the agent as a tool result. The agent — not you — will combine your output with other sources and write the final cited answer.
- Therefore you are an extractor, NOT an answerer. Do not interpret, conclude, or compose. Just pull the relevant raw text out of the page.

Overall research question: {overall_query}
Why this page was fetched: {focus}

Page title: {title}
Page URL: {url}
Page content:
{content}

Output rules:
- Output ONLY verbatim quotes from the page. Copy numbers, names, dates, and proper nouns exactly as written — never paraphrase facts.
- One quote per line. No bullets, no numbering, no section headers.
- Omit navigation, ads, cookie/subscription banners, related-article lists, author bios, comments, and anything off-topic.
- If nothing on the page helps, reply with exactly: NOT RELEVANT
- Do NOT include introductions ('Here is the relevant information:'), conclusions ('In summary...'), explanations of what you kept or skipped, or commentary on the source's quality, bias, or relevance.
- Maximum 1500 characters. Quality over quantity — fewer precise quotes beat many borderline ones.
```

变量：`{overall_query}` `{focus}` `{title}` `{url}` `{content}`
输出契约：纯 verbatim quote，一行一条；nothing relevant → 输出 `NOT RELEVANT`；上限 1500 chars。

> 备注：源码里 `SUMMARY_FOCUS_PROMPT`（不含 overall_query）与 `SUMMARY_FOCUS_QUERY_PROMPT`
> （含 overall_query）是两个变体；推荐用后者，能让 extractor 在 focus 措辞模糊时正确消歧。

### Prompt 2: section grader（综合阶段判章节是否够、要不要再搜）

源：`~/research-tmp/odr/src/legacy/prompts.py:168-198`

```
Review a report section relative to the specified topic:

<Report topic>
{topic}
</Report topic>

<section topic>
{section_topic}
</section topic>

<section content>
{section}
</section content>

<task>
Evaluate whether the section content adequately addresses the section topic.

If the section content does not adequately address the section topic, generate {number_of_follow_up_queries} follow-up search queries to gather missing information.
</task>

<format>
Call the Feedback tool and output with the following schema:

grade: Literal["pass","fail"] = Field(
    description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
)
follow_up_queries: List[SearchQuery] = Field(
    description="List of follow-up search queries.",
)
</format>
```

用法：用 `with_structured_output(Feedback)` 强约束输出；`grade=fail` 时把 `follow_up_queries`
回灌给搜索环节继续迭代，到达 max_depth 强制 pass。

### Prompt 3: reviewer "return None to terminate"（多轮 reviewer-reviser 收敛）

源：`~/research-tmp/gptr/multi_agents/agents/reviewer.py:25-38`

```
You have been tasked with reviewing the draft which was written by a non-expert based on specific guidelines.
Please accept the draft if it is good enough to publish, or send it for revision, along with your notes to guide the revision.
If not all of the guideline criteria are met, you should send appropriate revision notes.
If the draft meets all the guidelines, please return None.

(after a prior round:)
The reviser has already revised the draft based on your previous review notes with the following feedback:
{revision_notes}

Please provide additional feedback ONLY if critical since the reviser has already made changes based on your previous feedback.
If you think the article is sufficient or that non critical revisions are required, please aim to return None.

Guidelines: {guidelines}
Draft: {draft}
```

终止逻辑（源码原版）：response 中包含 `"None"` 字串 → 返回 `None` → orchestrator 跳出
reviewer-reviser 循环。优雅、零状态、对小模型友好。

### Prompt 4: forced answer（fact-recall 模式专用，绝不说"无法判断"）

源：`~/research-tmp/ldr-circuit/src/local_deep_research/citation_handlers/forced_answer_citation_handler.py:30-48`（initial）+ `:96-119`（followup）

```
Analyze the following information and provide a DIRECT answer to the question. Include citations using numbers in square brackets [1], [2], etc.

Question: {query}

Sources:
{formatted_sources}

Current time is {current_timestamp} UTC for verifying temporal references in sources.

CRITICAL INSTRUCTIONS:
1. Start your response with a direct answer to the question
2. NEVER say "I cannot determine" or "insufficient information"
3. If unsure between options, choose the MOST LIKELY based on evidence
4. After the direct answer, provide supporting analysis with citations
5. Do not create the bibliography, it will be provided automatically.

Example response format:
"[Direct Answer]. According to [1], this is supported by..."
```

兜底：源码会扫输出里有没有 `"cannot determine" / "insufficient" / "unclear"` 等短语，命中就跑
二次抽取 prompt 强抠一个 single-token 答案。Fact-recall / SimpleQA 类问题适用，开放式
research 用 grader 即可。

## 与现有 skill 协同

- **source-reader / source-verification**：extractor 输出的 quotes 直接喂给这两个 skill 做后续
  验证；不要让它们再去网上找一次。
- **content-source-workflow**：workflow 的"抽取"步骤可以直接用本 pattern 替换原始 summary。
- 不要 chain 两层 extractor（已 verbatim 不需要再 paraphrase），也不要把 extractor 输出
  直接当答案给用户（缺综合）。

## 使用示例

### 示例 1: "Hermes A2A 的端口号是多少"（事实查询 / fact-recall）

1. `mcp_searxng_searxng_web_search "Hermes A2A port"` → 返回 5 个 URL
2. 对 top-3 URL（如 `github.com/.../hermes/blob/main/a2a/server.py`、官方 docs）跑
   `mcp_searxng_web_url_read`
3. 每个页面分别灌入 Prompt 1（`focus="A2A server port number"`），收集 verbatim quotes
   （例：`"DEFAULT_A2A_PORT = 8765"`、`"a2a listens on 8765 by default"`）
4. 把所有 quotes 喂给 Prompt 4，让 LLM 选最可能端口；citation 用 quote 行号锚定

### 示例 2: "2026 年 Claude Opus 的 context 长度"（数字事实，强反幻觉）

1. `mcp_searxng_searxng_web_search "Claude Opus 4.7 context window 2026"` → 5 URL
2. fetch anthropic.com/news、docs.anthropic.com/models、相关 changelog
3. 每页跑 Prompt 1（`focus="Claude Opus context window length token count"`）；只接受写明
   token 数字的 verbatim 行（如 `"1,000,000 token context"`）。页面没数字 → `NOT RELEVANT`
4. 跑 Prompt 4 强答；若多源不一致，prompt 内置的 fact-check 子步骤会选"出现频次最高的版本"

### 示例 3: "对比 LangGraph 和 LlamaIndex 的 agent 模式"（综合分析 / 多源）

1. 各跑一次 `searxng_web_search`（query 1: LangGraph agent architecture；query 2: LlamaIndex
   agent workflow）
2. 两边各 fetch 3 个权威源（官方 docs + 一篇深度博客 + 一个对比文章）
3. 每个 URL 独立跑 Prompt 1（focus 分别写明），保留 quotes 池
4. 用 Prompt 2 把 quotes 写成"LangGraph 模式"、"LlamaIndex 模式"、"对比"三节，每节交一次
   grader；fail 就回灌 follow_up_queries 重搜
5. 全 pass 后跑 Prompt 3 reviewer 收敛，None → 出稿

## 常见错误

- ❌ 让一个 LLM 调用同时做"读页面"+"回答问题" → 幻觉高发
- ❌ extractor 输出"根据这篇文章..."一类 paraphrase → 不是 verbatim，citation 失效
- ❌ 跳过 extractor 直接把整页塞给综合答案 prompt → 失去 citation 锚点、context 爆炸
- ❌ extractor 阶段就调 forced-answer（Prompt 4）→ 提前承诺答案，后续 source 进不来
- ❌ reviewer 一直找毛病不肯返 None → 死循环；务必加 max_rounds 兜底
