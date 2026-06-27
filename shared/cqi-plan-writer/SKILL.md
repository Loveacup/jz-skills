---
name: cqi-plan-writer
description: |
  Writes and updates 持续质量改进 (CQI) plans — domain-agnostic methodology.
  Core: 8-element traceability (Signal→Impact→Root Cause→Fix→Verify→Before→After→Lessons Learned).
  4 domain profiles: Skill (agent skills) · Incident (postmortems) · System (architecture) · Process (business).
  Every issue traces. Every claim anchors in measured data. Every plan earns a health score.
  Use when: 写CQI, 做CQI, 质量改进计划, 事故复盘, 系统改进, 流程优化, CQI plan, postmortem, improvement plan, 审查CQI.
  Do NOT use for: 纯架构文档（无问题追踪）, 功能路线图, 状态报告, 一次性 bug report.
version: 2.0.0
author: Hermes Agent — v2.0 通用化 + 8 元素 + 4 Profile + 置信度 + 健康评分 + 自动信号采集
license: MIT
metadata:
  hermes:
    tags: [governance, cqi, quality, methodology, postmortem, improvement, skill-authoring]
    related_skills: [skill-authoring, grill-with-docs, obsidian-md-ac, claude-code]
---

# CQI Plan Writer v2.0

> **通用持续质量改进写作方法论。** Signal-driven, domain-agnostic.
>
> **v2.0 核心升级（2026-06-17）**：通用化重构。吸收 SRE postmortem 模板（8 元素格式）、claude-reflect（置信度+自动信号）、muratcankoylan（量化健康评分）、Varietyz（ALWAYS/NEVER 规则）。新增 4 个领域 Profile，Skill CQI 降级为其中一个 Profile。
>
> **v1.2 遗产**：重构回写模式、硬证据锚定、重大决策前置协议、Obsidian 双链规范——全部保留在 profile-skill 中。

---

## 🚨 Red Flags: DO NOT WRITE CQI WRONG

| 你会找的借口 | 为什么错 |
|-------------|---------|
| "这是给 XX 领域写的，方法论不能通用" | CQI 骨架（Signal→Root Cause→Fix→Verify→Lessons Learned）适用于任何领域。SRE postmortem、PIP、CAPA、PDCA 共用同一套核心结构。 |
| "I'll start with the architecture diagram first" | CQI starts with problems, not architecture. |
| "我直接 patch 旧文档追加几段就行" | 每次回写应**重构全文**——已完成→附录、进行中→更新、新发现→新增。patch 叠加 = 熵增。 |
| "内容太多，压缩到 300 行就够了" | CQI 是迭代基石，过度压缩 = 丢失关键上下文。按需决定节数，不复用死模板。 |
| "~90% success rate sounds fine" | 不能跑命令得出数字就不要写。 |
| "数据可以用'很多'、'比较慢'等模糊词" | 必须用实测数字（82进程/1.56GB, Exa 1.25s）。模糊词 = 不可信。 |
| "已完成项删掉就行" | 沉淀到 §历史已完成 CQI 项附录表（时间倒序）。删掉 = 下次重蹈覆辙。 |

---

## 🔀 Decision Tree: 我需要什么类型的 CQI？

```
用户说"写 CQI / 做复盘 / 改进计划"？
│
├── 对象是什么？
│   ├── Hermes/agent skill → 加载 references/profile-skill.md
│   ├── 系统/架构/基础设施 → 加载 references/profile-system.md
│   ├── 事故/故障/安全事件 → 加载 references/profile-incident.md
│   └── 业务流程/工作流 → 加载 references/profile-process.md
│
├── 是新写还是回写？
│   ├── 回写已有 CQI → ★ 重构模式（非 patch 追加）
│   │   ├── Step 0: 读旧 CQI 文档全文
│   │   ├── 识别三类内容：
│   │   │   ├── ✅ 已完成线程 → 移到 §历史已完成 CQI 项 附录表
│   │   │   ├── 🔄 进行中线程 → 保留在主文，更新进展
│   │   │   └── 🆕 新发现/决策 → 新增为主文章节
│   │   ├── 重新编号章节，保持逻辑流
│   │   └── 压缩同类线程
│   └── 全新 → 从零创建
│       ├── 搜索 Supermemory + session 了解背景
│       ├── **⚠️ 对照源码实测（Skill Profile 必须）** — 旧 CQI/审计文档只是方向参考，不是事实。必须先读目标 skill 的 SKILL.md + 实跑测试套件 + 实查部署状态，独立取证后再写。见 Pitfalls：信任旧审计文档是 2026-06-17 真实教训。
│       ├── 对目标对象做健康评分（见 §健康度量化评分）
│       └── 按 Profile 模板填充
│
├── 有重大架构决策（多方案选型）？
│   ├── YES → 必须先讨论后写文档（见重大决策前置协议，profile-skill 专属）
│   └── NO → 直接写
│
└── NOT a CQI task → stop
```

**第一步强制动作**：在任何 Profile 加载前，先用 `references/health-scoring.md` 的维度对改进对象做一次快速健康评分。这个数字是 CQI 的基线，也是后续验证改进效果的对标。

---

## 🧬 通用 CQI 骨架：8 元素追溯格式

这是所有 Profile 共用的 issue 描述格式。**每个 issue 必须包含全部 8 个元素。**

| # | 元素 | 问什么 | 示例 |
|:--|:-----|:------|:-----|
| 1 | **Signal** | 在哪发现的？怎么发现的？ | `fetch_all.py` returned null for subtitles；用户在 Telegram 反馈 |
| 2 | **Impact** | 影响多大？范围？持续时间？ | 2/2 videos failed；影响 xhs-crawler 全链路；持续 3 天 |
| 3 | **Root Cause** | 根因是什么？（不是表象） | fallback chain not implemented；而非 "subtitles 没了" |
| 4 | **Fix** | 怎么修？改了什么？ | Add audio download + whisper fallback call |
| 5 | **Verify** | 怎么证明修好了？什么命令/数据？ | `fetch_subtitle_auto.py <BV>` → has transcript；0 manual steps |
| 6 | **Before** | 修之前多差？（量化） | 2/2 videos needed manual intervention；100% failure rate |
| 7 | **After** | 修之后目标是什么？（量化） | 0 manual steps；95% auto-success rate |
| 8 | **Lessons Learned** | 学到了什么？下次怎么避免？ | 所有 fetch 链必须实现 fallback；新 skill 创建时强制加 fallback gate |

**置信度标注**（🆕 v2.0）：每个 issue 末尾标注 confidence 分数：

| 分数 | 含义 | 何时用 |
|------|------|--------|
| 0.90–0.95 | **硬确认** — 有 verbatim log、报错信息、可复现步骤 | Root cause 已通过复现确认 |
| 0.75–0.89 | **高置信** — 有间接证据链，尚缺直接复现 | 多个用户报告同一问题 |
| 0.60–0.74 | **推断** — 基于模式匹配，需进一步验证 | "看起来像 X 类问题" |

标注方式：在 Verify 行后追加 `**Confidence:** 0.85 — 两个独立 session 确认，尚未在干净环境复现`

---

## 📊 优先级体系

| Tier | 触发条件 | 行动要求 |
|:-----|:---------|:---------|
| 🔴 **P0** | 数据管线断裂 / 下游全阻断 / 安全事故 | 立即修复，阻塞所有其他工作 |
| 🟡 **P1** | 输出质量下降 / 用户须手动修复 / 性能退化 >30% | 当前迭代内修复 |
| 🟢 **P2** | 边界情况 / 体验优化 / 技术债 | 排入 backlog，不阻塞当前工作 |
| 🔵 **OBS** | 观测项 — 值得留意但尚未形成问题 | 记录在案，下次回写时评估是否升级 |

> 🆕 **OBS 层级**：从 claude-reflect 的信号采集机制来——不是所有信号都需要立即行动。低置信度、单次出现、影响小的信号进入 OBS，累积到 3 次出现后自动升级评估。

---

## 🏷️ 领域 Profile 系统

Profile 是加载在核心骨架上的领域特化层。**选择 Profile 后加载对应的 reference 文件，按其模板输出 CQI 文档。**

| Profile | 参考文件 | 适用场景 | 特有元素 | 文档结构差异 |
|---------|---------|---------|---------|------------|
| **Skill** | `references/profile-skill.md` | Hermes/agent skill 改进 | 重构回写模式、Obsidian 双链、CC+太子协议、版本附录 | 线程分组 + 架构决策段 |
| **Incident** | `references/profile-incident.md` | 事故/故障/安全事件复盘 | Timeline、blameless 文化、What went well/wrong/lucky、Detection | Timeline 为核心叙事线 |
| **System** | `references/profile-system.md` | 架构/系统质量改进 | ALWAYS/NEVER 规则、VALIDATION GATE 块、架构合规检查 | 门控段 + 合规矩阵 |
| **Process** | `references/profile-process.md` | 业务流程/工作流改进 | PDCA 映射、Before/After 指标对比表、利益相关者分析 | 指标对比表驱动 |

**Profile 间的共同点**：
- 都用同一个 8 元素 issue 格式
- 都用同一套优先级体系
- 都走同样的质量门检查
- 都产出一个数字健康评分

**Profile 间的差异**：
- 文档叙事结构不同（Incident 以 Timeline 驱动；Skill 以线程分组驱动）
- 领域特有的约束规则不同
- 成功标准的量化维度不同

---

## 🔁 跨领域机制

### 自动信号采集

CQI 不应该是纯手动写作。以下信号源应该被自动扫描：

| 信号源 | 采集方式 | 信号类型 |
|--------|---------|---------|
| **Session 历史** | `session_search` 搜 "bug/fix/错了/不对/报错" | 用户纠错 → CQI issue 候选 |
| **Supermemory** | `supermemory_search` 搜相关记忆 | 已知问题、历史决策、矛盾信息 |
| **Skill 源码** | `search_files` 搜 TODO/FIXME/HACK/workaround | 技术债记录 |
| **Cron 日志** | 检查 cron job 输出中的 ERROR/TIMEOUT | 运行时故障 |
| **用户直接反馈** | Telegram 消息中明确说 "XX 有问题" | 最高置信度信号 |

**信号处理流程**：
```
原始信号 → 置信度评分 → 
  ├── 高置信 (≥0.75) → 创建 CQI issue
  ├── 中置信 (0.60-0.74) → 标记 OBS，累积观察
  └── 低置信 (<0.60) → 记录但不行动，下次扫描时复查
```

### 去重

新信号进来时，与已有 issue 做语义去重。如果新信号是对已有 issue 的再次确认：
- 提升该 issue 的置信度
- 增加 OBS 出现计数
- 不创建重复 issue

### 健康度量化评分

每次 CQI 回写前，对被改进对象计算 0-1 健康分。详见 `references/health-scoring.md`。

核心维度：
- **功能完整性**（核心能力是否可用）
- **证据锚定度**（多少 claim 有实测数据支撑）
- **历史负债率**（P0/P1 issue 数量和存续时间）
- **可验证性**（多少 fix 有 verify 命令）

**评分规则**：初始 1.0，每个 P0 issue -0.15，每个 P1 -0.08，P2 -0.03。无 verify 的 fix -0.05。OBS 不计分但不升级超过 90 天 -0.02。

---

## 📝 通用文档结构

所有 Profile 产出的 CQI 文档遵循同一骨架（具体章节按 Profile 调整）：

```markdown
---
YAML frontmatter — status/type/priority/aliases/tags/created/modified
health_score: 0.85  # 🆕 健康度评分
---

# <对象名> 持续质量改进计划

> [!abstract] TL;DR
> 一句话总结 + 当前健康分

## 一、背景与驱动力
## 二、现状诊断 — 硬证据驱动（含健康评分明细）
## 三、核心决策 / 架构设计（如有）
## 四～N、问题线程（8 元素格式，含置信度）
## N+1、分阶段实施方案
## N+2、成功标准 — 每项数字目标 + 测量方式
## N+3、风险 — 影响 + 缓解
## N+4、关联 — Obsidian wikilinks + 外部 links
## N+5、历史已完成 CQI 项（附录表）
```

---

## 🔄 重构回写模式

每次 CQI 回写 = **全文重构**（非 patch 追加），保留旧版实质内容。

| 内容类型 | 处理 |
|---------|------|
| ✅ 已完成线程 | → §历史已完成 CQI 项附录表（时间倒序） |
| 🔄 进行中线程 | 保留在主文，更新进展，压缩同类 |
| 🆕 新发现/决策 | 新增为主文章节 |

**关键规则**：
1. **硬证据锚定** — 所有诊断用实测数字。`ps aux`、`curl -w`、`grep`+行号。
2. **无行号污染** — 用 Python `open().write()` 读写，禁止用行号工具。
3. **禁止 `/tmp/` 路径** — Obsidian 内用 `[[wikilinks]]`。

---

## ✅ Quality Gates (Run Before Saving)

- [ ] 选择了正确的 Profile？Profile reference 已加载？
- [ ] 健康评分已计算并写入 frontmatter？
- [ ] 所有 issue 含完整 8 元素 + 置信度标注？
- [ ] 所有诊断有实测数字锚定（非"大概"、"可能"）？
- [ ] 独立 auditor 验证了客观项（命令是否跑过、exit code、产物是否存在）？
- [ ] 回写时：旧 CQI 全文已读？三类内容已分类？
- [ ] 已完成项已沉淀到附录表？
- [ ] Profile-skill 类：加载了 `obsidian-md-ac`？链接用 Obsidian wikilinks？
- [ ] 无行号污染？

---

## ⚠️ Pitfalls

| Trap | Consequence |
|------|-------------|
| Writing architecture instead of problems | CQI reads like system docs, not improvement plan |
| Fake metrics (~90%) without measurement | Can't verify, can't track, trust destroyed |
| Overwriting old CQI | User's historical observations lost permanently |
| No source attribution | Can't tell what was user-found vs agent-found |
| No verification per issue | "Fixed" but no way to prove it |
| P0 code issues treated same as P2 wishlist | Data pipeline stays broken while docs get polished |
| Skipping Profile selection → 用错模板 | Incident 当 Process 写 = Timeline 缺位 |
| Confidence 过高但无证据 | 0.90 但没有 verbatim quote 支撑 = 不可信 |
| Health score 算完不用 | 写了分数但下次回写不对比 = 无法追踪趋势 |
| **信任旧审计文档而非实测源码** ★（2026-06-17 cc-tmux CQI 教训） | CQI 声称 v1.8.1/48 tests，实际 skill 已是 v1.13.2/86 tests——旧审计文档是快照，源码是真相。写 CQI 前**必须读目标对象的实际源码 + 实跑测试/命令**做独立证人验证，不自采信已有文档的自报。旧 CQI/审计文档只作参考方向，不作事实来源。 |

---

## 📋 Verification Checklist (RUN BEFORE SAVING)

- [ ] Profile 选对了？对应的 reference 已加载？
- [ ] 健康评分已计算？写入 frontmatter `health_score`？
- [ ] 所有 issue 含 8 元素（Signal/Impact/Root Cause/Fix/Verify/Before/After/Lessons Learned）？
- [ ] 所有 issue 含置信度标注（0.60-0.95）？
- [ ] 所有诊断有实测数字？
- [ ] 回写时旧文档已读、三类内容已分类？
- [ ] 已完成项→附录表？
- [ ] 已废弃项→标记废弃并说明原因？
- [ ] 进行中项→更新状态？
- [ ] 新增问题→新增章节？
- [ ] 独立 auditor 验证了客观项？
