# 禁词与概率刻度 v1.0 (morning-news-briefing v4.0)

> **Read when:** 分析段落写作 / Critic regex 自动驳回 / audit 步骤。本规则给 morning-news 注入"质量地板"。
> **Source:** `~/research-tmp/the-briefing/agents/writer.py:52-101` + `agents/critic.py:48-78` (the-briefing PIC pipeline)
> **Sibling refs:** [./anti-hallucination-rules.md](./anti-hallucination-rules.md) · [./analysis-format.md](./analysis-format.md)

---

## 一、Writer Banned Phrases（写作禁词）

### 英文 — Writer prompt verbatim（the-briefing/agents/writer.py:52-60）

```
BANNED PHRASES (instant failure if used):
- "significant developments"
- "remains to be seen"
- "time will tell"
- "various factors"
- "could potentially"
- "the situation is evolving"
- "in the coming weeks"
- "major implications"
```

### 英文 — Critic regex 全集 verbatim（agents/critic.py:52-68）

```python
BANNED_PHRASES = [
    "remains to be seen",
    "time will tell",
    "could potentially",
    "significant developments",
    "various factors",
    "the situation is evolving",
    "in the coming weeks",
    "major implications",
    "it is unclear",
    "only time will tell",
    "the jury is still out",
    "at the end of the day",
    "moving forward",
    "perfect storm",
    "game changer",
]
```

### 中文等价（本地化补充）

| 英文 | 中文等价 | 为什么禁 |
|---|---|---|
| significant developments | 重大进展 / 意义重大 | 空话、无具体动作 |
| remains to be seen | 尚待观察 / 有待时间检验 | 推卸判断 |
| time will tell / only time will tell | 时间会证明 / 时间会给出答案 | 不下断 |
| various factors | 多重因素 / 综合多方原因 | 不解释因果 |
| could potentially | 可能潜在 / 或许会 | 双重弱化 |
| the situation is evolving | 形势仍在演变 / 局势仍在发展 | 套话 |
| in the coming weeks | 未来几周 / 接下来数周 | 模糊时间 |
| major implications | 重大影响 / 深远意义 | 不具体 |
| it is unclear | 尚不清楚 | 应明示"已知/未知" |
| the jury is still out | 尚无定论 / 仍存争议 | 推卸判断 |
| at the end of the day | 归根结底 / 说到底 | 总结陈词式套话 |
| moving forward | 展望未来 / 接下来 | 套话过渡 |
| perfect storm | 完美风暴 | 滥用比喻 |
| game changer | 游戏规则改变者 / 颠覆性 | 营销腔 |

---

## 二、Sherman Kent 概率刻度

### Writer prompt verbatim（the-briefing/agents/writer.py:92-101）

```
<sherman_kent_scale>
Use ONLY these probability terms:
- ALMOST CERTAIN (93-99%)
- HIGHLY LIKELY (80-92%)
- LIKELY (60-79%)
- ROUGHLY EVEN (40-59%)
- UNLIKELY (21-39%)
- HIGHLY UNLIKELY (8-20%)
- REMOTE (1-7%)
</sherman_kent_scale>
```

### Critic 校验集 verbatim（agents/critic.py:70-78）

```python
SHERMAN_KENT_TERMS = [
    "ALMOST CERTAIN",
    "HIGHLY LIKELY",
    "LIKELY",
    "ROUGHLY EVEN",
    "UNLIKELY",
    "HIGHLY UNLIKELY",
    "REMOTE",
]
```

### 中英对照表（唯一允许的 7 档）

| # | 概率区间 | 英文 | 中文 |
|---|---|---|---|
| 1 | 93-99% | ALMOST CERTAIN | 几乎确定 |
| 2 | 80-92% | HIGHLY LIKELY | 极有可能 |
| 3 | 60-79% | LIKELY | 较可能 |
| 4 | 40-59% | ROUGHLY EVEN | 不相上下 / 大致五五开 |
| 5 | 21-39% | UNLIKELY | 不大可能 |
| 6 | 8-20% | HIGHLY UNLIKELY | 极不可能 |
| 7 | 1-7% | REMOTE | 几无可能 |

### Opening template（writer.py:78-82 verbatim）

```
"Constrained by [CONSTRAINT], [ACTOR] is [PROBABILITY] to [ACTION], likely resulting in [3RD ORDER EFFECT]."

Example:
"Constrained by depleted foreign reserves and IMF conditionality, Ankara is HIGHLY LIKELY (80-90%) to delay further rate cuts, forcing a pivot toward Gulf sovereign wealth funds that will deepen Turkey's strategic dependency on Riyadh."
```

中文版（本地化）：

```
"在 [约束] 之下，[主体] [概率词] [将采取行动]，可能导致 [三阶效应]。"

示例：
"在外汇储备耗尽与 IMF 条件性贷款约束下，安卡拉（80-92%）极有可能延后进一步降息，迫使其转向海湾主权基金，并加深土耳其对利雅得的战略依附。"
```

---

## 三、Critic Regex 自动驳回（audit 步骤用）

```bash
# 1. 英文禁词扫描（Writer prompt 8 条 + Critic 全 15 条）
grep -niE "significant developments|remains to be seen|time will tell|various factors|could potentially|the situation is evolving|in the coming weeks|major implications|it is unclear|only time will tell|the jury is still out|at the end of the day|moving forward|perfect storm|game changer" "$file"

# 2. 中文禁词扫描
grep -niE "重大进展|尚待观察|时间会证明|多重因素|可能潜在|形势仍在演变|未来几周|重大影响|尚不清楚|尚无定论|归根结底|展望未来|完美风暴|游戏规则改变者" "$file"

# 3. 非法概率词（出现 % 但不在 7 档之内）
grep -niE "[0-9]+(\.[0-9]+)?%" "$file" | grep -viE "93-99|80-92|60-79|40-59|21-39|8-20|1-7"

# 4. 必须出现 Sherman Kent 至少一档（分析段缺则降级）
grep -ciE "ALMOST CERTAIN|HIGHLY LIKELY|LIKELY|ROUGHLY EVEN|UNLIKELY|HIGHLY UNLIKELY|REMOTE|几乎确定|极有可能|较可能|不相上下|不大可能|极不可能|几无可能" "$file"
```

Critic 评分对照（agents/critic.py:606-620 verbatim 逻辑）：

```python
weasels_found = [p for p in BANNED_PHRASES if p.lower() in draft_lower]
if not weasels_found:
    return 20, []
deduction = min(20, len(weasels_found) * 5)
return 20 - deduction, [f"Remove banned phrases: {weasels_found[:3]}"]
```

即每命中 1 个 banned phrase 扣 5 分，封顶 20 分。

---

## 四、与 anti-refusal-prompt.md 的协同

- 本文件提供"质量地板" regex（hard reject 集）
- `web-research-router/references/anti-refusal-prompt.md` 提供"hedge 检测 + 重写"循环（soft rewrite）
- 一致流程：banned phrase 命中 → 调用 anti-refusal forced-answer rewrite → 重跑 regex → 仍命中 → REJECT，audit log 标 `banned-phrase-fail`，条目降级为"待核实"

---

## 五、源路径与行号

| 内容 | Source |
|---|---|
| Writer BANNED PHRASES（8 条） | `~/research-tmp/the-briefing/agents/writer.py:52-60` |
| Critic BANNED_PHRASES（15 条） | `~/research-tmp/the-briefing/agents/critic.py:52-68` |
| Sherman Kent 7 档（writer） | `~/research-tmp/the-briefing/agents/writer.py:92-101` |
| Sherman Kent 7 档（critic） | `~/research-tmp/the-briefing/agents/critic.py:70-78` |
| Opening template + 示例 | `~/research-tmp/the-briefing/agents/writer.py:71-83` |
| Critic 扣分逻辑 | `~/research-tmp/the-briefing/agents/critic.py:606-620` |
| Sherman Kent 校验逻辑 | `~/research-tmp/the-briefing/agents/critic.py:235-246` |
