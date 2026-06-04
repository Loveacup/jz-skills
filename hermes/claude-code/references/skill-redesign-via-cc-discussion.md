# Skill 架构重设计 — 通过 CC 讨论协议

> 使用 CC agent team discussion protocol 做 skill 架构重设计的完整模式。
> 2026-06-02 首次实践：morning-news-briefing v3.0 → v4.0 重构讨论。

## 使用场景

- Skill 需要整体架构重构（模块拆分、编排方式变更、依赖关系重新设计）
- 问题涉及多个层面（可靠性、模块化、编排选型、功能取舍）
- 需要多轮深度讨论才能确定方案，不适合直接执行

## 四步模式

### Step 1: 准备 Context 文件

写一个 5-8KB 的 markdown 文件（`/tmp/cc-<task>-redesign.md`），结构：

```markdown
# <Skill名称> 重构 — Context for CC Agent Team

## Task
一句话描述重设计目标。

## Current State
- 当前架构（文件结构、关键决策树、数据流）
- 直接列出文件路径供 CC 自行读取

## What's Broken
- 按严重度分级：🔴 可靠性（系统在骗人）、🟡 架构/模块化、🟢 编排选型
- 每个问题附具体现象和证据（字节数、幻觉数字、日志片段）

## Design Goals
- 明确硬约束（"Alex 偏精简"、"必须通用化"）
- 要保住的资产（格式规则、模板、门禁检查）

## 技术选项（供 CC 评估）
- 列出候选技术/架构选项，让 CC 自己做 tradeoff 分析
- 附上参考文档路径（Obsidian 笔记、GitHub 项目、CQI 计划）

## Key Discussion Questions
- 3-5 个开放式问题，每问对应一个架构决策维度
- 不要预判答案——让 CC 给出它的独立判断

## Constraints & Assets
- 用户偏好、环境约束
- 现有模板/规则/门禁清单
```

### Step 2: 启动 CC 讨论模式

```bash
# 新建独立 session
tmux new-session -d -s hermes-cc-{task}-{ts}
# 启动 CC（架构重设计 = max effort）
tmux send-keys "HOME=/Users/alexcai claude --model claude-opus-4-8 --effort max" Enter
# Sleep 15s 等初始化 → 发送文件读取指令
tmux send-keys "Read /tmp/cc-{task}-redesign.md。读完告诉我你理解的任务，然后进入讨论——先别动手执行。" Enter
```

**关键**：用单句 "Read file + 讨论指令" 而非多行 send-keys（避免排队污染，见 Pitfall #33）。

### Step 3: 多轮讨论

CC 读完后通常会：
1. **复述理解** — 用表格/层级总结任务
2. **识别张力** — 发现需求中的内在矛盾（"通用化 vs 编排耦合"、"过度工程 vs 特性清单"）
3. **提出未验证假设** — "这个方案吊在 X 假设上，需要实测才能拍死"

Hermes 的回应原则：
- 直接回应 CC 提出的张力，附自己的判断和理由
- 确认/纠正环境假设（"Kanban v0.15 在本机能跑"）
- 引导下一步：让 CC 去读关键文件验证假设，或继续讨论未决维度
- **不提前结束讨论**：方案没清晰前不写代码

### Step 4: 收口为 Plan

讨论产出应包括：
- 模块拆分方案（哪些子 skill、各自的职责边界）
- 编排方式选择（delegate_task / Kanban Swarm / cron）及 tradeoff 理由
- 搜索/抓取链的修复方案（含 fallback 层级）
- 功能取舍清单（吸收什么、砍掉什么）
- 待验证假设列表（需实测才能确定的点）

## CC 的四层紧急性分析框架

在本次实践中，CC 自发使用了四层分类来组织问题，这套框架值得复用：

| 层 | 含义 | 性质 | 指导原则 |
|:---|:---|:---|:---|
| 🔴 可靠性 | 系统在骗人（编造引用、输出幻觉数字） | bug，不是重构 | 先修，不等到架构重设计 |
| 🟡 架构 | 耦合到特定 profile/skill，不可移植 | 重构 | 模块拆分应服务于修复后的数据流 |
| 🟡 模块化 | 巨石 skill，功能未解耦 | 重构 | 能力（搜索/渲染/审计）与编排（谁先谁后）分开 |
| 🟢 编排 | 选 delegate_task 还是 Kanban Swarm | 选型 | 最不重要——换了编排层不应影响子能力 |

**核心原则**：模块拆法应该服务于 fetch 链，而非反过来。先确定数据怎么进来、怎么验证、怎么引用，再谈怎么拆模块。

## WRR 抓取链修复 — 可复用模式

本次发现的通用技术：**把 web 内容抓取收口到 WRR 的第三方 API 引擎，绕过 web_extract 的 SSRF 守卫**。

```
❌ 之前: web_search → web_extract(裸抓取→撞SSRF守卫) → 抓取失败但silent → 编造引用
✅ 之后: web_search → WRR路由 → Exa Fetch / Tavily Extract(第三方API抓取) → 干净正文
                                             ↓ 失败时
                                        fail-loud: 标记"未读"→禁止引用→审计门禁拦截
```

**适用条件**：本地 MCP 已配置 Exa/Tavily/Brave/SearXNG 四个引擎。

**关键原则**：
- web_extract 可以直接退役——不修它，删了它
- browser/CDP 仅作为 fallback（Tavily 抓不动的中文源才用）
- 抓取失败必须 fail-loud：标记"未读"→禁止任何数字/引用挂在未读源上→审计门禁强制拦截

## Swarm vs delegate_task 决策框架

对 cron 触发的数据采集型任务：

| 维度 | Swarm | delegate_task | 本案例选择 |
|:---|:---|:---|:---|
| worktree 隔离 | 负收益（采集无文件冲突） | 不需要 | delegate_task ✅ |
| per-task model | ✅ 但 delegate_task 也能做到 | ✅ | 平手 |
| 一条命令拉起 | 便利 | 需显式编排 | Swarm 有优势但不足以翻盘 |
| fail-loud 控制 | 依赖 Kanban 实现，不确定 | 显式写在 skill 里 | delegate_task ✅ |
| cron 日更适配 | 过度复杂 | 同构于已验证的 cron+校验模式 | delegate_task ✅ |

**结论**：采集型 cron 任务用 delegate_task，不上 Swarm。但子能力（搜索/分析/渲染/审计）做成可复用 skill，编排层做薄——将来换 Swarm 只换编排层。
