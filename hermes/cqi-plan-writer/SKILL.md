---
name: cqi-plan-writer
description: |
  Writes and updates 持续质量改进 (CQI) plans for Hermes skills. Signal-driven. 
  Every issue traces signal→root cause→fix→verify. Every claim anchors in measured data. 
  Supports restructure-on-update pattern (completed→appendix, in-progress→update, new→add). 
  Use when: 写CQI, 做CQI, 质量改进计划, CQI plan, 回写CQI, 重构CQI, 改进skill, CQI写得太差, 审查CQI. 
  Do NOT use for: 架构文档（纯设计无问题追踪）, 功能路线图, 状态报告, 一次性的bug report.
version: 1.2.0
author: Hermes Agent — v1.2 重构回写 + 硬证据锚定 + 已完成附录 + 重大决策协议 + 双链归档 + Mermaid
license: MIT
metadata:
  hermes:
    tags: [governance, cqi, skill-authoring, quality]
    related_skills: [skill-authoring, grill-with-docs, obsidian-md-ac, claude-code]
---

# CQI Plan Writer v1.2

> Signal-driven, not template-driven. Every issue traces. Every claim anchors in measured data.
> **v1.2 核心升级（2026-06-07 WRR CQI 实战总结）**：重构回写模式 + 硬证据锚定 + 已完成项附录表 + 重大决策前置协议 + Obsidian 双链规范。

## 🚨 Red Flags: DO NOT WRITE CQI WRONG

| 你会找的借口 | 为什么错 |
|-------------|---------|
| "I'll start with the architecture diagram first" | CQI starts with problems, not architecture. |
| "我直接 patch 旧文档追加几段新内容就行" ★ | **WRR CQI 教训。** 每次回写应**重构全文**——已完成→附录、进行中→更新、新发现→新增。patch叠加=熵增。 |
| "内容太多，压缩到 300 行就够了" ★ | CQI 是 skill 迭代基石，过度压缩=丢失关键上下文。按需决定节数，不复用死模板。 |
| "~90% success rate sounds fine" | If you can't run a command that returns the number, don't write it. |
| "I'll just overwrite the old CQI with new findings" ★ | 旧内容必须保留：操作型用 `📝`+`🔧` 合并，架构级用重构+已完成→附录。 |
| "链接写 /tmp/ 或外部 URL 就行" ★ | Obsidian 内必须用 `[[wikilinks]]`。研究产物归档到 `40-Archives/10_Projects_Archive/`。 |
| "不用 Mermaid 图，纯文字够了" ★ | 架构决策用 Mermaid 图=agent 一眼看懂。WRR CQI 的 3 层分离图省了 200 行。 |
| "已完成项删掉就行" ★ | 沉淀到 §历史已完成 CQI 项 附录表（时间倒序）。删掉=下次重蹈覆辙。 |
| "数据可以用'很多'、'比较慢'等模糊词" ★ | 必须用实测数字（82进程/1.56GB, Exa 1.25s, Brave 0.77s）。模糊词=不可信。 |

## 🔀 Decision Tree

```
写 CQI / 回写 CQI？
│
├── 是回写已有 CQI → ★ 重构模式（非 patch 追加）
│   ├── Step 0: 读旧 CQI 文档全文
│   ├── 识别三类内容：
│   │   ├── ✅ 已完成线程 → 移到 §历史已完成 CQI 项 附录表
│   │   ├── 🔄 进行中线程 → 保留在主文，更新进展
│   │   └── 🆕 新发现/决策 → 新增为主文章节
│   ├── 重新编号章节，保持逻辑流
│   └── 压缩同类线程
│
├── 是全新 skill → 从零创建
│   ├── 搜索 Supermemory + session 了解背景
│   ├── 读目标 skill 的 SKILL.md 了解当前状态
│   └── 提取 version history 作为附录表初始数据
│
├── 有重大架构决策（多方案选型）？
│   ├── YES → 必须先讨论后写文档（见 §重大决策前置协议）
│   └── NO → 直接写
│
└── NOT a CQI task → stop
```

---

## 通用文档结构

CQI 骨架一致，节数按需增减：

```markdown
---
YAML frontmatter — status/type/priority/aliases/tags/created/modified
---

# <Skill> 持续质量改进计划

> [!abstract] TL;DR
> 一句话总结

## 一、背景与驱动力
## 二、现状诊断 — 硬证据驱动
## 三、架构决策 / 核心架构设计（如有）
## 四～N、线程或问题分组
## N+1、分阶段实施方案
## N+2、成功标准 — 每项数字目标 + 测量方式
## N+3、风险 — 影响 + 缓解
## N+4、关联 — Obsidian wikilinks + 外部 links
## N+5、历史已完成 CQI 项（附录）
```

---

## Issue Format: 6-Element Traceability

Every issue must have ALL six elements:

| # | Element | Question | Example |
|:--|:--------|:---------|:--------|
| 1 | **Signal** | Where was the problem observed? | `fetch_all.py` returned null for subtitles |
| 2 | **Root Cause** | What caused it? | fallback chain not implemented |
| 3 | **Fix** | What change solves it? | Add audio download + whisper call |
| 4 | **Verify** | What command proves it's fixed? | `fetch_subtitle_auto.py <BV>` → has transcript |
| 5 | **Before** | What was the failure rate? | 2/2 videos needed manual intervention |
| 6 | **After** | What's the target? | 0 manual steps |

---

## Priority Tiers

| Tier | Criteria | Examples |
|:-----|:---------|:---------|
| 🔴 **P0** | Data pipeline broken → downstream fails | Subtitle fallback not triggering, file path mismatch |
| 🟡 **P1** | Output quality degraded → user must manually fix | Report too thin, logic chain bloated |
| 🟢 **P2** | Edge cases / nice-to-have | Multi-video merge, cross-session staleness |

---

## 🔄 Restructure Pattern: Updating Existing CQI ★ (v1.2)

每次 CQI 回写 = **全文重构**（非 patch 追加），但必须保留旧版实质内容。

### 三类内容处理

| 内容类型 | 处理 | 示例 |
|---------|------|------|
| ✅ 已完成线程 | → §历史已完成 CQI 项 附录表（时间倒序） | Scrapling 微信实测→附录 v3.9 |
| 🔄 进行中线程 | 保留在主文，更新进展，压缩同类 | 5 个 threads → 主+辅助线程 |
| 🆕 新发现/决策 | 新增为主文章节 | MCP架构决策 → §三+§四 |

### 关键规则

**1. 硬证据锚定** — 所有诊断锚定实测数据。禁止模糊词。工具：`ps aux`（进程/资源）、`curl -w`（API延迟）、`grep`+行号（源码位置）、计算+来源（token消耗）。

**2. Obsidian 双链规范** — 同 vault 用 `[[笔记名]]`；研究产物用 `[[40-Archives/10_Projects_Archive/项目名/文件]]`；**禁止** `/tmp/` 路径。

**3. 重大决策前置协议** — 多方案选型/架构变更时，先讨论后写：写背景文件 → CC agent team + 太子并行评估 → 调和分歧 → 写入CQI → 研究产物归档到 `40-Archives/` → 创建索引笔记。

**4. 附录表格式** — `| 日期 | 版本 | 类别 | 改进项 | 说明 |`。来源：目标 skill 的 SKILL.md version headers + CHANGELOG。

**5. Mermaid 图** — 系统分层用 `flowchart TD` + subgraph。用 Python `open().write()` 直写避免行号污染。

**6. 美化** — 写完必须加载 `obsidian-md-ac`：emoji标题、callout选型、YAML五维元数据、双链+关系符号。

**7. 避免行号污染** — 用 Python 原生 `open().read()` 读旧文档、`open().write()` 写新文档。**禁止** `execute_code` 的 `read_file`/`write_file` 做 CQI 读写。

### 反例：2026-06-07 WRR CQI 三版迭代

| 版本 | 行数 | 问题 |
|------|------|------|
| v1 | 847 | 5线程并列但无架构决策、无附录 |
| v2 压缩版 | 290 | **过度压缩**——丢失线程A-D实质内容 |
| v2 终版 | 638 | ✅ 结构升级+内容保留+架构决策+附录表 |

---

## Quality Gates (Run Before Saving)

- [ ] 回写时：旧 CQI 全文已读？三类内容已分类（✅已完成/🔄进行中/🆕新发现）？
- [ ] 所有诊断有实测数字锚定（非"大概"、"可能"）？
- [ ] 链接为 Obsidian wikilinks（非 `/tmp/` 路径）？
- [ ] 重大决策经 CC + 太子讨论后写入？
- [ ] 已完成项沉淀到附录表？
- [ ] 加载 `obsidian-md-ac` 做了美化？
- [ ] 无行号污染（用 Python 原生 open() 读写）？

---

## Workflow Integration

CQI 是 skill 改进的输入：`cqi-plan-writer`（写CQI）→ `skill-authoring`（改SKILL.md）→ CC audit（验证修复）。

---

## Pitfalls

| Trap | Consequence |
|------|-------------|
| Writing architecture instead of problems | CQI reads like system docs, not improvement plan |
| Fake metrics (~90%) without measurement | Can't verify, can't track, trust destroyed |
| **Overwriting old CQI** ★ | User's historical observations lost permanently |
| No source attribution | Can't tell what was user-found vs agent-found |
| **过度压缩** ★ | 丢失关键上下文，用户纠正返工 |
| **行号污染** ★ | YAML frontmatter解析失败，文件永久损坏 |
| **归档目录放错** ★ | `02-Plan&CQI/` 堆杂物，研究产物应放 `40-Archives/` |

---

## ✅ Verification Checklist (RUN BEFORE SAVING)

- [ ] Read existing CQI doc before writing (if updating)?
- [ ] Three content types classified (✅completed/🔄in-progress/🆕new)?
- [ ] Claims anchored in measured data (not "many"/"slow"/"probably")?
- [ ] Links use Obsidian wikilinks (not /tmp/ paths)?
- [ ] Major decisions went through CC + regent discussion protocol?
- [ ] Completed items moved to appendix table (date + version + category)?
- [ ] `obsidian-md-ac` loaded for beautification?
- [ ] Written with Python native open() (no line-number pollution)?
