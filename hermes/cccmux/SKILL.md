---

name: cccmux
description: |
  Orchestrate Claude Code agent teams via `cmux claude-teams` — cmux-native, event-driven (stability-first).
  cmux 版的 claude-code 编排手册:用 cmux 的 events 事件流 + Feed 决策面板 + workspace 隔离,
  取代 raw-tmux 的盲轮询 + PTY 对话框导航。

  Triggers: cccmux, cmux claude-teams, cmux 起 team, 用 cmux 驱动 claude, cmux agent team,
  claude-teams, cmux 跑 CC
  DO NOT use for: 纯 raw-tmux 编排(用 claude-code skill)、非 cmux 环境、简单单工具调用(直接做)、
  非 macOS/cmux 终端
type: routine
version: 0.1.0
author: Hermes Agent + cccmux team (从 hermes/claude-code v4.2.0 改造:底座 tmux→cmux,监控盲轮询→事件驱动)
license: MIT

---

# cccmux — 用 cmux claude-teams 驱动 Claude Code Agent Team（事件驱动 · 稳定性优先）

把复杂任务交给 `cmux claude-teams` 启动的 **CC 原生 agent team**。监控走 **cmux events 事件流**，决策点走 **Feed**，隔离单位是 **workspace**。

> **本 skill 是 `hermes/claude-code` 的 cmux 变体。** 凡与底座无关的纪律（任务分解、context 传递、effort 路由、讨论协议、磁盘校验、CQI、治理）沿用原 skill；本文件只讲 cmux 带来的**改变**。原 skill 的 raw-tmux 细节不再适用。

## §0 范式转移（先读这个,否则会照搬 tmux 旧习惯）

`cmux claude-teams [claude-args...]` 经实测 = **启动单个 CC，开 native teammate mode `auto`，外加一条 tmux shim 把 CC 发的 tmux 窗格命令翻译成 cmux split**。它做四件事:① teammate mode 默认 `auto`;② 设 tmux-like 环境让 auto 模式用 cmux splits;③ 设 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`;④ 把私有 tmux shim 前置到 PATH(动态注入,磁盘无 shim 文件——预期如此);其余参数透传 `claude`。

两条硬结论:

1. **CC 原生 team 心智整体保留。** team 仍是「一个 CC leader 内部 spawn teammate」——任务分解、按关注点拆、写 context 文件、worker timeout 全部沿用。变的只是**底座**:不再手设 `--teammate-mode tmux`,改 `cmux claude-teams`;teammate 由 shim 映射成 cmux surface。「Hermes 自己起多个独立 CC 进程手动调度」降级为边缘特例(改用多 workspace)。
2. **盲轮询的物理前提消失。** tmux 无事件 → 旧版用「每次 capture 必汇报」当人肉心跳。cmux 有 `cmux events`(NDJSON,可重连重放)+ Feed + `~/.cmuxterm/workstream.jsonl` 审计 + 每会话 lifecycle。**红线① 必须演化为事件驱动,不能照搬。**

### 🔄 防漂移
任何修改必须在源仓库 `~/code/jz-skills/hermes/cccmux/` 进行,单向同步到部署端/测试端;禁止在部署端热修复(分叉根源)。

## 🧪 cccmux 测试验收标准（P0）

只证明「能启动、能写文件、events 有日志」**不算测试通过**。cccmux 的核心价值是**用户可见监控 + 可干预控制面**，所以 smoke/回归测试必须同时证明 3 件事:

1. **用户可见进度**:任务运行中至少发 1 条 `📡 cccmux Team` 状态块,包含 workspace/surface、当前事件 seq、leader 状态、Feed pending 数；不能等全部完成后才总结。
2. **可干预能力**:展示至少 1 个干预动作及结果,例如 `cmux capture-pane` 读屏、`cmux send-key enter` 推动卡住输入、`cmux send --surface ... "<追加指令>"`、`cmux close-workspace` 收尾；必须说明“我现在可以这样打断/推进/收尾”。
3. **落盘闭环**:Stop/idle 后做磁盘校验,展示产物路径、size、内容摘要。

> 若测试过程中没有对用户汇报进度、没有展示干预点,即使文件写成功也只能判定为 **机制半通,交互验收失败**。

## 🔴 不可协商红线（3 条）

### 🔴 红线① — 事件流不静默(cccmux 版)

发任务后**必须**起一条常驻 events 订阅,并对关键事件**即时**汇报,不得静默:

```bash
cmux events --category agent --category feed --category surface --category notification \
  --cursor-file ~/.cache/cmux/cccmux.seq --reconnect
```

- **`feed.item.received` 先分类,再动作**:实测 SessionStart/UserPromptSubmit/Stop 也会产生非阻塞 feed 归档项；只有 payload/Feed TUI 显示为 Permission / ExitPlanMode / AskUserQuestion / needsInput 的才是🔴决策点 → 立即转发用户 + 讨论简报,不得代答。
- **`agent.hook.Stop`** / lifecycle→`idle`(=回合结束)→ 汇报结果 + **磁盘校验**(Core #12)。
- **`agent.hook.PreToolUse/PostToolUse`** → 汇报「CC 正在 {tool_name}」。
- **事件流断连 / heartbeat(15s) 丢失 >2min** → 报「事件流中断,转 `cmux capture-pane` 兜底」。
- **兜底节流**:事件稀疏的长任务(max-effort 深思)至少每 60-90s 发一次 `📡` 存活块(可由 heartbeat 驱动)。

> **这不是旧版的「每次 capture 1:1 汇报」**——capture-pane 退化为「事件不够用时的取证手段」(详见 `references/cmux-events-monitoring.md`)。但**行为纪律保留**:① 决策点绝不静默/不代答;② 投递失败也算未汇报;③ 不许用一句「我会监控」结束回合——必须确认 events 订阅进程仍在跑(订阅在跑 = 轮巡在跑);④ 违规当轮补做(Core #11),禁「下轮改」。

| 你会找的借口 | 为什么是错的 |
|---|---|
| 「events 在跑就行,不用汇报」 | 订阅是数据源,用户看不到。关键事件必须转成 user-visible `📡` |
| 「决策点我替 CC 答了更快」 | 红线②:方案审定前是讨论。架构/方案类 `feed.item.received` 一律转用户 |
| 「长任务没事件,我就不报了」 | heartbeat 驱动兜底:60-90s 一个存活块,沉默 >2min 自标 `⏰超时` |
| 「我最后总结就算汇报了」 | 错。cccmux 的验收点是运行中可见性；结束后总结不能替代中途 `📡` 状态块 |
| 「我能控制但没必要展示」 | 错。测试必须展示至少一个干预动作,否则没证明 cmux 控制面真的可用 |

### 🔴 红线② — 讨论协议:用户说「看方案 / 优化 / 处理决策点」= 讨论,不是执行

只有用户明确说「执行吧 / 可以做了 / 拉 CC 改」才动手。方案必须经用户**逐条审定**后才能开 team / 改文件。(与原 skill 完全一致,底座无关。)

### 🔴 红线③ — 测试必须展示“用户可见 + 可干预”

测试 cccmux 时,**必须在运行中汇报**,并展示至少一个可干预动作。只在工具后台看 events、最后报告“写文件成功”=交互验收失败。最小合格测试节奏:

1. 启动后立刻发 `📡 cccmux Team [0min · seq=N]` 状态块。
2. 中途展示一次干预能力:读屏 / 追加指令 / 补 Enter / 关闭 workspace / 处理 Feed,并说明可让用户选择。
3. Stop/完成后做磁盘校验并报告。

> 这条是从 2026-06-11 实测失败追加:当轮只做了后台验证,没有向用户展示进度和干预面。

> 违反任一红线 → 立即标记 + 当轮补做,禁「下轮改」口头了事。

## 🚦 执行前 Gate Stamp（开 team / 改文件前必须打印）

```
🚦 执行前 Gate Stamp (cccmux)
  方案审定 ✓  用户已说「执行吧 / 可以做了」?(红线②)
  该调 CC ✓  这是重活(多文件/架构/skill/部署)?
  effort   ✓  已按任务信号选档?(地板 high)
  workspace✓  独立 workspace + 独立 cwd?title=hermes-cc-{agent}-{ts}?
  占用检测 ✓  跑了 occupancy-scan.sh,无 running/needsInput 冲突?
  ── 五项全 ✓ → 开 team;任一 ✗ → 停,报用户后再继续
```

## 🚀 启动:cmux claude-teams

### 1. 占用检测（唯一权威脚本,读 lifecycle 非 grep emoji）

```bash
bash ~/code/jz-skills/hermes/cccmux/references/occupancy-scan.sh
```
读 `~/.cmuxterm/claude-hook-sessions.json` 的 `agentLifecycle`:`running`=忙 / `needsInput`=等决策 / `idle`=空闲。有 `running`/`needsInput` → 汇报用户后等确认。fail-open:文件缺失视为无占用。

### 2. 新建隔离 workspace + 启动原生 team

```bash
# 新建 workspace 打开任务 cwd(隔离边界 = 独立 workspace + 独立 cwd)
cmux new-workspace --name "hermes-cc-{agent}-{ts}" --cwd /path/to/task-cwd --focus false
# 记录返回的 workspace ref(形如 workspace:N),再在该 workspace 的 surface 里启动原生 team
cmux send --surface surface:N "cmux claude-teams --effort high"
cmux send-key --surface surface:N enter
```

- **无需** `HOME=/Users/<username>` 前缀——cmux 终端原生注入 `HOME` 与 `CMUX_WORKSPACE_ID`(实测已是用户真实 home)。
- **无需**手设 `--teammate-mode tmux` 或 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`——`cmux claude-teams` 已包办。
- effort 体系沿用原 skill:地板 `high`;多文件/审查/设计/原型 → `xhigh`;深度架构/多 lens/根因/全栈/安全/写 skill → `max`(≈3×high)。`cmux claude-teams --model claude-opus-4-8 --effort max`。⚠️ `xhigh`/`max` 仅 Opus 4.8/4.7 专属。完整体系 → 原 skill `references/effort-routing.md`。
- 实测注意:对 Claude TUI 输入 prompt 时,`cmux send "...\n"` 可能只把文本塞进输入框而不提交；稳妥做法是 **send 文本 + send-key enter** 两步。若 `capture-pane` 仍看到 prompt 停在 `❯` 输入框且没有 `⏺` 执行块,再补一次 `send-key enter`。shell 命令场景仍可用 `cmux send "echo hi\n"`。
- **surface 未物化兜底**:新建 workspace 后先用 `cmux top --workspace workspace:N --processes` 或 `cmux debug-terminals` 看目标 surface 是否 `runtime=1 / tty=... / ghostty=...`。若 `read-screen/capture-pane` 报 `Failed to read terminal text` 且 `runtime=0, tty=nil, ghostty=nil`,先跑 `cmux refresh-surfaces`;仍不行再 `cmux reload-config`,然后重试读屏/启动命令。不要把这误判为 Claude/teammate 失败。

### 3. 写 context 文件
复杂任务把 context 写 `/tmp/cc-context-{task}.md`,含:任务描述(按关注点拆,数量由 CC 自定)、`timeout 10min per worker`、已知事实/记忆摘要、权限默认策略(读 Allow / 写走 Feed)。调用另一 skill 时把该 skill 验收标准原样写入(跨 skill 规格透传)。

## 📡 监控:cmux events 事件流

详见 `references/cmux-events-monitoring.md`。要点:

- 订阅命令见红线①。`agent.hook.*` = CC 原生 hook(`PreToolUse`/`PostToolUse`/`Stop`/`SubagentStart`/`SubagentStop`/`Notification`)经 cmux 转发;`feed.*` = 决策点。
- 每帧带 `seq` + `boot_id`;`--cursor-file` 持久化游标断线续传;`ack.resume.gap=true` → cursor 太旧,用 `cmux tree`/`occupancy-scan.sh` 重新快照对齐。
- **枚举 team 拓扑**:`cmux tree --all`(window→workspace→pane→surface)、`cmux list-panels`(surface 列表)、`cmux top --processes`(唯一能看 surface↔进程↔teammate node 子进程映射的命令)。
- **对特定 teammate 操作**:`cmux capture-pane --surface surface:N --lines 40` 读屏、`cmux send --surface surface:N "..."` 发文本、`cmux send-key --surface surface:N enter` 发键。
- **磁盘校验(Core #12,原样保留)**:宣布完成前 `find <cwd> -newer /tmp/cc-marker -type f` / `ls -la` 确认产物落盘 size>0;找不到产出先 `mdfind -name`(CC 常直写 OB vault)。事件流**不保证**写盘成功。

**汇报模板(必须按此状态块对用户可见输出；测试时至少一次,长任务按 heartbeat 60-90s 一次):**
```
📡 cccmux Team [Xmin · 事件 seq=N]
  ⚡ Leader: <当前 tool / 状态>
  ├─ ✅ Worker A: <描述> (idle)
  ├─ 🔵 Worker B: <PostToolUse: Edit> (running)
  └─ 🟡 Worker C: 假死 — find 校验中
  📊 lifecycle: running ·  Feed: 0 pending
```
状态 emoji:⚡运行 💤idle ✅完成 🔵进行中 🟡假死 🔴真死 🎫Feed决策点 ❌错误 ⏰超时(>120s沉默)

## 🎫 决策点:Feed 取代 PTY

详见 `references/cmux-feed-decision-points.md`。要点:

- 权限 / ExitPlanMode / AskUserQuestion 全部走 **Feed**(侧栏 `Ctrl-4`)——**不再手工 `send-keys Down→Enter` 导航 PTY 对话框**。
- `feed.item.received` → **先分类,再动作**:Permission / ExitPlanMode / AskUserQuestion / lifecycle=`needsInput` 才是🔴决策点,立即转用户 + 讨论简报；SessionStart/UserPromptSubmit/Stop 等也可能作为 feed 归档项出现,不一定阻塞。**架构/方案类不得代答**;纯机械读类权限可按 context 预设策略放行。
- Feed 软等待 120s 超时不死锁(吐 `{}`,CC 回落 TUI)。
- **作废的 Pitfall**:#1(Dialog 2 默认 No)、#13/Shift-Tab、#26(AskUserQuestion 表单不可靠——cmux Feed 原生支持点选,**解禁**)。
- **副作用**:很多 worker 假死本质是权限弹窗阻塞;Feed 收编弹窗后这类假死大幅减少。

## 🔥 讨论协议（grill / 双向拷问 / 讨论简报 — 几乎原样保留）

底座无关,沿用原 skill:开场即讨论(除非需求明确);双向拷问;现状陈述带可验证 artifact;多轮辩证 + 立场更新;≤3 轮分歧 → assumption log 带条件推进;每轮发 `📋 讨论简报`。

**cmux 带来的松绑**:决策点可用 Feed 的 AskUserQuestion 点选(原 Pitfall #26 解禁),但 Hermes 侧仍发讨论简报。**连续推进模式**:用户说「继续/不用问」时按已知顺序推进,仅真决策点停。

```
📋 讨论简报 R{n}
  · 讨论了什么 / 决定了什么 / 分歧未决
  · 我的拷问(每问带推荐答案)
  · 下一步(执行前必须等审定)
```

## ⚡ Core Rules（沿用原 skill 13 条,改 3 条措辞）

- **#0** 调 CC 前跑 `occupancy-scan.sh`(读 lifecycle,非 grep emoji)。
- **#1** 每任务新建**独立 workspace + 独立 cwd**(载体从 tmux session→workspace);`--continue` 仍默认禁(避免拿到 cmux 之外的 CC 历史)。
- **#9** 🔴 事件驱动汇报(红线① 执行细则):events 订阅常驻 + 关键事件即时 `📡` + heartbeat 兜底。
- 其余 #2(复杂任务必 team)/#4(已无需 HOME 前缀,本条作废)/#11(违规当轮补做)/#12(完成前磁盘校验) 等沿用原 skill `references/core-rules-detail.md`。

## 🛟 异常恢复

- **Worker 假死**:判定 = `agent.hook.*` 停流 + lifecycle 卡 `running` + `find -newer` 无产出。先 `ls`/`find` 查磁盘;文件存在 → `cmux send --surface surface:N "Agent N done. Files on disk. Continue."`;不存在 → 真死。**多数假死已被 Feed 收编弹窗消除**。
- **新 workspace 空壳 surface**:症状 = `cmux tree` 有 surface,但 `cmux top` 无进程、`read-screen/capture-pane` 报 `Failed to read terminal text`、`cmux debug-terminals` 显示 `runtime=0 / tty=nil / ghostty=nil`。处理顺序:① `cmux select-workspace --workspace workspace:N` 让 surface 进入窗口；② `cmux refresh-surfaces`;③ 必要时 `cmux reload-config`;④ 重新 `read-screen`,确认 `runtime=1 / tty=...` 后再 `send` 启动 `cmux claude-teams`。若仍失败,关闭该 workspace 重建,并把 blocker 报用户。
- **全队冻结**:`tmux kill-session` → 改为关 workspace/surface 重开(见生命周期);「降 worker 数 + 缩范围 + 预填权限策略」保留。
- **思考保护**:lifecycle=`running` 且 `agent.hook.*` 仍在发 = 深度推理活跃,**勿打断**;只有事件完全停流 >3min 才算卡死 → 单行短命令推动 → 仍循环则 `cmux send-key --surface ... C-c` 缩到原子任务。

## 🧹 生命周期收尾（cmux 没有 tmux kill-session）

| tmux | cmux |
|---|---|
| `kill-pane` | `cmux close-surface --surface surface:N`(关一个 tab) |
| `kill-window`(整组) | `cmux close-workspace --workspace workspace:N`(关整个 workspace 及所有 surface) |
| `respawn-pane` | `cmux respawn-pane --surface surface:N [--command <cmd>]` |

**干净收尾一个 team 会话:**
1. 先让 CC 自己退(`cmux send --surface surface:N "/exit"` 或 `send-key C-c` 两次),让 hook 正常写 session-restore 状态;
2. 再 `cmux close-surface`;teammate 被 split 成独立 surface 时逐个 close,或 `cmux close-workspace` 一次性收掉整组。
- **阶段性结束前不收尾**——保留到用户确认整个阶段结束(沿用原 skill 纪律)。
- **收尾安全门(弱化保留)**:收尾前 `cmux capture-pane --surface surface:N --lines 3` 看末行有无残留 + 检查有无 pending Feed 项。cmux 下 CC 不再靠 send-keys 注命令,危险动作多走工具→Feed 权限门,但安全诉求仍在。

## ✅ Verification Checklist

- [ ] **占用检测?** 跑了 `occupancy-scan.sh`,无 `running`/`needsInput` 冲突?
- [ ] **workspace 隔离?** 独立 workspace + 独立 cwd?title=`hermes-cc-{agent}-{ts}`?避免了 `--continue`?
- [ ] **surface 已物化?** `read-screen/capture-pane` 可读?若 `runtime=0/tty=nil`,已执行 `refresh-surfaces` / `reload-config` 后再启动 CC?
- [ ] **🔴 事件流(红线①)?** events 订阅常驻?运行中已对用户发 `📡 cccmux Team` 状态块?`feed.item.received` 分类正确?`Stop`→idle 汇报 + 磁盘校验?断流/heartbeat 丢失有兜底?
- [ ] **可干预展示(红线③)?** 测试/长任务期间是否展示过至少一个干预动作(读屏/追加指令/补 Enter/处理 Feed/收尾)并说明用户可如何介入?
- [ ] **决策点走 Feed?** 没有手工 PTY `send-keys Down→Enter` 导航?架构类未代答?
- [ ] **磁盘校验(Core #12)?** 宣布完成前 `find -newer`/`ls` 确认产物 size>0?
- [ ] **effort?** 地板 high,按信号上抬?`cmux claude-teams --effort ...` 透传?
- [ ] **收尾安全?** `capture-pane` 末行无残留 + 无 pending Feed?阶段确认结束才 `close-workspace`?

## 📦 References

| 文件 | 何时读 |
|---|---|
| `references/cmux-events-monitoring.md` | 事件流订阅、event 清单、lifecycle、capture 兜底、状态推送 |
| `references/cmux-feed-decision-points.md` | Feed 取代 PTY:权限/计划/提问三类决策点处理 |
| `references/occupancy-scan.sh` | 占用检测脚本(读 hook lifecycle) |
| (原 skill)`hermes/claude-code/references/effort-routing.md` | effort 完整体系(底座无关,原样适用) |
| (原 skill)`hermes/claude-code/references/decision-trees.md` | 调不调 CC / 单 CC vs Team(改 tmux→cmux 措辞后适用) |
| (原 skill)`hermes/claude-code/references/agent-team-disk-verification.md` | 磁盘校验(原样适用) |
| (原 skill)`hermes/claude-code/references/cqi-event-emission.md` | CQI 事件吐出(可选用 `Stop` 事件触发 ingest) |

> **未移植(待后续按需补)**:原 skill 的业务 pattern 类 reference(research-agent-team / two-phase-* / cross-project-analysis 等)是任务编排层,底座无关,需要时扫一遍 tmux 命令措辞即可带过来。纯 tmux 的 `tmux-bridge-integration.md` / `teammate-mode-tmux-verified.md` / `cc-session-isolation.md` 已被 cmux 取代,不移植。

---

## §CQI 事件吐出（沿用原 skill,可选增强）

CC 侧每轮把 issue/evolution 以 JSONL 追加写 `/tmp/cc-cqi-events-<session>.jsonl`(`type` 只取 `issue`/`evolution`)。**cmux 增强**:用 `cmux events` 的 `agent.hook.Stop` 事件触发 `mem_ingest.py`,替代旧版「grep `❯` 无 `●` >2min」的会话结束探测。
