---
name: strategic-insight-longform
description: |
  战略洞察长文工作流 v5.0 - CC 原生 + 四层质量门 + 双轴方法论。基于 S-T-D 立方体 / dual-axis 双轴 / GoT 自适应 / CoV 反幻觉验证，将商业现象、行业趋势、企业战略转化为结构化深度洞察报告。16-agent team 火力全开，12-20 分钟产出 8000-15000 字成稿。

  触发词: 战略洞察、深度分析、行业研究、趋势研判、现象解构、长文撰写、整理成深度报告、商业洞察、战略报告、全息分析、S-T-D 分析、双轴分析、deep dive、industry analysis、strategic insight。

  DO-NOT trigger（以下场景请走对应 skill，不要触发本工作流）:
  - 事实查询 / 单点问答（"Manner 总部在哪？" → 直接搜索回答）
  - 翻译 / 改写 / 润色（→ 直接 prompt 或 humanizer / de-slop skill）
  - 邮件 / 公文 / GTD / 日程（→ copywriting / 日历类 skill）
  - 代码调试 / README / 技术文档（→ 通用工程 agent）
  - 文章摘要 / 总结（→ 摘要类 skill；本 skill 是从素材生成新分析，不是压缩既有文章）
  - 概念解释 / 教学（"什么是波特五力？" → 直接回答）
  - PPT / 海报 / 卡片图（→ ppt-creator / xiaohongshu-cards）
  - 主观偏好对比，无素材（"Manner 和瑞幸哪个更好喝？" → 普通对话）
metadata:
  version: 5.0.0
  last_updated: "2026-05-31"
---

# Strategic Insight Longform v5.0

CC-native agent-team 工作流。Leader 调度 16 agent + 4 层质量门，产出单文件深度洞察长文。

> **本文档第一读者是 CC Leader agent。Hermes 运行时映射见底部脚注。**

---

## 🚨 Red Flags — 立即停止（前置预拦截 8 条）

任何一条命中 → Leader 不进入 pipeline，直接告知用户。

| # | 触发条件 | 处置 |
|---|----------|------|
| 1 | 用户主题 < 8 字且无素材 | 强制走 `question-refiner` 澄清后再启动 |
| 2 | 素材单一来源 + 主题预测性强 | 不启动，提示补来源 |
| 3 | `knowledge-enricher` 返回 qmd 0 命中 + Exa 0 命中 | 停止，信息真空告警 |
| 4 | CoV Layer 1（引用完整性）覆盖率 < 60% | 全回 researchers（max 1 轮），不进 Stage 4 |
| 5 | CoV Layer 2（URL 可达性）死链率 > 40% | 同上 + 降级来源 |
| 6 | `longform-writer` 字数 < 2500 或 > 30000 | 直接 reject 回 writer |
| 7 | 主标题与正文核心论点偏离 > 50% | 回 finalizer 重提炼，不进美化 |
| 8 | 主题命中政治敏感词 | 停止，提示改写或转私域 |

---

## Decision Tree（Leader 启动流）

```
用户 query
   ↓
[Red Flags 8 条预扫] ──命中──→ STOP / 询问
   ↓ 未命中
[识别 analysis_type]   ←─ 关键词 → {战略级全息 / 现象解构 / 趋势研判 / 企业战略 / 政策分析 / 行业研究}
   ↓
[Stage -1] question-refiner   （主题 < 8 字或意图模糊时触发；否则跳过）
   ↓
[Stage 0~7]  16-agent pipeline 全部启用（见 Workflow Architecture）
```

**v5.0 取消 Deep/Standard/Quick 三模式**——只有一种执行流：16 agent 全跑、L1-L4 四闸门全开、GoT + CoV + 双轴按 analysis_type 自动启用。如需轻量分析，请用其它 skill（不是本 skill 的简化版本）。

---

## CC Native Dispatch Template

**两步派单**：

```python
# 步骤 1：建任务节点
t_spatial = TaskCreate(
  subject="空间维度研究",
  description="spatial-researcher: 横轴 A/B/C 或 S-T-D 空间分析",
  blockedBy=[t_framework]  # 或 [t_got]
)

# 步骤 2：派 worker 启动任务
agent_prompt = Read("agents/core/spatial-researcher.md")
Task(
  prompt=agent_prompt + f"\n\n# 本次输入\nuser_input={user_input}\nworkspace={WORKSPACE}\ntask_id={t_spatial.id}\nSKILL_DIR={SKILL_DIR}",
  subagent_type="general-purpose",
  team_name="sil-{topic_short}",
  name="spatial-researcher"
)
```

**关键约定**（缺一不可）：

1. **Leader 必须 `Read(agents/core/<name>.md)` 把 agent prompt 全文塞入 `Task(prompt=...)`**——16 个 worker 都以 `general-purpose` 启动，没有内置 role-prompt。
2. **并行 = 同一条 assistant message 里发多个 `Task` 调用**，不是 `await wait_all()`。
3. **TaskUpdate 心跳协议**：所有 worker 在 (a) 阶段切换 (b) 每 90 秒 (c) 完成时 调 `TaskUpdate(task_id, status, progress_pct, message)`；Leader 通过 `TaskGet` 轮询或 `Monitor` 流式监听，超心跳间隔 2 倍未更新视为卡死。
4. **`${SKILL_DIR}` 注入**：Leader 在 Task prompt 里显式传入 `SKILL_DIR` 绝对路径，所有 Bash 调用统一 `python3 "${SKILL_DIR}/scripts/..."`。
5. **完整 CC 原生工具白名单**：`TeamCreate / TaskCreate / Task / TaskGet / TaskUpdate / TaskStop / SendMessage / Monitor / TeamDelete / Read / Write / Edit / Bash / WebSearch / WebFetch / Skill`。禁用自造 verb（`dispatch_teammate / wait_task / wait_all / run_script / broadcast_shutdown`）。

完整伪代码与失败恢复见 `references/agent-pipeline.md`。

---

## Workflow Architecture

```
Leader (主进程)
  ├─ TeamCreate("sil-{topic_short}")
  │
  ├─ Stage -1: question-refiner          （主题模糊时触发，否则跳过）
  ├─ Stage 0:  topic-preprocessor
  ├─ Bash:     python3 "${SKILL_DIR}/scripts/memory_reader.py" ...
  ├─ Stage 0.5: knowledge-enricher       （qmd + Exa + 历史）
  ├─ Stage 1:  framework-builder         （analysis_type 路由 → S-T-D / dual-axis）
  ├─ Stage 1.5: got-controller           （维度评分 + 资源分配）
  │
  ├─ Stage 2a 并行 (3 Task 同 turn)
  │   ├─ spatial-researcher              （横轴 A/B/C 或 S-T-D 空间）
  │   ├─ temporal-researcher             （纵轴 5 步 或 S-T-D 时间）
  │   └─ domain-researcher               （领域维度）
  │
  ├─ Stage 2b 并行 (2 Task 同 turn，blocked_by 2a)
  │   ├─ stakeholder-analyst
  │   └─ causal-analyst
  │
  ├─ Stage 3:  source-manager            （CoV 三层 + 早期触发钩子）
  ├─ Stage 4:  insight-synthesizer       （多阶推论 + 交叉矩阵 + 横纵交汇）
  ├─ Stage 5:  longform-writer           （L2 自检内置 + neat-freak + 章节硬字数）
  ├─ Stage 6:  output-finalizer
  │     ├─ L1 硬扫（anti-ai-blacklist）
  │     ├─ L3 内容终审（CoV + 论证链 + HKR + 引用密度）
  │     ├─ L4 活人感（命中软违规 → Skill("de-slop")；硬违规回 writer）
  │     └─ 综合评分 ≥ 4.0 → 通过；< 4.0 → SendMessage 触发 writer 修订（max 1 轮）
  ├─ Stage 6.5: Leader 调 Skill("obsidian-md-ac") 美化终稿
  │
  ├─ Stage 7 并行 (2 Task 同 turn，非阻塞)
  │   ├─ memory-curator
  │   └─ pattern-crystallizer
  │
  ├─ cp final-article → ~/Obsidian/AlexCai/00-Inbox/
  └─ TeamDelete()
```

---

## Agent Roster（16 个，全部启用）

| # | Agent | Stage | 输出文件 | 关键能力 |
|---|-------|-------|----------|----------|
| 1 | question-refiner | -1 | structured-prompt | 意图评估 + 结构化 Prompt（用 AskUserQuestion）|
| 2 | topic-preprocessor | 0 | topic-analysis.json | 主题预处理 + 记忆匹配 |
| 3 | knowledge-enricher | 0.5 | knowledge-context.json | qmd vsearch + Exa 多层搜索 + 历史回顾 |
| 4 | framework-builder | 1 | multi-dim-framework.md | analysis_type 路由 + S-T-D / dual-axis 二选一 |
| 5 | got-controller | 1.5 | got-evaluation.json | 4 维评分 + 资源分配（balanced/breadth/depth）|
| 6 | spatial-researcher | 2a | research-spatial.md | 横轴 A/B/C 决策树 或 S-T-D 空间四级 |
| 7 | temporal-researcher | 2a | research-temporal.md | 纵轴 5 步（6000-15000 字）或 S-T-D 时间三段 |
| 8 | domain-researcher | 2a | research-domain.md | 领域 + 跨领域 + 复合视角 |
| 9 | stakeholder-analyst | 2b | research-stakeholder.md | 利益相关者博弈 + LinkedIn 搜索 |
| 10 | causal-analyst | 2b | research-causal.md | 5 层因果链 + 反事实 |
| 11 | source-manager | 3 | source-verification.json | CoV 三层 + verdict JSON + 3.5 早期触发钩子 |
| 12 | insight-synthesizer | 4 | core-insights.md | 二/三阶推论 + S×T/S×D/T×D 交叉 + 横纵交汇（5 问 + 三剧本）|
| 13 | longform-writer | 5 | final-article.md | 思维链内嵌 + L2 自检 + neat-freak + 章节硬字数 |
| 14 | output-finalizer | 6 | 战略洞察-{title}.md | L1 → L3 → L4 三段闸门 + de-slop + 修订循环 |
| 15 | memory-curator | 7 | memory/*.json | 会话记忆整理 + 模式归档 |
| 16 | pattern-crystallizer | 7 | patterns.json | 模式结晶（置信度 + 衰减）|

每个 agent 的完整 prompt 在 `agents/core/` 和 `agents/optional/`。Leader 派单时全文 Read 后塞入 Task。

---

## Framework Selection（analysis_type 路由）

`framework-builder` 在 Stage 1 按用户 query 识别 `analysis_type`，自动选 3 必选 + 3-5 补充框架，并在输出 `multi-dim-framework.md` 顶部 frontmatter 声明 `axis_type: std-cube` 或 `dual-axis`，作为下游 spatial/temporal researcher 的分流契约。

| analysis_type | 必选框架 | axis_type |
|---------------|----------|-----------|
| 战略级全息 | S-T-D + 5W2H + PESTLE | `std-cube` |
| **现象解构** | **dual-axis** + 5W2H + 因果链 | `dual-axis` |
| **趋势研判** | **dual-axis** + S 曲线 + 技术成熟度 | `dual-axis` |
| **企业战略** | **dual-axis** + 波特五力 + 价值链 | `dual-axis` |
| 政策分析 | PESTLE + 利益相关者 + S-T-D | `std-cube` |
| 行业研究 | 波特五力 + S-T-D + 价值链 | `std-cube` |

完整框架库：`references/framework-library.md`（~75 个框架）。
双轴方法论：`references/dual-axis-methodology.md`。
S-T-D 立方体：`references/std-cube-methodology.md`。

---

## Quality Gates L1-L4（统一 verdict 协议）

四道质量门 + Red Flags 顶部预拦截 + neat-freak 副闸门。所有 Gate 输出 `<verdict>{...JSON...}</verdict>` 包裹，Leader regex + json.loads 提取后按 `next_action` 路由。

| Gate | 位置 | 核心指标 | 命中处置 |
|------|------|----------|----------|
| **Red Flags** | Stage 0 之前 | 8 条预拦截（见顶部） | STOP / 回炉 |
| **L3 早期** | Stage 3 内 | CoV L1 < 60% 或 L2 死链 > 40% | 触发 Red Flag 4/5 |
| **L2 风格** | Stage 5 末（writer 自检） | 段长方差 ≥ 0.40 / 伏笔回收 ≥ 70% / 重复论点 = 0 | 局部自重写（max 2）|
| **L1 硬扫** | Stage 6 首段 | AI 词黑名单 = 0 / 教科书开头 = 0 / 连续破折号 = 0 / YAML = 100% | 局部回炉（max 2）|
| **L3 终审** | Stage 6 中段 | 论证链 ≥ 90% / CoV 引用 ≥ 95% / URL 可达 ≥ 85% / 交叉验证 ≥ 70% / HKR ≥ 3.5 / 引用密度 1 条/400 字 ±30% | SendMessage 回对应 agent |
| **L4 活人感** | Stage 6 末段 | AI 味密度 ≤ 0.3/千字 / 破折号 ≤ 1/800 字 / 三段式 ≤ 2 / 否定排比 ≤ 1 | 软违规自动调 `Skill(skill="de-slop", args="检测并改写以下文本的AI味：{text}")`；硬违规回 writer |
| **neat-freak** | Stage 6 末段 | 膨胀比 ≤ 5.0（最终字数/核心洞察字数）/ 单章节占比 ≤ 35% | warning + 微调 |

**任何 Gate 不死锁**：累计回炉到上限标记低置信度放行 + 评分扣分 + 报告告警。详见 `references/quality-gates.md`。

---

## 输出规范

**唯一输出文件**：`战略洞察-{提炼的主标题}.md`

- 主标题由 `output-finalizer` 从文章核心论点提炼（8-15 字），不是简单复制用户输入
- 禁止书名号、引号等特殊字符（文件名安全）
- 示例：`战略洞察-美国阶层脆弱性与中国叙事流变.md`

**文章结构**：

```
1. YAML frontmatter
2. 全息摘要（150-200 字，融合三轴或双轴）
3. 主思维链（整体推理路径）
4. 核心观点速览（3-5 个要点）
5. 正文（按 S-T-D 或 dual-axis 结构，每章含分章节思维链 callout）
6. 战略启示
7. 横纵交汇洞察（dual-axis 启用时）：5 核心问题 + 🎯/⚠️/🚀 三剧本
8. 附录 A-E（数据汇总表 / 因果链 / 博弈矩阵 / 情景假设）
9. 附录：来源索引（CoV 验证后）
```

**自动保存**：Leader 在 `TeamDelete` 前 cp 终稿到 `~/Obsidian/AlexCai/00-Inbox/`。

---

## Subsystems

| 子系统 | 入口 | 详情 |
|--------|------|------|
| **Memory** | Bash `${SKILL_DIR}/scripts/memory_reader.py` | 6 个 JSON（topics / sources / frameworks / sessions / preferences / patterns），schema 见 `references/memory-schema.md` |
| **Knowledge** | `knowledge-enricher` agent | qmd vsearch（relevance > 0.5）+ Exa 多层（web_search / company / crawling / linkedin）+ WebSearch 降级。`references/qmd-setup-guide.md` |
| **CoV 反幻觉** | `source-manager` agent | L1 引用完整性 / L2 URL 可达性 / L3 交叉验证。verdict JSON 标准化 |
| **GoT 自适应** | `got-controller` agent | 4 维评分（data_availability / topic_relevance / insight_potential / differentiation_value），输出 enhance/standard/reduce/skip 决策 + 资源分配策略 |
| **Learning** | `pattern-crystallizer` agent | 5 类模式 + 置信度 ≥ 0.85 自动生效 + 每日衰减 0.01 |

---

## Verification Checklist（Leader 自检 10 条）

启动前：

- [ ] Red Flags 8 条全部扫过，未命中
- [ ] 识别 analysis_type 成功，传给 framework-builder
- [ ] `SKILL_DIR` 已注入 Task prompt
- [ ] 已 Read 全部 16 个 agent .md 准备塞入 Task

执行中：

- [ ] Stage 2a 三 Task 同一 turn 发送（spatial / temporal / domain）
- [ ] Stage 2b 两 Task 同一 turn 发送（stakeholder / causal），blocked_by 2a
- [ ] TaskGet 心跳监听，无 worker 卡死（超 180 秒未更新 → TaskStop + 降级）
- [ ] CoV 三层 verdict JSON 全部提取成功

结尾：

- [ ] 四层 Gate verdict JSON 全部到位，综合评分计算正确
- [ ] Stage 6.5 `Skill(skill="obsidian-md-ac", args=f"美化文件 {final_file}：emoji 标题、==高亮==、Mermaid、callouts、YAML 合规、wikilinks 关系分析")` 成功
- [ ] 终稿出现在 `~/Obsidian/AlexCai/00-Inbox/战略洞察-*.md`

---

## References Index

| 文件 | 用途 |
|------|------|
| `references/agent-pipeline.md` | CC 原生执行流完整伪代码 + 失败恢复 + 超时治理 |
| `references/quality-gates.md` | L1-L4 + Red Flags + neat-freak 量化阈值 + verdict schema + 失败回路图 |
| `references/anti-ai-blacklist.md` | L1 黑名单 26 词 + 教科书开头 + 禁止标点 |
| `references/dual-axis-methodology.md` | hv-analysis 双轴方法论（纵轴 5 步 + 横轴 A/B/C + 横纵交汇）|
| `references/std-cube-methodology.md` | S-T-D 立方体方法论 + 与双轴关系 |
| `references/framework-library.md` | ~75 框架 + analysis_type 路由 + 双轴一级条目 |
| `references/cot-templates.md` | 各 Stage CoT 模板（按需加载）|
| `references/source-citation-guide.md` | 引用规范 + 引用密度阈值（1 条/400 字 ±30%）|
| `references/obsidian-format-guide.md` | Obsidian 格式规范（Stage 6.5 美化前置）|
| `references/qmd-setup-guide.md` | qmd 部署 |
| `references/memory-schema.md` | 6 个 memory JSON schema |
| `config.json` | 全参数（quality_gates / dual_axis / task_timeouts / neat_freak）|
| `agents/core/` + `agents/optional/` | 16 agent 完整 prompt |
| `scripts/` | 3 个 Python（memory_reader / writer / pattern_analyzer）|
| `CHANGELOG.md` | v5.0 演进 |

---

## 配置概览

详见 `config.json`：`quality_gates` / `dual_axis` / `frameworks` / `task_timeouts` / `neat_freak` / `memory` / `knowledge` / `learning` / `got_controller` / `cov_verification` / `search_iteration` / `revision_loop`。

---

## Hermes 兼容（脚注）

本 skill 原生为 Claude Code agent-team。在 Hermes 运行时按以下映射：

- `TeamCreate / TaskCreate / Task / TaskUpdate / SendMessage` → Hermes `delegate_task`，按阶段依赖手动编排
- `AskUserQuestion` → `clarify`
- `WebSearch / WebFetch` → 已配置的 Exa MCP 或 Hermes `web_search` / `web_extract`
- qmd CLI → 本机 qmd CLI；不存在时跳过向量搜索（不视为失败）
- `Skill("obsidian-md-ac")` → 若不存在，由主 Hermes agent 按 `references/obsidian-format-guide.md` 直接整理
- `Skill("de-slop")` → 若不存在，由主 Hermes agent 按 `references/anti-ai-blacklist.md` 手动扫描 + 改写

---

*Strategic Insight Longform v5.0 — CC 原生 + 四层质量门 + 双轴方法论*
