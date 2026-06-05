---
name: claude-code
description: |
  Orchestrate Claude Code CLI from Hermes — tmux interactive + agent team (stability-first).
  Print mode is secondary and only used for connectivity smoke tests.
  
  Triggers: claude code, cc, delegate to claude, use claude, let claude handle, 用claude,
  让claude, agent team, claude review
  DO NOT use for: simple single-tool calls (Hermes does those directly), grammar fixes,
  non-coding creative writing (use appropriate creative skills)
version: 4.1.1
author: Hermes Agent + Teknium (v4.1.1 三路合并去分叉 + CQI 诊断吸收：通用性声明 / read hook 防漂移 / 跨 skill 透传 / 记忆同步 / 磁盘校验 / 连续推进 / Pitfalls 修复)
license: MIT
---

# Claude Code — Hermes Orchestration（稳定性优先）

Delegate complex tasks to Claude Code via tmux interactive sessions + agent team. Print mode is secondary.

## §0 本 skill 是什么（加载者 / 被驱动方）

> [!important] 谁加载、谁被驱动
> **本 skill 是「如何驱动 Claude Code」的操作手册，被所有 Hermes agent 加载——不限于小黄 / default。** 任何 Hermes agent（`default` / `cron-worker` / `kanban-worker` / `subagent`）只要需要驱动 Claude Code，都加载这个 skill。
> - **加载者 = 当前 Hermes agent**（部署端 `~/.hermes/skills/autonomous-ai-agents/claude-code/SKILL.md` 是各 agent 实际读的）；**被驱动方 = CC（Claude Code）**，CC 本身不读这个 skill。
> - 因此「监控汇报」「轮巡」「占用检测」等规则是给 **加载它的 Hermes agent** 的职责，违规主体也是该 agent，不是 CC。

### 🔄 防漂移：加载时 hash 校验（read hook）

加载本 skill 时，应校验 runtime 副本与源仓库 provenance 是否一致——v4.1.0 曾发生「红线宪法 commit 进源仓库却没部署到运行端」的双向分叉（CQI 事件 #3）：

```bash
SRC=~/code/jz-skills/hermes/claude-code/SKILL.md  # 源 = 唯一真源
DEP=~/.hermes/skills/autonomous-ai-agents/claude-code/SKILL.md
[ "$(md5 -q "$SRC")" = "$(md5 -q "$DEP")" ] || echo "⚠️ claude-code skill 漂移：源 ↔ 运行端 hash 不一致，先同步再用"
```

**铁律**：任何修改必须在源仓库 `~/code/jz-skills/hermes/claude-code/` 进行，`cp` 单向同步到部署端；**禁止在部署端直接热修复**（那是分叉的根源）。

## 🔴 不可协商红线（Non-Negotiable）

> **分级声明：** 本 skill 只有 **2 条红线**。**红线 = 违反即停 + 用户介入**；其余全部是**规范（best practice）**——可按情境判断取舍。别让"必须"通货膨胀：真正不可破的就这两条，其余的"必须 / MUST"都是强建议，不是红线。`effort / session 隔离 / 占用检测 / 该不该调 CC` 属执行前硬门（见 🚦 Gate Stamp），不是红线。

### 🔴 红线① — 📡 汇报：每次 `capture-pane` 必须紧跟一个 📡 汇报块

发任务后从第 15 秒起持续汇报，沉默 >2min = 用户不知 CC 死活，可能误判卡死而中断（2026-05-31 真实违规）。capture 与 📡 **1:1 成对**——执行了 capture 却不汇报 = 违反红线①。

| 你会找的借口 | 为什么是错的 |
|-------------|-------------|
| "CC 在思考 / 空闲，没什么可报" | 用户要的就是"看到 CC 还活着"——空闲也得报"❯ 空闲，等待中" |
| "模板太繁，简化成一行" | 简化 = 未汇报（Rule#9）。用户要的就是这么详细 |
| "攒几轮一起报" | 合并 = 沉默期变长 = 违反。capture 与 📡 必须 1:1 |
| "抓了几次屏就算监控" | `capture-pane` 只是内部取证；没有同轮 user-visible 📡 = 没监控 |

### 🔴 红线② — 讨论协议：用户说"看方案 / 优化 / 处理决策点" = 讨论，不是执行

只有用户明确说"执行吧 / 可以做了 / 拉 CC 改"才动手（Pitfall #23）。方案必须经用户**逐条审定**后才能开 team / 改文件。

| 你会找的借口 | 为什么是错的 |
|-------------|-------------|
| "用户说优化方案 = 让我去改" | "优化方案"是要你**提方案**，不是改文件。默认讨论 |
| "方案差不多了，先动手再说" | 未经逐条审定 = 禁止执行。2026-05-31 真实违规：未审定就改 30 项 + commit |
| "改完再让用户看" | 反了。审定在前、执行在后，不可倒置 |

> 违反任一红线 → 见 `## ⚡ Core Rules` #11「违规自修正协议」：立即标记 + 当轮补做，**禁止"下轮改"口头了事**。

## 🚦 执行前 Gate Stamp（开 team / 改文件前必须打印）

> **软 checklist → 硬门。** 开 agent team 或让 CC 改任何文件**之前**，必须打印下方签章并逐项核对。**任一项 ✗ → 立即阻断执行 + 报用户**，不得跳过、不得"先做着"。借鉴 china-legal-optimized output-gate「五项硬检查，任一不过即 block」。

```
🚦 执行前 Gate Stamp
  方案审定 ✓  用户已说"执行吧 / 可以做了"？（红线②）
  该调 CC ✓  这是重活（多文件/架构/skill/部署）？重活调 CC，别自己扛（2026-06-03 教训）
  effort   ✓  已按任务信号选档？（地板 high，见 § Model & Effort）
  session  ✓  独立名 hermes-cc-{agent}-{ts}？禁 --continue？
  占用检测 ✓  已扫描所有 tmux session，无 ●/✻ 冲突？（脚本见 § Multi-Agent）
  ── 五项全 ✓ → 开 team / 发任务；任一 ✗ → 停，报用户后再继续
```

> 占用检测完整扫描脚本是唯一权威，放在 `§ 🤝 Multi-Agent Coordination Protocol`；此处只做执行前一次性勾选确认（不重复脚本）。

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "我直接用 terminal 调 claude 就行" | 不加载 skill = 不知道 PTY 对话框处理、不知道 `--max-turns` 防止失控、不知道 background 超时会被杀 |
| "任务太简单，print mode 就行" | 简单任务也有坑：`--max-turns` 不设 = 可能无限循环烧钱；`--model` 不指定 = 开销不可控 |
| "我用 tmux 不需要这个 skill" | PTY 有两个对话框需要精确按键序列。权限对话框默认是"No, exit"——你必须 Down+Enter。错过 = Claude 直接退出 |
| "agent team 就是普通 Task subagent" | Claude Code 的 agent team 是独立机制。用户明确说过不要用普通 Task subagent 冒充 team |
| "我设置 budget=$0.05 够了" | 系统 prompt cache 创建本身就 ~$0.05。更低 → 立即报错。烟雾测试用 `$0.2` |
| "我先静默检查 tmux，等 CC 有结果再汇报" | **2026-05-31/06-01 真实违规。** 发送任务后必须从第 15 秒起持续汇报 📡；**每次 `capture-pane`/poll 后都要立刻给用户一个进度块，即使只是 `✳ thinking`、未完成、或没有新结果**。不得把多轮 poll 藏在工具调用里等最终成果 |
| "我用简化格式 `📡 CC [~Xmin]` 汇报就行" | **2026-06-01 真实违规。** skill 规定模板是 `📡 CC Agent Team [Xmin]` + 状态 emoji + token 统计。简化格式 = 未汇报，即使内容正确。单 CC（无 worker）时仍需完整格式 |
| "用户骂我没监控，我先道歉解释一下" | **错。** 道歉必须伴随立即 `capture-pane`，把所有活跃/思考/等待输入的 CC session 用完整 📡 模板转发；若任务还在跑，立即恢复 30-60s 轮巡 + 完整 📡，**靠 Hermes 自身持续轮巡，不靠 watchdog 代劳**（父皇校准：不建 watchdog）。只道歉、不抓屏、不恢复轮巡 = 第二次违规 |
| "我已经报了一次 📡，等用户回复/等结果再继续" | **错。** 首次 📡 不是结束，是监控循环开始。用户回"好"不是暂停许可，而是继续推进信号。不要用一条"我会继续监控"结束回合后实际沉默 |
| "Hermes 设计 → Hermes 写代码，不用调 CC" | **2026-06-03 真实违规。** 用户说"要调用cc干活啊别自己干"。多文件架构改动、skill 编写、部署验证这些重活——Hermes 做好设计文档，CC agent team 执行 |
| "设计完直接部署就行，不需要审查" | **2026-06-03 真实违规。** 用户说"核心设计要让cc审查"。涉及多文件/架构/外包集成的设计，Hermes 写好方案后必须让 CC 审查再执行（曾发现致命缺陷：source-verification 不存在、降级链回环） |
| "CC 现在有忙/残留 session，所以我只能先不处理" | **错。** 先处理确定部分并推进可验证工作；不复用脏 session，但也不要把 CC 占用当停工理由。可新建隔离 CC 做 shadow-review；破坏性步骤仍等 CC `no blockers`。见 `references/direct-numbered-batch-shadow-review.md` |
| "用户问 CC 的能力/功能/机制，我凭 memory 直接答" | **2026-06-01 真实违规。** CC 功能变化极快（一个月四版），training data 严重滞后。**任何关于 CC 能力/功能/机制/配置的问题，必须先搜 `code.claude.com/docs` + GitHub issues 再答，不准凭记忆** |

## 🔀 Decision Tree（稳定性优先 — 仅 tmux + agent team）

```
调 CC 之前 → 🛑 先跑占用检测（扫描所有 tmux session 的 ● 工具调用 + ✻ 思考态）
         │
         ├── 有 BUSY / THINKING session → 汇报用户，等确认（不抢占，❯ ≠ 空闲见 #24）
         │
         └── 全部空闲 / 用户确认新建
              │
              ├── ⭐ Agent Team（默认，绝大部份场景）
              │   └── tmux 交互模式
              │       ├── 默认 → 每次新建独立 session `hermes-cc-{agent}-{ts}`（不复用）
              │       └── 需复用上下文 → 写 `/tmp/cc-context-{task}.md` 传递，新 session 读取
              │           （⚠️ 不再复用共享 `hermes-claude-longterm` — 见 § Multi-Agent）
              │
              ├── 单文件小修（仅当用户明确说"简单"）
              │   └── Hermes 自己做，不调 CC
              │
              └── ⚠️ 多 Agent
                  └── 各自独立 session + 独立 workdir，**禁 `--continue`**
```

**不做：** print mode `-p`。简单任务 Hermes 自己干，调 CC 就是为了 tmux + agent team 的重活。

### 🚦 单 CC vs Agent Team vs 并行多 CC

**默认是「CC Agent Team」。** 「并行多 CC」是特例——仅当任务流真正相互独立、无共享上下文时才用。

```
任务来了 → 这活 Hermes 自己就能干？
         │
         ├── 能（单工具调用 / 改一行 / 查一下）→ 🚫 根本别调 CC
         │
         └── 不能 → 任务之间有共享上下文吗？
                   │
                   ├── 有共享上下文（同一项目/同一目标）
                   │   │
                   │   ├── 用户明确说"简单"+ 单文件小修 → 单个 CC（不开 team）
                   │   │
                   │   └── 多文件/多步骤/根因/实现+测试/架构/多 lens → ⭐ CC Agent Team（默认）
                   │
                   └── 无共享上下文（如两个不相干项目）→ ⚠️ 并行多 CC（特例）
```

| 执行形态 | 适用场景 | 关键约束 |
|---------|---------|---------|
| **单个 CC（不开 team）** | 用户明确说"简单"的单文件小修；改动逻辑单一、无需拆领域。**注意：** 真能 Hermes 自己干的活根本别调 CC。 | 别为简单任务付 team 启动开销（cache 创建 + leader 协调）。 |
| **CC Agent Team（默认）** | 多文件 / 多步骤 / 根因分析 / 实现+测试 / 架构判断 / 多 lens 审查。一个 CC 内 spawn 多 worker，**共享一份上下文**，CC leader 协调。 | context 文件必须含 worker timeout 规则（`timeout 10min per worker`）；按关注点拆分（见 `### 🧩 Agent 数量与拆分原则`）；数量由 CC 自定。 |
| **并行多 CC（特例）** | 真正相互独立、无共享上下文的任务流（如同时跑两个不相干项目）。 | 各自独立 session 名 + **独立 workdir**；**禁 `--continue`**（同一 workdir 下 CC 会自动 resume，导致串台）；每个 session 独立跑占用检测与 Post-Send 汇报。 |

> 选型口诀：**Hermes 能干 → 不调 CC；要拆领域 → Agent Team；任务互不相干 → 并行多 CC。** 拿不准时默认 Agent Team。

### 🧩 Agent 数量与拆分原则

> **Let CC decide agent count.** Context 文件只描述任务，不规定 team 规模。

**让 CC 自己决定 agent 数量。** 写 context 文件时只描述「要做什么」，不要写「用 3 个 agent」「开 5 个 worker」。把数量决策权交给 CC——它看到任务全貌（文件依赖、关注点边界、测试范围）后，比你更清楚该开几个 worker。任何硬编码的 agent 数量都是过早优化。

| 维度 | ❌ 不要写进 context | ✅ 应该写进 context |
|------|--------------------|--------------------|
| 规模 | "spawn 3 个 agent" / "最多 N 个 worker" | "覆盖 API / schema / 前端三个关注点" |
| 分工 | "Agent 1 改这个文件" | "每个 worker 拥有一个完整领域，边界自洽" |
| 决策权 | Hermes 预先切好蛋糕 | CC leader 按复杂度自行拆分 |

> **Break work by concern, not by file.** 按关注点拆，不按文件拆。

**按关注点拆分，不按文件拆分。** 一个逻辑改动往往横跨多个文件；按文件切，会把同一个改动散落到多个 agent 手里，制造协调地狱和共享文件写冲突。按关注点（领域 / 层 / skill）切，每个 agent 拥有一个**完整领域**、边界清晰、可独立验证。

```
❌ 按文件拆（协调地狱）          ✅ 按关注点拆（边界清晰）
   Agent 1 → a.py                  Agent 1 → API 层（路由+handler+校验）
   Agent 2 → b.py                  Agent 2 → 数据库 schema（迁移+模型）
   Agent 3 → c.py                  Agent 3 → 前端组件（UI+状态+样式）
   ⚠️ 一个改动跨 3 个 agent         ✅ 一个领域归 1 个 agent
   ⚠️ 多 agent 抢同一文件          ✅ 文件归属随领域自然分开
```

> 拆分后别忘记 worker 纪律：context 文件必须含 `timeout 10min per worker`，假死先 `ls -la` 查磁盘再 `send-keys "Agent N done."`——详见 `## ⚡ Core Rules` #10/#12 与「Worker 假死恢复协议」。

## 🔥 讨论协议（Discussion Protocol — Hermes↔CC 双向拷问）

> **何时用：** 任务方案不明确、涉及架构决策、或用户说"看方案 / 处理决策点 / 讨论一下"时。**默认进入讨论，不是执行**（Pitfall #23）。方案审定后才动手。

复杂任务执行前，Hermes 与 CC 先进入一轮或多轮**双向拷问**，把模糊需求逼成精确规格，再开 agent team。本协议吸收自 Matt Pocock 的 grill pattern（[`mattpocock/skills`](https://github.com/mattpocock/skills) 的 `/grill-me` + `/grill-with-docs`）与多智能体辩证/投票研究。

### grill 核心机制（来源：github.com/mattpocock/skills）

| 机制 | 做法 | 出处 |
|------|------|------|
| **逐问（one-at-a-time）** | 一次只问一个问题，等回答后再问下一个——让每个答案影响后续方向 | grill-me |
| **带推荐答案提问** | 提问方附上"我倾向 X，理由 Y"，被问方有锚点可确认/反驳 | grill-me + grill-with-docs |
| **先查事实再接受主张** | 任何"现状应该如何"的陈述，先核查代码/文档/配置/git log 再接受 | grill-with-docs |

> 💡 **Hermes 已部署 `grill-with-docs` skill**（`~/.hermes/skills/governance/grill-with-docs`）。需要正式 grill 一个方案时可直接调用它；本节是其在 Hermes↔CC 编排场景下的精简协议。

### Hermes↔CC 双向拷问规则

> **讨论简报是强制产物。** 用户 2026-06-04 纠正："记得讨论的内容给我简报"。凡进入 Discussion Protocol / 双向拷问 / CC agent team 方案讨论，每轮或关键转向后必须主动发 `📋 讨论简报`：讨论了什么、决定了什么、分歧/未决、Hermes 的拷问、下一步。即使正在写文件或验证，也不要把讨论脉络藏到最终交付里。

1. **开场即讨论**，除非需求明确到不需要讨论。
2. 任何不明确的环节 → 发起一轮或多轮拷问；**双向**——Hermes 可拷问 CC，CC 也可拷问 Hermes，非单向受审。
3. **关于"现状"的陈述必须带可验证 artifact**（文件路径、命令输出、git log）。
4. **多轮辩证 + 立场更新**：每轮拷问后被问方须显式声明"立场是否更新、为何"，不允许沉默接受（Du et al. 2023 debate-then-revise）。
5. **终止条件**：双方对所有未决分支达成显式一致 → 进入执行；若 ≤3 轮仍有分歧 → 标记未决、写入 assumption log、带条件推进。
6. 提问走**纯文本**，不要 AskUserQuestion 表单——tmux 下表单导航不可靠（Pitfall #26）。
7. **🧠 思考保护 vs 思考循环（RA-07）** — max/xhigh 长思考是 CC 的正常深度推理，**不得用静默阈值打断**：`✻ 思考态` 且 **token 在增长** = 思考链活跃，继续等、继续 📡 报"Leader 思考中"。**只有 token 计数完全冻结 >3min**（非慢思考，是真卡死）才 `Ctrl+C` → 缩小范围重问（如"只讨论 C 和 F，简短回复"）。⚠️ 用户明确说"等 CC 好"时，即使 token 冻结也继续监控、不抢跑（Pitfall #36）。2026-06-01 复现：6min Flummoxing → 窄化为"只聊 C 和 F" → 16s 回应。

### Agent Team 对齐原则（执行前的闸门）

- **方案未审定 = 讨论，不是执行。** 用户说"处理决策点 / 看方案 / 优化方案"时默认是讨论；只有明确说"可以做了 / 执行吧 / 拉 CC 改"才动手（Pitfall #23）。
- 开 agent team 前，方案范围须经用户**逐条审定**。
- 涉及 skill / 已有文件修改时，先确认用户是否有备份。

### 🔄 连续推进模式（Autonomous Continuation）

> **何时启用：** 用户说"继续"/"不用问用户"/"你们讨论就行"/"直接动手"——表示已信任当前方向，不希望每步完成都停下来等审批。

1. 当前子任务完成后，直接按已知顺序推进下一步，不输出"要我继续就说一声"式的征询。
2. 仅在真决策点停止：方法分歧、架构选择、产出需审查时汇报结果+选项等决策。批量流水线工作步（如写第 5→第 6 个文件）不算决策点。
3. 连续推进仍需 📡 协议每 30-60s 汇报，用进度体感（"✅ 5/10 · 🔵 写作中"）。
4. 用户随时可打断——收到新消息立即检查 CC 状态。
5. 退回讨论模式：CC 提需决策的问题 / 进入未知领域 / 用户说"先看一下"/"等等"。

**反例（2026-06-01）：** 每写完一个文件就问"要我继续就说一声"——用户已说"继续"，不应在每步完成后暂停。

### 讨论简报模板（每轮拷问结束发给用户）

```
📋 讨论简报 R{n}
  · 讨论了什么
  · 决定了什么
  · 分歧 / 未决
  · 我的拷问（需用户回答的问题，每问带推荐答案）
  · 下一步（执行前必须等审定）
```

> **设计依据：** 逐问 / 辩证 / 共识终止三原则分别对应 grill-me、Du et al. 2023《Multiagent Debate》(arXiv:2305.14325)、Wang et al. 2023《Self-Consistency》(arXiv:2203.11171)；裁决角色参考 ChatEval (arXiv:2308.07201) 与 LLM-as-Judge (arXiv:2306.05685)。

## 🔗 跨 Skill 规格透传（调用另一 skill 时强制 — RA-08）

> **问题：** Hermes 调用另一个 skill（如 strategic-insight、methodology-writer）让 CC 执行时，若只写自己的低配 briefing，会覆盖目标 skill 的核心验收标准——曾把 strategic-insight full roster 降成 4-worker。

**规则：** 调用另一 skill 前，必须把**该 skill 的核心验收标准原样写入 CC context**，不得用 Hermes 自拟的简化版替代。

```
调 skill X → context 文件必须含：
  · skill X 的 roster / 阶段 / 门禁原文（从 skill X 的 SKILL.md 摘录，不改写）
  · "以 skill X 的验收标准为准，不要用本 briefing 的简化描述覆盖"
  · skill X 要求的输出格式 / 文件结构
```

## 🧠 任务记忆同步（任务交接时 — RA-09）

> **问题：** Hermes 的 supermemory 记忆池与 CC / claude-mem 隔离。CC 拿不到 Hermes 侧的相关记忆，信息不对齐。

**规则：** 任务交接 / 讨论阶段，Hermes 必须把**任务相关的记忆摘要**显式写入 CC context（人物、项目约定、历史结论、已知陷阱），不要假设 CC 能看到 Hermes 的记忆。摘要落 `/tmp/cc-context-{task}.md` 的「已知事实」段。

## 📡 Post-Send Protocol（发送任务后 — 强制执行）

**发送任务后，必须立即进入 30-60s polling 循环，从第 15 秒起向用户汇报 `📡` 进度块。这不是"等结果再汇报"——这是"让用户看到 CC 还活着"。**

```
发送 send-keys Enter
     │
     ▼
sleep 15 → 首次 polling → 立即向用户汇报 📡 状态
     │
     ▼
每 30-60s polling → 每次向用户汇报 📡 进度块
     │
     ├── 看到 ● 工具调用 → 汇报"CC 正在 [工具名]：[描述]"
     ├── 看到 ❯ 空闲 → 检查是否完成
     ├── 看到 worker 列表 → 汇报 worker 树（状态 emoji + 耗时 + token）
     └── 沉默 >2min → ⚠️ 向用户声明"CC 无响应 2min，继续等待中"。若 ❯ 处有新文本未执行 → 补发 Enter 触发
  └── CC 在决策点提问但 Hermes 无法代答 → 🛑 立即转发问题给用户，附讨论简报。不要猜测或静默等待
```

**违反此协议 = 用户不知道 CC 死活，可能误判卡死而中断。2026-05-31 真实违规教训。**

**🔗 机械配对规则（红线① 的可执行形式）：** 每一次 `capture-pane` **必须**紧跟一个 📡 块，二者 1:1 成对——执行了 capture 却没 📡 = 违反红线①。每个 📡 块头标注 `[距上次 Xs]`，>120s 自标 `⏰超时` 并解释原因。这不是"有事才报"，是"capture 即报"。

## 🧠 Model & Effort Level（Opus 4.8 + 思维链）

> **🔒 默认地板 = `high`。** 除非用户明确说 "fast / cheap / quick / 快一点 / 省钱"，**永远不要低于 `high`**。没信号 → 从 `high` 起步，按任务复杂度往上抬，**绝不擅自往下降**——简单也得 `high`。

**一句话路由：** 没信号 → `high`；碰到「多文件 / 审查 / 设计 / 原型」→ `xhigh`；碰到「深度架构 / 多 lens / 根因调试 / 全栈 / 安全审计 / 写 skill」→ `max`。拿不准往上抬一档——返工远比多想几秒贵。

**启动即定档**（比会话内 `/effort` 切换省 cache）：

```bash
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort high   # 地板；xhigh / max 按上面路由往上抬
```

> 🧠 **思考保护：** `✻ 思考态` 且 token 在增长 = 深度推理活跃，**勿因静默打断**；只有 token 冻结 >3min 才算卡死（详见讨论协议 #7 + Pitfall #7/#36）。
> 📦 **完整 effort 体系** → `references/effort-routing.md`：五级表、智能路由三档表、自检决策树、实战配置、成本换算（`max` ≈ 3× `high`）、`/effort` 会话内切换陷阱。⚠️ `xhigh` / `max` 仅 Opus 4.8/4.7 专属，别名机型不可用。

## ⚡ Core Rules（Hermes Agent 执行规则）

0. **🛑 发任务前必须扫描 CC 占用状态（🚦 Gate Stamp「占用检测」项的执行细则）** — 不同 agent 不知道彼此是否在用 CC。**每次调 CC 前，必须扫描所有 tmux session 的活跃状态**（`●` 工具调用 **+** `✻` 思考态——`❯` 不等于空闲，见 Pitfall #24）。**完整扫描脚本是唯一权威，见 `§ 🤝 Multi-Agent Coordination Protocol`（不再重复）。**

   - 有 `●` 或 `✻` → **必须汇报用户**："CC 正被 session `<name>` 占用，等待还是新建独立 session？"
   - 真正空闲 = `❯` + 无 `●` + 无 `✻/✶/✽/✳` + 无 `Waiting for N background agents`
   - ⚠️ **不要自作主张开新 session 绕过去**——用户可能不知道两个 CC 在同时跑，消耗翻倍
   - ✅ **但默认本就该新建独立 session**（`hermes-cc-{agent}-{ts}`）；占用检测是安全网，不是复用许可

1. **默认每次新建独立 session，不复用** — 每次调 CC 用独立 session 名 `hermes-cc-{agent}-{ts}`（**不复用**共享 `hermes-claude-longterm`）。**不用 `--continue`**（同一 workdir 下 CC 会自动 resume 最近 session → 串台）。需跨会话传上下文 → 写 `/tmp/cc-context-{task}.md`。
2. **复杂任务必须 agent team** — 多文件/多步骤/根因分析/实现+测试/架构判断 → 让 CC 自己 spawn subagent。**Agent 数量由 CC 按复杂度自定，context 文件只描述任务，不规定 team 规模。** 按关注点拆，不按文件拆 → 详见 `### 🧩 Agent 数量与拆分原则`。
3. **Always set `workdir`** — 让 CC 聚焦正确项目目录。
4. **Always 带 `HOME=/Users/alexcai`** — 避免 Hermes profile HOME override 导致认证失败。
5. **不要杀慢会话** — 用 `capture-pane` 检查进度，确认卡死才 `Ctrl+C`。
6. **清理一次性 tmux 会话** — 用完就 `tmux kill-session`，避免泄漏。
7. **每轮 agent team 后 `/clear`** — 避免 context 膨胀。
8. **⚡ bypass permissions** — 启动后验证，通常默认已启用。
9. **📡 无条件持续汇报进度（🔴 红线① 执行细则）** — 每 30-60s polling，沉默 >2min 不可接受。**必须使用 Progress Reporting 段规定的 `📡 CC Agent Team [Xmin · 距上次 Xs]` 模板格式**，自由发挥 / 简化 / 合并多轮 = 违反红线①。
10. **Worker 假死先查磁盘** — `ls -la` → 文件存在则 `send-keys "Agent N done."` → 不存在则手动接管。
11. **🔴 违规自修正协议** — 一旦发现自己违反红线① 或 ②：**立即** (1) 显式标记「⚠️ 我刚违反红线 X」；(2) **当轮补做**——漏报就立刻补一个完整 📡 块，越权执行就停手退回讨论；(3) **禁止**用"下轮改正 / 抱歉以后注意"口头了事。说了不改 = 二次违规。
12. **🔍 完成前磁盘一致性校验（RA-06）** — agent team 完成摘要**不得只凭 tmux task board**（只显运行时间，不显真实产出）。宣布完成前必须 `find <workdir> -newer /tmp/cc-marker -type f` 或 `ls -la <预期产物>` 校验文件真实存在且 size>0；摘要里写明"已磁盘校验：N 个文件落盘"。task board 显示 done ≠ 文件已写盘（Pitfall #37 socket error 静默失败）。

## 🤝 Multi-Agent Coordination Protocol（多 Agent 协调）

> **核心问题：** Hermes 的多个 agent（主 agent、cron-worker、kanban worker、subagent）彼此不知道对方是否在用 CC。没有协调机制 = session 冲突 = 任务互相覆盖。

### 启动前：占用检测（每次调 CC 前必须执行）

```bash
# Step 1: 扫描所有 tmux session
for s in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
  pane=$(tmux capture-pane -t "$s" -p -S -8 2>/dev/null)
  
  # 检测 ● 活跃工具调用（CC 正在工作）
  if echo "$pane" | grep -q '●'; then
    tool=$(echo "$pane" | grep '●' | tail -1 | sed 's/.*● //' | head -c 60)
    echo "⚠️ BUSY: $s — $tool"
  fi
  
  # 检测 ✻/✶/✽/✳ 思考状态（CC 深度思考中，不是空闲）
  if echo "$pane" | grep -qE '✻|✶|✽|✳|Sublimating|Zigzagging|Billowing|Crunched|Wandering|Swooping|Cooking'; then
    echo "🧠 THINKING: $s — CC 在深度思考旧任务，不可打扰"
  fi
  
  # 检测 ❯ 空闲（CC 等待输入）
  if echo "$pane" | tail -1 | grep -q '❯'; then
    echo "✅ IDLE: $s — CC 空闲，可复用"
  fi
done
```

### 决策矩阵

| 扫描结果 | 决策 | 操作 |
|---------|------|------|
| 无 tmux CC session | 直接新建 | `tmux new-session -d -s hermes-cc-{agent}-{ts} ...` |
| 有空闲 CC（`❯` + 无 `●` + 无 `✻`） | **仍默认新建** | 不复用旧 session（避免 scrollback 污染 + 被劫持风险）；仅当明确延续同一任务才复用 |
| 有忙碌/思考 CC（`●` 或 `✻`） | **先汇报用户** | "CC 正被 `{session}` 占用。等待还是新建独立 session？" |
| 用户确认新建 | 新建隔离 session | 独立 session 名 `hermes-cc-{agent}-{ts}` + **独立 workdir** |

### Session 命名规范

| Agent | Session 名 | 说明 |
|-------|-----------|------|
| 主 agent (小黄) | `hermes-cc-default-{ts}` | 默认 |
| cron-worker | `hermes-cc-cron-{ts}` | 定时任务 |
| kanban worker | `hermes-cc-kanban-{ts}` | 看板 |
| 手动/临时 | `hermes-cc-{task}-{ts}` | 用完即杀 |

> ⚠️ **不再使用共享 `hermes-claude-longterm`。** 每个 agent / 每个任务用独立 `hermes-cc-{agent}-{ts}`，用完即杀。共享 longterm 是 2026-06-01/02 多次劫持事件的根因（#24/#25）。

### 清理纪律 + Session GC（RA-12）

- **🛑 阶段性结束前不杀 session** — CC/tmux 会话保留到用户确认整个阶段结束。即使单个任务完成，等用户说"可以了 / 结束 / 推吧"再 `tmux kill-session`。提前杀 = 用户可能需要复用上下文但你已销毁（2026-06-02 用户偏好）。
- 同一任务多轮间 → `/clear`（清 context，保留**当前** session）。
- ⚠️ 不同任务 → **新建独立 session**，不在旧 session 里 `/clear` 复用（避免劫持，见 #25）。
- 阶段结束 → `tmux kill-session`（用户确认后清理）。
- **🗑️ 残留 session GC（阶段结束后回收）**：按 ① 命名（`hermes-cc-{agent}-{ts}` 中 `{ts}` 超过 N 小时）② 假空闲（`❯` 且无 `●/✻` 持续 >30min）③ 阶段已确认结束 三条任一命中 → 候选回收，回收前 `capture-pane` 确认无未读产出。**不在阶段中途按 age 杀**（与"阶段未结束不杀"不冲突：GC 只清已确认结束的残留）。

### ⚠️ Session 劫持诊断

当你发送任务后 CC 无响应，或 `capture-pane` 显示 `❯` 后面跟着**不是你发的命令**，说明另一个 agent 正在竞争同一 CC session。此时：

1. 发 `pwd` 测试 CC 是否处理你的输入
2. 如果 `❯` 处出现其他 agent 的命令文本 → **不要继续发任务**
3. `/clear` 清空后立即重发你的任务
4. 若反复出现 → `killall claude` + 重建 tmux session
5. 深度诊断 → `references/cc-session-isolation.md`

## 🚀 Prerequisites

```bash
which claude && claude --version && claude auth status || true
```

> ℹ️ **Hermes 使用 CC 的策略：** 只用 tmux 交互 + agent team。print mode `-p` 保留参考但不主动使用——简单任务 Hermes 自己做。

## 🖥️ Interactive Mode — tmux + Agent Team

### ⚡ Bypass Permissions

CC v2.1+ 默认启用。启动后验证：`tmux capture-pane -t <s> -p -S -2 | grep "bypass permissions on"`。若是 `off`：不用 `Shift-Tab`（macOS 下是窗口切换），改用手动 `send-keys Down → Enter` 处理权限对话框。

### 📡 Progress Reporting（持续汇报进度）

**tmux 模式下必须主动汇报，不要沉默等待。**

> ⚠️ **这不是建议，是命令。** 每次 `capture-pane` 后必须按下方模板汇报。不要简化、不要自由发挥、不要合并多轮为一句话。如果你觉得「模板太复杂，用户不需要这么详细」— 用户要的就是这么详细。

**汇报节奏：** 发送任务后 15 秒首次检查 → 之后每 30-60 秒轮询一次 → 看到关键信号立即汇报（不等下次轮询）。

```bash
# 取最后 60 行，看 CC 在做什么（用本任务的 session 名，不是共享 longterm）
tmux capture-pane -t hermes-cc-{agent}-{ts} -p -S -60
```

> **硬规则：`capture-pane` 不是内部动作，而是一次用户可见的监控事件。** 每次抓屏后必须立即发一个 `📡 CC Agent Team [Xmin]` 块。不要连续抓屏 2-3 次后才汇总；若只是看到 `✳ thinking`，也要汇报"Leader 正在思考/读文件，暂无 worker 完成"。
>
> **Telegram/当前对话特例：工具调用 ≠ 用户可见。** 连续执行 `sleep && capture-pane` 但不发正文，用户看到的是沉默，这仍算未监控。正确节奏：`capture-pane` → 立刻用完整模板回禀 → 下一轮再继续工具调用。若用户发"进度？"或"为什么不监控"，第一动作必须是抓屏并立即可见汇报，不要先解释。
>
> **投递失败也算未汇报。** 若 `send_message` 转发被 gateway/确认门拦截，不得把失败当已通知；应立即改用当前对话正文回禀同一 `📡` 块。原则：每次 `capture-pane` 都必须形成用户可见进度。

> 💡 **Agent Team 磁盘验证（推荐）**：tmux task board 只显示 worker 运行时间，无法判断实际文件产出。用 `find <workdir> -newer /tmp/cc-marker -type f` 每 30s 扫一次磁盘，绕过 UI 盲区精确追踪进度（亦是 Core Rule #12 的完成校验手段）。详见 `references/agent-team-disk-verification.md`。

> 💡 **找不到输出文件？** CC 拿到显式目标路径时往往直接写到最终位置（如 OB vault），而非 `/tmp/`。先用 `mdfind -name "关键词"` 全盘秒搜，再 fallback 到 `find`。详见 `references/cc-output-file-discovery.md`。

**关键信号识别：**

| 信号 | 含义 | 动作 |
|------|------|------|
| `●` 前缀 + 工具名 | CC 正在调用工具 | 汇报："CC 正在 [工具名]：[简短描述]" |
| `❯` 前缀（最后一行） | CC 等待输入/完成 | 检查是否已完成任务 |
| `Error` / `Traceback` | 出错 | 立即汇报错误内容 |
| `bypass permissions off` | 权限模式丢失 | 立即处理（Down+Enter） |
| `[Fact-Forcing Gate]` | CC 编辑前安全门（正常） | 等待 5-10s |
| `Waiting for N background agent` + worker token 不变（>2min） | **worker 假死，文件可能已写盘** | 见下方「Worker 假死恢复协议」 |
| 多轮无 `●` 也无 `❯` | 可能卡死 | 等待 2 分钟，仍无变化 → `Ctrl+C` |

#### Worker 假死恢复协议

**症状:** `Waiting for N background agents` + worker token >2min 不变。**错误做法:** ❌ 反复 `send-keys Enter` ❌ 杀 worker

```bash
# 1. 检查产出文件是否存在且 size > 0
ls -la <expected output path(s)>
# 2. 文件存在 → 告诉 CC
tmux send-keys -t <s> 'Agent N is done. All files exist on disk. Continue.' Enter
```
**若文件不存在或 size == 0** → Worker 真死 → `tmux kill-session` → 手动接管。**教训:** context file 加 `timeout 10min per worker`。

**汇报模板（必须严格按此格式，不按模板 = 未完成汇报）：**
```
📡 CC Agent Team [Xmin · 距上次 Xs]
  ⚡ Leader: <当前操作>
  ├─ ✅ Worker A: <描述> (Xs, X.Xk tokens)
  ├─ 🔵 Worker B: <描述> (running)
  └─ 🟡 Worker C: 假死 — ls 确认文件中
  📊 Token: X.Xk · 🛡️ Gate: N 次
```

> 完整模板（单任务/异常/等待/限流）→ `references/progress-reporting-enhanced.md`。状态 emoji：⚡运行 💤空闲 ✅完成 🔵进行中 🟡假死 🔴真死 🛡️Gate ❌错误 🐚卡死 ⏳限流 ⏰超时未报(>120s)

**结束信号：** 当 `capture-pane` 最后一行是 `❯` 且上方不再有 `●` 工具调用时，CC 已完成当前任务。汇报最终结果并询问用户是否继续。

### ⚠️ PTY 对话框处理

**Dialog 1 "Trust this folder"** → `Enter`（默认正确）
**Dialog 2 "Yes, I accept"** → **先 `Down` 再 `Enter`**（默认是"No"！）

```bash
sleep 3 && tmux send-keys -t <s> Down && tmux send-keys -t <s> Enter
```

### TUI 状态速查
- `❯` = 等待输入 · `●` = 正在用工具 · `⏵⏵ bypass permissions on` = 权限模式

## 🔌 MCP Bridge: Claude Octopus

`references/claude-octopus-hermes-mcp.md` — 适用于只读探针、实验性任务。

## 👥 Non-Code Agent Team Reviews

**Agent team ≠ 普通 Task subagent。** 用户要 team 时：
1. 写 context 到 `~/.hermes/tmp/` markdown 文件
2. 用 CC team/teammate 流程（`--teammate-mode tmux` 或 settings.json 设 `"teammateMode": "tmux"`）
3. 让 team 用多个 lens（engineering/API、content/UX、compliance）
4. 保存为 Telegram 可读的 bullet Markdown（不要表格）
5. 报告用了哪种 team workflow + 输出路径，**并附磁盘一致性校验结果**（Core Rule #12）

> ✅ `--teammate-mode tmux` 经 2026-05-31 公网验证：CC 官方文档 [code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams) 确认 split-pane 模式支持，非第三方 hack。

**内容研究简报：** 当 delegate_task 被 kanban gate 拦截时，CC agent team 可作为 fallback。context 文件必须含 worker timeout 规则 + extractor prompt。详见 `references/cc-agent-team-content-research.md`。

## ⚠️ Critical Pitfalls

> 完整细节见 `references/common-pitfalls.md`。这里只列出稳定性核心坑。
> **编号纪律：** 编号永久递增、不重用。`#16 #17 #29 #32 #34 #35` 为历史合并/废弃编号，已并入其他条目，不再出现属正常。

| # | Pitfall | 一句话修复 |
|---|---------|-----------|
| 1 | **Dialog 2 默认"No"** | `Down → Enter`，不是 `Enter` |
| 2 | **HOME override 认证失败** | 始终 `HOME=/Users/alexcai claude ...` |
| 3 | **Worker 假死（文件在磁盘）** | `ls -la` 确认文件存在 → `send-keys "Agent N done. Continue."` |
| 4 | **Worker 真死（无磁盘产出）** | `kill-session` → 手动接管。context file 写 timeout 规则 |
| 5 | **多轮 context 膨胀** | 每轮后 `/clear` |
| 6 | **Fact-Forcing Gate** | 正常流程，不是卡死。等 5-10s |
| 7 | **send-keys 不执行 / CC 思考循环** | 15s 无 `●` → 补发空 `Enter`。若 `✻/✽ thinking` 持续 >3min 且 **token 完全不变**（真卡死，非慢思考）→ `Ctrl+C` → 缩小范围重问；仍循环 >2min → 再 `Ctrl+C` → 压缩到单一原子任务（"把 X 替换为 Y，改完说 done"）。**token 增长 → 真在思考，继续等**（RA-07 思考保护）。2026-06-02 复现：4min token 冻结 → Ctrl+C+单任务 → 26s 执行 |
| 8 | **📡 沉默 >2min** | 即使无事也要汇报 |
| 9 | **Agent team schema 持久化** | Leader wiring 后写 curl 脚本验证新字段 |
| 10 | **MacOS TCC 沙盒** | `cp` 到 `/tmp/` → CC 处理 → `cp` 回去 |
| 11 | **Background shell stall** | 发 redirect 指令 → 30s 无响应 → 手动接管 |
| 12 | **Token 脱敏破坏语法** | 字符串拼接不用 f-string |
| 13 | **TMUX Shift-Tab 无效** | 不用——Dialog 直接 `Down → Enter` |
| 14 | **Scrollback 污染** | 复用 session 前先 `pwd` 验证 |
| 15 | **Print mode 长文档不稳定** | 改用 Python + Playwright（`references/python-playwright-pdf-fallback.md`） |
| ★18 | **多 Agent Session 冲突** | 先跑占用检测（`§ Multi-Agent Coordination Protocol`） |
| ★19 | **Session 被劫持：❯ 显示非本 agent 命令** | 发 `pwd` 测试 → 看到 `❯ cd /other/path && other task` → 另一个 agent 在竞争。`/clear` + 重发任务。反复出现 → kill CC daemon + 所有 tmux session 后重建。**不要继续往被劫持的 session 发任务** |
| ★20 | **send-keys 命令在 ❯ 处但不执行** | 两层原因：(A) CC 初始化期（`tmux new-session` 后 3-5s）只显示不执行；(B) 长/多行命令文本可见于 ❯ 但 CC 未处理。**修复**：(1) 初始化后 `sleep 5` + `capture-pane` 确认 ❯ 稳定；(2) 发送后 15s 内无 `●` → **立即补发空 `Enter`**；(3) 仍无 `●` → 再补一次。**不要反复发相同命令** |
| ★21 | **Obsidian Vault Gate 循环：写入被反复拦截** | `Ctrl+C` → 显式放行指令（覆盖文件引用者/Glob/数据结构/用户指令 4 项）。**预防**：context file 预填 Gate 事实。详见 `references/common-pitfalls.md` #21 |
| ★22 | **Hermes cross-profile write guard 阻拦 context file** | context file 写到 `/tmp/`（中性位置），CC 从 `/tmp/` 读取后直接在目标 workdir 改文件——CC 的 Write 工具不受 Hermes profile guard 影响 |
| ★23 | **CC 在方案未审定时提前执行：修改文件+提交，但用户没批准** | 当用户说"处理决策点"/"看方案"时，**默认 = 讨论，不是执行**。只有用户明确说"可以做了"/"执行吧"后才动手。详见 `references/common-pitfalls.md` #23 |
| ★24 | **CC 假空闲 — 底部 ❯ 可见但 ✻ 思考中** | `capture-pane` 底部 `❯` 不等于 CC 空闲。上方可能正深度思考旧任务（`✻ Sublimating…`）。占用检测必须同时 grep `✻|✶|✽|✳`。2026-06-02 主 agent 劫持了 cron-worker 任务 |
| ★25 | **Session 被另一 agent 的 /clear 劫持：当前任务被完全覆写** | 复用共享 session 时，另一 agent 发 `/clear` + 新任务会完全覆盖你正在执行的任务。**修复**：独立任务用专用 session 名，发任务前 `capture-pane -S -20` 验证末尾是 `❯` 且无新任务文本，被劫持立即重建独立 session |
| ★26 | **CC 权限表单 tmux send-keys 无法可靠导航** | Tab/Enter/Arrow 序列在权限表单下不可靠。**修复**：按 `Escape` 取消 → CC 显示 "User declined to answer questions" → 立即发**纯文本决策消息**（如 "选 1+2+3"）。⚠️ Escape+文本后常触发 stall：文本出现在 ❯ 处但不处理 → 补发空 `Enter`（同 #20）。详见 `references/common-pitfalls.md` #26 |
| ★27 | **CC 自动恢复旧会话——不是干净启动** | workdir 下有 `.claude/` 状态时，新 session 的 `claude` 会**自动 resume 最近会话**。看到熟悉 task board 说明是旧会话。**处置**：先检查是否已有成果；需干净启动优先切到无 `.claude/` 的临时 workdir，或启动后 `/clear` 验证 `❯` 为空。不要盲用 `claude --new-session`（先 `claude --help` 确认支持，否则 pane 直接退出）。详见 #27 |
| ★28 | **完成后 CC 输入行残留"下一步建议"** | CC 最终报告可能把建议命令/危险 `rm ...` 留在 `❯` 输入行，这不是用户授权。**处置**：最终 `capture-pane` 后检查底部输入行；有残留先 `C-u`/`Escape` 清空；清不掉且阶段已结束立即 `tmux kill-session`。不要按 Enter，不要让 CC 执行它自己刚建议的动作 |
| ★30 | **被用户抓到未监控后只道歉、不立刻补监控** | 立即执行恢复序列：`capture-pane` 全量扫描 → 用完整 📡 模板转发所有活跃/思考/等待输入 session → 处理 `❯ <残留输入>`（Enter 不动就 Escape+短英文重发+C-m）→ 若仍运行，**恢复 Hermes 自身 30-60s 轮巡**（不建 watchdog，父皇校准）。详见 `references/cc-status-watchdog-after-complaint.md` |
| ★31 | **让 CC shadow-review 协助高风险清理，但主 agent 抢在审查完成前执行破坏性删除** | 对删除/迁移/清理/远端数据变更：先让 CC 审脚本与守卫，等 CC 明确 `no blockers` 后再执行破坏性动作；必须并行则破坏性步骤前设硬闸（archive 完整性、稳定 L0 覆盖、dry-run manifest）。详见 `references/destructive-cleanup-shadow-review.md` |
| ★33 | **多行 send-keys 排队污染 — 命令逐行发送，CC 无法消费，形成死队列** | **症状**：多个 `send-keys Enter` + `sleep 1` 逐行发任务时，CC 消费第一行后进入思考态，剩余行在 ❯ 处形成队列（"Press up to edit queued messages"）。**修复**：(1) 🏆 **文件传递**（最可靠）— 写任务到 `/tmp/cc-task-<name>.md`，再单行 `Read /tmp/cc-task-<name>.md。然后按里面做。`；(2) 必须内联则一句完整命令 ≤200 字符不拆行；(3) 已污染 → `tmux kill-session` + 重建。2026-06-02 复现 4 次，靠文件传递解决 |
| ★36 | **CC 思考循环但用户说"等 CC 好"时，Hermes 抢跑手动编辑** | 症状：CC 在 `✻ almost done thinking` 循环 3-4min，token 不增，Hermes 判断卡死开始手动改。用户说"不行，你等cc好"。**根因**：用户信任 CC 输出质量>速度。用户明确说"等"时，即使 token 冻结 >3min 也继续监控，不代劳、不抢跑。只在用户说"别等了/你来改"时才接手 |
| ★37 | **Socket error 后不验证文件是否写成功** | 症状：CC Write 报 "socket connection closed" 但未重试直接进入下一步，事后发现文件根本没创建。**修复**：socket error 后 Hermes 必须① `stat` 目标文件确认存在 ② 不存在则明确告诉 CC "文件未写成功，请重试" ③ 不在未验证下假设已写入（呼应 Core Rule #12） |
| ★38 | **Context file 未交代 skill 架构背景——CC 误解自身角色** | 当 CC 被要求讨论/修订 `claude-code` skill 自身时，context file 必须显式声明：**此 skill 部署在 Hermes 上、由 Hermes 加载、教 Hermes 如何驱动 CC；CC 本身不读此 skill；监控违规主体是 Hermes（加载者），不是 CC（被驱动方）。** 2026-06-04 复现：未交代背景 → CC 误把监控违规归因于"CC 不听话" → 用户纠正"监控是 Hermes 的事情"。**修复**：context file 开篇即写清「加载者=Hermes / 被驱动方=CC / CC 不读此 skill」 |
| ★39 | **CC 路线图/架构文档重写后，`❯` 输入行残留“下一步建议”** | 症状：CC 完成报告后，底部输入行预填了它建议的下一步（如“开始 P2 manifest 骨架”）。这不是用户授权，尤其当下一步会改代码/manifest。**修复**：最终 capture 后先检查残留输入；尝试 `C-u`/`Escape` 清空；若清不掉且阶段已完成，直接 kill 这个隔离 session。不要按 Enter。完整模式见 `references/jz-plugin-ecc-roadmap-pattern.md`。 |

## 📦 References

| 文件 | 何时读取 |
|------|---------|
| `references/cli-reference.md` | 需要完整 CLI flags（7 张表） |
| `references/effort-routing.md` | Effort 完整体系：五级表 / 智能路由三档表 / 自检决策树 / 实战配置 / 成本换算 / `/effort` 切换陷阱（v4.1.0 从主体下沉） |
| `references/print-mode.md` | Print 模式深度：JSON/流式/管道/Schema/Session/Bare |
| `references/interactive-reference.md` | Slash Commands + 键盘快捷键 |
| `references/configuration.md` | Settings/CLAUDE.md/Subagents/Hooks/MCP/环境变量/同步 |
| `references/claude-octopus-hermes-mcp.md` | MCP 桥接配方 |
| `references/obsidian-agent-team-rewrite.md` | Obsidian 大规模重写模式 |
| `references/alex-longterm-agent-team-preference.md` | 用户偏好：默认 tmux 长会话 > print mode |
| `references/two-phase-research-build.md` | 两阶段研究→构建模式 |
| `references/two-phase-review-polish.md` | 两阶段审查→优化模式（2026-05-31） |
| `references/worker-stall-detection.md` | Worker 假死检测：token stalls → ls → tell cc |
| `references/worker-true-stall-no-disk-output.md` | Worker 真死（无磁盘产出）：杀会话 → 手动接管 |
| `references/cc-agent-team-content-research.md` | CC agent team 做内容研究简报的 fallback 工作流 |
| `references/cc-agent-team-parallel-implementation.md` | 并行实施：Leader-wiring 避免共享文件冲突 |
| `references/post-deploy-verification-pattern.md` | 部署后验证：curl 模式、token 脱敏陷阱、持久化字段验证 |
| `references/cc-session-isolation.md` | CC 多 Agent session 隔离完整调查 |
| `references/cc-clean-start-and-residual-input.md` | Clean-start + residual input guard |
| `references/agent-team-multi-lens-review.md` | Agent Team 多 Lens 并行审查模式（2026-05-31） |
| `references/agent-team-disk-verification.md` | Agent Team 磁盘验证：`find -newer` 绕过 tmux UI 盲区（Core Rule #12） |
| `references/teammate-mode-tmux-verified.md` | `--teammate-mode tmux` 官方文档验证（2026-05-31） |
| `Obsidian: CC tmux Agent Team 稳定性优化方案` | 稳定性全流程：session 生命周期、worker 诊断树、异常恢复 |
| `references/progress-reporting-enhanced.md` | 增强进度模板：emoji 状态映射、worker 树、token 跟踪、4 场景模板 |
| `references/cc-status-watchdog-after-complaint.md` | 用户指出未监控后的立即恢复序列（Hermes 自身轮巡，非 watchdog） |
| `references/destructive-cleanup-shadow-review.md` | 高风险删除让 CC shadow-review 成为破坏性步骤前的安全门 |
| `references/direct-numbered-batch-shadow-review.md` | 编号要求"直接处理让 CC 协助"时：解码、先推进确定部分、隔离 shadow-review |
| `references/CHANGELOG.md` | 版本历史：v3.1.0→v4.1.1 完整变更记录 |
| `references/de-slop-cc-integration.md` | de-slop（AI 味去除）CC skill 集成（2026-05-31） |
| `references/taste-skill-mobile-prototype.md` | CC + taste-skill 移动端原型图快速生成（2026-05-31） |
| `references/home-and-sandbox.md` | HOME override 认证 + macOS TCC 沙盒完整方案 |
| `references/cc-agent-team-document-audit.md` | CC agent team 文档审计模式 |
| `references/hermes-research-to-cc-strategic-insight.md` | Hermes 研究 → CC 战略洞察长文的交接模式 |
| `references/claude-octopus-upstream.md` | Claude Octopus 上游项目参考 |
| `references/literary-rewrite-pattern.md` | 文学化重写模式 |
| `references/license-verification-pattern.md` | CC 驱动外部项目许可证核查 |
| `references/cc-self-audit-instruction-following.md` | CC 自审计模式：用讨论协议优化自身 skill 的指令遵循 |
| `references/agent-team-model-selection.md` | CC Agent Team worker 模型选择机制（2026-06-01） |
| `references/hermes-production-env-verification.md` | CC 部署生产服务后按真实 `HOME/HERMES_HOME/PYTHONPATH` 验证 |
| `references/cqi-audit-v41-runtime-fork.md` | v4.1.0 CQI 反审：同版本号分叉、测 A 跑 B、去分叉前暂停单侧 patch |
| `references/cc-output-file-discovery.md` | CC 输出文件定位：`mdfind` vs `find`、`/tmp` 假设陷阱（2026-06-01） |
| `references/three-phase-redesign-pattern.md` | 三阶段大规模重构：讨论→侦察验证→Agent Team 执行（2026-06-02） |
| `references/reference-drift-debugging.md` | Reference 漂移诊断：SKILL.md 已更新但 references 仍教旧模式（2026-06-02） |
| `references/skill-redesign-via-cc-discussion.md` | 通过 CC 讨论协议做 skill 架构重设计（2026-06-02） |
| `references/destructive-system-cleanup-pattern.md` | 四阶段系统清理模式：Archive → Pre-Review → Destroy → Post-Audit（2026-06-03） |
| `references/cqi-instance-pattern.md` | CQI Instance 模式：skill CQI 计划重构为母计划实例的 8 节骨架 + 三桶分流（2026-06-04） |
| `references/three-lens-infra-debugging.md` | 🆕 3-Lens 基础设施调试：CC agent team 并行调查 adapter+网络+配置（2026-06-04 GPT-5.5 排查） |
| `references/jz-skills-cc-first-pattern.md` | jz-skills 仓库改动走 CC agent team 先审查后执行模式（2026-06-03） |
| `references/jz-plugin-ecc-roadmap-pattern.md` | Jz-Plugin 路线图吸收 ECC 优点的 CC 文档重写模式：context 边界、OB+源码+网络 evidence、CQI handoff、残留输入 guard（2026-06-05） |
| `references/hermes-infrastructure-self-audit.md` | Hermes 基础设施自审计模式（2026-06-03） |
| `references/kanban-swarm-practical-syntax.md` | Kanban Swarm CLI 实测语法 vs 概念语法对照表（2026-06-03） |
| `references/cc-session-mass-cleanup.md` | CC session 批量清理命令序列（2026-06-03） |

---

## ✅ Verification Checklist（稳定性优先）

- [ ] **🛑 占用检测？** 调 CC 前是否扫描了所有 tmux session 的 `●` **和 `✻`**？思考态（`✻/✶/✽/✳`）也视为忙碌！
- [ ] **Session 隔离？** 是否避免了 `--continue` **和共享 `hermes-claude-longterm`**？每任务新建独立 `hermes-cc-{agent}-{ts}`？
- [ ] **Workdir 隔离？** 多 agent 是否用了不同 workdir？
- [ ] **HOME override？** 是否带了 `HOME=/Users/alexcai`？
- [ ] **Bypass permissions？** 标题栏是否 `⏵⏵ bypass permissions on`？
- [ ] **PTY 对话框？** 是否处理了 Dialog 2（Down + Enter）？
- [ ] **🔴 Progress（红线①）？** 每次 `capture-pane` 是否都紧跟一个 📡 块（1:1 成对）？是否严格用 `📡 CC Agent Team [Xmin · 距上次 Xs]` 模板（worker 树 + emoji + token）？沉默 >2min 是否自标 `⏰超时`？
- [ ] **Agent team：** 是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] **🔍 完成前磁盘校验（Core Rule #12）？** 宣布完成前是否 `find -newer`/`ls` 确认文件真实落盘、size>0？摘要是否写明"已磁盘校验"？
- [ ] **Worker 监控：** 假死先 `ls` 查磁盘 → 文件存在则 `send-keys "Agent N done."`
- [ ] **轮间清理：** 每轮 agent team 后是否 `/clear`？完成后是否 `tmux kill-session`？
- [ ] **Session 干净度：** 启动 CC 前是否检查了 workdir 是否有 `.claude/` 残留？任务可能已由之前 session 完成时，是否先验证再决定是否重新执行？
- [ ] **收尾安全：** 最终报告后是否检查 `❯` 输入行没有残留下一步/commit/外发命令？
- [ ] **生产环境复核：** 若 CC 部署/重启 Hermes、A2A、gateway、launchd 服务，是否用服务真实 `HOME/HERMES_HOME/PYTHONPATH` 复现导入并核对 live pid/log/artifact？
- [ ] **🔄 skill 漂移？** 改完是否 `cp` 同步部署端、两端 `md5` 一致？（§0 read hook）

---

## §CQI 事件吐出（memory-hub 接入）

> CC 每轮任务结束时，把本轮发现的 **issue / evolution** 以 JSONL 追加写到 handoff 文件
> `/tmp/cc-cqi-events-<session>.jsonl`（`<session>` = 当前 CC session 名）。一行一条 JSON。
> 这是 fail-open 的旁路：写不写都不影响主任务交付，但写了能让 memory-hub 自动归集。

- **字段（对齐 live 6 硬字段 + payload）**：`type`（`issue`|`evolution`）、`skill`（受影响技能名）、
  `source`（恒为 `"cc"`）、`evidence`（原话/trace 逐字，勿摘要）、`ts`（ISO-8601 带时区）；
  `id` 可省（归集时自动生成 `ISSUE-/EVO-<skill>-NNN`）。`payload` 可选：issue 填 `implicated_rule`/`change_type`；
  evolution 必填 `change_type`，可带 `validation_score`/`changelog_ref`。`session_id` 建议带上。
- **CC 自判事件类型**：
  - `issue` —— 发现某技能的规则缺陷 / 指令未遵循 / 反复踩同一坑（trigger 多为 `runtime_failure` 或 `user_correction`）。
  - `evolution` —— 本轮实际改进了某技能正文/脚本/版本（trigger 多为 `manual_review`，带 `change_type`）。
- **状态语义**：CC 只吐 `issue`/`evolution` 原始事件，**不写 status**；状态机（new→acknowledged…）由 memory-hub 侧 `cqi_runtime.py` 维护。
- **Hermes 侧触发（三步链，全异步 + fail-open）**：Hermes 检测到 CC session 结束（`❯` 提示符且无 `●` 持续 >2min，复用 Session GC 判据）时，
  在 `memory-hub/` 下依次调用，**任一步失败不阻断后续，也不阻断 Hermes 主任务**：
  1. `scripts/mem_ingest.py` —— 归集该 handoff 文件 → 校验 → 批量写入 shard → 删 handoff。
  2. `scripts/cqi_runtime.py` —— 拉本期 new issue，自动追加 status_event（new→acknowledged，by=cqi-auto）；幂等。
  3. `scripts/mem_merge.py` —— 将新 issue 合并进 Obsidian CQI 审计文档（waterline 去重，只追加）；幂等。
- **cron 兜底**：上述链以 CC session 结束为触发；另有每 30 分钟的 cron 跑 `cqi_runtime.py && mem_merge.py`，
  捕获漏触发的批次。两脚本均幂等（无 new issue 直接跳过、waterline 去重），重复跑无副作用。
