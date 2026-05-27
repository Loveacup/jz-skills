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

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "我直接用 terminal 调 claude 就行" | 不加载 skill = 不知道 PTY 对话框处理、不知道 `--max-turns` 防止失控、不知道 background 超时会被杀 |
| "任务太简单，print mode 就行" | 简单任务也有坑：`--max-turns` 不设 = 可能无限循环烧钱；`--model` 不指定 = 开销不可控 |
| "我用 tmux 不需要这个 skill" | PTY 有两个对话框需要精确按键序列。权限对话框默认是"No, exit"——你必须 Down+Enter。错过 = Claude 直接退出 |
| "agent team 就是普通 Task subagent" | Claude Code 的 agent team 是独立机制。用户明确说过不要用普通 Task subagent 冒充 team |
| "用 MCP bridge 调 CC 更方便，不用管 tmux" | MCP 对长任务超时不稳定（实测已验证）。安全/架构/运维并行审查、Obsidian 大规模重写等——必须走 tmux，MCP 仅用于只读探针 |
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
9. **始终设 budget 上限** — 无上限 = 失控烧钱。烟雾测试 `$0.2`，简单任务 `$0.5`，复杂任务 `$2-5`。低于 `$0.05` 会因 prompt cache 创建开销立即报错。

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
# 启动或复用
tmux new-session -d -s hermes-claude-longterm -x 140 -y 40
tmux send-keys -t hermes-claude-longterm 'cd /path/to/project && claude' Enter

# 发送任务
tmux send-keys -t hermes-claude-longterm 'Refactor auth to use JWT' Enter

# 监控
sleep 15 && tmux capture-pane -t hermes-claude-longterm -p -S -50
```

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

Agent team ≠ 普通 Task subagent。用于审查 skills、工作流、配置、设计文档等非代码制品。

### 快速模式：Skill/Workflow Audit（已验证）

送审文件 + 3 路并行 agent（安全/架构/运维视角）→ P0/P1/P2 分级报告。
完整配方见 `references/agent-team-skill-review.md`。

要点：
1. 把目标文件全文内联到 prompt（或确保 CC 可读路径）
2. 明确要求 3 个 agent，各自独立审查，每人一个 lens
3. 要求合并报告落盘到 `/tmp/cc-agent-team-review.md`
4. 要求 bullet markdown（Telegram 兼容），不要 pipe table
5. 读报告 → 逐条 patch → skill_view 验证 → 删临时文件

### 通用模式

用户要 team 时：
1. 写 context 到 `~/.hermes/tmp/` markdown 文件
2. 用 CC team/teammate 流程（`--teammate-mode` 或 tmux team workflow）
3. 让 team 用多个 lens（engineering/API、content/UX、compliance、security、ops）
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

## ⚠️ Critical Pitfalls

| Pitfall | Why it burns you | Recovery |
|---------|-----------------|----------|
| **Dialog 2 默认"No"** | `--dangerously-skip-permissions` 时默认选中退出。错过 = CC 直接退出 | Down+Enter，不等 |
| **Budget 低于 $0.05** | prompt cache 创建就 ~$0.05。设更低 → 立即报错 | 烟雾测试 $0.2 起步 |
| **Foreground 超时 600s** | 长 print 任务超时被杀，产出空 JSON | 用 `background=true, notify_on_complete=true` |
| **`--bare` 需要 API key** | 跳过 OAuth 但没有 `ANTHROPIC_API_KEY` → 立即失败 | 确认 env 设置后再跑 |
| **Context 超 70% 退化** | 窗口用满后 CC 开始重复/遗忘指令 | `/context` 监控，`/compact` 主动压缩 |
| **CC tmux 会话崩溃** | send-keys 后无响应，capture-pane 空白 | 先 `capture-pane` 检查 TUI 状态（`❯`/`●`/空）。确认崩溃→ `tmux kill-session`→重建→重新 send-keys。不要盲目重发 |
| **MCP bridge 长任务超时** | 并行 agent team 审查超 2min → MCP timeout，无产出 | 长任务必须走 tmux，MCP 仅用于 <30s 只读探针 |

完整 Pitfalls (19 条) 见 `references/print-mode.md`。

## 📦 References

| 文件 | 何时读取 |
|------|---------|
| `references/cli-reference.md` | 需要完整 CLI flags（7 张表） |
| `references/print-mode.md` | Print 模式深度：JSON/流式/管道/Schema/Session/Bare |
| `references/interactive-reference.md` | Slash Commands + 键盘快捷键 |
| `references/configuration.md` | Settings/CLAUDE.md/Subagents/Hooks/MCP/环境变量/同步 |
| `references/claude-octopus-hermes-mcp.md` | MCP 桥接配方 |
| `references/agent-team-skill-review.md` | Non-code agent team audit recipe (P0/P1/P2, 3-lens, validated) |
| `references/obsidian-agent-team-rewrite.md` | Obsidian 大规模重写模式 |
| `references/alex-longterm-agent-team-preference.md` | 用户偏好：默认 tmux 长会话 > print mode |

---

## ✅ Verification Checklist

- [ ] Print mode：是否设置了 `--max-turns` 和 `workdir`？
- [ ] Print mode：长任务是否用了 `background=true, notify_on_complete=true`？
- [ ] Interactive：是否处理了 PTY 对话框（Dialog 2 = Down+Enter）？
- [ ] Agent team：是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] 超时/错误后：是否先检查了产物再重试？
- [ ] 完成后：一次性 tmux session 是否清理了？
- [ ] 结果是否向用户报告了（做了什么、改了什么、是否用了 team）？

---

## Deployment & Sync

This skill is synced to `jz-skills` via the standard bidirectional flow. After ANY update:

```bash
# 1. Sync back from local to repo
cd ~/code/jz-skills && ./deploy/sync-back.sh

# 2. Sanitize — never blind commit (catches secrets, emails, IPs, home paths)
grep -rE '(/Users/[a-z]|gho_|sk-[0-9a-zA-Z]|192\.168|@[a-zA-Z0-9.-]+\.(com|cn))' hermes/autonomous-ai-agents/claude-code/ \
  && echo "⚠️  SENSITIVE DATA FOUND — sanitize before commit" && exit 1 || true

# 3. Stage skill directory only, then push
git add hermes/autonomous-ai-agents/claude-code/ \
  && git commit -m "sync: claude-code" \
  && git push
```
