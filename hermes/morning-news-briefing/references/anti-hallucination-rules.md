# 反幻觉规则集 v1.0 (morning-news-briefing v4.0)

> **Read when:** assembly 步骤写正文 / audit 步骤校验产出 / Skill 触发反骑墙 grep。本规则集是「质量地板」，任一违反即重写或降级。
> **Source:** `~/research-tmp/news-aggregator-skill/` (cclank) 的 SKILL.md + instructions/briefing_general.md + MISTAKES.md
> **Sibling refs:** [./banned-phrases-and-probability-scale.md](./banned-phrases-and-probability-scale.md) (禁词与概率刻度) · [./analysis-format.md](./analysis-format.md) (分析格式) · `../web-research-router/references/anti-refusal-prompt.md` (检测+重写)

---

## 一、Anti-Hallucination 核心规则（verbatim 自 cclank SKILL.md:173-180）

```
## ⚠️ Rules (Strict)

1. Language: ALL output in Simplified Chinese (简体中文). Keep well-known English proper nouns (ChatGPT, Python, etc.).
2. Time: MANDATORY field. Never skip. If missing in JSON, mark as "Unknown Time". Preserve "Real-time" / "Today" / "Hot" as-is.
3. Anti-Hallucination: Only use data from the JSON. Never invent news items. Use simple SVO sentences. Do not fabricate causal relationships.
4. Smart Keyword Expansion: When user says "AI" → auto-expand to "AI,LLM,GPT,Claude,Agent,RAG,DeepSeek".
5. Smart Fill: If results < 5 items in a time window, supplement with high-value items from wider range. Mark supplementary items with ⚠️. Exception: International News sources are a hard 24h window; do not supplement with older items.
6. Save: Always save report to reports/YYYY-MM-DD/ before displaying.
```

中文解读：
- 规则 3：只允许从 fetcher 返回的结构化数据中取材；不允许"补全"标题、链接或来源。
- 规则 3 同时要求 SVO（主-谓-宾）句式，禁止编造因果链。
- 规则 5：Smart Fill 是允许的"软扩展"，但条目必须 ⚠️ 前缀；International News 是硬 24h 窗口，不允许扩展。

---

## 二、Anti-Laziness Protocol（verbatim 自 briefing_general.md:10-21）

```
## ⚠️ Anti-Laziness Protocol (STRICT)

1. Volume Target (REAL ITEMS ONLY): The input JSON usually contains ~60+ items.
   - Target: Aim for 20-25 distinct items, but NEVER invent items to meet this number.
   - Global Scan: Pick top 10-15 real items.
   - HN AI: Pick top 5-8 real items.
   - GitHub: Pick top 8-10 real items.
2. No Aggregation: Do NOT summarize multiple distinct news items into one bullet point. One Item = One Section.
3. Deep Dive & Linking:
   - Hacker News: You MUST include [Discussion](hn_url) next to the Source.
   - Context: Use the content field for deep analysis.
```

中文解读：宁可少 5 条真条目，也绝不为了凑数编造；禁止把多条新闻聚合为一个 bullet。

---

## 三、Time 处理规则（MISTAKES.md:3-24 教训萃取）

| 子规则 | 内容 |
|---|---|
| **MANDATORY** | Time 字段不可缺。JSON 缺失则标 "Unknown Time"，不允许猜测。 |
| **绝对时间** | 数据层必须 `YYYY-MM-DD HH:MM`，禁止裸 `HH:MM`（会被误读为今日/昨日）|
| **展示层转换** | "1h ago" 这类相对时间只能在渲染层根据绝对时间换算，不能存进数据层 |
| **Unknown Time** | 保留原始字符串如 "Real-time" / "Today" / "Hot"，不强行格式化 |
| **Smart Fill ⚠️** | 跨时间窗口补来的条目必须以 ⚠️ 前缀标注，且不允许出现在 International 区 |

教训来源：`~/research-tmp/news-aggregator-skill/MISTAKES.md:3-24` (WallStreetCN Timestamp Ambiguity, 2026-01-24)

---

## 四、Source 处理规则

- **One Item = One Section**（briefing_general.md:17）：禁止把多条新闻合并为一个 bullet 或一个 section。
- **24h 窗口强制**（SKILL.md:64）：International News 必须只用最近 24h RSS 条目，不允许 Smart Fill 补旧条目。
- **Empty Data = mother of Hallucination**（MISTAKES.md:55）：fetcher 返回 0 条结果时必须触发 fallback（如"广义 keyword 重试"），不能让 LLM"帮忙"凑数。
- **CLI stdout first**（MISTAKES.md:91）：永远以本次 CLI 工具调用的 stdout 为唯一真源；不要去项目根目录读 `*_raw.json` 这类 stale 缓存。读 cache 之前先校验 mtime 与内部日期字段。
- **路径规范**（MISTAKES.md:88）：报告/数据写入 `reports/YYYY-MM-DD/`，不要在 root 自由发挥。

---

## 五、SVO 句式约束（MISTAKES.md:60-74）

- 用简单 SVO（subject-verb-object）句式描述新闻
- 禁弱因果连接词：避免 "虽然/Although/可能/However" 在因果链薄弱时硬连
- 不编造因果关系：grammar fix 同时也是 fact claim，改写句子=新增事实声明，必须可验证
- 例："半决赛大胜晋级决赛"中"大胜"是事实陈述，写之前必须有数据支持

---

## 六、检测+重写流水线（与 anti-refusal-prompt 协同）

1. **assembly** 写完正文后，跑 [./banned-phrases-and-probability-scale.md](./banned-phrases-and-probability-scale.md) 提供的 regex 扫描
2. 命中 banned phrase 或 hedge phrase → 触发 forced-answer rewrite（参考 `web-research-router/references/anti-refusal-prompt.md`）
3. 重写一次后仍命中 → REJECT，audit log 标 `anti-halluc-fail`
4. 不阻塞渲染：REJECT 条目降级为 `需 cross-check` tag，保留在末尾"待核实"区块

---

## 七、Audit 时检查清单（embedded into 7 sentinels）

- [ ] 所有 bullet 带绝对日期或 `(日期不详)` 标记？
- [ ] 时间戳是 `YYYY-MM-DD HH:MM` 完整格式（无裸 HH:MM）？
- [ ] Smart Fill 条目带 ⚠️ 前缀？且 International 区无 ⚠️？
- [ ] banned phrase regex 扫零命中？
- [ ] 无弱因果连接词（虽然 / Although / However + 弱因果）？
- [ ] One Item = One Section（无多条聚合 bullet）？
- [ ] 来源链接为 fetcher 真返回的 URL（不是 LLM 拼出的）？

---

## 八、源文件路径与行号

| 规则块 | Source |
|---|---|
| Anti-Hallucination 6 条核心 | `~/research-tmp/news-aggregator-skill/SKILL.md:173-180` |
| Anti-Laziness Protocol | `~/research-tmp/news-aggregator-skill/instructions/briefing_general.md:10-21` |
| International 24h 硬窗口 | `~/research-tmp/news-aggregator-skill/SKILL.md:64` |
| 时间戳格式教训 | `~/research-tmp/news-aggregator-skill/MISTAKES.md:3-24` |
| Empty Data is Dangerous | `~/research-tmp/news-aggregator-skill/MISTAKES.md:55` |
| SVO + 弱因果禁连 | `~/research-tmp/news-aggregator-skill/MISTAKES.md:60-74` |
| CLI stdout first / stale cache | `~/research-tmp/news-aggregator-skill/MISTAKES.md:78-93` |
