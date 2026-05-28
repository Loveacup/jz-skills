# Anti-Refusal Prompt · 反拒答提示

> **Read when:** fact-recall 类查询（端口号、版本号、日期、命名实体、估值数字）但 LLM 回 hedge
> （"我无法确定" / "信息不足"）；综合答案时 LLM 拒绝下断言而堆砌"可能"；
> SearXNG 已返回足够 verbatim quote 但 LLM 不肯综合。
> **Source:** `~/research-tmp/ldr-circuit/src/local_deep_research/citation_handlers/forced_answer_citation_handler.py`
> **Sibling refs:** `fetch-extract-pattern.md` (verbatim quote 收集前置步骤) · `query-decomposition.md` (sub-query 拆解前置步骤) · `deep-research-loop.md`
> **范围限定：** 仅对 fact-recall 类问题使用；分析类、伦理敏感类、推荐类问题**不要**用，会强迫 LLM 编造。

---

## 何时启用 forced-answer mode

| 场景 | 启用 | 备注 |
|---|---|---|
| 端口号 / 版本号 / 价格 / token 数 | ✅ | 有唯一正确答案 |
| 人名 / 公司名 / 产品名 | ✅ | quote-anchored，可逐字核对 |
| 历史日期 / 历史数字 | ✅ | 有据可查 |
| 综合分析 / 比较 / 优劣 | ❌ | 需要 hedge 才负责 |
| 伦理 / 法律 / 医疗建议 | ❌ | hedge 是责任，不是缺陷 |
| 未来预测 / 趋势判断 | ❌ | 不存在唯一答案 |
| 推荐类 ("哪个最好") | ❌ | 主观题，强答 = 越界 |

---

## 8 个 hedge phrase（local-deep-research 原文）

来源：`forced_answer_citation_handler.py:132-143` 的 `no_answer_indicators` 列表（verbatim）：

英文（**verbatim from source line 134-143**）：
```
1. "cannot determine"
2. "unable to find"
3. "insufficient"
4. "unclear"
5. "not enough"
6. "cannot provide"
7. "no specific answer"
8. "cannot definitively"
```

中文等价（本地搜索场景常见，**补充非源码原文**）：
```
1. "我无法确定"
2. "信息不足以判断"
3. "目前没有公开数据表明"
4. "可能存在多种可能性"
5. "暂无明确答案"
6. "无法给出具体"
7. "尚不清楚"
8. "难以确定"
```

---

## 检测 + 重写 pipeline

1. LLM 给出第一版答案
2. 用 substring scan 扫 8 + 8 个 hedge phrase（小写匹配；中文不区分大小写）
3. 命中任意一个 → 触发 `_extract_direct_answer` 路径（源码 line 165-196）
4. **补一条额外触发**：query 以 `what / who / which / where / when / name / 谁 / 哪 / 何时 / 多少` 开头，但 first-100-chars 不含 `is/was/are/were/:/是/为/在` → 也触发（源码 line 153-161）
5. 重写最多 1 次（避免无限循环）
6. 重写后仍 hedge → 输出 `"需要 cross-check：现有 quote 不足以下断言"` 而非伪造（守 alignment 边界）

---

## forced-answer prompt（verbatim from source）

### Initial analysis（`forced_answer_citation_handler.py:30-48`）

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

### Follow-up（关键收尾句，`forced_answer_citation_handler.py:96-119`）

```
CRITICAL INSTRUCTIONS:
1. You MUST start with a direct, specific answer
2. NEVER say "I cannot determine" or similar phrases
3. If the question asks for a name, provide a specific name
4. If the question asks for a place, provide a specific place
5. If unsure, choose the answer with the most supporting evidence
6. Format: "[Direct Answer]. Supporting evidence from [1], [2]..."
7. Do not create the bibliography, it will be provided automatically.

Remember: A wrong answer is better than no answer for this task.
```

### Forced extraction prompt（`forced_answer_citation_handler.py:169-183`）

```
Based on the content below, extract a SINGLE, DIRECT answer to the question.

Question: {query}

Content: {content[:1500]}

Sources: {sources[:1500]}

RULES:
1. Respond with ONLY the answer itself (name, place, number, etc.)
2. No explanations, just the answer
3. If multiple candidates exist, pick the one mentioned most
4. If truly no information exists, make an educated guess

Answer:
```

> ⚠️ **不可滥用：** "Remember: A wrong answer is better than no answer" 是 benchmark-oriented 指令，仅适合**有 ground truth 的 fact-recall**。对分析 / 推荐 / 伦理类问题强行 forced-answer = 制造幻觉 + 不负责。
> alex 实际场景守门：触发前必须验证 query 落在上表"启用"区。

---

## fact-recall mode 说明

- fact-recall 是一个隐式 mode，触发条件：query 落在上表"启用"区
- 必经路径：先走 SearXNG + fetch-extract 收集 verbatim quote（见 `fetch-extract-pattern.md`）
- 收集到的 quote ≥ 1 条 → 用 forced-answer prompt 综合
- 收集到的 quote = 0（extractor 全部返回 `NOT RELEVANT`）→ **不要** forced-answer，直接说"未找到 / 需要更换搜索词或引擎"
- 与 deep-research-loop.md 关系：fact-recall mode 跳过"reviewer 多轮迭代"，单轮 fetch-extract + forced-synthesize

---

## 与现有 mode 的关系

- **grounding mode**：现有的事实核验路径已有 cross-check 节奏；fact-recall 是 grounding 的"末段强答"环节，**不取代** cross-check
- **deep-research-loop**：deep loop 默认带 hedge（综合分析需要谨慎），fact-recall mode 只在 sub-task 是 fact-recall 时局部启用
- **academic-lane**：学术问题大多需要 hedge（综述、争议），**不启用** forced-answer

---

## 使用示例

### 示例 1：启用 forced-answer 的正例
**Query:** "Redis 7 的默认端口是什么"
**第一版答案:** "Based on available sources, the default port may be 6379, but this could vary depending on configuration..."
**hedge 检测:** 命中 `"may"` 旁的不确定语气 + 未直接答出
**重写后:** "6379. According to [1], Redis 7 ships with default `port 6379` in `redis.conf`..."
**正确性：** verbatim quote 充分，强答合规。

### 示例 2：不该启用 forced-answer 的反例
**Query:** "新项目该用 React 还是 Vue？"
**第一版答案:** "It depends on your team's skill set and project requirements..."
**判断:** 这是推荐 / 主观题 → **不该启用** forced-answer
**正确处理:** 保持 hedge，按对比维度（learning curve / ecosystem / job market）展开，给决策框架而非答案。

### 示例 3：quote = 0 时的正确退让
**Query:** "X 公司 2026 年 5 月的某次内部调整里 CTO 是谁"
**SearXNG + fetch-extract 结果:** 5 个 source 全部返回 `NOT RELEVANT`
**判断:** 没有 verbatim quote 锚定 → **不要** forced-answer（会凭空编造人名）
**正确处理:** "未找到公开来源记录该信息。建议：(a) 换查询词；(b) 走 academic-lane / discussion-lane；(c) 直接查公司公告页"

---

## 常见误用

- ❌ 把所有"模糊"回答都 forced-answer → 制造幻觉
- ❌ 没收集 verbatim quote 就 forced-answer → LLM 凭空编（必须先过 fetch-extract）
- ❌ 多次重写循环（>1 次）→ 浪费 token + 越改越离谱（源码本身只重写 1 次）
- ❌ 把"推荐类 / 哪个最好"当 fact-recall → 越界，违反 alignment
- ❌ 中文 hedge phrase 漏检（只扫英文 list）→ 中文回答的"无法确定"会逃过检测
- ❌ 把 forced-answer 当作 deep-research-loop 的默认综合策略 → deep mode 综合分析时应允许 hedge
