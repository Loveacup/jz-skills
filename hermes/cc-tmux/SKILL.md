---
name: cc-tmux
description: >
  Drive Claude Code via tmux with script-enforced safeguards.
  Thin skill — scripts do the enforcement, prose only tells you which script to call.
  Parallel version to claude-code skill for testing the simplified architecture.
  
  Use when: 调 CC, 用 claude, 拉 CC, delegate to CC, agent team, 重活调 CC.
  Do NOT use for: simple single-tool calls, grammar fixes, non-coding tasks.
type: routine
version: 1.3.1
author: "Hermes Agent + Claude Code (v1.3.1: +post-send liveness check +monitor state-blind-spot pitfalls +test-repro ref; P0/P1 hardened; CC self-audited)"
license: MIT
---

# CC via tmux — Script-Enforced Orchestration

> **设计原则**：脚本做 gate，LLM 做决策。"能不能做"由代码判，"怎么做"由 LLM 判。
> **与 claude-code skill 的关系**：并行版本，不覆盖。v4 是 full prose，v5 (cc-tmux) 是 thin prose + fat scripts。
> **核心赌注**：把义务数从 80+ 砍到 ~10 per turn（curse of instructions），让合规=最省事。

## 🚨 Red Flags: DO NOT SKIP THE SCRIPTS

| Excuse your brain will make | Why it's wrong |
|---|---|
| "我先手动 tmux 起一个 CC 看看" | 绕过 `cc-start.sh` = 绕过占用锁 = 并发冲突破坏。只用脚本。 |
| "等 CC 跑完我再看结果" | 📡 汇报是红线。每 30-60s 用 `cc-monitor.sh` 抓屏并汇报。 |
| "任务很简单，不用走完整流程" | 简单 ≠ 可以跳过占用检测。5 秒的脚本值得跑。 |
| "我把 📡 输出总结一下/换个格式" | `cc-monitor.sh` 输出已是 copy-paste-ready。**原样转发**，不要总结、合并、改格式。 |

## 🔀 Decision Tree

```
需要调 CC？
├── Hermes 自己能干？ → 不调 CC
├── 需要拆领域讨论？ → agent team（默认）
├── 任务互不相干？ → 并行多 CC（特例，独立 workdir）
└── 拿不准 → agent team

调哪个 effort？
├── 没信号 → high（地板）
├── 多文件 / 审查 / 设计 → xhigh
└── 深度架构 / 根因调试 / 写 skill → max
```

## 🚦 执行前 Gate Stamp（开 CC 前必须逐项核对）

```
🚦 执行前 Gate Stamp
  该调 CC ✓  重活（多文件/架构/skill/部署）？简单任务 Hermes 自己干。
  effort ✓  已按任务信号选档？（地板 high）
  session ✓  独立名 hermes-cc-{agent}-{ts}？禁 --continue？
  占用锁 ✓  cc-start.sh 自动检测，BUSY 时汇报用户等确认。
  session扫描 ✓  cc-start.sh 自动扫全量 tmux，其他活跃 CC → exit 3，用户确认后 --ack-active。
  方案审定 ✓  用户已说"执行吧 / 做吧"？（红线②）
  ── 六项全 ✓ → 开 CC；任一 ✗ → 停，汇报后继续
```

## 🔴 两条红线（违反 = 停 + 补做）

1. **📡 汇报**：每次 `cc-monitor.sh` 输出必须**原样转发**给用户。沉默 >2min = 违规（`cc-finish.sh` 拒绝收尾）。
2. **讨论协议**：用户说"看方案 / 优化方案"= 讨论，不是执行。只有"执行吧 / 拉 CC 改"才动手。

## 📡 Relay Contract（机械执行 — 不是建议）

`cc-monitor.sh` 的 stdout 被 `===📡 BEGIN (relay verbatim)===` 和 `===📡 END===` 包裹。**这两个标记之间的内容 = 用户直接可用的 📡 块。**

**铁律**：
- **原样转发** stdout 到用户可见的 📡 块。不总结、不合并、不改格式。
- 机器元数据去 stderr（`META` 行），不在 relay 范围内。
- `cc-finish.sh` 会审计心跳新鲜度。>120s 监控间隙 → reject 收尾（除非 `--force`）。
- 每次 `cc-monitor.sh` 跑完 = 一次心跳写入 `/tmp/cc-heartbeat-<session>`。这不只是"建议"——`cc-finish.sh` 真会堵你。

## 🔥 讨论协议（任务不明确或涉及架构决策时触发）

**默认进入讨论，不是执行**（v4 Pitfall #23 真实教训）。方案审定后才动手。

### 双向拷问规则
1. **开场即讨论**，除非需求明确到不需要讨论。
2. **逐问**：一次一个问题，答案影响后续方向。
3. **带推荐答案**：附"我倾向 X，理由 Y"，对方有锚点可确认/反驳。
4. **陈述带 artifact**：关于"现状"的声明必须有可验证证据（文件路径、命令输出）。
5. **终止条件**：双方达成显式一致 → 执行；≤3 轮仍有分歧 → 标记未决 + 带条件推进。
6. **提问用纯文本**，不要 AskUserQuestion 表单（tmux 下导航不可靠）。

### 讨论简报模板（每轮拷问后发给用户）

```
📋 讨论简报 R{n}
  · 讨论了什么
  · 决定了什么
  · 分歧 / 未决
  · 下一步（执行前等审定）
```

### 连续推进模式
用户说"继续 / 直接动手 / 不用问"时→ 子任务完成后直接推进下一步，只在真决策点停止。批量流水线步（写第 N→第 N+1 个文件）不算决策点。用户随时可打断。

## 🖥️ 四步操作流程

### 1. 启动 — `scripts/cc-start.sh`

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-start.sh \
  --target "jz-skills" \
  --effort high \
  --task "简述任务"
```

脚本自动完成（v1.3）：
- **全量 tmux session 扫描** — 检测所有 hermes-cc-* session 的 6 种状态（SHELL/WAITING_AGENTS/IDLE/TOOL/THINKING/STARTING）。有其他活跃 CC → exit 3，输出扫描报告让用户确认，确认后重跑加 `--ack-active`。
- **僵尸锁清理** — 锁目录在但记录的 session 已死 → 自动 rm，不再永久阻塞。
- **占用锁**（mkdir 原子操作）+ session 命名（含 target，**同分钟碰撞自动加 PID 后缀**）+ HOME=/Users/alexcai + 启动 tmux。
- **锁回滚** — tmux new-session 失败 → 自动释放锁，不 wedge target。

**退出码**：0=OK, 1=环境错误, 2=BUSY（本 target 被存活 session 占用）, 3=其他活跃 CC（需 --ack-active）。

**启动后等 5s 处理 PTY 对话框**（Dialog 2 = `Down → Enter`）。

### 2. 发送 — `scripts/cc-send.sh`

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session "hermes-cc-default-20260615" \
  --context "/tmp/cc-context-task.md"
```

**⚠️ 不要在 CC 思考态时发消息！** `✻/✽/✶ Composing…` 时发送 → 消息进入队列但不执行 → ❯ 显示 "Press up to edit queued messages"。解决方法：`Escape` 退出队列模式 → 发纯文本命令 "Please read /tmp/…" Enter。

**🔍 发送后存活验证**（v1.3.1 新增 — Pitfall #5 教训）：
`cc-send.sh` 返回 `✓ Sent` 不代表 CC 已开始执行。必须做存活验证：

```bash
# 发完后等 3-5s，抓屏看 ❯ 后面是否有消息残留
tmux capture-pane -t <session> -p -S -5
```

判断标准：
- ❯ 后为空（只有光标）→ CC 可能已开始执行，继续监控
- ❯ 后有文字残留（如 "Please read /tmp/…"）→ **Enter 未生效**，手动 `tmux send-keys Enter`
- ❯ 后显示 "Press up to edit queued messages" → Pitfall #1，`Escape` 后重发
- 看到 `⏺/✢/✻/✳/✶` → CC 已在工作中，正常

不经验证直接等 30s 后跑 `cc-monitor.sh` = 可能白等一轮。

### 3. 监控 — `scripts/cc-monitor.sh`

```bash
# 每 30-60s 运行。stdout 原样转发给用户（见 📡 Relay Contract）。
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-monitor.sh \
  --session "hermes-cc-default-20260615"
```

**v1.3 机械强制执行**（不依赖 Hermes agent 自觉）：
- **心跳文件** `/tmp/cc-heartbeat-<session>` — 每次运行写入时间戳。`cc-finish.sh` 审计新鲜度。
- **状态日志** `/tmp/cc-state-<session>.log` — JSONL，记录每次状态转移（`changed:true/false`）。`cc-finish.sh` 输出转移摘要。
- **6 状态机**：SHELL > WAITING_AGENTS > IDLE > TOOL > THINKING > STARTING。
- **状态转移即时可见** — 每个 📡 块内联 `🔀 PREV → STATE`，随块**原样转发**，不得攒着批量补报。
- **Token 冻结检测** — WAITING_AGENTS >120s / THINKING >180s 自动告警。
- **崩溃检测** — CC 回落 shell（无 bypass 横幅 + shell 提示符）→ SHELL 状态告警。

看到的关键信号（已编码在脚本中，但知道这些有助于理解 📡 输出）：
- `⏺/●` 工具调用 · `❯ 空` 空闲/可能完成 · `✻/✳/✶` 思考态
- `Waiting for N background agents` + token 冻结 >120s → 假死告警

**⚠️ 状态检测盲区**（v1.3.1 已知 — 待脚本修复）：
`cc-monitor.sh` 的 6 状态机可能在 CC 的 `✢ Julienning` / `⏺` 工具调用 / `✻ Cogitated` 等阶段全部报 `IDLE`，导致 📡 块中看不到状态转移。本轮测试中 4 次抓屏全部 IDLE（changed=false），但 CC 实际经历了 TOOL→THINKING→TOOL→完成。

**应对**：当 `cc-monitor.sh` 连续 ≥2 次报 IDLE 且 changed=false 时，不要假设 CC 卡死——先用 `tmux capture-pane` 人工确认实况。常见情况：
- IDLE + 屏上有 `✢/✻/⏺` → CC 工作中，monitor 漏检，继续等
- IDLE + ❯ 空 + 产物目录已有文件 → CC 可能已完成
- IDLE + ❯ 空 + 产物目录为空 → CC 未开始或失败，查 pane 历史

**Agent Team 假死恢复**：
- `Waiting for N background agents` + worker token >2min 不变 → 先 `ls -la` 查产出 → 文件存在则告知 CC，不存在则真死。
- Context 文件必含 `timeout 10min per worker`。

### 4. 结束 — `scripts/cc-finish.sh`

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-finish.sh \
  --session "hermes-cc-default-20260615" \
  --target "jz-skills" \
  --release-lock
```

**v1.3 机械安全门**（7 步，顺序执行）：
1. **❯ 残留检测** — 边框感知提取，危险模式识别（rm -rf / git push / sudo 等）。残留 ≠ 空 → 告警。
2. **监控间隙审计** — 心跳 >120s 陈旧 / 从未有心跳 → reject（exit 2，锁不释放、session 不杀）。加 `--force` 可覆盖监控 gap（不能覆盖残留 gate）。
3. **状态转移摘要** — 从 JSONL 日志读取：抓屏次数、转移次数、最大间隙、状态序列。
4. **Hard Gate** — 监控未达标 → 拒绝收尾。
5. **产物验证** — `find -L /tmp`（macOS symlink 兼容），0 字节文件标 ⚠️。
6. **释放锁** — `--release-lock`。
7. **杀 session** — `--kill-session`，同步清理心跳 + 状态文件。

## ⚠️ 常见坑（Pitfalls）

| # | 症状 | 原因 | 修复 |
|---|------|------|------|
| 1 | ❯ 显示 "Press up to edit queued messages" | 在 CC ✻/✽/✶ 思考态时发送了多条消息，全部进队列不执行 | `Escape` 退出队列 → 发纯文本 "Please read /tmp/…" Enter |
| 2 | CC session 意外消失（中间产出丢失） | CC 进程崩溃 / OOM / API 中断 | 检查 `/tmp/cc-heartbeat-*` 和 `/tmp/cc-state-*.log` 看最后状态；读取磁盘上已修改文件确认哪些已完成；用 `cc-finish.sh --force` 清理残留锁 |
| 3 | `cc-start.sh` exit 3 "其他活跃 CC" | 另一个 agent 正在用 CC | 把输出的 `===📋 BEGIN cc-start 扫描报告===` 原样转发给用户，等确认后重跑加 `--ack-active` |
| 4 | `cc-finish.sh` exit 2 "监控未达标" | 收尾前某段时间没跑 `cc-monitor.sh`（心跳间隙 >120s） | 补跑一次 `cc-monitor.sh` 再收尾，或加 `--force` |
| 5 | `cc-send.sh` 返回 ✓ 但 CC 未执行，❯ 后残留消息文字 | `send-keys` 键入文本后 Enter 未生效（时序/pty 缓冲问题） | **发送后存活验证**：`capture-pane` 看 ❯ 后是否有残留文字 → 有则手动 `tmux send-keys Enter` |
| 6 | `cc-monitor.sh` 连续报 IDLE（changed=false），但 CC 实际在 ✢/✻/⏺ 工作中 | monitor 的状态检测正则未覆盖 CC 全部工作态指示符（特别是 `✢ Julienning`） | 连续 2 次 IDLE 后用 `tmux capture-pane` 人工确认；不要仅凭 monitor 判断 CC 卡死 |

## ✅ Verification Checklist

- [ ] 是否用 `cc-start.sh` 启动？（不用裸 tmux）
- [ ] 启动时是否检查了 exit code？（2=本 target BUSY, 3=其他活跃 CC 需确认）
- [ ] `cc-send.sh` 后是否做了存活验证？（`capture-pane` 确认 ❯ 后无残留文字，CC 已开始执行）
- [ ] 是否每 30-60s 跑 `cc-monitor.sh` 并**原样转发** stdout 到 📡 块？
- [ ] 沉默是否从未超过 2min？（`cc-finish.sh` 会检测心跳间隙）
- [ ] 🔀 状态转移是否即时可见、随 📡 块转发？（非事后补报）
- [ ] 结束前是否跑了 `cc-finish.sh`？（检查 ❯ 残留 + 监控间隙 + 释放锁）
- [ ] 产物是否经磁盘校验（`ls -la` 确认 size > 0）？
- [ ] `cc-finish.sh` 是否通过（exit 0）？（exit 2 = 监控未达标被拒）

**Every box must honestly pass. If unchecked, go back.**

---

> 📦 **设计依据**：`references/design-principles.md`（6 原则 + 4 组件架构）
> 📋 **Phase 分解**：`references/phases.md`（4 phase × ~7 义务）
> 📊 **合规度量**：`scripts/eval-compliance.sh`（机器判定，同任务对比 v4 vs cc-tmux）
> 🐛 **CC Hook Bug Registry**：`references/cc-hook-bug-registry.md`（4 个已知开放 bug）
> 📊 **V4 对比**：`references/v4-comparison-findings.md`（功能矩阵 + 尺寸对比 + 使用场景）
> 🔗 **源仓库**：`~/code/jz-skills/hermes/cc-tmux/`
> 📡 **Relay Contract**：`references/relay-contract.md`（机械执行细则 + 反模式）
> 🧪 **测试复现**：`references/test-repro-2026-06-16.md`（cc-send Enter 未生效 + monitor 盲区复现步骤）
