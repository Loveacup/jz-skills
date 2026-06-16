---
name: cc-tmux
description: >
  Drive Claude Code via tmux with script-enforced safeguards.
  Thin skill — scripts do the enforcement, prose only tells you which script to call.
  Parallel version to claude-code skill for testing the simplified architecture.
  
  Use when: 调 CC, 用 claude, 拉 CC, delegate to CC, agent team, 重活调 CC.
  Do NOT use for: simple single-tool calls, grammar fixes, non-coding tasks.
type: routine
version: 1.8.1
author: "Hermes Agent + Claude Code (v1.8.1: §3.1 冻结检测改用 THINK_TIME 计时器——CC 长思考 token=? 但计时器递增→不打断；双停才告警。计时器提取锚定 spinner 行+放宽格式（2m 3s / 49m · / 37s 全覆盖，防 tool 输出随机数字误重置）；心跳补第 7 字段 THINK_TIME，cc-finish reader 同步。test-monitor-freeze 6/6。全量 48/48)"
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

**CC_TMUX_SESSION 注入 (v1.4)**：`cc-start.sh` 启动 CC 时注入环境变量 `CC_TMUX_SESSION=<tmux-session-name>`，供所有 hook 统一 D-4 键。详见 `hooks/README.md` §2、§4。

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
- **Token 冻结检测** — 基于 THINK_TIME（CC 思考计时器每秒递增）+ TOKENS 双信号：计时器在走 → 不告警；双停 → 真告警。WAITING_AGENTS >120s / THINKING >180s 超时告警。
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

## 🔍 第 5 步：审核（委派包 → gate → auditor 验收）

> 承接 D3 客观/主观分治：**客观半调 `scripts/gate/` 的硬脚本 gate（不可绕），主观半由 auditor 角色审（L1 起步）。**
> 失败检测（超时/崩溃/token 冻结）仍归 cc-tmux 本体（`cc-monitor.sh` / `cc-finish.sh`），因其内在耦合 tmux pane —— 见 5.0 反转记账。

### 5.0 角色契约与 Verdict 结构（红线层接口）

> **裁决③ 反转记账**：基质无关红线脚本原计划独立成 audit skill，现按 YAGNI 收回，落 `cc-tmux/scripts/gate/`（当前唯一委派基质）。脚本**物理隔离**于该子目录、每个头注「零 tmux 耦合·遇第 2 消费者即提升为独立 skill」——搬迁成本为零的前提见脚本头注。

**角色契约**：审核只命名两个角色——`delegator`（委派者）与 `auditor`（审核者）。auditor 是**角色**不是 agent，由委派包的 `auditor` 字段（默认 `self`=delegator）+ `independence_level`（L1–L3 隔离强度）参数化。客观/主观分治：gate 脚本只裁**客观半**（有唯一答案、脚本可判）；主观半交 auditor 角色。

**audit() 槽位契约**：

    audit( artifact, criterion, threshold, context, independence_level ) → Verdict

`context` 是独立性的物理载体（L2 干净 session / L3 独立 agent）；`independence_level` 编码 delegator↔auditor 的强制隔离强度。

**Verdict 结构**：

| 字段 | 取值 | 说明 |
|---|---|---|
| `severity` | pass / nit / concern / blocker | 判定细则见 5.3 |
| `evidence[]` | 新证据指针数组 | 每条 = **此刻新取**的命令输出摘要 / 文件路径；禁用历史运行、禁用自报 |
| `reject_instruction?` | 退回指令 | concern/blocker 必填：指明哪条 criterion 未过 + 需补的客观证据 |

### 5.1 委派包格式（开 CC 前 `cc-send.sh` 的 context 必含）

```yaml
task:        简述任务目标
criterion:   [验收标准列表，按产物类型选模板，见 5.2]
threshold:   pass 线（all_pass / allow_N_nit / critical_zero_tolerance）
risk:        readonly | write | dangerous     # 决定门控与独立性档（SOUL 三级门控）
auditor:     self                              # 默认 self=delegator（L1）；未来可指定独立 agent
independence_level: L1 | L2 | L3               # 隔离强度：readonly→L1 / write→L1→L2 / dangerous→L2/L3
```

委派包缺 `criterion` ⇒ 不准发送。

### 5.2 criterion / threshold 模板库（按产物类型）

| 产物类型 | criterion（喂 `gate-verify.sh --cmd/--artifact`） | threshold |
|---|---|---|
| **编译类** | `build/compile` 退出 0；无新增 error | critical_zero_tolerance |
| **测试类** | `test` 命令退出 0；目标用例真绿（非 skip） | critical_zero_tolerance |
| **文档类** | 产物文件存在且 size>0；章节齐全；无占位符 | allow_N_nit |
| **安全类** | 无危险操作（`gate-danger.sh`）；无明文密钥；权限改动经确认 | critical_zero_tolerance |

模板沉淀在此（可复用、可审计），每次委派只挑不现编。

### 5.3 severity 判定细则（接 D5，与计数器挂钩）

| severity | 含义 | 动作 | 计数（`gate-counter.sh --kind reject`） |
|---|---|---|---|
| **pass** | 全过 | 收 | 不计 |
| **nit** | 非阻断瑕疵 | 收 + 记一笔 | **不计**（防吹毛求疵耗尽退回预算） |
| **concern** | 阻断 | 退回 CC | **+1** |
| **blocker** | 强阻断 | 退回 CC，须附客观证据 | **+1** |

退回累计 **2 次**未过 → 停自动退回，升级人工（`gate-counter.sh` 返回 exit 20）。

### 5.4 auditor 身份切换 checklist（四步机械过程 —— 裁决②）

> auditor 是**一段带步骤的过程**，不是一种心态。L1/L2/L3 同一套过程，只在第 ① 步「上下文裁剪」的强制强度上分档。

- [ ] **① 封掉自报证据**：禁引用"CC 说跑过了 / 我已验证 / 应该没问题"。任何 pass/fail 必须指向**此刻新取**的证据，否则该判断作废。
  - L1：靠自律（证据替换）｜ L2：开**干净 session**，设计上下文物理不在窗口｜ L3：独立 auditor agent，从未接触设计。
- [ ] **② 客观半重跑**：不信任何历史运行，调 `gate-verify.sh` **现在**重新执行验收命令、抓退出码。
- [ ] **③ 对 criterion 审，不对意图审**：输入 = `criterion + artifact + 新证据`，**不是**"我本来想造什么"。逐条 criterion 出 `evidence:verdict`。
- [ ] **④ 产出结构化 Verdict**：每个 severity 必须挂一个**新证据指针**（命令输出 / 文件路径），否则无效（见 5.0 Verdict 结构）。

### 5.5 与 gate 脚本的调用关系（裁决③ 反转后落点）

| 职责 | 落点 | 调用 |
|---|---|---|
| 客观验收（命令/退出码/产物） | `scripts/gate/`（基质无关，暂居本 skill） | `bash scripts/gate/gate-verify.sh …` |
| 危险操作拦截 | `scripts/gate/` | `bash scripts/gate/gate-danger.sh --scan-file <委派包/diff>` |
| 终止计数器（讨论轮/退回轮） | `scripts/gate/` | `bash scripts/gate/gate-counter.sh --key <session> --kind reject --inc --limit 2` |
| 失败检测（超时/崩溃/token 冻结） | cc-tmux 本体（耦合 tmux pane） | `cc-monitor.sh` / `cc-finish.sh` 第 2 步监控间隙审计 |
| **计数器文件清理** `cc-counter-<key>.json` | `cc-finish.sh` 收尾 | session 结束时随心跳/状态文件一并清理 |

**铁律**：cc-finish.sh 的客观验收/危险拦截/计数 **调 `scripts/gate/` 的 gate，不内嵌进 cc-finish.sh 本体** —— 保持 gate 零 tmux 耦合，遇第 2 消费者可整组搬走。计数器**原语**在 `gate-counter.sh`；**触发自增**的事件（一次 concern/blocker 退回）由 cc-tmux 跑循环发；计数器文件的**清理**由 `cc-finish.sh` 收尾统一负责（落点进 cc-tmux 后自然归属，不留悬空）。

## ⚠️ 常见坑（Pitfalls）

| # | 症状 | 原因 | 修复 |
|---|------|------|------|
| 1 | ❯ 显示 "Press up to edit queued messages" | 在 CC ✻/✽/✶ 思考态时发送了多条消息，全部进队列不执行 | `Escape` 退出队列 → 发纯文本 "Please read /tmp/…" Enter |
| 2 | CC session 意外消失（中间产出丢失） | CC 进程崩溃 / OOM / API 中断 | 检查 `/tmp/cc-heartbeat-*` 和 `/tmp/cc-state-*.log` 看最后状态；读取磁盘上已修改文件确认哪些已完成；用 `cc-finish.sh --force` 清理残留锁 |
| 3 | `cc-start.sh` exit 3 "其他活跃 CC" | 另一个 agent 正在用 CC | 把输出的 `===📋 BEGIN cc-start 扫描报告===` 原样转发给用户，等确认后重跑加 `--ack-active` |
| 4 | `cc-finish.sh` exit 2 "监控未达标" | 收尾前某段时间没跑 `cc-monitor.sh`（心跳间隙 >120s） | **补跑一次 cc-monitor 再立刻 finish**：`cc-monitor.sh --session X && cc-finish.sh --session X ...`（同一条命令链，间隙归零）。`--force` 跳过硬门但会丢审计覆盖 |
| 5 | `cc-send.sh` 返回 ✓ 但 CC 未执行，❯ 后残留消息文字 | `send-keys` 键入文本后 Enter 未生效——**系统性 PTY 时序问题，不是一次性修复** | **每次发送后必做存活验证**：`capture-pane` 看 ❯ 后是否有残留文字 → 有则手动 `tmux send-keys Enter`。即使上一次 Enter 生效了，下一次仍可能不生效——这是模式，不是偶发 |
| 6 | ~~`cc-monitor.sh` 连续报 IDLE（changed=false），但 CC 实际在 ✢/✻/✳/✽/✶/⏺ 工作中~~ **✅ 已修复 (v1.6.0)** | 根因 = **优先级 bug**：`IDLE` 检测排在 `TOOL`/`THINKING` 之前。修正：反转优先级（TOOL/THINKING > IDLE）+ 收窄取样窗口到 `ACTIVE_TAIL`（最后 6 非空行）。测试 `tests/test-monitor.sh` 6/6 通过。 | 已内建修复，不再需要人工应对 |
| 7 | `cc-start.sh` 报 "No such file or directory" | profile 的 `HERMES_HOME` 重定向导致 `~/` 解析到 profile home 而非真实 home | 用绝对路径 `/Users/<user>/.hermes/skills/...` 或在命令前加 `HOME=/Users/<user>` |
| 8 | CC 写了大量输出（20K+ tokens）但 `capture-pane` 只能抓到最后 24 行；要求 CC "保存到文件" 的指令在排队中丢失 | CC 大输出在 pane scrollback buffer 之外；内联指令进入队列（→Pitfall #1）不被执行 | **方法 A（预防）**：任务 context 文件末尾加 `"Save your full response to /tmp/cc-output-<task>.md"`——CC 在写响应时会主动创建文件。**方法 B（恢复）**：若已丢失，清队列（`Escape`×2）后发 `"Continue writing /tmp/xxx.md"`——CC 记住未完成的写操作 |
| 9 | `cc-send.sh` 中 `(( tries++ ))` 在 `set -euo pipefail` 下首次重试即 abort | `tries` 初始化为 0 → `(( tries++ ))` 返回 rc=1（后置++表达式值=0）→ `set -e` 下整个脚本退出，重试循环一次都不跑。**2026-06-16 实读 line 5 确认 `set -euo pipefail`；此 bug 经 CC 对抗核验确认成立** | 所有自增必须用 `(( ++tries ))` 或 `tries=$((tries+1))`——前缀 `++` 使表达式值非零，不触发 `set -e` abort |
| 10 | CC 执行 `/usage` 后卡在 TUI 全屏面板，无法继续 | `/usage` 是 CC CLI 内置命令，执行后进入交互式 TUI（全屏仪表盘），CC 本身不会自己退出，pane 冻结在用量面板 | `tmux send-keys Escape` 退出 TUI → 回到 ❯ prompt。不要在 CC 工作中途敲 `/usage`——只在任务边界（开始/结束）由用户手动敲，CC 读屏后汇报。Hermes 侧不可代敲 `/usage`（非可注入的 shell 命令） |
| 11 | 用户要求「每次任务开始/结束汇报用量」，但 CC 无法自理 | `/usage` 不是 shell 命令也不是 tool，CC 的 Bash/任何工具都无法执行它。本地 `npx ccusage` 可估算 token/成本但无剩余额度；`~/.claude/` 下无可直接读的订阅额度文件 | **方案 3（推荐）**：CC 每次任务边界自动跑 `npx ccusage` 给消耗估算；用户方便时敲 `/usage` 补真实剩余额度。CC 在每个子任务边界主动提醒用户敲 `/usage`。详见 `references/usage-reporting-pattern.md` |
| 12 | `cc-finish.sh` 拒绝收尾：监控未达标（心跳间隙 >120s） | Hermes 用 `tmux capture-pane` 手动查 CC 进度（绕过 monitor 盲区，Pitfall #6），但**忘了同时跑 `cc-monitor.sh`** 刷新心跳。手动抓屏 ≠ 心跳——`cc-finish.sh` 看的是 `/tmp/cc-heartbeat-*` 时间戳，不是 pane 内容。 | **每次手动 `capture-pane` 后立刻跑 `cc-monitor.sh`**——即使只是为了刷心跳。习惯性写成一行：`capture-pane ... && cc-monitor.sh ...`。沉默 >90s 还没跑 monitor → 补跑一次再 finish（同 Pitfall #4）。2026-06-17 WRR platform mode 任务中连续两次被拒，根因即此。 |
| 13 | CC 报告「已完成/N 个测试通过」但**磁盘上没有任何产物** | CC 在长时间的 xhigh 思考后，有时会在**思考态内部形成「已经做过」的幻觉**——它在对话流里描述了完成状态和结果，但从没用 Write/Bash 工具真正写过文件。验证方法：**不要信 CC 说的任何完成声明，必须 `ls -la` / `find` / `stat` 独立取证**。这与 SOUL 委派审核规则「禁止采信执行方自报」完全一致。 | ① 听到「已完成」→ 立刻 `ls -la` 查产物目录 ② 若文件不存在 → `tmux send-keys C-c` 中断 + 「用 Write 工具写文件，不要只说不做」③ 每次验证后汇报文件路径 + size + 行数。**Hermes 永远不代信 CC 的自报，必须亲眼看到磁盘文件**。 |
| 14 | CC xhigh effort 陷入 >5min 思考冻结（token/screen 完全不更新，spinner 静止） | xhigh effort 在工程实现类任务上极度易冻结。CC 不报错、不崩溃、不会自己挣脱。**v1.8.1 冻结检测已改用 THINK_TIME 计时器**：token=? 但计时器每秒递增 → 不误报。双停（计时器+token 全不动 >3min）→ 真告警。见 Pitfall #16。 | ① 发现 THINK_TIME 停止 + token 完全不动 >3min → C-c ② 发 /effort high + 缩小范围 ③ 预防：工程实现类任务地板用 high |
| 15 | CC hook 被误判为不触发，实际产物全堆 unknown/ 目录 | CLAUDE_SESSION_ID 在 hook 执行环境中为空（CC v2.1.178 实测）。所有 hook 脚本用兜底值 → 产物归入 unknown/。验证时按 session 名找产物找不到 → 误判。根因不在 hook 配置，在 session ID 来源。修复：从 hook 的 stdin JSON 中提取 session_id 字段。关键：stdin 只能读一次——必须先 in=$(cat) 保存，再从 $in 中提取 sid 和 tool_response。见 references/cc-hook-deployment-20260617.md。 | ① 不引用 CLAUDE_SESSION_ID 环境变量 ② stdin JSON → jq 取 session_id ③ in=$(cat) 先保存——禁止分两次读 stdin |
| 16 | cc-monitor.sh 在 CC 正常长思考时误报 token 冻结 >3min，打断正在产出的 CC | 冻结检测只看 TOKENS（token 计数字符串）是否变化。CC 写文件/深度思考时 token 显示为 ?（不可读），连续多轮 ? → TOKENS 不变 → 冻结时钟累计 → >180s 误报。但 CC 自己的思考计时器 THINK_TIME（如 4m 13s）每秒递增——这个信号之前被忽略了。修复 (v1.8.1)：冻结重置条件增加 THINK_TIME 变化检测。? 但计时器在走 → 不告警；双停（计时器 + token 都不动）→ 真告警。计时器提取**锚定到 spinner 行**（避免 tool 输出里的随机 `5s`/`3m` 误重置而掩盖真冻结）且**放宽格式**覆盖全部渲染：`2m 3s`（完整）/ `49m ·`（分钟制，本 Pitfall 的 xhigh 形态）/ `37s`（不足 1 分钟）。新测试 tests/test-monitor-freeze.sh 6/6 覆盖。 | ① token 在涨 / spinner 在动 / pane 有新输出 → CC 活跃，不要 C-c ② 判准是双停（THINK_TIME + TOKENS 全不动 >3min），不是时间长 ③ 用户明确要求「只要他持续在思考，就先别干预他」 |

## 👤 用户偏好与约束（不可协商）

以下偏好在所有 cc-tmux 驱动的 CC 任务中必须遵守：

- **🔴 杀 session 必须用户确认**：`cc-finish.sh` 的 `--kill-session` 永不自动执行。Hermes 收尾时必须先释放锁、完整汇报产物，等用户明确确认后再跑带 `--kill-session` 的 finish。
- **📊 用量汇报**：每次任务开始和结束时汇报 token 消耗（方案 3：`npx ccusage` 估算 + 用户补 `/usage` 真实值）。
- **🧪 TDD 落地**：实现类任务先写测试 → 确认失败 → 写代码 → 确认通过。
- **📝 方案回写 Obsidian**：产出方案/计划必须同步写入 Obsidian vault（`02-Plan&CQI/`），附带完整 YAML frontmatter。
- **🤝 CC + Hermes 协商决策**：遇到待决策点时，CC 和 Hermes 各自给出分析后协商决定，不逐条等用户拍板（除非涉及架构方向/安全边界/资源取舍）。
- **⏳ CC 思考时不干预**：只要 CC 的 token 计数在增长、pane 显示活跃 spinner（✻/✽/✶/✢/✳），**不要 C-c 中断**——即使 xhigh 思考超过 5 分钟。Pitfall #14 的冻结判定是「token 完全不动 + spinner 静止」，不是「思考时间长」。用户明确要求「只要他持续在思考，你就先别干预他」。

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
> 🔍 **审核 Agent 槽位**：`references/audit-agent-slot-design-20260616.md`（通用 audit 槽位契约 + 独立性四档 + 灰度扩展）
> ⚖️ **三问题裁决**：`references/audit-three-issue-verdict-20260616.md`（去 regent 化 / 切 auditor 身份机制 / 脚本物理落点）
> 🔍 **审核 gate 脚本**：`scripts/gate/`（基质无关红线：gate-verify / gate-danger / gate-counter，零 tmux 耦合，遇第 2 消费者提升为独立 skill），见 5.0 / 5.5。
> 📋 **Phase 分解**：`references/phases.md`（4 phase × ~7 义务）
> 📊 **合规度量**：`scripts/eval-compliance.sh`（机器判定，同任务对比 v4 vs cc-tmux）
> 🐛 **CC Hook Bug Registry**：`references/cc-hook-bug-registry.md`（4 个已知开放 bug）
> 🧠 **CC 写作任务超长思考**：`references/cc-overthinking-writing-tasks.md`（xhigh 在文档任务上易冻结，恢复 Ctrl+C→重定向，预防用 high）
> 📊 **V4 对比**：`references/v4-comparison-findings.md`（功能矩阵 + 尺寸对比 + 使用场景）
> 🔄 **多轮 CC 设计迭代**：`references/multi-round-design-pattern.md`（4 轮模式：设计→优化→产出→终审）
> 🔗 **源仓库**：`~/code/jz-skills/hermes/cc-tmux/`
> 🔗 **源仓库**：`~/code/jz-skills/hermes/cc-tmux/`
> 📡 **Relay Contract**：`references/relay-contract.md`（机械执行细则 + 反模式）
> 🧪 **测试复现**：`references/test-repro-2026-06-16.md`（cc-send Enter 未生效 + monitor 盲区复现步骤）
> 🔀 **路由对照**：`references/hermes-deck-routing-comparison.md`（hermes-deck Primer + AgentRouting 块 vs cc-tmux 长会话模型对照分析）
> 🔍 **CC 审核模式**：`references/cc-audit-cross-evaluation-pattern.md`（用 CC 做多文档交叉审核：典型发现层级、常见误判、输出格式）
> 📦 **Obsidian 重构**：`references/obsidian-restructuring-pattern.md`（CC 驱动的 vault 文件重组：批量重命名 + 合并 + wikilink 全局更新 + 库外断链修复 + perl 编码坑）
> 🚀 **Ultracode Dynamic Workflow**：`references/ultracode-workflow-pattern.md`（用 CC 原生 ultracode 模式做 13-agent 并行深度调研的完整流程：触发方式、编排设计、监控、产出验收、适用/不适用场景）
> 📊 **用量汇报**：`references/usage-reporting-pattern.md`（CC 无法自理 `/usage` 的根因 + 方案 3 实现细节 + npx ccusage 使用）
> 📋 **优化方案（2026-06-16）**：Obsidian `02-Plan&CQI/cc-tmux优化方案_20260616.md`（ultracode 13-agent 深度调研产出：P0 脚本修复 + P1 CC hook 混合架构 + 基质无关内核收敛 + CQI 闭环 + 6 决策点）
> 🧪 **TDD 测试套件**：`tests/test-monitor.sh`（§3.1 6/6）· `tests/test-monitor-freeze.sh`（§3.1 冻结检测 6/6，含计时器格式覆盖）· `tests/test-send.sh`（§3.2 9/9）· `tests/test-start.sh`（§3.8+D-4 注入 5/5）· `tests/test-finish.sh`（§3.7+D-4 清理契约 6/6）· `tests/test-hooks.sh`（§3.3-3.7 D-4 键统一 16/16）→ **48/48 全绿**（实跑核实，2026-06-17）
> 🪝 **CC Hook 脚本**：`hooks/cc-posttool.sh`（§3.3 PostToolUse 归档）· `hooks/cc-stop-check.sh`（§3.7 Stop 软门）· `templates/settings.template.json`（§3.4/3.5 Notification+SessionStart 内联，**单一事实源**，stdin-jq + D-4 键统一 `${CC_TMUX_SESSION:-<stdin session_id>}`）· `hooks/README.md`（部署 + D-4 + smoke 清单）
> 🧪 **测试结果记录**：`references/test-results-33of33-20260617.md`（历史文件名；现为 **45/45**，含 D-4 键统一 + 冻结检测修复记录 + 部署 smoke 清单）
> 🔬 **Hook 部署验证 (2026-06-17)**：`references/cc-hook-deployment-20260617.md`（部署流程 · CLAUDE_SESSION_ID 空值根因 · stdin 消费陷阱 · 验证方法 · 修复记录）
> 📋 **状态审计 (2026-06-17)**：Obsidian `88-审计/cc-tmux 状态审计 20260617.md`（CC 自主审计：Readiness 6→8 · D-4 键分裂 · 测试失真 · 三步修复落地全记录）
