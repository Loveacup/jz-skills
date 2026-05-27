---
name: claude-code
description: |
  Orchestrate Claude Code CLI from Hermes. Two modes: print (`-p`) for one-shot tasks,
  interactive tmux sessions for multi-turn work. Use when delegating coding, PR review,
  refactoring, agent-team tasks, or any Claude Code invocation.
  
  Triggers: claude code, cc, delegate to claude, use claude, let claude handle, 用claude,
  让claude, agent team, claude review
  DO NOT use for: simple single-tool calls (use terminal directly), grammar fixes,
  non-coding creative writing (use appropriate creative skills)
version: 3.0.0
author: Hermes Agent + Teknium
license: MIT
---

# Claude Code — Hermes Orchestration

Delegate coding tasks to Claude Code CLI via print mode or interactive tmux sessions.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "我直接用 terminal 调 claude 就行" | 不加载 skill = 不知道 PTY 对话框处理、不知道 `--max-turns` 防止失控、不知道 background 超时会被杀 |
| "任务太简单，print mode 就行" | 简单任务也有坑：`--max-turns` 不设 = 可能无限循环烧钱；`--model` 不指定 = 开销不可控 |
| "我用 tmux 不需要这个 skill" | PTY 有两个对话框需要精确按键序列。权限对话框默认是"No, exit"——你必须 Down+Enter。错过 = Claude 直接退出 |
| "agent team 就是普通 Task subagent" | Claude Code 的 agent team 是独立机制。用户明确说过不要用普通 Task subagent 冒充 team |
| "我设置 budget=$0.05 够了" | 系统 prompt cache 创建本身就 ~$0.05。更低 → 立即报错。烟雾测试用 `$0.2` |

## 🔀 Decision Tree

```
任务类型？
├── 一次性：单文件修复、代码审查、数据提取、CI 任务
│   └── Print Mode (`claude -p`, no PTY)
│       ├── 短任务（<2min）→ foreground terminal
│       └── 长任务（>2min）→ background + notify_on_complete
│
├── 多轮迭代：重构→审查→修复→测试、探索性开发
│   └── Interactive tmux
│       ├── 长会话复用 → `hermes-claude-longterm`
│       └── 一次性 → 新建 session，用完杀
│
└── Agent Team：多文件、多步骤、架构判断、对比分析
    └── Print Mode + `--teammate-mode` 或 tmux team workflow
```

## ⚡ Core Rules (Hermes Agent 执行规则)

1. **默认 tmux 长会话** — 优先复用 `hermes-claude-longterm`。仅用户明确说"一次性/print mode"或单点读取时才用 `-p`。
2. **复杂任务必须 agent team** — 多文件/多步骤/根因分析/实现+测试/架构判断 → 让 CC 自己 spawn subagent。普通 Task subagent ≠ agent team。
3. **Always set `--max-turns` in print mode** — 不设 = 无上限。简单任务 5-10，复杂任务 15-25。
4. **Always set `workdir`** — 让 CC 聚焦正确项目目录。
5. **长 print 任务用 background** — foreground `terminal()` 600s 上限，超时会被杀且产出空 JSON。用 `background=true, notify_on_complete=true`。
6. **超时后先检查产物再重试** — CC 可能已写了部分文件但超时被截断。检查输出路径、文件列表、transcript，别重复劳动。
7. **不要杀慢会话** — CC 在做多步工作。用 `capture-pane` 检查进度，确认卡死（多轮无工具调用 + 无 prompt）才 `Ctrl+C`。
8. **清理一次性 tmux 会话** — 只保留长会话。用完就 `tmux kill-session`，避免泄漏。
9. **⚡ 始终使用 bypass permissions 模式** — tmux 启动后立即 `Shift+Tab` 切换到 `bypass permissions on`（标题栏显示 `⏵⏵ bypass permissions on`）。此模式下 CC 不会弹出权限确认对话框，避免阻塞。print mode 加 `--dangerously-skip-permissions`。
10. **📡 tmux 模式持续汇报进度** — 发送任务给 CC 后，每 30-60 秒 polling `capture-pane`，向用户汇报：当前正在做什么（最后一条工具调用/输出）、是否有错误、是否完成。不要沉默等待——用户需要知道 CC 在干活。

## 🚀 Prerequisites & Smoke Test

```bash
which claude && claude --version && claude auth status --text || true
```

连通性测试（只读，不改文件）：
```bash
claude -p 'Hermes 连通性测试。用中文简短回答：你是否已作为 Claude Code 启动；当前工作目录。不要修改任何文件。' \
  --output-format json --max-turns 1 --allowedTools 'Read,LS'
```

## 🖥️ Print Mode — One-Shot Tasks

```bash
claude -p 'Fix the auth bug in src/auth.py' \
  --allowedTools 'Read,Edit,Bash' --max-turns 10 \
  --output-format json
```

**何时用：** Bug 修复、代码审查、CI/CD、结构化提取、管道输入。

详见 `references/print-mode.md`（JSON 输出、流式、管道、Schema、Session 续接、Bare Mode、Fallback）。

## 🖥️ Interactive Mode — Multi-Turn via tmux

```bash
# 1. 启动或复用长会话
tmux new-session -d -s hermes-claude-longterm -x 140 -y 40
tmux send-keys -t hermes-claude-longterm 'cd /path/to/project && claude' Enter

# 2. ⚡ 切换到 bypass permissions 模式（必须）
sleep 3
tmux send-keys -t hermes-claude-longterm Shift-Tab
# 确认标题栏显示：⏵⏵ bypass permissions on

# 3. 发送任务
tmux send-keys -t hermes-claude-longterm 'Refactor auth to use JWT' Enter

# 4. 📡 持续监控进度（见下方 Progress Reporting）
```

### ⚡ Bypass Permissions（启动后必须执行）

CC 默认权限模式会弹出确认对话框，阻塞自动化流程。启动后必须立即切换到 bypass：

```bash
# 新建会话后
sleep 3  # 等 CC 初始化完成
tmux send-keys -t hermes-claude-longterm Shift-Tab

# 验证：标题栏应显示 ⏵⏵ bypass permissions on
tmux capture-pane -t hermes-claude-longterm -p | grep "bypass permissions on"
```

如果已有长会话，检查当前模式：
```bash
tmux capture-pane -t hermes-claude-longterm -p -S -5 | grep -o "bypass permissions \(on\|off\)"
```
如果是 `off`，发送 `Shift-Tab` 切换。

### 📡 Progress Reporting（持续汇报进度）

**tmux 模式下必须主动汇报，不要沉默等待。**

**汇报节奏：**
- 发送任务后 15 秒 → 首次检查
- 之后每 30-60 秒 → 轮询一次
- 看到关键信号 → 立即汇报（不等到下次轮询）

**检查方法：**
```bash
# 取最后 60 行，看 CC 在做什么
tmux capture-pane -t hermes-claude-longterm -p -S -60
```

**关键信号识别：**

| 信号 | 含义 | 动作 |
|------|------|------|
| `●` 前缀 + 工具名 | CC 正在调用工具 | 汇报："CC 正在 [工具名]：[简短描述]" |
| `❯` 前缀（最后一行） | CC 等待输入/完成 | 检查是否已完成任务。如果任务结束 → 汇报完成 |
| `Error` / `Traceback` | 出错 | 立即汇报错误内容 |
| `bypass permissions off` | 权限模式丢失 | 立即发 `Shift-Tab` 恢复 |
| 多轮无 `●` 也无 `❯` | 可能卡死 | 等待 2 分钟。仍无变化 → `Ctrl+C` 中断 |

**汇报模板：**
```
📡 CC 进度 [已运行 X 分钟]
  ● 正在：<最后一条工具调用>
  ✅ 已完成：<已完成的里程碑>
  ⚠️ <任何异常>
```

**结束信号：** 当 `capture-pane` 最后一行是 `❯` 且上方不再有 `●` 工具调用时，CC 已完成当前任务。汇报最终结果并询问用户是否继续。

> 💡 用户在 TG 收到进度汇报后可能回复新指令。收到用户消息后立即 `capture-pane` 检查 CC 是否空闲（`❯`），空闲则发送新指令。

### ⚠️ PTY 对话框处理（关键）

**Dialog 1：工作区信任（首次访问）**
```
❯ 1. Yes, I trust this folder    ← 默认正确
  2. No, exit
```
处理：发送 `Enter` 即可。

**Dialog 2：权限警告（`--dangerously-skip-permissions`）**
```
❯ 1. No, exit                    ← 默认是错的！！
  2. Yes, I accept
```
处理：必须先 `Down` 再 `Enter`：
```bash
sleep 3 && tmux send-keys -t <session> Down && sleep 0.3 && tmux send-keys -t <session> Enter
```

### 读取 TUI 状态
- `❯` = 等待输入（CC 完成或在问问题）
- `●` = 正在用工具
- `⏵⏵ bypass permissions on` = 权限模式

详见 `references/interactive-reference.md`（Slash Commands、快捷键、输入前缀）。

## 🔌 MCP Bridge: Claude Octopus

Hermes 通过 `claude_octopus` MCP 直接调用 CC，获得结构化 `run_id`/`session_id`/cost。配方见 `references/claude-octopus-hermes-mcp.md`。适用于只读探针、代码审查探测、实验性任务。保持 tmux 用于长会话协作。

## 👥 Non-Code Agent Team Reviews

Agent team ≠ 普通 Task subagent。用户要 team 时：
1. 写 context 到 `~/.hermes/tmp/` markdown 文件
2. 用 CC team/teammate 流程（`--teammate-mode` 或 tmux team workflow）
3. 让 team 用多个 lens（engineering/API、content/UX、compliance）
4. 保存为 Telegram 可读的 bullet Markdown（不要表格）
5. 报告用了哪种 team workflow + 输出路径

## 🔍 PR Review Pattern

```bash
# 快速审查（Print Mode）
git diff main...feature-branch | claude -p 'Review for bugs, security, style' --max-turns 1

# 深度审查（Interactive + Worktree）
claude -w pr-review --tmux  # 创建隔离 worktree + tmux
# 或从 PR 编号
claude -p 'Review this PR' --from-pr 42 --max-turns 10
```

## ⚠️ Critical Pitfalls (Top 5)

1. **Dialog 2 默认"No"** — 用 `--dangerously-skip-permissions` 时，对话框默认选中"No, exit"。必须 Down+Enter
2. **Budget 下限 ~$0.05** — prompt cache 创建本身就要这些。设更低 → 立即报错
3. **Foreground 超时 600s** — 长任务用 background，否则超时被截断
4. **`--bare` 需要 API key** — 跳过 OAuth，必须设 `ANTHROPIC_API_KEY`
5. **Context 退化** — 超出 70% 窗口后质量下降。用 `/context` 监控，`/compact` 主动压缩

完整 Pitfalls (16 条) 见 references → 已嵌入本文件 Core Rules 和 `references/print-mode.md`。

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

---

## ✅ Verification Checklist

- [ ] Bypass permissions：tmux 会话是否切换到 `bypass permissions on`？print mode 是否加了 `--dangerously-skip-permissions`？
- [ ] Print mode：是否设置了 `--max-turns` 和 `workdir`？
- [ ] Print mode：长任务是否用了 `background=true, notify_on_complete=true`？
- [ ] Interactive：是否处理了 PTY 对话框（Dialog 2 = Down+Enter）？
- [ ] Progress：tmux 模式下是否每 30-60 秒 polling `capture-pane` 并向用户汇报进度？
- [ ] Agent team：是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] 超时/错误后：是否先检查了产物再重试？
- [ ] 完成后：一次性 tmux session 是否清理了？
- [ ] 结果是否向用户报告了（做了什么、改了什么、是否用了 team）？
