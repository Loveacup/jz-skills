---
name: source-verification
description: |
  Use when a draft briefing/report contains factual claims (prices, figures, policies, rankings, named statements) that must be confirmed against live web sources before delivery. Does: claim extraction → per-claim web re-verification → confidence labeling (verified / partial / contradicted / not found) → gate decision. 通用「声明级事实核验」skill,被 morning-news-briefing / news-assembly 等复用。
  Triggers: 事实核验, 声明验证, claim verification, fact-check claims, 核实数字, verify sources.
  DO NOT use for: 搜索发现(用 web-research-router)、汇编去重(用 news-assembly)、去 AI 味(用 de-slop)、整篇 deep-research 报告(用 web-research-router deep loop)。
version: 1.0.0
author: Hermes Agent (v1.0 — P2 外包,从 morning-news-briefing 抽出的独立核验闸门)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [verification, fact-check, claims, sources, anti-hallucination, gate, reusable]
    related_skills: [web-research-router, news-assembly, morning-news-briefing]
---

# Source Verification v1.0

声明级事实核验闸门。输入一篇草稿 + 其 `source_map`，对**高风险 claim**（价格/数据/政策/排名/具名声明）逐条做 web 二次核验，给每条标 4 档置信度，按门禁规则决定删除 / 标注 / 放行。

**定位**：这是**核验闸门**，不是搜索器。发现取数走 `web-research-router`；本 skill 只做"草稿里的话能不能在原始来源 + 实时 web 找到支撑"。

## 🚨 Red Flags: DO NOT SKIP

| Excuse | Why it's wrong |
|---|---|
| "汇编时已经引过来源了，不用再核" | 汇编引用 ≠ claim 被验证。LLM 综合时会把两条来源的数字串味、把"约 5%"写成"5.2%"。必须逐条回到 `extracted_quotes[]` 比对 |
| "全篇都核一遍" | 浪费成本且拖垮交付。**只核高风险 claim**（价格/数据/政策/排名/具名声明），叙述性/推理层句子不进核验队列 |
| "contradicted 就标个⚠️留着" | contradicted = 两来源互斥，留着就是发布错误事实。必须**删除并回退重写**该段，不能软标注 |
| "core_map 损坏就跳过整个核验" | source_map 损坏时降级为**纯 web 二次核验**（不比对 quote），仍要出置信度，不可整体跳过 |
| "not found 等于假的，删掉" | not found ≠ 假。可能是推理层产出或冷门事实。标 `⚠️未验证` 保留，不删除（删除 = 误伤分析层） |

## 🔀 Decision Tree

```
草稿 + source_map 就绪？
├── Step 1: Claim 抽取
│   从草稿正文抽出高风险 claim（不抽叙述/推理句）：
│   ├── 价格/数字   ($78.3/barrel、GDP 5.2%、涨跌幅、market cap)
│   ├── 政策/法规   (X 部 Y 月起施行、税率调整、禁令)
│   ├── 排名/序数   ("全球第一"、"史上最大"、"首次")
│   └── 具名声明     ("X 表示…"、"Y 公司宣布…")
│   → claims[]: {id, text, type, citation_id, char_offset}
│   ⚠️ 抽样上限：≤10 条/版（按风险排序取 top-N，叙述层不进队列）
│
├── Step 2: 逐条核验（每 claim 两路证据）
│   ├── 路 A — 内部比对：回 source_map.extracted_quotes[] 找直接支撑的 verbatim quote
│   └── 路 B — 外部二次核验：对价格/数据/政策类，独立调 web_search / web-research-router
│   │         grounding（不复用原 URL，换源交叉）
│   详见 references/claim-verification-workflow.md
│
├── Step 3: 标置信度（4 档，见下）
│   verified / partial / contradicted / not found
│
└── Step 4: 门禁决策 + 落盘
    按「门禁规则」表处理每条 → 写 verification-{date}.json
```

## 📊 置信度 4 档

| 档 | 判定 | 标记 |
|---|---|---|
| **verified** | `extracted_quotes[]` 直接支撑 **或** web 二次核验一致（数字 ±2% 内） | 通过 |
| **partial** | 间接支撑 / 口径可能不同（如"约""左右"、单位换算、时点差） | `📎 部分验证`，通过 |
| **contradicted** | 两个来源相互矛盾，或 web 核验与草稿数字超 ±2% 冲突 | `🔴` |
| **not found** | 任何 source + web 都查不到支撑 | `⚠️ 未验证` |

## 🚦 门禁规则（被调用方据此动作）

| 档 | 动作 |
|---|---|
| **contradicted** | **删除该 claim + 回退重写该段落**（hard）。不可软标注保留 |
| **not found** | 标 `⚠️ 未验证` **保留**（可能是推理层产出），不删除、不阻塞 |
| **partial** | 标 `📎 部分验证`，通过 |
| **verified** | 直接通过 |
| **放行条件** | 全部 claim ∈ {verified, partial, not found(已标注)} 且**无 contradicted 残留** → 通过 |

> 与调用方对齐：本 skill 的**唯一硬阻塞是 contradicted**。`not found` 是软标注、不阻塞交付（与 morning-news-briefing `p2-outsourcing-integration.md` 第 2 节一致）。

## ⚡ Core Rules

1. **只核高风险 claim，抽样 ≤10 条/版** — 按风险排序取 top-N；叙述句/推理句不进队列。逐条全核会拖垮交付。
2. **两路证据，外部换源交叉** — 路 A 比对 `extracted_quotes[]`，路 B 对价格/数据/政策**独立换源** web 二次核验（不复用原 URL，否则等于自证）。
3. **唯一硬阻塞 = contradicted** — contradicted 必删 + 回退重写；not found 软标注保留；partial 通过。
4. **数字容差 ±2%** — 价格/比率类，web 核验与草稿差 ≤2% 判 verified，超过判 contradicted（取中位 + 标"数据冲突"）。
5. **source_map 损坏不整体跳过** — 降级为纯 web 二次核验（仅路 B），仍出置信度；标 `verification-degraded`。
6. **结果落盘** — `verification-{date}.json`，含每条 claim 的 `{id, type, label, evidence, action}`。

## 错误处理

| 故障 | 降级 |
|---|---|
| `source_map` 损坏/缺失 | 仅走路 B（纯 web 核验），标 `verification-degraded`，不整体跳过 |
| web_search 全部超时 | 仅走路 A（内部比对），标 `verification-internal-only`，无外部交叉的 claim 降级为 partial |
| 全部 claim 都 not found | 不阻塞交付，但日志 `WARN: zero-verified`，提示来源链可能断裂 |
| 抽不出任何高风险 claim | 跳过核验，标 `no-verifiable-claims`，通过 |

## References

| File | Content |
|---|---|
| `references/claim-verification-workflow.md` | claim 抽取规则 + 两路证据取证流程 + ±2% 容差判定 + 落盘 schema |

## 调用方接口（被 morning-news-briefing 等复用）

```
输入: { draft_path, source_map_path }   # 草稿 md + 落盘的 source_map JSON
输出: verification-{date}.json          # 每 claim 置信度 + 动作
副作用: contradicted → 调用方据此删 claim + 回退重写;其余调用方按标记渲染
```
