---

name: claude-code
description: |
  Orchestrate Claude Code CLI from Hermes — tmux interactive + agent team (stability-first).
  Print mode is secondary and only used for connectivity smoke tests.
  
  Triggers: claude code, cc, delegate to claude, use claude, let claude handle, 用claude,
  让claude, agent team, claude review
  DO NOT use for: simple single-tool calls (Hermes does those directly), grammar fixes,
  non-coding creative writing (use appropriate creative skills)
type: routine
version: 4.2.0
author: Hermes Agent + Teknium (v4.2.0 salience slim：685→446 行，坑表/红旗/Core Rules/决策树/References/CQI 下沉到 references/，主体只留高频骨架)
license: MIT

---

# Claude Code — Hermes Orchestration（稳定性优先）

Delegate complex tasks to Claude Code via tmux interactive sessions + agent team. Print mode is secondary.

## §0 本 skill 是什么（加载者 / 被驱动方）

> [!important] 谁加载、谁被驱动
> **本 skill 是「如何驱动 Claude Code」的操作手册，被所有 Hermes agent 加载——不限于小黄 / default。** 任何 Hermes agent（`default` / `cron-worker` / `kanban-worker` / `subagent`）只要需要驱动 Claude Code，都加载这个 skill。
> - **加载者 = 当前 Hermes agent**（部署端 `~/.hermes/skills/autonomous-ai-agents/claude-code/SKILL.md` 是各 agent 实际读的）；**被驱动方 = CC（Claude Code）**，CC 本身不读这个 skill。
> - 因此「监控汇报」「轮巡」「占用检测」等规则是给 **加载它的 Hermes agent** 的职责，违规主体也是该 agent，不是 CC。

### 🔄 防漂移：加载时 hash 校验（fail-open read hook）

加载本 skill 时，校验 runtime 副本与源仓库是否一致——v4.1.0 曾发生「红线宪法 commit 进源仓库却没部署到运行端」的双向分叉（CQI 事件 #3）。跑 `scripts/drift-check.sh`：

```bash
bash ~/code/jz-skills/hermes/claude-code/scripts/drift-check.sh   # 对比源↔运行端 SKILL.md md5
```

**fail-open 设计（DP3）**：脚本漂移时打印 `⚠️ claude-code skill 漂移…先同步再用` 但 **永远 `exit 0`**——只告警、不 block skill 加载。校验失败绝不能让 skill 不可用（fail-open 而非 fail-closed）。

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

> **完整 16 条「借口 → 反驳」表见 `references/red-flags-table.md`。** 最高频三条：①"我直接用 terminal 调 claude 就行" → 不加载 = 不懂 PTY 对话框 / `--max-turns` / background 超时。②"我先静默检查，等结果再报" → 真实违规，每次 `capture-pane` 必须紧跟 📡（红线①）。③"用户问 CC 能力我凭记忆答" → CC 一个月四版，必须先搜 `code.claude.com/docs` 再答。

## 🔀 Decision Tree（稳定性优先 — 仅 tmux + agent team）

> **完整三棵决策树（调不调 CC / 单 CC vs Team vs 并行 / 按关注点拆分）+ 对照表见 `references/decision-trees.md`。** 速记：
> 1. 调 CC 前 🛑 跑占用检测；有 `●`/`✻` → 汇报等确认，全空闲才新建。
> 2. **选型口诀：Hermes 能干 → 不调 CC；要拆领域 → ⭐ Agent Team（默认）；任务互不相干 → 并行多 CC（特例，独立 workdir + 禁 `--continue`）。** 拿不准默认 Agent Team。
> 3. **拆分按关注点（领域/层），不按文件**——一个领域归一个 agent，数量由 CC 自定，context 只描述任务、必含 `timeout 10min per worker`。
> **不做：** print mode `-p`。简单任务 Hermes 自己干，调 CC 就是为了 tmux + agent team 的重活。

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

**🔁 手动轮巡 canonical（持续轮巡不是一句承诺）：** 用户要求当前 Hermes agent「持续轮巡 / 持续监控」时——发完 📡 后**必须立即启动下一轮轮巡工具调用**（`capture-pane` → 📡），而不是结束 turn 等用户再催。口头「我会持续监控」不算轮巡。**只用 Hermes 自身手动轮巡，不建 watchdog / 不建 cron / 不写脚本**，除非用户明确要求自动化（父皇校准："你就自己轮巡不就好了"）。收到后台 `[Background process … completed]` 通知 = 先 `read_file`/重抓屏 → 立即 📡 → 再起下一轮，不能当作已汇报。详见 `references/manual-patrol-after-report.md`。

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

> **完整 13 条（#0–#12）见 `references/core-rules-detail.md`。** 高频骨架：
> **#0** 调 CC 前扫所有 tmux session 占用（`●`+`✻`，详见 § Multi-Agent）· **#1** 每次新建独立 session，禁 `--continue` · **#2** 复杂任务必 agent team，按关注点拆 · **#4** 带 `HOME=/Users/alexcai` · **#9** 🔴 无条件持续 📡（红线①执行细则）· **#11** 🔴 违规自修正：当轮补做，禁"下轮改" · **#12** 完成前 `find -newer`/`ls` 磁盘校验。其余 #3/#5/#6/#7/#8/#10 见 detail 文件。

## 🤝 Multi-Agent Coordination Protocol（多 Agent 协调）

> **核心问题：** Hermes 的多个 agent（主 agent、cron-worker、kanban worker、subagent）彼此不知道对方是否在用 CC。没有协调机制 = session 冲突 = 任务互相覆盖。

### 启动前：占用检测（每次调 CC 前必须执行）

**唯一权威脚本 = `references/occupancy-scan.sh`**（扫所有 session 的 `●`/`✻`/`❯`，输出 BUSY/THINKING/IDLE）：

```bash
bash ~/code/jz-skills/hermes/claude-code/references/occupancy-scan.sh
```

> 有 `●` 或 `✻` → 必须汇报用户后等确认；全空闲 / 用户确认 → 新建 `hermes-cc-{agent}-{ts}`。`❯` ≠ 空闲（Pitfall #24）。

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

> **硬规则（红线① 复述）：`capture-pane` = 一次用户可见监控事件，每次抓屏必立即发 `📡` 块**，不连抓 2-3 次才汇总；只看到 `✳ thinking` 也要报"Leader 思考中"。`sleep && capture-pane` 不发正文 = 沉默 = 未监控。投递失败（gateway/确认门拦截）也算未汇报 → 改用当前对话正文回禀同一 `📡`。用户问"进度？"第一动作是抓屏 + 可见汇报，不先解释。
>
> 💡 **磁盘验证**（`find <workdir> -newer /tmp/cc-marker -type f` 每 30s 扫，绕过 UI 盲区，Core Rule #12）见 `references/agent-team-disk-verification.md`；**找不到输出文件**（CC 常直写 OB vault 而非 `/tmp/`，先 `mdfind -name` 秒搜）见 `references/cc-output-file-discovery.md`。

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

## 🔌 MCP Bridges: Claude Octopus + tmux-bridge

- **Claude Octopus**（`references/claude-octopus-hermes-mcp.md`）— 只读探针、实验性任务。
- **tmux-bridge pilot（DP2）**（`references/tmux-bridge-integration.md`）— [tmux-bridge-mcp](https://github.com/howardpen9/tmux-bridge-mcp)（MIT, v0.3.0）把 `capture-pane`/`send-keys` 封装成 MCP 工具（`tmux_read`/`tmux_type`/`tmux_keys`，read-act-read guard）。**首选 pilot，非硬依赖**：没配/报错/mid-session 未生效时无缝回退 raw `tmux capture-pane`+`send-keys`，红线① 与所有 Pitfall 在两种通道下都成立。⚠️ 配置坑：`args` 经 `hermes config set` 会存成 JSON 字符串致 MCP 启动失败，须在 config.yaml 手写 YAML 列表（详见 reference）。

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

> **完整坑表（39 条）见 `references/critical-pitfalls-table.md`；更深细节见 `references/common-pitfalls.md`。** 此处只列最高频 3 坑：
> **编号纪律：** 永久递增、不重用。`#16 #17 #29 #32 #34 #35` 为废弃编号，`#49` 跳号，原重号 `#40` 已于 2026-06-08 拆为 #40（思考循环）+ #51（send-keys 排队）。

| # | Pitfall | 一句话修复 |
|---|---------|-----------|
| 1 | **Dialog 2 默认"No"** | `Down → Enter`，不是 `Enter` |
| 2 | **HOME override 认证失败** | 始终 `HOME=/Users/alexcai claude ...` |
| 7 | **send-keys 不执行 / CC 思考循环** | 15s 无 `●` → 补发空 `Enter`；`✻ thinking` >3min 且 token 冻结 → 单行短命令推动 → 仍循环则 `Ctrl+C` 缩到原子任务。token 增长 = 真在思考，继续等。详见坑表 #7 |

## 📦 References

> **完整 60+ 条 reference 目录见 `references/index.md`。** 最常用入口：

| 文件 | 何时读取 |
|------|---------|
| `references/index.md` | 🗂️ 完整 reference 目录（所有模式/陷阱/历史） |
| `references/cli-reference.md` | 完整 CLI flags（7 张表） |
| `references/effort-routing.md` | Effort 完整体系：五级表 / 路由 / 成本换算 / `/effort` 陷阱 |
| `references/configuration.md` | Settings/CLAUDE.md/Subagents/Hooks/MCP/环境变量/同步 |
| `references/critical-pitfalls-table.md` | 完整坑表（39 条）；深度细节见 `common-pitfalls.md` |
| `references/red-flags-table.md` | 完整 16 条「借口 → 反驳」表 |
| `references/core-rules-detail.md` | Core Rules 完整 13 条（#0–#12） |
| `references/decision-trees.md` | 三棵决策树 + 单 CC/Team/并行对照表 |
| `references/progress-reporting-enhanced.md` | 增强进度模板：emoji 状态映射、worker 树、token 跟踪 |
| `references/manual-patrol-after-report.md` | 手动持续轮巡：📡 后必须实际起下一轮 patrol |
| `references/cc-session-isolation.md` | CC 多 Agent session 隔离完整调查 |
| `references/tmux-bridge-integration.md` | tmux-bridge MCP pilot + raw tmux fallback（DP2） |
| `references/CHANGELOG.md` | 版本历史：v3.1.0→v4.1.1 完整变更记录 |

---

## 🚧 收尾输入行安全门（Final Input-Line Gate）

> **canonical 收尾硬门：** CC 宣布完成后、`tmux kill-session` 之前**必须**检查 pane 底部 `❯` 输入行——专防 CC 把「下一步建议 / commit / `rm -rf` / 外发命令」预填在 `❯` 等一个误触 Enter。

```bash
tmux capture-pane -t <session> -p -S -3 | tail -1   # 看最后一行 ❯ 后有无残留文本
```

- `❯` 后**为空** → 安全，可收尾 / `kill-session`。
- `❯ <任何残留命令>` → **绝不按 Enter**。先 `C-u` 清行 → 清不掉 `Escape` → 仍残留且阶段已结束直接 `tmux kill-session`。
- CC 自己建议的危险动作（`rm` / `git push` / 部署）出现在 `❯` ≠ 用户授权，一律不执行。

> 关联 Pitfall ★28 / ★39（残留输入）+ ✅ Checklist「收尾安全」。**行为验证（T8）须在真实任务收尾时实跑本门一次。**

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

> **完整规格（6 硬字段 + payload、自判规则、Hermes 三步链触发、cron 兜底）见 `references/cqi-event-emission.md`。** 核心铁律：

- CC 每轮结束把 **issue / evolution** 以 JSONL 追加写 `/tmp/cc-cqi-events-<session>.jsonl`（fail-open 旁路，一行一条 JSON）。
- **🔴 type 枚举铁律（v4.1.2）：`type` 只取 `issue` 或 `evolution`，禁自由发挥。** 审计发现缺陷/新约束 → `issue`；修复/改进/回写 → `evolution`；状态变更 → 不写 type（状态机由 memory-hub 维护）。写错 = mem_ingest.py 拒收（degrade），事件永久丢失。
- 硬字段：`type`/`skill`/`source`(="cc")/`evidence`(逐字勿摘要)/`ts`(ISO-8601)；`id` 可省，`payload`/`session_id` 可选。
- Hermes 侧检测到 CC session 结束（`❯` 无 `●` >2min）→ 异步跑 `mem_ingest.py → cqi_runtime.py → mem_merge.py`（任一步失败不阻断），另有每 30min cron 兜底，全幂等。
