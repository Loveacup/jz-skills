# Decision Trees — 稳定性优先（仅 tmux + agent team）

> 从 `SKILL.md ## 🔀 Decision Tree` 下沉（v4.1.2 slim）。SKILL.md 保留口诀 + 本文件指针。

## 主决策树：调不调 CC / 用什么形态

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

## 🚦 单 CC vs Agent Team vs 并行多 CC

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
| **CC Agent Team（默认）** | 多文件 / 多步骤 / 根因分析 / 实现+测试 / 架构判断 / 多 lens 审查。一个 CC 内 spawn 多 worker，**共享一份上下文**，CC leader 协调。 | context 文件必须含 worker timeout 规则（`timeout 10min per worker`）；按关注点拆分（见下）；数量由 CC 自定。 |
| **并行多 CC（特例）** | 真正相互独立、无共享上下文的任务流（如同时跑两个不相干项目）。 | 各自独立 session 名 + **独立 workdir**；**禁 `--continue`**（同一 workdir 下 CC 会自动 resume，导致串台）；每个 session 独立跑占用检测与 Post-Send 汇报。 |

> 选型口诀：**Hermes 能干 → 不调 CC；要拆领域 → Agent Team；任务互不相干 → 并行多 CC。** 拿不准时默认 Agent Team。

## 🧩 Agent 数量与拆分原则

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
