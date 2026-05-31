---
name: claude-code
description: |
  Orchestrate Claude Code CLI from Hermes — tmux interactive + agent team (stability-first).
  Print mode is secondary and only used for connectivity smoke tests.
  
  Triggers: claude code, cc, delegate to claude, use claude, let claude handle, 用claude,
  让claude, agent team, claude review
  DO NOT use for: simple single-tool calls (Hermes does those directly), grammar fixes,
  non-coding creative writing (use appropriate creative skills)
version: 3.5.0
author: Hermes Agent + Teknium
license: MIT
---

# Claude Code — Hermes Orchestration（稳定性优先）

Delegate complex tasks to Claude Code via tmux interactive sessions + agent team. Print mode is secondary.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "我直接用 terminal 调 claude 就行" | 不加载 skill = 不知道 PTY 对话框处理、不知道 `--max-turns` 防止失控、不知道 background 超时会被杀 |
| "任务太简单，print mode 就行" | 简单任务也有坑：`--max-turns` 不设 = 可能无限循环烧钱；`--model` 不指定 = 开销不可控 |
| "我用 tmux 不需要这个 skill" | PTY 有两个对话框需要精确按键序列。权限对话框默认是"No, exit"——你必须 Down+Enter。错过 = Claude 直接退出 |
| "agent team 就是普通 Task subagent" | Claude Code 的 agent team 是独立机制。用户明确说过不要用普通 Task subagent 冒充 team |
| "我设置 budget=$0.05 够了" | 系统 prompt cache 创建本身就 ~$0.05。更低 → 立即报错。烟雾测试用 `$0.2` |
| "我先静默检查 tmux，等 CC 有结果再汇报" | **2026-05-31 真实违规。** 用户说\"你没有遵循skill给我转发监控的cc界面啊\"。发送任务后必须从第 15 秒起持续汇报 📡，沉默 >2min = 用户不知道 CC 死活，可能误判卡死中断 |

## 🔀 Decision Tree（稳定性优先 — 仅 tmux + agent team）

```
调 CC 之前 → 🛑 先跑占用检测（扫描所有 tmux session 的 ●）
         │
         ├── 有 BUSY session → 汇报用户，等确认
         │
         └── 无 BUSY / 用户确认新建
              │
              ├── ⭐ Agent Team（默认，绝大部份场景）
              │   └── tmux 交互模式
              │       ├── 新任务 → 新建 session `hermes-cc-{profile}-{ts}`
              │       ├── 复用上下文 → `claude --resume <id> --fork-session`
              │       └── 长会话 → `hermes-claude-longterm`（仅当扫描确认空闲时）
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

**让 CC 自己决定 agent 数量。** 写 context 文件时只描述「要做什么」，不要写「用 3 个 agent」「开 5 个 worker」。把数量决策权交给 CC——它看到任务全貌（文件依赖、关注点边界、测试范围）后，比你更清楚该开几个 worker。任何硬编码的 agent 数量都是过早优化，会把一个本该 2 个 worker 的活硬塞进 4 个、或把 6 个领域的活压进 3 个。

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

| 对比 | 按文件拆 ❌ | 按关注点拆 ✅ |
|------|------------|-------------|
| 改动归属 | 一个逻辑改动散落多个 agent | 一个领域完整归一个 agent |
| 共享文件 | 多 agent 写同一文件 → 冲突 | 文件随领域分开，少交叉 |
| 边界 | 模糊，需大量协调 | 清晰，可独立完成与验证 |
| Leader 协调成本 | 高（缝合多处碎片） | 低（合并完整领域成果） |

> 拆分后别忘记 worker 纪律：context 文件必须含 `timeout 10min per worker`，假死先 `ls -la` 查磁盘再 `send-keys "Agent N done."`——详见 `## ⚡ Core Rules` #10 与「Worker 假死恢复协议」。

## 📡 Post-Send Protocol（发送任务后 — 强制执行）

**发送任务后，必须立即进入 30-60s polling 循环，从第 15 秒起向用户汇报 `📡` 进度块。这不是\"等结果再汇报\"——这是\"让用户看到 CC 还活着\"。**

```
发送 send-keys Enter
     │
     ▼
sleep 15 → 首次 polling → 立即向用户汇报 📡 状态
     │
     ▼
每 30-60s polling → 每次向用户汇报 📡 进度块
     │
     ├── 看到 ● 工具调用 → 汇报\"CC 正在 [工具名]：[描述]\"
     ├── 看到 ❯ 空闲 → 检查是否完成
     ├── 看到 worker 列表 → 汇报 worker 树（状态 emoji + 耗时 + token）
     └── 沉默 >2min → ⚠️ 向用户声明\"CC 无响应 2min，继续等待中\"
```

**违反此协议 = 用户不知道 CC 死活，可能误判卡死而中断。2026-05-31 真实违规教训。**

## 🧠 Model & Effort Level（Opus 4.8 + 思维链）

> **v2.1.158 起可用。** Opus 4.8 默认 effort = `high`，支持五级思维链。

### 启动时指定

```bash
claude --model claude-opus-4-8 --effort max   # 完整模型名 + 最强推理
claude --model opus --effort xhigh             # 别名 + 高推理
claude --effort low                            # 轻量任务，省钱
```

### 五级 effort

| Level | CLI flag | 说明 |
|-------|----------|------|
| `low` | `--effort low` | 最少思考，适合简单翻译/格式转换 |
| `medium` | `--effort medium` | 中等 |
| `high` | `--effort high` | **Opus 4.8 默认** |
| `xhigh` | `--effort xhigh` | 更深推理，仅次 max（Opus 4.8/4.7 专属） |
| `max` | `--effort max` | 最强推理，Cogitated 时间最长 🧠 |

### 会话内切换：`/effort`

```
/effort xhigh
```

> ⚠️ 弹出确认对话框（默认是 "No, go back" → **选 1**）。切换会清除当前 cache，history 全部重读——长会话中慎用。确认后状态栏显示 `◉ xhigh`。

### 🧭 智能 Effort 路由（按任务信号选档）

> **🔒 默认地板 = `high`。** 除非用户明确说 "fast / cheap / quick / 快一点 / 省钱"，**永远不要低于 `high`**。没有信号 = 从 `high` 起步，按任务复杂度往上抬，**绝不往下降**。地板就是地板，不要因为"这任务看起来简单"就自作主张降到 `medium`——简单也得 `high`，除非用户开口要快。

调 CC 前先选档，不要默认全用 `high` 凑合：`high` 是地板不是天花板。多文件、审查、设计、根因——这些信号一出现，**必须**往上抬到 `xhigh` 或 `max`。该抬不抬 = 推理深度不够 = 返工。

#### 三档路由表

| 任务信号 | 推荐 effort | 为什么 |
|---------|------------|--------|
| 简单重构、rename、提取函数 | `high` | 地板档，单点改动不需要更深推理 |
| 单文件编辑、局部 bugfix | `high` | 改动面小，`high` 足够覆盖 |
| 直白内容生成（翻译润色后的成文、模板填充） | `high` | 无架构判断，地板即可 |
| 基础研究（查一个 API、读一个模块） | `high` | 检索型任务，深思无增益 |
| 多文件架构改动、跨模块重构 | `xhigh` | 改动有连锁影响，需推演依赖关系 |
| agent team 审查、code review | `xhigh` | 要找出非显性问题，浅推理会漏 |
| 设计决策（选型、API 设计、方案权衡） | `xhigh` | 需要对比多方案 trade-off |
| 复杂内容创作、taste-skill 原型图 | `xhigh` | Design Read 质量随 effort 明显提升 |
| 深度架构分析、全栈功能实现 | `max` | 跨层推理 + 大量隐性约束 |
| 多 lens 并行审查（3+ lens） | `max` | 每个 lens 都要深推，汇总更要 |
| 根因调试、疑难 bug 定位 | `max` | 症状到根因链长，浅推理只能治标 |
| 安全审计、skill 撰写/重写 | `max` | 高风险 + 高抽象，错一处全盘塌 |

> 💡 **`xhigh` / `max` 仅 Opus 4.8/4.7 专属。** 别名机型上不可用——选 `max` 前确认 `--model` 是 Opus 4.8/4.7。

#### 自检决策树（顺着走到一个明确档位）

```
选 effort 前 → ❓ 用户是否说了 "fast / cheap / quick / 快一点 / 省钱"？
            │
            ├── ✅ 是 → 可降到地板以下
            │        ├── 纯格式转换 / 一次性翻译 → `--effort medium`
            │        └── 用户说"越快越好" / 烟雾测试 → `--effort low`
            │        （⚠️ 仅此一种情况允许低于 high）
            │
            └── ❌ 否 → 🔒 从 `high` 起步，按信号往上抬：
                     │
                     ├── ❓ 涉及多文件 / 架构改动 / 任何审查 / 设计决策 / 原型图？
                     │   ├── 否 → 停在 `high`  ✅（单文件、直白生成、基础研究）
                     │   └── 是 → 抬到 `xhigh`，再问下一层 ↓
                     │
                     └── ❓ 是「深度」级别？（深度架构分析 / 多 lens 并行 / 根因调试 / 全栈功能 / 安全审计 / 写 skill）
                         ├── 否 → 停在 `xhigh`  ✅
                         └── 是 → 抬到 `max`  ✅（最强推理，认了这个成本）
```

**一句话规则：** 没信号 → `high`；碰到「多文件/审查/设计/原型」→ `xhigh`；碰到「深度/多 lens/根因/全栈/安全/写 skill」→ `max`。**只有用户喊"快"才允许往地板下走。** 拿不准时往上抬一档，不要往下省——返工的成本远高于多想几秒的成本。

### ⚙️ 实战配置（Effort in Practice）

智能 Effort 路由决定档位后，**首选在启动 CC 时就用 `--effort` 落地**——比会话内切换省事、省钱、省 cache。

**场景 → 启动 flag：**

| 场景 | 路由判断 | 启动 flag |
|------|---------|----------|
| 单文件小修，用户没说"快" | 地板档 | `--effort high` |
| Agent team code review | 多 lens 并行需深推理 | `--effort xhigh` |
| 安全审计 / skill 重写 | 高风险、根因级 | `--effort max` |

```bash
# 在目标 workdir 下启动 tmux session，按路由结果定档
# 单文件小修（用户未要求"快"）→ high
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort high

# agent team code review → xhigh
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort xhigh --teammate-mode tmux

# 安全审计 / skill 重写 → max
HOME=/Users/alexcai claude --model claude-opus-4-8 --effort max
```

> 💡 启动命令照常带 `HOME=/Users/alexcai` + `--model`，并在目标 workdir 下启动 session，effort 只是多一个 flag。

**会话内临时改档**用 `/effort <level>`，见上方 `### 会话内切换：/effort` 子节。

> ⚠️ **关键陷阱：切档会清空当前 prompt cache，整个 history 被重读——又慢又烧钱。** 所以**不要在会话中途随意切档**，除非任务性质真的变了（例如从研究阶段进入深度调试阶段）。**能在启动时就定对档位，永远比中途切强。**

> 💰 **成本提示：** `max` ≈ 2× `xhigh`，`xhigh` ≈ 1.5× `high` → 换算下来 **`max` ≈ 3× `high`**。"按需路由"不是抠门，是避免给简单任务付深度推理的钱。
> **结论：** 能用 `high` 解决的别开 `max`；但该上 `max` 的任务（安全审计、根因调试）省这点钱会得不偿失——**返工比深度推理贵得多。**

## ⚡ Core Rules（Hermes Agent 执行规则）

0. **🛑 发任务前必须扫描 CC 占用状态（新增）** — 不同 agent 不知道彼此是否在用 CC。**每次调 CC 前，必须先扫描所有 tmux session 是否已有活跃的 CC 工具调用**：

   ```bash
   # 扫描所有 tmux session，检查是否有活跃的 ● 工具调用（表示 CC 正在工作）
   for s in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
     if tmux capture-pane -t "$s" -p -S -8 2>/dev/null | grep -q '●'; then
       echo "⚠️ BUSY: $s — 其他 agent 正在使用 CC"
     fi
   done
   ```

   - 有 `●` → **必须汇报用户**："CC 正被 session `<name>` 占用（`●` 活跃工具调用），等待或新建独立 session？"
   - 无 `●` + 看到 `❯` → 空闲，可安全使用
   - ⚠️ **不要自作主张开新 session 绕过去**——用户可能不知道两个 CC 在同时跑，消耗翻倍

1. **默认 tmux 新 session + 独立 workdir** — 每次调 CC 用独立 session 名 `hermes-cc-{profile}-{ts}`。**不用 `--continue`**。同一 workdir 下 CC 会自动恢复最近 session → **每个 agent 独立 workdir**。
2. **复杂任务必须 agent team** — 多文件/多步骤/根因分析/实现+测试/架构判断 → 让 CC 自己 spawn subagent。**Agent 数量由 CC 按复杂度自定，context 文件只描述任务（要做什么 / 覆盖哪些关注点），不规定 team 规模，不硬编码 worker 个数。** 按关注点拆，不按文件拆 → 详见 `### 🧩 Agent 数量与拆分原则`。
3. **Always set `workdir`** — 让 CC 聚焦正确项目目录。
4. **Always 带 `HOME=/Users/alexcai`** — 避免 Hermes profile HOME override 导致认证失败。
5. **不要杀慢会话** — 用 `capture-pane` 检查进度，确认卡死才 `Ctrl+C`。
6. **清理一次性 tmux 会话** — 用完就 `tmux kill-session`，避免泄漏。
7. **每轮 agent team 后 `/clear`** — 避免 context 膨胀。
8. **⚡ bypass permissions** — 启动后验证，通常默认已启用。
9. **📡 无条件持续汇报进度** — 每 30-60s polling，沉默 >2min 不可接受。**必须使用下方 Progress Reporting 段规定的 `📡 CC Agent Team [Xmin]` 模板格式**，自由发挥视为未汇报。
10. **Worker 假死先查磁盘** — `ls -la` → 文件存在则 `send-keys "Agent N done."` → 不存在则手动接管。

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
  
  # 检测 ❯ 空闲（CC 等待输入）
  if echo "$pane" | tail -1 | grep -q '❯'; then
    echo "✅ IDLE: $s — CC 空闲，可复用"
  fi
done
```

### 决策矩阵

| 扫描结果 | 决策 | 操作 |
|---------|------|------|
| 无 tmux CC session | 直接新建 | `tmux new-session -d -s hermes-cc-{profile}-{ts} ...` |
| 有空闲 CC（`❯`，无 `●`） | 可复用 | 用 `/clear` 清空旧 context → 发新任务 |
| 有忙碌 CC（`●`） | **先汇报用户** | "CC 正被 `{session}` 占用，{工具名}。等待还是新建独立 session？" |
| 有忙碌 CC + 用户确认新建 | 新建隔离 session | 独立 session 名 + **独立 workdir** |

### 汇报模板

```
⚠️ CC 占用检测
  BUSY: hermes-claude-longterm — ● Reading src/auth.py
  → 等待完成（预计 X 分钟）还是新建独立 session？
```

### Session 命名规范

| Agent | Session 名 | 说明 |
|-------|-----------|------|
| 主 agent (小黄) | `hermes-cc-default-{ts}` | 默认 |
| cron-worker | `hermes-cc-cron-{ts}` | 定时任务 |
| kanban worker | `hermes-cc-kanban-{ts}` | 看板 |
| 手动/临时 | `hermes-cc-{task}-{ts}` | 用完即杀 |

### 清理纪律

- 每次任务完成 → `/clear` + `tmux kill-session`
- 多轮任务间 → `/clear`（不清 session，保留 tmux）
- 最终完成 → `tmux kill-session`

### ⚠️ Session 劫持诊断

当你发送任务后 CC 无响应，或 `capture-pane` 显示 `❯` 后面跟着**不是你发的命令**（如 `❯ cd ~/code/hermes-a2a && Read ...`），说明另一个 agent 正在竞争同一 CC session。此时：

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

**汇报节奏：**
- 发送任务后 15 秒 → 首次检查
- 之后每 30-60 秒 → 轮询一次
- 看到关键信号 → 立即汇报（不等到下次轮询）

**检查方法：**
```bash
# 取最后 60 行，看 CC 在做什么
tmux capture-pane -t hermes-claude-longterm -p -S -60
```

> 💡 **Agent Team 磁盘验证（推荐）**：tmux task board 只显示 worker 运行时间，无法判断实际文件产出。用 `find <workdir> -newer /tmp/cc-marker -type f` 每 30s 扫一次磁盘，可以绕过 UI 盲区精确追踪进度。详见 `references/agent-team-disk-verification.md`。

**关键信号识别：**

| 信号 | 含义 | 动作 |
|------|------|------|
| `●` 前缀 + 工具名 | CC 正在调用工具 | 汇报："CC 正在 [工具名]：[简短描述]" |
| `❯` 前缀（最后一行） | CC 等待输入/完成 | 检查是否已完成任务。如果任务结束 → 汇报完成 |
| `Error` / `Traceback` | 出错 | 立即汇报错误内容 |
| `bypass permissions off` | 权限模式丢失 | 立即发 `Shift-Tab` 恢复 |
| `[Fact-Forcing Gate]` | CC 编辑前安全门（正常） | 等待 5-10s，CC 会自动陈述事实后重试 |
| `Waiting for N background agent` + worker token 不变（>2min） | **worker 假死，文件可能已写盘** | 见下方「Worker 假死恢复协议」 |
| 多轮无 `●` 也无 `❯` | 可能卡死 | 等待 2 分钟。仍无变化 → `Ctrl+C` 中断 |

#### Worker 假死恢复协议

**症状:** `Waiting for N background agents` + worker token >2min 不变。

**错误做法:** ❌ 反复 `send-keys Enter` ❌ 杀 worker

**正确恢复:**
```bash
# 1. 检查产出文件是否存在且 size > 0
ls -la <expected output path(s)>

# 2. 文件存在 → 告诉 CC
tmux send-keys -t <s> 'Agent N is done. All files exist on disk. Continue.' Enter
```
**若文件不存在或 size == 0** → Worker 真死 → `tmux kill-session` → 手动接管。**教训:** context file 加 `timeout 10min per worker`。

**汇报模板（必须严格按此格式，不按模板 = 未完成汇报）：**
```
📡 CC Agent Team [Xmin]
  ⚡ Leader: <当前操作>
  ├─ ✅ Worker A: <描述> (Xs, X.Xk tokens)
  ├─ 🔵 Worker B: <描述> (running)
  └─ 🟡 Worker C: 假死 — ls 确认文件中
  📊 Token: X.Xk · 🛡️ Gate: N 次
```

> 完整模板（单任务/异常/等待/限流）→ `references/progress-reporting-enhanced.md`。状态 emoji：⚡运行 💤空闲 ✅完成 🔵进行中 🟡假死 🔴真死 🛡️Gate ❌错误 🐚卡死 ⏳限流

**结束信号：** 当 `capture-pane` 最后一行是 `❯` 且上方不再有 `●` 工具调用时，CC 已完成当前任务。汇报最终结果并询问用户是否继续。

> 💡 用户在 TG 收到进度汇报后可能回复新指令。收到用户消息后立即 `capture-pane` 检查 CC 是否空闲（`❯`），空闲则发送新指令。

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
5. 报告用了哪种 team workflow + 输出路径

> ✅ `--teammate-mode tmux` 经 2026-05-31 公网验证：CC 官方文档 [code.claude.com/docs/en/agent-teams](https://code.claude.com/docs/en/agent-teams) 确认 split-pane 模式支持，非第三方 hack。Flag 合法，SKILL.md 原文无误。

**内容研究简报：** 当 delegate_task 被 kanban gate 拦截时，CC agent team 可作为 fallback。context 文件必须含 worker timeout 规则 + extractor prompt。详见 `references/cc-agent-team-content-research.md`。

## ⚠️ Critical Pitfalls

> 完整细节见 `references/common-pitfalls.md`。这里只列出稳定性核心坑。

| # | Pitfall | 一句话修复 |
|---|---------|-----------|
| 1 | **Dialog 2 默认"No"** | `Down → Enter`，不是 `Enter` |
| 2 | **HOME override 认证失败** | 始终 `HOME=/Users/alexcai claude ...` |
| 3 | **Worker 假死（文件在磁盘）** | `ls -la` 确认文件存在 → `send-keys "Agent N done. Continue."` |
| 4 | **Worker 真死（无磁盘产出）** | `kill-session` → 手动接管。context file 写 timeout 规则 |
| 5 | **多轮 context 膨胀** | 每轮后 `/clear` |
| 6 | **Fact-Forcing Gate** | 正常流程，不是卡死。等 5-10s |
| 7 | **send-keys 不执行** | 15s 无 `●` → 补发空 `Enter` |
| 8 | **📡 沉默 >2min** | 即使无事也要汇报 |
| 9 | **Agent team schema 持久化** | Leader wiring 后写 curl 脚本验证新字段 |
| 10 | **MacOS TCC 沙盒** | `cp` 到 `/tmp/` → CC 处理 → `cp` 回去 |
| 11 | **Background shell stall** | 发 redirect 指令 → 30s 无响应 → 手动接管 |
| 12 | **Token 脱敏破坏语法** | 字符串拼接不用 f-string |
| 13 | **TMUX Shift-Tab 无效** | 不用——Dialog 直接 `Down → Enter` |
| 14 | **Scrollback 污染** | 复用 session 前先 `pwd` 验证 |
| 15 | **Print mode 长文档不稳定** | 改用 Python + Playwright（`references/python-playwright-pdf-fallback.md`） |
| ★18 | **多 Agent Session 冲突** | 先跑占用检测（`§ Multi-Agent Coordination Protocol`） |
| ★19 | **Session 被劫持：❯ 显示非本 agent 命令** | 发 `pwd` 测试→看到 `❯ cd /other/path && other task` → 另一个 agent 在竞争同一 CC。`/clear` + 重发任务。若反复出现 → kill CC daemon + 所有 tmux session 后重建。**不要继续往被劫持的 session 发任务**——命令会被覆盖。 |
| ★20 | **send-keys 命令在 ❯ 处但不执行** | 两层原因：(A) CC 初始化期（`tmux new-session` 后 3-5s）— CC 在渲染 bypass 横幅/claude-mem/❯ 时收到的 send-keys 只显示不执行。(B) **长/多行命令**（即使初始化完成后）— `send-keys` 长命令 + Enter 后，文本可见于 ❯ 处但 CC 未开始处理（无 `●` 出现）。**修复**：(1) 初始化后 `sleep 5` + `capture-pane` 确认 ❯ 稳定；(2) 发送长命令后 15s 内无 `●` → **立即补发空 `Enter`** 触发执行（⚠️ 不要等——越快越好）；(3) 补发后仍无 `●` → 再补发一次空 Enter。**不要反复发相同命令**——会重复出现在 ❯ 处。本会话 2026-05-31 两次复现（一次初始化后 / 一次长命令后）。 |
| ★21 | **Obsidian Vault Gate 循环：写入被反复拦截** | `Ctrl+C` → 显式放行指令（覆盖文件引用者/Glob/数据结构/用户指令 4 项）。**预防**：context file 预填 Gate 事实。详见 `references/common-pitfalls.md` #21。 |
| ★22 | **Hermes cross-profile write guard 阻拦 context file** | context file 写到 `/tmp/`（中性位置），CC 从 `/tmp/` 读取后直接在目标 workdir 改文件——CC 的 Write 工具不受 Hermes profile guard 影响。 |
| ★23 | **CC 在方案未审定时提前执行：修改文件+提交，但用户没批准** | 当用户说"处理决策点"/"看方案"时，**默认 = 讨论，不是执行**。只有用户明确说"可以做了"/"执行吧"后才动手。详见 `references/common-pitfalls.md` #23。 |
| ★23 | **CC 自动恢复旧会话——不是干净启动** | 当 workdir 下有 `.claude/` 状态时，新 tmux session 的 `claude` 命令会**自动 resume 最近一次会话**，不会从零开始。看到熟悉的 task board 和历史记录说明是旧会话。**处置**：(1) 先检查是否已有成果——如果上轮已完成任务，直接收成果；(2) 如需干净启动，用 `claude --new-session` 或切到无 `.claude/` 的目录；(3) 不要假设每次 `tmux new-session + claude` 都是全新开始。2026-05-31 复现：启动 CC 执行 SIL v5.0 改造，结果恢复了之前已全部完成的 session。 |

## 📦 References

| 文件 | 何时读取 |
|------|---------|
| `references/cli-reference.md` | 需要完整 CLI flags（7 张表） |
| `references/print-mode.md` | Print 模式深度：JSON/流式/管道/Schema/Session/Bare |
| `references/interactive-reference.md` | Slash Commands + 键盘快捷键 |
| `references/configuration.md` | Settings/CLAUDE.md/Subagents/Hooks/MCP/环境变量/同步 |
| `references/claude-octopus-hermes-mcp.md` | MCP 桥接配方 |
| `references/obsidian-agent-team-rewrite.md` | Obsidian 大规模重写模式 |
| `references/alex-longterm-agent-team-preference.md` | 用户偏好：默认 tmux 长会话 > print mode |
| `references/two-phase-research-build.md` | 两阶段研究→构建模式：Phase 1 研究出 Obsidian → Phase 2 agent team 构建 |
| `references/two-phase-review-polish.md` | 🆕 两阶段审查→优化模式：Phase 1 agent team 审查 → Phase 2 单 CC 产出干净交付文档（2026-05-31） |
| `references/worker-stall-detection.md` | Worker 假死检测：token stalls → ls → tell cc · 本会话复现 3 次 |
| `references/worker-true-stall-no-disk-output.md` | Worker 真死（无磁盘产出）：send-keys 无效 → 杀会话 → 手动接管 |
| `references/cc-agent-team-content-research.md` | CC agent team 做内容研究简报：delegate_task blocked 时的 fallback 工作流、verbatim quote 局限性、worker stall 预防 |
| `references/cc-agent-team-parallel-implementation.md` | 并行实施模式：Leader-wiring 策略避免共享文件冲突 + context 文件模板 + schema 验证 |
| `references/post-deploy-verification-pattern.md` | 部署后验证：Python subprocess curl 模式、token 脱敏陷阱、持久化字段验证 |
| `references/cc-session-isolation.md` | CC 多 Agent session 隔离完整调查：`--session-id` 验证、`--fork-session`、交互模式陷阱 → Obsidian `00-Inbox/CC tmux 多Agent 会话隔离问题.md` |
| `references/agent-team-multi-lens-review.md` | 🆕 Agent Team 多 Lens 并行审查模式：3-lens 并行审查流程、context file 模板、worker timeout 策略、cost 特征（2026-05-31） |
| `references/agent-team-disk-verification.md` | 🆕 Agent Team 磁盘验证：用 `find -newer` 绕过 tmux UI 盲区追踪 worker 实际文件产出（2026-05-31） |
| `references/teammate-mode-tmux-verified.md` | 🆕 `--teammate-mode tmux` 官方文档验证（2026-05-31）：code.claude.com/docs/en/agent-teams 确认 split-pane 模式，`teammateMode: "tmux"` 或 `--teammate-mode tmux` |
| `Obsidian: CC tmux Agent Team 稳定性优化方案` | 稳定性全流程：session 生命周期、worker 诊断树、进度监控、异常恢复速查表 |
| `references/progress-reporting-enhanced.md` | 🆕 增强进度模板：emoji 状态映射、worker 树、token 跟踪、4 场景模板 |
| `references/CHANGELOG.md` | 🆕 版本历史：v3.1.0→v3.5.0 完整变更记录 |
| `references/de-slop-cc-integration.md` | 🆕 de-slop（AI 味去除）CC skill 集成：从 jz-skills 安装、调用签名、L4 质量门用法（2026-05-31） |
| `references/taste-skill-mobile-prototype.md` | 🆕 CC + taste-skill 移动端原型图快速生成：Design Read → HTML/CSS → Playwright 截图（2026-05-31） |

---

## ✅ Verification Checklist（稳定性优先）

- [ ] **🛑 占用检测？** 调 CC 前是否扫描了所有 tmux session 的 `●`？有 BUSY 是否汇报了用户？
- [ ] **Session 隔离？** 是否避免了 `--continue`？session 名用 `hermes-cc-{profile}-{ts}`？
- [ ] **Workdir 隔离？** 多 agent 是否用了不同 workdir？
- [ ] **HOME override？** 是否带了 `HOME=/Users/alexcai`？
- [ ] **Bypass permissions？** 标题栏是否 `⏵⏵ bypass permissions on`？
- [ ] **PTY 对话框？** 是否处理了 Dialog 2（Down + Enter）？
- [ ] **Progress：** 是否每 30-60s polling `capture-pane`？每次汇报是否严格使用规定的 `📡 CC Agent Team [Xmin]` 模板格式（含 worker 树 + emoji 状态 + token 统计）？
- [ ] **Agent team：** 是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] **Worker 监控：** 假死先 `ls` 查磁盘 → 文件存在则 `send-keys "Agent N done."`
- [ ] **轮间清理：** 每轮 agent team 后是否 `/clear`？完成后是否 `tmux kill-session`？
- [ ] **Session 干净度：** 启动 CC 前是否检查了 workdir 是否有 `.claude/` 残留？如果任务可能已由之前的 session 完成，是否先验证再决定是否重新执行？
