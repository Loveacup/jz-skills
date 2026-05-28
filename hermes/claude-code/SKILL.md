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
version: 3.1.0
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
9. **⚡ 始终使用 bypass permissions 模式** — CC v2.1+ 默认已启用 bypass permissions（标题栏显示 `⏵⏵ bypass permissions on`），**绝大多数情况无需手动切换**。启动 CC 后先用 `capture-pane` 验证标题栏：如果显示 `bypass permissions off`，再尝试 `Shift-Tab` 切换。⚠️ 注意：`tmux send-keys -t <session> Shift-Tab` 在部分终端/macOS 组合下会被当作文本字面量输入「Shift-Tab」而非按键组合——如果验证发现 switch 失败但标题栏已经是 `on`，直接跳过这步。print mode 加 `--dangerously-skip-permissions`。
10. **📡 tmux 模式持续汇报进度** — 发送任务给 CC 后，每 30-60 秒 polling `capture-pane`，向用户汇报：当前正在做什么（最后一条工具调用/输出）、是否有错误、是否完成。不要沉默等待——用户需要知道 CC 在干活。

## 🚀 Prerequisites & Smoke Test

```bash
which claude && claude --version && claude auth status || true
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

### ⚡ Bypass Permissions（启动后验证，通常无需操作）

CC v2.1+ 默认已启用 bypass permissions（标题栏显示 `⏵⏵ bypass permissions on`），**绝大多数情况无需手动切换**。启动后只需验证：

```bash
# 验证：标题栏应显示 ⏵⏵ bypass permissions on
tmux capture-pane -t <session> -p -S -2 | grep "bypass permissions on"
```

如果显示 `off`，尝试 `Shift-Tab` 切换。⚠️ **`tmux send-keys Shift-Tab` 不可靠**——在部分终端/macOS 组合下会被当作文本字面量「Shift-Tab」输入。如果切换失败但 CC 后续没有弹出权限对话框，说明当前模式已足够，直接继续。

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

**症状**: `Waiting for N background agents` + worker token 数 >2min 不变。

**常见误操作（无效）**:
- ❌ 反复 `send-keys Enter` — CC 在等待状态，不处理输入
- ❌ 切换到 worker → 看不到 worker 的具体输出，只是背景 agent
- ❌ 杀 worker — 主 agent 会报错

**正确恢复流程**:
```bash
# 1. 检查产出文件是否已在磁盘上
ls -la <expected output path(s)>

# 2. 如果文件存在且 size > 0，直接告诉 CC 继续
tmux send-keys -t hermes-claude-longterm \
  'Agent X is actually done. All files exist on disk. Continue with [next step].' Enter

# 3. CC 会读取文件、验证质量，然后继续后续步骤
#    不要只发空 Enter — 必须明确告诉 CC "already done"
```

**已验证有效的恢复短语**（直接复制使用）:
- `Agent 3 is actually done. All 4 reference files exist on disk. Continue with the audit.`
- `Worker C is done — keyword-expansion-dict.md exists on disk at 7791 bytes. Continue with cross-check and SKILL.md update.`
- `Agent 3 is done, all files created. Continue.'
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

**内容研究简报（news/research briefing）**：当 delegate_task 被 kanban gate 拦截时，CC agent team 可作为 fallback。详见 `references/cc-agent-team-content-research.md`。关键教训：context 文件必须含 worker timeout 规则 + 明确的 extractor prompt；CC workers 擅长搜源和元数据，但 verbatim quote 深度提取需 parent 补充。

## 🔍 PR Review Pattern

```bash
# 快速审查（Print Mode）
git diff main...feature-branch | claude -p 'Review for bugs, security, style' --max-turns 1

# 深度审查（Interactive + Worktree）
claude -w pr-review --tmux  # 创建隔离 worktree + tmux
# 或从 PR 编号
claude -p 'Review this PR' --from-pr 42 --max-turns 10
```

## ⚠️ Critical Pitfalls (Top 7)

1. **Dialog 2 默认"No"** — 用 `--dangerously-skip-permissions` 时，对话框默认选中"No, exit"。必须 Down+Enter
2. **Budget 下限 ~$0.05** — prompt cache 创建本身就要这些。设更低 → 立即报错
3. **Foreground 超时 600s** — 长任务用 background，否则超时被截断
4. **`--bare` 需要 API key** — 跳过 OAuth，必须设 `ANTHROPIC_API_KEY`
5. **Context 退化** — 超出 70% 窗口后质量下降。用 `/context` 监控，`/compact` 主动压缩

6. **macOS TCC 沙盒** — CC 可能无法读写 `~/Documents/`、`~/Desktop/`、`~/Downloads/`（取决于是否已授权终端「文件与文件夹」权限）。如果报 `EPERM`：先 `cp` 到 `/tmp/` 再让 CC 处理，完成后 `cp` 回去。一次授权永久解决：系统设置 → 隐私与安全性 → 文件与文件夹 → 给终端开启「文档文件夹」权限。**本机环境已授权，通常可直接写，但 `/tmp/` 作为安全 fallback 仍然有效**。

7. **HOME override 导致 CC 找不到认证/配置** — Hermes profile 将 `HOME` 重定向到 `~/.hermes/profiles/<name>/home/`。当 CC 从 Hermes 环境启动时（无论是 `terminal()`、`delegate_task`、还是 A2A 任务），继承此 HOME。CC 在以下位置查找 OAuth token 和配置：
   - `~/.claude.json`（OAuth 认证凭据）
   - `~/.claude/`（settings, history, credentials）
   - npm 全局 node_modules（`~/.npm/`）
   
   如果这些文件不在 profile 的 HOME 下，`claude auth status` 返回 `Not logged in`，即使真实 HOME 下已认证。
   
   **临时修复**：启动 CC 时显式 override HOME：
   ```bash
   HOME=/Users/alexcai claude -p '...' --dangerously-skip-permissions
   ```
   
   **永久修复（推荐）**：符号链接 auth 文件到 profile home：
   ```bash
   PROFILE_HOME=~/.hermes/profiles/regent/home
   ln -sf /Users/alexcai/.claude.json $PROFILE_HOME/.claude.json
   ln -sf /Users/alexcai/.claude $PROFILE_HOME/.claude
   ```
   
   **验证**：`HOME=$PROFILE_HOME claude auth status --text` 应返回已登录。
   
   此问题与 `hermes-a2a` 的 `launchctl` HOME 陷阱同根——所有从 Hermes 环境 init 的子进程都受影响。详见 `references/home-and-sandbox.md`。

18. **沙箱 + HOME 组合陷阱（TCC + profile HOME）** — 当 CC 同时遇到 TCC 沙箱和 HOME override：`~/Documents/` 在 macOS 沙箱中受保护，而 profile HOME 下没有 TCC 授权记录。即使执行 `HOME=/Users/alexcai claude`，CC 的子进程仍可能使用 profile HOME 导致路径混乱。**最可靠方案**：将 CC 需要操作的文件先 `cp` 到 `/tmp/`，任务完成后 `cp` 回目标位置。
7. **复用 tmux 长会话时 scrollback 污染** — `capture-pane -S -N` 会显示历史 scrollback 中所有旧任务输出，导致误判 CC 状态。进入复用会话后：先确认 CC 空闲（最后一行 `❯`），发送无害指令如 `pwd` 确认响应正常，再派任务
8. **背景 agent 假死（文件已写完，UI 仍显示 running）** — agent team 模式下，worker 可能已完成文件写入但 CC 主线程未收到完成通知，UI 持续显示 `◯ agent-N … running` 且 tokens 数不再增长。诊断：`ls -la` 检查目标文件是否存在且大小 > 0。确认文件已在磁盘 → 不要反复 `send-keys Enter`（CC 在等后台事件，**不处理输入**），直接向 CC 发送消息告知文件已完成，如：`tmux send-keys 'Agent 3 is actually done. All files exist on disk. Continue.' Enter`。CC 收到后会读取文件并通过交叉链接检查验证质量，然后继续下一步。**不要杀 worker — 会破坏 agent team 状态。** 详细恢复协议见 Progress Reporting 中「Worker 假死恢复协议」。
9. **Fact-Forcing Gate 不是卡死** — CC 编辑文件前会触发安全门，要求陈述 (1) 用户指令原文 (2) 文件引用者 (3) 受影响函数/类 (4) 数据结构。然后自动重试编辑。每次停顿 5-10s，属正常流程。**不要**在 Gate 阶段误判 CC 卡死并杀会话——看 `capture-pane` 是否有 `[Fact-Forcing Gate]` 字样
10. **send-keys 长命令可能未执行** — 超长 `send-keys` 文本 + `Enter` 有时 CC 不处理。若 15s 后 `capture-pane` 仍无新 `●`，补发一个空 `Enter`（`tmux send-keys -t <session> Enter`）
11. **Worker 真正假死（无磁盘产出）** — 当 worker token 数 >2min 不变 AND `ls -la` 发现目标文件不存在或大小为 0，这是真正的 stall（不是 UI 延迟）。此时 send-keys 发消息给 CC 无效——CC 主线程在 `Waiting for N background agents` 状态下**不处理用户输入**。唯一有效恢复：`tmux kill-session` 杀掉整个 CC 会话，重新评估已完成产出的质量，手动接管剩余工作。**教训：agent team 任务启动前，在 context 文件中写入「timeout 10min per worker，超时视为失败，Leader 直接进入汇编」以避免无限等待。**
10. **send-keys 长命令可能未执行** — 超长 `send-keys` 文本 + `Enter` 有时 CC 不处理。若 15s 后 `capture-pane` 仍无新 `●`，补发一个空 `Enter`（`tmux send-keys -t <session> Enter`）
11. **TMUX Shift-Tab 被当成文本发送** — `tmux send-keys Shift-Tab` 在大部分终端中不会发送键盘快捷键，而是把 "Shift-Tab" 作为字面文本输入到 CC 提示符中。绕过权限对话框的正确方法是：在启动 CC 后直接 `send-keys Enter` 确认默认选项（Dialog 1 "Yes, trust"），然后用 `send-keys Down` + `send-keys Enter` 处理 Dialog 2（"Yes, accept"）。在 macOS Terminal.app 中 Shift-Tab 本身就是窗口切换快捷键，永远不会到达 tmux。
12. **CC 提示符处输入文本不执行** — 当 `capture-pane` 显示 `❯ 你的指令文本` 但没有下方响应时，CC 可能没收到 Enter。先等 15 秒确认不是 LLM 在思考，再补发一个 `tmux send-keys -t <session> Enter`。
13. **Print mode 对长文档渲染不稳定** — 超过 ~15KB 的 markdown 转 PDF 任务，CC print mode 可能静默运行 >8 分钟而无输出。此时改用本地 Python + Playwright 直接渲染（见 `references/python-playwright-pdf-fallback.md`）。
14. **多轮 agent team 间 context 膨胀** — Round 1 的 70k+ tokens 输出（文件内容、diff、验证日志）填满 context window 后，Round 2 的新任务发送到 CC 会触发极慢的 `Spinning… (2m+)` 状态。**在每轮 agent team 完成后、发送下一轮任务前，必须 `/clear`**。清空后 CC 重新初始化，响应速度恢复。不要在新任务上跟旧 context 较劲——`/clear` 比等 3 分钟快得多。已验证有效：本会话 Round 1 (70k tokens, 17min) → `/clear` → Round 2 (43k tokens, 24min)，两轮均无延迟。

15. **CC agent team 不知道持久化 schema** — 当 workers 产出的代码向数据库/SQLite/文件存储写入新字段时，它们不知道 schema 只持久化已知列。2026-05-28 案例：Worker C 在 `audit_hook.py` 中正确实现了 `score_task()` → `task["audit_score"] = {...}`，但 `storage.py:_store.save()` 只存 `status/artifact/error/...` 等预定义列。新字段 `audit_score` 被静默丢弃——pytest 通过、server 无报错、curl GET 返回 artifact 里没有 audit_score。**教训**：agent team 产出的代码中，任何新增的持久化字段必须在 Leader wiring 阶段验证是否真正写入存储。验证方法：写 Python subprocess curl 脚本，POST → sleep → GET，检查 artifact 中是否含预期字段（见 `references/post-deploy-verification-pattern.md`）。修复方案：将新字段写入 `artifact` dict 内（artifact 列以 JSON 整存），而非 task 顶层新列。

16. **Hermes token 脱敏破坏代码语法** — 代码或 shell 命令中含 token 时（`f"Bearer ***` 或 `TOKEN=***`），Hermes 脱敏替换 `***` 时可能删除相邻字符（`}`、`"`），导致 Python SyntaxError / bash glob 错误。2026-05-28 会话 4+ 次复现。
   - ✅ 用字符串拼接代替 f-string：`'Bearer ' + token` 而非 `f'Bearer ***`
   - ✅ 在脚本内通过 `subprocess` 读 token 文件，避免传入命令行
   - ✅ Shell 中避免直接引用 token；含 token 操作写入 Python 脚本后 `python3 script.py`
   - 写入文件后用 `read_file` 验证实际内容；terminal syntax error 时先怀疑脱敏破坏。

17. **Background shell stall（后台 shell 卡死，token 数长时间不变）** — CC 显示 `Skedaddling…`/`Puzzling…`/`Cultivating…` 等思考状态，token 数 >3min 不变，且 `capture-pane` 下方显示 `· 1 shell` 或 `(ctrl+b ctrl+b to run in background)` 有后台进程。此时 CC 主线程可能在等后台 shell 返回但 shell 已挂起。**诊断**：连续两轮 polling（~90s）token 数无变化 + 有活动后台 shell → 判定为 stall。**恢复**：先 `tmux send-keys` 发送一条简短 redirect 指令（如 `'Skip the search. Just directly edit <file>: <action>. Then run tests.' Enter`）。若 30s 后仍无响应 → 父 agent 直接手动执行任务，不要无限等待。CC 产出的文件通常在磁盘已存在，父 agent 可继续操作。此模式 2026-05-28 复现：dispatcher 修复任务中 CC 卡在 `cat` 后台 shell 5 分钟，手动接管 2 分钟完成。

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

---

## ✅ Verification Checklist

- [ ] Bypass permissions：标题栏是否显示 `⏵⏵ bypass permissions on`？print mode 是否加了 `--dangerously-skip-permissions`？⚠️ 不要盲目发 `Shift-Tab`——先 verify，off 才切。
- [ ] Print mode：是否设置了 `--max-turns` 和 `workdir`？
- [ ] Print mode：长任务是否用了 `background=true, notify_on_complete=true`？
- [ ] Interactive：是否处理了 PTY 对话框（Dialog 2 = Down+Enter）？
- [ ] Progress：tmux 模式下是否每 30-60 秒 polling `capture-pane` 并向用户汇报进度？
- [ ] Agent team：是否用了 CC 原生 team 机制而非普通 Task subagent？
- [ ] 超时/错误后：是否先检查了产物再重试？
- [ ] 完成后：一次性 tmux session 是否清理了？
- [ ] 结果是否向用户报告了（做了什么、改了什么、是否用了 team）？
