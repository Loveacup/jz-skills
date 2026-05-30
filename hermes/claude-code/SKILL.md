---
name: claude-code
description: |
  Orchestrate Claude Code CLI from Hermes — tmux interactive + agent team (stability-first).
  Print mode is secondary and only used for connectivity smoke tests.
  
  Triggers: claude code, cc, delegate to claude, use claude, let claude handle, 用claude,
  让claude, agent team, claude review
  DO NOT use for: simple single-tool calls (Hermes does those directly), grammar fixes,
  non-coding creative writing (use appropriate creative skills)
version: 3.2.0
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
2. **复杂任务必须 agent team** — 多文件/多步骤/根因分析/实现+测试/架构判断 → 让 CC 自己 spawn subagent。
3. **Always set `workdir`** — 让 CC 聚焦正确项目目录。
4. **Always 带 `HOME=/Users/alexcai`** — 避免 Hermes profile HOME override 导致认证失败。
5. **不要杀慢会话** — 用 `capture-pane` 检查进度，确认卡死才 `Ctrl+C`。
6. **清理一次性 tmux 会话** — 用完就 `tmux kill-session`，避免泄漏。
7. **每轮 agent team 后 `/clear`** — 避免 context 膨胀。
8. **⚡ bypass permissions** — 启动后验证，通常默认已启用。
9. **📡 无条件持续汇报进度** — 每 30-60s polling，沉默 >2min 不可接受。
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

**汇报模板：**
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

Agent team ≠ 普通 Task subagent。用户要 team 时：
1. 写 context 到 `~/.hermes/tmp/` markdown 文件
2. 用 CC team/teammate 流程（`--teammate-mode` 或 tmux team workflow）
3. 让 team 用多个 lens（engineering/API、content/UX、compliance）
4. 保存为 Telegram 可读的 bullet Markdown（不要表格）
5. 报告用了哪种 team workflow + 输出路径

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
| `references/worker-stall-detection.md` | Worker 假死检测：token stalls → ls → tell cc · 本会话复现 3 次 |
| `references/worker-true-stall-no-disk-output.md` | Worker 真死（无磁盘产出）：send-keys 无效 → 杀会话 → 手动接管 |
| `references/cc-agent-team-content-research.md` | CC agent team 做内容研究简报：delegate_task blocked 时的 fallback 工作流、verbatim quote 局限性、worker stall 预防 |
| `references/cc-agent-team-parallel-implementation.md` | 并行实施模式：Leader-wiring 策略避免共享文件冲突 + context 文件模板 + schema 验证 |
| `references/post-deploy-verification-pattern.md` | 部署后验证：Python subprocess curl 模式、token 脱敏陷阱、持久化字段验证 |
| `references/cc-session-isolation.md` | CC 多 Agent session 隔离完整调查：`--session-id` 验证、`--fork-session`、交互模式陷阱 → Obsidian `00-Inbox/CC tmux 多Agent 会话隔离问题.md` |
| `Obsidian: CC tmux Agent Team 稳定性优化方案` | 稳定性全流程：session 生命周期、worker 诊断树、进度监控、异常恢复速查表 |
| `references/progress-reporting-enhanced.md` | 🆕 增强进度模板：emoji 状态映射、worker 树、token 跟踪、4 场景模板 |
| `references/CHANGELOG.md` | 🆕 版本历史：v3.1.0→v3.3.0 完整变更记录 |

---

## ✅ Verification Checklist（稳定性优先）

- [ ] **🛑 占用检测？** 调 CC 前是否扫描了所有 tmux session 的 `●`？有 BUSY 是否汇报了用户？
- [ ] **Session 隔离？** 是否避免了 `--continue`？session 名用 `hermes-cc-{profile}-{ts}`？
- [ ] **Workdir 隔离？** 多 agent 是否用了不同 workdir？
- [ ] **HOME override？** 是否带了 `HOME=/Users/alexcai`？
- [ ] **Bypass permissions？** 标题栏是否 `⏵⏵ bypass permissions on`？
- [ ] **PTY 对话框？** 是否处理了 Dialog 2（Down + Enter）？
- [ ] **Progress：** 是否每 30-60s polling `capture-pane` 并汇报 `📡` 进度？
- [ ] **Agent team：** 是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] **Worker 监控：** 假死先 `ls` 查磁盘 → 文件存在则 `send-keys "Agent N done."`
- [ ] **轮间清理：** 每轮 agent team 后是否 `/clear`？完成后是否 `tmux kill-session`？
