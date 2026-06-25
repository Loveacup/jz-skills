---
name: cc-tmux
description: >
  Drive Claude Code via tmux with script-enforced safeguards.
  Thin skill — scripts do the enforcement, prose only tells you which script to call.
  Parallel version to claude-code skill for testing the simplified architecture.
  
  Use when: 调 CC, 用 claude, 拉 CC, delegate to CC, agent team, 重活调 CC.
  Do NOT use for: simple single-tool calls, grammar fixes, non-coding tasks.
type: routine
version: 1.29.0
author: "Hermes Agent + Claude Code (v1.22.0: R9b Topic↔Session 会话复用——新增 scripts/cc-topic-map.sh（JSON 注册表 /tmp/cc-topic-map.json，get/set/unset/unset-by-session/cleanup/list，原子写）；cc-start.sh 加可选 --topic：映射 session 存活+IDLE+心跳新鲜(<2h CC_TOPIC_FRESH_S)→复用(输出 session 名/不新建/不碰锁)，占用/异常态→新建不打断，已死→unset+新建，新建覆盖映射；cc-finish.sh 加 --keep-topic-map(默认)/--clean-topic-map(反查 unset-by-session)，并补清 cc-status-<s>.json。cc-start 所有 tmux 调用过 tmuxc 包装（CC_TOPIC_TMUX 注入 stub）做 hermetic 测试，默认真 tmux 零回归。复用判定：classify==IDLE(叠加 cc-status COMPLETED/IDLE)，TOOL/THINKING/WAITING_AGENTS/EMPTY/SHELL/UNKNOWN 保守新建。踩坑同 P0-2/3：CJK 全角括号紧贴 unbraced $var 在 set -u 吞字节→perl 全量加 ${}。新增 tests/test-topic-map.sh 9/9（5 注册表+unset-by-session+复用/新建/无topic cc-start）；127→136 全绿；test-start 9/9 零回归；真 tmux 复用冒烟通过。| v1.21.0: R8b CC 配置决策自动化（决策指南，零脚本）——新增 references/r8b-config-decision-guide.md：信号→配置映射（effort 地板 high/多文件 xhigh/架构调试写skill max；模型默认 Opus/杂活 Sonnet；Agent Team 按关注点拆/Ultra Code 深调研/Ultrathink 单命令级/Workflow 数天项目）+ 落地通道（effort·模型走 cc-start 参数，模式开关走 context 指示或 Hermes 侧）+ 边界案例 + 「何时问 Alex」（仅未见过任务类型/含红线代价/用量逼近天花板）。SKILL §2「调哪个 effort？」小树系统化增强为完整配置决策（单一入口），Gate Stamp「effort ✓」升级为「配置 ✓」。冲突对齐 PRD（架构→max，非现有树的设计→xhigh）。不新增脚本，cc-start 接口不变；纯文档，测试维持 127/127。| v1.20.0: R2.1 澄清式交接落地（协议+模板，零脚本）——CC 接任务后、执行前多一个「澄清」阶段：Hermes 用增强版 context 模板（6 段：任务简报/相关记忆/知识库路标/Skill 建议/约束与红线/澄清指令）派发 → CC 只读工具查证（WRR/SuperMemory/session_search/OB/CodeGraph）理解任务 → grill 节奏讨论（逐问+带推荐答案+查证优先于提问+矛盾即指出）→ 对齐后才执行。新增 templates/r2.1-context-template.md（复杂任务）+ references/r2.1-clarification-protocol.md（完整协议）；旧 discuss-first-snippet.md 保留为简化版（简单任务，只复述不调工具）。R2.1 模板与 §5.1 委派包分离+交叉引用（模板=上下文富化，委派包=验收契约）。只读约束靠 convention 不靠脚本强制（同节点①）。SKILL §3 节点① 增 R2.1 澄清阶段；新增 §3.x 增强版 context 模板用法。纯文档/模板，零脚本改动，测试维持 127/127。| v1.19.0: wait-marker 事件驱动（P1-2）——cc-wait-marker.sh 的 sleep-2 轮询换成 fswatch -1 事件驱动等待，CLI/语义/退出码契约完全不变。两阶段：文件不存在→短轮询 0.5s 等创建（fswatch 监听不了空路径）→文件存在→fswatch -1 等变更；fswatch 返回后回循环顶复判 is_newer/timeout（不靠 fswatch 退出码区分真事件 vs 被 kill）。超时：macOS 无 timeout → 纯 bash 后台 sleeper kill；预算横跨所有阶段与多次重入（每次算 remaining）。看门狗：每次 fswatch 等待上限 min(remaining, FSW_CAP=3s) 兜底 TOCTOU 漏检（marker 在 is_newer 后、fswatch 起监听前被写 → fswatch 空等不存在的下次事件 → ≤3s 回顶复判，实测修掉真 fswatch 耗满超时的 bug）。优雅降级：fswatch 不在 PATH / CC_WAIT_MODE=fallback → 回原 sleep-2 轮询。CC_WAIT_FSWATCH 注入 stub 做 hermetic 测试。新增 test-wait-marker TC13-15（fswatch 路径/回退/超时包裹，断言 stub 真被调用）12→15；124→127 全绿；12 旧 TC 零回归。| v1.18.0: Hook 成状态权威（P1-1）——架构翻转：hook 事件推→直接写权威状态文件 /tmp/cc-status-<key>.json，bash capture-pane 正则降级为 fallback。新增 hooks/cc-status-writer.sh：所有 hook 追加调用（event 名走参数、不依赖 stdin .hook_event_name），event→state 映射（PreToolUse/PostToolUse→TOOL · Notification→IDLE/含 permission→BLOCKED · UserPromptSubmit→RECEIVED · Stop→COMPLETED · SessionStart→ACTIVE · SessionEnd→GONE …），原子写（temp+mv）+ state_since 同态续接 + seq 自增 + 同步刷心跳；裁断——writer 只负责 status+heartbeat，turn-done/state-log/re-block 仍归现有 hook（不双主）。templates/settings.runtime.json：7 事件各追加 writer command（PreToolUse async）。cc-monitor.sh：心跳新鲜时优先读 cc-status 文件（比 ACTIVE_HOOK 更具体），无则回退旧 fast-path/抓屏。cc-watcher.sh：缩职责——心跳陈旧时对 IDLE/COMPLETED/GONE/BLOCKED/ERROR（静默本属预期）信 hook 不探，仅在途/未知/无 status 才兜底抓屏（注：hook 不写 THINKING，故按状态语义而非字面判定）。CC_STATUS_TMPDIR 注入做 hermetic 测试。新增 tests/test-status-writer.sh 12/12 + test-hooks 21→22 + test-monitor 8→9；110→124 全绿；TDD 先红后绿。| v1.17.0: cc-gc Session 垃圾回收（PRD R9c 堆积检测 + R9d Session GC）——新增 scripts/cc-gc.sh：纯 bash+tmux+文件系统、可独立运行、三模式（scan/gc/suggest）；R9c 残留>3 告警；R9d 4 触发（僵尸=锁目录指向死 session / 完成=turn-done+存活+IDLE / IDLE>2h=心跳陈旧>7200s / 总数>8 超限列最旧）；3 安全规则（绝不自动杀存活 session·活跃 TOOL/THINKING/WAITING_AGENTS 不碰·completed 附产物计数提醒先归档/commit）；裁断——僵尸孤儿文件清理需显式 --apply（默认所有模式只读·干运行），--apply 只删已死 session 的孤儿锁+state，绝不碰活 session；锁真实约定=锁目录+session 文件（非扁平文件）；classify() 移植自 cc-start.sh；CC_GC_TMUX/CC_GC_TMPDIR 注入做 hermetic 测试（stub tmux + fixture 文件，零真实 session）。踩坑同 P0-2：CJK 全角括号紧贴 unbraced $var 在 set -u 下吞字节 → 全量加 ${} 花括号。新增 tests/test-gc.sh 10/10；100→110 全绿；TDD 先红后绿。| v1.16.0: cc-usage 用量管理（PRD R8c）——新增 scripts/cc-usage.sh：pre 模式跑 ccusage 写基线 /tmp/cc-usage-baseline-<session>.json、post 模式读基线算本轮 delta，全程提醒敲 /usage 取真实剩余；诚实边界——ccusage 只有累计无剩余额度，脚本不伪造预测/剩余数字；自带可移植 run_bounded()（macOS 无 timeout → gtimeout/timeout/纯 bash 三级回退）；CC_USAGE_CMD 注入做 hermetic 测试；ccusage 不可用/超时/非 JSON → 降级 exit 0 不打断任务流。修正 references/usage-reporting-pattern.md 的 jq 路径（.totalTokens→.totals.totalTokens，实测核实）。新增 tests/test-usage.sh 4/4；96→100 全绿；TDD 先红后绿。| v1.15.0: cc-monitor 状态金标准——active tail（末6非空行）出现 CC 自渲染的 `esc to interrupt` 即判 BUSY，比 spinner 字符/token/否定推理更可靠；glyph ⏺/● vs ✻ 仍细分 TOOL/THINKING，esc-only（无 glyph）兜底归 THINKING（复用输出分支+冻结时钟）；IDLE 守卫加 `-z ESC`（源头互锁）；esc 不豁免冻结（token+timer 双停仍判冻结，Pitfall #24 防护）；esc 只在 active tail 扫，scrollback 残留不误判。新增 tests/test-monitor-esc.sh 4/4；92→96 全绿；TDD 先红后绿。| v1.13.1: doc 校正——version 字段 1.12.0→1.13.1 对齐实际；references 测试计数 80/80→86/86 修正（test-wait-marker 6→12，补参数校验，实跑核实）。零脚本改动。| v1.13.0: 中间过程可视性——新增 `## 📡 Progress Reporting` 段（6 状态机 emoji 映射 + 4 场景模板 + 信息密度原则）+ references/progress-reporting.md（搬运适配自 claude-code skill）；§3 in-turn wait 增「三段协议」（发任务前讨论/中间状态汇报/完成后讨论，全程 📡 可见）；Pitfall #21「in-turn wait 全程沉默 + 判断环节直接中断」；F1-F4 一致性修复（节点③补 📡 模板④引用 / 新增模板⓪ Pre-Send 理解对齐 / Pitfall #21 症状-原因四反模式对齐三段协议 / 节点① 补 context「先复述」约定 + templates/discuss-first-snippet.md）。纯文档增强，零脚本改动，核心契约不变，测试维持 86/86。| v1.12.0: Turn 内等待（in-turn wait）——新增 scripts/cc-wait-marker.sh（严格 mtime>after 阻塞等 turn-done marker）+ tests/test-wait-marker.sh 6/6；SKILL.md §3 增 in-turn wait 决策树/操作步骤（事件驱动唤醒的紧凑互补）+ Pitfall #20 mtime 比较陷阱；测试 74→80 全绿；TDD 三轮交付。归源时修复 v1.11.0 deploy 热修丢失的 Pitfall #18。| v1.11.0: 事件驱动唤醒——CC 深度调研发现 Hermes 内置 terminal(background/notify_on_complete)→gateway watcher→合成消息注入机制；加 Pitfall #19「被动沉默让用户蒙在鼓里」；加 references/event-driven-wakeup.md（零代码方案+行业共识+不可行清单）。SKILL.md §3 增唤醒模式。| v1.10.0: Phase 3 被动落地 | v1.9.0: Phase 2 事件驱动监控)"
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
| "等 CC 跑完我再看结果" | 📡 汇报是红线。等 turn-done 标记出现 → 立即读产物并汇报。 |
| "任务很简单，不用走完整流程" | 简单 ≠ 可以跳过占用检测。5 秒的脚本值得跑。 |
| "我把 📡 输出总结一下/换个格式" | `cc-monitor.sh` 输出已是 copy-paste-ready。**原样转发**，不要总结、合并、改格式。 |

## 🔀 Decision Tree

```
需要调 CC？
├── Hermes 自己能干？ → 不调 CC
├── 需要拆领域讨论？ → agent team（默认）
├── 任务互不相干？ → 并行多 CC（特例，独立 workdir）
└── 拿不准 → agent team

CC 配置自动决策（R8b · 细则见 references/r8b-config-decision-guide.md）
├── effort（地板 high，绝不更低）
│   ├── 没信号 / 单点 / 机械 → high
│   ├── 多文件 / 审查 / 批量 → xhigh
│   └── 架构 / 根因调试 / 写 skill → max   ⚠️ 实现类即便复杂也优先 high（避冻结 Pitfall #14/16）
├── 模型（默认 Opus）
│   ├── 杂活 / 格式化 / 简单提取 → Sonnet (claude-sonnet-4-6)
│   └── 推理 / 设计 / 调试 / 写作 → Opus (claude-opus-4-8)
└── 模式开关（默认关，按需开）
    ├── Agent Team  → 拆分型任务默认开；按【关注点】拆非按文件；context 指示
    ├── Ultra Code  → 深度调研 / 批量搜索 / 多源交叉验证；context 指示
    ├── Ultrathink  → 某步需深推；context 里单条命令级指示（非全局开关）
    └── Workflow    → 持续数天大型项目才开；Hermes 侧编排
```

> **落地通道**：effort/模型 → `cc-start.sh --effort/--model` 参数；Agent Team/Ultra Code/Ultrathink → **context 里指示 CC**（不是脚本 flag）；Workflow → Hermes 侧。**默认 Hermes 自主决策**，仅「从未见过的任务类型 / 含红线代价 / 用量逼近天花板」才问 Alex。完整信号→配置映射 + 边界案例见 `references/r8b-config-decision-guide.md`。

## 🚦 执行前 Gate Stamp（开 CC 前必须逐项核对）

```
🚦 执行前 Gate Stamp
  该调 CC ✓  重活（多文件/架构/skill/部署）？简单任务 Hermes 自己干。
  配置 ✓  已按任务信号选 effort（地板 high）/ 模型（默认 Opus）/ 模式开关？（R8b 决策，细则 references/r8b-config-decision-guide.md）
  session ✓  独立名 hermes-cc-{agent}-{ts}？禁 --continue？
  占用锁 ✓  cc-start.sh 自动检测，BUSY 时汇报用户等确认。
  session扫描 ✓  cc-start.sh 自动扫全量 tmux，其他活跃 CC → exit 3，用户确认后 --ack-active。
  方案审定 ✓  用户已说"执行吧 / 做吧"？（红线②）
  ── 六项全 ✓ → 开 CC；任一 ✗ → 停，汇报后继续
```

## 🔴 两条红线（违反 = 停 + 补做）

1. **📡 汇报（被动模型 v1.9.0+）**：**不再有定时轮询义务**——hook+watcher 自动维护心跳，沉默不再违规。但 `cc-turn-done-<s>` 标记一出现，必须及时读产物并汇报（漏看 = 违规）；读 `cc-freeze-<s>` 告警则必须响应。任何时候读取 CC 状态/`cc-monitor` 输出，都**原样转发**给用户，不总结、不合并、不改格式。
2. **讨论协议**：用户说"看方案 / 优化方案"= 讨论，不是执行。只有"执行吧 / 拉 CC 改"才动手。

## 📡 Relay Contract（机械执行 — 不是建议）

`cc-monitor.sh` 的 stdout 被 `===📡 BEGIN (relay verbatim)===` 和 `===📡 END===` 包裹。**这两个标记之间的内容 = 用户直接可用的 📡 块。**

**铁律**：
- **原样转发** stdout 到用户可见的 📡 块。不总结、不合并、不改格式。
- 机器元数据去 stderr（`META` 行），不在 relay 范围内。
- 现在 **hook 事件驱动的心脏持续刷新心跳**（PreToolUse/PostToolUse/Notification 写），watcher 守护进程兜底探针（心跳陈旧时 capture-pane 读 THINK_TIME）。Hermes **不再背定时轮询义务**——想知道状态时读 `/tmp/cc-heartbeat-<s>` 和 `/tmp/cc-turn-done-<s>` 标记即可。
- `cc-finish.sh` 仍审计心跳新鲜度（但现在心跳由 hook 自动维护，不会陈旧）。`--force` 语义不变。

## 📡 Progress Reporting（中间过程可视化 — 不只是「开始」和「结束」）

> **解决的问题**：in-turn wait / 事件驱动唤醒下，用户只看到「派了任务」和「拿到产物」，中间 CC 的状态、Hermes 的判断、与 CC 的讨论全是黑盒。每次读 CC 状态 → 用下面的 📡 块汇报，**结构化总览 + Hermes 自主判断**，不要只说一句「CC 在干 X」。
> 搬运并适配自旧 `claude-code` skill，详见 `references/progress-reporting.md`。

### 🔴 长任务持续汇报（红线 — 不可沉默等 turn-done）

**事件驱动唤醒不能替代中间汇报。** 即使用了 `notify_on_complete=true` 的 waiter，CC 可能在 **同一次 session 内花 15-45 分钟做多轮调研/分析**——如果 Hermes 只在 turn-done 后才冒头，用户看到的将是「派了任务」→ 30 分钟沉默 →「做完了」。用户无法区分「在正常工作」和「卡死了（AskUserQuestion / 冻结 / 崩溃）」。

**铁律**：派 CC 长任务（预计 >5 分钟）后，Hermes **不能结束 turn 然后静默等通知**。必须先用 in-turn control loop 校验起步阶段；进入稳态后才可切 checkpoint delegate 或完成唤醒。每次可见状态都要汇报 `cc-monitor` 输出（或 fallback 抓屏）+ 一句 Hermes 判断（「方向正常，继续等」/「发现异常，需干预」）。

**三档选择**：

1. **起步阶段：必须 in-turn control loop**。发 context 后先确认 `cc-send` 已消费、路径/任务理解正确、无 AskUserQuestion/queued input，再放手。
2. **稳态长任务：允许 async checkpoint delegate**。当 CC 已稳定工作但预计还需 10–30 分钟，派一个 one-shot `delegate_task` checkpoint worker：等待 120–180s → 读取 `/tmp/cc-status-*` / heartbeat / turn-done / freeze / `tmux capture-pane` → 返回 verdict → 注入回当前 Telegram 会话。主会话收到后决定继续/干预/收尾。
3. **只要最终产物：可用事件驱动完成唤醒**。仅当上一轮已明确「预计 ≤10 分钟，下轮 turn-done 见」且不需要中途判断时，才可只挂 `notify_on_complete`。

```
正确姿势（长任务）：
  起步 in-turn 校验 → 稳态 checkpoint delegate → 回叫后主会话判断/汇报/干预
  用户每 2-3 分钟看到一条「CC 还在干 X，方向正常」= 安心。

错误姿势（长任务）：
  挂 event-driven wakeup → 结束 turn → 30 分钟沉默 → 用户「？」
  → 用户不知道是卡了还是仍在跑，Hermes 也失去中途干预权。
```

**什么时候可用事件驱动唤醒代替中间汇报**：仅当**上一轮 📡 汇报已告知用户「CC 预计还需 N 分钟，下轮 turn-done 见」且 N ≤ 10**，才可以结束 turn 挂唤醒。否则必须 in-turn wait 持续汇报。

### ⏱️ R4c · async checkpoint delegate（稳态长任务回叫）

当 CC 已经过起步阶段校验（`cc-send` 被消费、路径正确、理解没偏、无 AskUserQuestion/queued input），但预计还需 10–30 分钟时，可以使用 Hermes v0.17 顶层 `delegate_task` 的后台异步模式作为 **one-shot checkpoint worker**：

1. 子 agent 等待 120–180 秒；
2. 只读检查 `/tmp/cc-status-<s>.json`、heartbeat、turn-done、freeze，必要时 `tmux capture-pane -t <s> -p -S -80`；
3. 输出 `OK / DONE / BLOCKED / SUSPICIOUS / ERROR` verdict 后结束；
4. async delegation completion queue 把结果注入回当前 Telegram 会话；
5. 主会话小黄继续判断：继续等、亲自干预、读取产物、或升级给 Alex。

**定位**：checkpoint worker 是「到点巡检员 / 回叫闹钟」，不是自动驾驶。它不得 kill session、不得 C-c、不得替用户选择 AskUserQuestion、不得发语义纠偏指令给 CC；唯一允许的机械修复是明确残留输入时补一次 Enter，或 queued messages 时 Escape 清队列并报告。完整模板见 `references/delegate-task-checkpoint-monitoring.md`。真实验证流程见 `references/r4c-real-smoke-test-pattern.md`：必须启动真实 CC、完成起步 in-turn 校验、派 one-shot checkpoint、读磁盘产物、诚实区分「dispatch 已测」与「async callback 已回注」。

**禁止**：cron 监控 CC、永久循环 delegate、子 agent 高风险干预、起步阶段直接退场、只挂 `notify_on_complete` 后沉默。

**用户催进度 = 最高优先级状态请求**：如果用户中途问「进度？」「你没监控吧？」「怎么还没反应？」之类，不要继续解释背景或等下一轮工具自然返回；立刻读取当前 CC 状态并回一个 📡 块。若 `cc-monitor.sh` 自身报错/崩溃（例如 shell `unbound variable`），**不要把监控失败当成 CC 状态失败**，立即 fallback 到 `tmux capture-pane -t <session> -p -S -60`，根据 pane 的 spinner/tool/write diff/turn-done 现状给用户可见进度。监控工具失败时仍要汇报：「monitor 失败，我已切到 tmux 抓屏」。

### 状态 Emoji 映射（对齐 cc-monitor 6 状态机）

| Emoji | 含义 | cc-monitor 状态 / pane 信号 |
|:--:|------|------|
| ⚡ | CC 工具调用中 | `TOOL` · `⏺/●` |
| 🧠 | CC 思考态 | `THINKING` · `✻/✽/✶/✢/✳` + THINK_TIME 递增 |
| 💤 | CC 空闲 / 可发新指令 | `IDLE` · `❯` 末行为空 |
| ✅ | 完成 | turn-done marker 出现 / 产物已写盘 |
| 🔵 | 进行中 | — |
| 🟡 | 假死（UI 卡但文件已写盘） | `WAITING_AGENTS` + token 冻结但 `ls` 有产出 |
| 🔴 | 真死（无磁盘产出，需接管） | `SHELL` 回落 / 双停 >3min 且产物目录空 |
| 🛡️ | Gate 安全门（正常流程） | cc-finish 7 步门 |
| ❌ | 出错 | pane 出现 `Error/Traceback` |
| ⏳ | 限流 / 等待 | rate limit |

**关键信号识别**：`⏺/●`→调工具 · `❯` 末行为空→空闲/完成 · `✻/✽/✶`→思考态 · `Error/Traceback`→**立即汇报**。
（注意 Pitfall #6 已修但仍有盲区：`cc-monitor` 连报 IDLE+changed=false 时，`tmux capture-pane` 人工确认实况，别误判冻结。）

### 5 种场景模板

**⓪ Pre-Send 理解对齐（发任务后、CC 开干前 — 对应三段协议节点①）**
```
📡 CC [1min · 距上次 12s] 🧠 已读 context
  🧠 CC 复述理解: 要分析 X 测试覆盖率 + 列遗漏 + 建议补测
  └─ Hermes 判断: 理解到位 ✓ 确认开干 / 或 CC 漏了「保存到文件」→ 先纠正再开干
  📊 Token: 2.1k · 🛡️ Gate: 0 次
```

**① 单任务进度**
```
📡 CC [5min · 距上次 22s]
  ⚡ 当前: Write(src/auth/login.ts) — 重构 auth 模块
  ├─ ✅ 已完成: 读完 context + 列出 3 处改点
  └─ 🔵 进行中: 写 login.ts（已 142 行）
  📊 Token: 12.4k · 🛡️ Gate: 0 次
```

**② 异常 / 假死**
```
📡 CC [18min · 距上次 41s] ⚠️
  🟡 假死检测: WAITING_AGENTS + token 2min 不变
  ├─ `ls -la /tmp/cc-output` → 文件已写盘 (2.1KB) → 判定假死非真死
  └─ Hermes 判断: 不 C-c，发 "worker done, continue" 推一把
  📊 Token: 31k · ❌ 0 · 🛡️ Gate: 1 次
```

**③ 等待中（in-turn wait 超时一轮）**
```
📡 CC [9min · 距上次 180s] ⏳
  🧠 当前: THINKING（THINK_TIME 4m13s 仍在递增）→ 非冻结，继续 wait
  └─ Hermes 判断: 方向正常，不干预；本轮 wait 超时 → 再 wait 一轮
  📊 Token: ? (写文件中) · 🛡️ Gate: 0 次
```

**④ 完成**
```
📡 CC [12min] ✅ turn-done
  ✅ 产物: /tmp/cc-coverage.md (86 行) · /tmp/fix.diff (2 处)
  └─ Hermes 判断: 覆盖核心契约，但缺 X 边界 → 拟和 CC 讨论补测
  📊 Token: ~47k · 🛡️ Gate: 1 次
```

### 信息密度原则
- **第 1 行**：总览 = `[耗时 · 距上次抓屏 Xs]` + 整体状态标记（⚠️/⏳/✅）。
- **中间 N 行**：树形详情（`├─ └─`），每行一个 emoji + 关键指标（行数/token/文件）。
- **最后 1 行**：`📊 Token: X.Xk · 🛡️ Gate: N 次`（+ `❌`/`⏳` 计数如有）。
- **每块必含 Hermes 自主判断**：不是转述 CC 在干嘛，而是「我据此判断 → 要不要干预 / 下一步」。
- `cc-monitor.sh` 的 `===📡 BEGIN/END===` 块**原样转发**（见 Relay Contract）；上面的手写块用于「读状态后的判断汇报」，两者不冲突——前者是机器产出，后者是 Hermes 的解读层。

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
  --task "简述任务" \
  --topic 56082         # R9b 可选：同一 Topic 连续任务复用 session（不传=原行为）
```

**R9b 会话复用（v1.22.0，`--topic` 可选）**：传 `--topic <id>` 时，cc-start 启动前查 `scripts/cc-topic-map.sh`（注册表 `/tmp/cc-topic-map.json`）——映射的 session 存活+IDLE+心跳新鲜（<2h）→ **复用**（输出该 session 名、不新建、不碰锁）；被占用（TOOL/THINKING/WAITING_AGENTS）或异常态 → **新建不打断**；已死 → unset 旧映射后新建。新建成功覆盖映射。**不传 `--topic` 行为完全不变**（零回归）。Topic↔Session 映射手动操作用 `cc-topic-map.sh get/set/unset/unset-by-session/cleanup/list`。

脚本自动完成（v1.3）：
- **全量 tmux session 扫描** — 检测所有 hermes-cc-* session 的 6 种状态（SHELL/WAITING_AGENTS/IDLE/TOOL/THINKING/STARTING）。有其他活跃 CC → exit 3，输出扫描报告让用户确认，确认后重跑加 `--ack-active`。
- **僵尸锁清理** — 锁目录在但记录的 session 已死 → 自动 rm，不再永久阻塞。
- **占用锁**（mkdir 原子操作）+ session 命名（含 target，**同分钟碰撞自动加 PID 后缀**）+ HOME=/Users/alexcai + 启动 tmux。
- **锁回滚** — tmux new-session 失败 → 自动释放锁，不 wedge target。

**退出码**：0=OK, 1=环境错误, 2=BUSY（本 target 被存活 session 占用）, 3=其他活跃 CC（需 --ack-active）。

**启动后等 5s 处理 PTY 对话框**（Dialog 2 = `Down → Enter`）。

**CC_TMUX_SESSION 注入 (v1.4)**：`cc-start.sh` 启动 CC 时注入环境变量 `CC_TMUX_SESSION=<tmux-session-name>`，供所有 hook 统一 D-4 键。详见 `hooks/README.md` §2、§4。

**Hook 自动部署 (v1.8.2 / Phase 1)**：`cc-start.sh` 启动行自动追加 `--settings "$SKILL_ROOT/templates/settings.runtime.json"` + 导出 `CC_TMUX_HOOK_DIR`。skill 是 hook 的唯一真源——改模板或脚本后，下个 CC 启动自动生效，零 cp / 零 jq / 零重启。全局 `~/.claude/settings.json` 的 cc-tmux hooks 已摘除（R1 验证为累积触发，保留会双写）。详见 `references/hook-evolution-plan-20260617.md`、`references/cc-hook-facts-v2.1.178-20260617.md`。

### 2. 发送 — `scripts/cc-send.sh`

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session "hermes-cc-default-20260615" \
  --context "/tmp/cc-context-task.md"
```

**⚠️ 不要在 CC 思考态时发消息！** `✻/✽/✶ Composing…` 时发送 → 消息进入队列但不执行 → ❯ 显示 "Press up to edit queued messages"。解决方法：`Escape` 退出队列模式 → 发纯文本命令 "Please read /tmp/…" Enter。

**🔍 发送后存活验证**（v1.3.1 Pitfall #5 教训 → v1.25 已内化进 `cc-send.sh`）：
**v1.25 起 `cc-send.sh` 自带发后回读校验**（经 `cc-send-robust.sh` 的 `send_to_pane`）：发送后回读 pane 底部并分类——残留→补 Enter / queue→Escape 重发 / 已消费→成功，有界重试（默认 4 次），耗尽则 `exit 2` 报人工，**不静默假成功**。所以正常情况下 `✓ Sent` 已是校验过的结果，**无需再手动抓屏补 Enter**。

**仅当 `cc-send.sh` 返回非零（rc=2，重试耗尽）时**，才需人工抓屏诊断卡点：

```bash
tmux capture-pane -t <session> -p -S -5
```

- ❯ 后有文字残留 → Enter 始终未生效（罕见，PTY 异常）→ 手动 `tmux send-keys -t <session> Enter`
- ❯ 后 "Press up to edit queued messages" → `Escape` 后重发（Pitfall #1）
- 看到 `⏺/✢/✻/✳/✶` 或 ❯ 空 → 其实已消费，rc=2 多为回读时序误判，复查一次再判

不经验证直接等 30s 后跑 `cc-monitor.sh` = 可能白等一轮。

### 3. 监控 — 事件驱动 + 守护探针（Phase 2 落地，v1.9.0）

**架构变更**：监控从「Hermes 定时轮询」变为「CC hook 事件推 + watcher 守护进程探针 + Hermes 被动读」。

**Hook 事件驱动心跳**（无需 Hermes 参与）：
- `PreToolUse(async)` / `PostToolUse` 每次工具调用前后刷心跳 → CC 在干活时心跳恒新鲜
- `Notification(idle)` 空闲时写心跳
- `Stop` 在 turn 完成时写 `cc-turn-done-<s>` 标记 → Hermes 的「该去看结果了」信号
- `UserPromptSubmit` / `SessionStart` / `SessionEnd` 生命周期事件记入 state log

**Watcher 守护进程**（cc-start 后台拉起，确定性 shell 循环）：
- 每 N 秒读 `/tmp/cc-heartbeat-<s>` 新鲜度
- 心跳够新 → 什么都不做（hook 在刷，CC 在调工具）
- 心跳陈旧 → 跑一次 `cc-monitor` 探针 → 读 THINK_TIME → 区分「深思」vs「冻结」
- 确认冻结 → 写 `/tmp/cc-freeze-<s>` 告警标记（Hermes 被动检查）
- cc-finish 收尾时 kill watcher PID

**Hermes 的新职责**（被动，无节律义务）：
- 想知道状态 → 读心跳文件
- 想知道「该看结果了吗」→ 读 `cc-turn-done-<s>` 标记（出现=本轮完成）
- 想知道「有没有出事」→ 读 `cc-freeze-<s>` 告警标记

**⚡ 事件驱动唤醒（v1.11.0 新增）** — 从「被动读」升级为「CC 一完成 Hermes 就自动醒」：

Hermes 内置后台进程完成注入机制：派发 CC 的同一个 turn 内，起一个后台子进程阻塞等 `cc-turn-done-<s>` marker（`terminal(background=true, notify_on_complete=true)`），然后 Hermes 正常结束 turn。子进程不占 Hermes 注意力。CC Stop hook 写完 marker → 子进程退出 → gateway watcher（≤5s）自动注入 `[IMPORTANT: Background process completed]` 合成消息到同一个 Telegram 会话 → 触发 Hermes 新 turn → 读产物、汇报、讨论。

**实现只改编排行为，零代码改动**——Hermes gateway 的 `_inject_watch_notification`（`gateway/run.py:11701`）和 `_run_process_watcher`（`:11782`）已完整实现此机制。详见 `references/event-driven-wakeup.md`。

**约束**：必须 `notify_on_complete=true`；派发 CC 的 turn 必须结束（watcher 在 turn 后才 arm）；不要 `process(action=poll/wait/log)` 这个等待子进程（agent 消费完成事件会使 watcher 跳过注入）；检测延迟 ≤5s。

**⏳ Turn 内等待模式（in-turn wait，v1.12.0 新增）** — 事件驱动唤醒的「紧凑互补」：

事件驱动唤醒（上）是**结束 turn → CC 完成 → 注入新 turn**，适合长任务 / 无人值守，但每轮是离散 turn。当你要**紧凑连续干预**（派 CC → 等 → 读 → 立即发下一条 → 再等，全程同一段推理，且用户能 ~1s 插话）时，用 in-turn wait：在**同一 turn 内** `process(action=wait)` 阻塞等 `scripts/cc-wait-marker.sh`，不结束 turn。

**决策树（何时用哪种）**：
```
预计 CC 往返 ≤ ~10  且要紧凑连续干预 / 即时插话  → in-turn wait（本节）
预计往返 > ~10  或单轮很久 / 无人值守           → 事件驱动唤醒（上一节）
拿不准 → 先 in-turn wait 跑前几轮，接近 ~12-16 往返（单 turn max_iterations≈50）时
        主动收尾 → 挂事件驱动唤醒（notify_on_complete=true）接力
```

**📡 三段协议（贯穿 in-turn wait 全程，让中间过程可见 — 见 `## 📡 Progress Reporting`）**：

in-turn wait 不是「写好任务 → send → 静默等 → 拿产物」。每个阶段都要让用户看见 CC 状态 + Hermes 的判断/讨论。三个必经节点：

1. **发任务前讨论（不是写好就 send 执行）**：写好 context → `cc-send` → **等 CC 读完首轮**（一个 wait 周期）→ `capture-pane` 看 CC 对任务的理解 → 用 📡 块汇报「CC 怎么理解的 + Hermes 判断对不对」（模板⓪ Pre-Send 理解对齐）。**若 CC 理解偏了，先和 CC 讨论纠正方案、确认后再让它开干**，不是放任它按错误理解跑。这段讨论过程同样用 📡 格式汇报给用户。
   **⚠️ 关键约定（否则本节点不可操作）**：`cc-send.sh` 只传文件路径、不加工内容，CC 读完 context **默认直接开干**、不会自己停下等讨论。要产生「读完但没动手」的可讨论停顿，**context 末尾必须显式写**：`先复述你对本任务的理解，并停下等我确认，勿直接执行`（可复用 `templates/discuss-first-snippet.md`）。这是 convention，不是脚本强制——同 Pitfall #8「context 末尾加 Save your full response」、§5.1 委派包必含字段。简单任务（决策树判定无需 Pre-Send 讨论）可跳过本约定。
   **🔎 R2.1 澄清式交接（复杂任务的节点① 增强，v1.20.0）**：复杂任务（多文件/架构/调研/有歧义/高风险）不只让 CC「复述理解」，而是让 CC **先用只读工具查证再讨论**——用 `templates/r2.1-context-template.md`（6 段：任务简报/相关记忆/知识库路标/Skill 建议/约束与红线/澄清指令）派发，CC 调 WRR/SuperMemory/`session_search`/OB/CodeGraph 等**只读**工具把理解建立在事实上，再按 grill 节奏（逐问+带推荐答案+查证优先于提问+矛盾即指出）讨论对齐，**达成共识后再发「确认，开始执行」（带委派包 criterion）**。**P0-2 gate 化（v1.23）**：澄清阶段结束后、执行前，跑 `gate-danger.sh --scan-file <CC-transcript> --patterns-file templates/clarify-write-patterns.txt` 验证无写操作——exit 10 是硬门，不可绕过。**简单任务**仍用简化版 `discuss-first-snippet.md`（只复述、不调工具），别把重模板套在琐碎任务上。完整协议见 `references/r2.1-clarification-protocol.md`。

2. **中间状态汇报（wait 超时 ≠ 静默再等）**：`process(action=wait, timeout=180)` 超时返回 → **不是闷头再 wait**，而是：`capture-pane` 抓屏 → 判断 CC 方向（🧠 思考中？⚡ 在调工具？走偏了？）→ 用 📡 块汇报「当前状态 + Hermes 自主判断」→ 再决定 wait 下一轮。**若判断 CC 方向有问题 → 先把判断汇报给用户、等确认，不直接 `C-c` 中断**（在判断环节直接中断 = 违规，见 Pitfall #21）。CC 仍在正常思考（THINK_TIME 递增）时按用户偏好不打断。

3. **完成后讨论（turn-done ≠ 直接汇报转发）**：marker 出现 → 读产物 → **先和 CC 讨论**（产物是否达标、有无遗漏、要不要补）→ 讨论完带上 **Hermes 的判断**、**用 📡 模板④（完成）汇报给用户**。不是把 CC 产物原样丢给用户就完事——Hermes 要先做一层解读和把关。

**操作步骤（start → send → wait-marker → read → loop）**：
```bash
S="hermes-cc-default-<ts>"
# 1. 记录基线 = 发指令前的 marker mtime（无 marker 则 0）—— ⚠️ 必须先记，见 Pitfall #20
AFTER=$(stat -f %m /private/tmp/cc-turn-done-$S 2>/dev/null || echo 0)
# 2. 发任务
bash .../scripts/cc-send.sh --session "$S" --context /tmp/cc-context.md
# 3. 起后台 waiter；Hermes 在同一 turn 内 process(action=wait) 阻塞它
#    （单次 wait ≤180s，循环兜长任务；notify_on_complete=false 见要点）
terminal(command="bash .../scripts/cc-wait-marker.sh --session $S --after $AFTER --timeout 21600",
         background=true, notify_on_complete=false)
process(action="wait", session_id=<上一步 id>, timeout=180)
#   exited → CC 本轮完成；timeout → 再 wait；interrupted → 用户插话，先响应再续
# 4. 读产物 → 决策 → 回到第 1 步（AFTER 更新为刚见到的新 marker mtime）再发下一条
```

**要点**：
- waiter 用 `notify_on_complete=false`——in-turn wait 自己消费完成，**不要**和事件驱动唤醒对同一进程双触发（`process(action=wait)` 退出会标 `_completion_consumed`，反让 gateway 注入被跳过）。
- 单次 `process(action=wait)` ≤180s（`TERMINAL_TIMEOUT` clamp）；超时进程不死 → 再 wait；用户消息 ~1s 中断 wait（真可中断，非傻等满 180s）。
- 单 turn 约 ~12-16 个 CC 往返封顶（`max_iterations≈50`，每个 wait→读→send 周期 ~3-4 次工具调用）；要更多请调 `agent.max_turns`。
- `cc-wait-marker.sh` 用**严格 `mtime > --after`**，每轮必须重记基线 → 见 Pitfall #20。
- 等待机制 (v1.19.0/P1-2)：**fswatch 事件驱动**（文件创建前短轮询 0.5s，存在后 `fswatch -1` 等变更，看门狗 ≤3s 兜底 TOCTOU 漏检）替代 sleep-2 轮询；CLI/语义不变。`fswatch` 不在 PATH 或 `CC_WAIT_MODE=fallback` → 回退原 sleep-2 轮询。

**手动监控**（按需，不再强制定时）：
```bash
# 想看 CC 现在在干嘛时手动跑
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-monitor.sh \
  --session "hermes-cc-default-20260615"
```

**v1.3 机械强制执行**（不依赖 Hermes agent 自觉）：
- **状态权威文件 (P1-1, v1.18.0)** `/tmp/cc-status-<session>.json` — hook 事件**直接写**的权威状态 `{state, state_since, last_event, last_tool, last_tool_since, seq, heartbeat}`，由 `hooks/cc-status-writer.sh` 原子写入（temp+mv）。这是状态的**第一真源**：`cc-monitor.sh` 心跳新鲜时**优先读它**（fast path），bash capture-pane 正则降级为 fallback（仅纯思考冻结这种 hook 看不见的盲区才抓屏）。
- **心跳文件** `/tmp/cc-heartbeat-<session>` — freshness 信号（mtime）。cc-status-writer 与各 hook 同步刷新，`cc-finish.sh` 审计新鲜度。
- **状态日志** `/tmp/cc-state-<session>.log` — JSONL，记录每次状态转移（`changed:true/false`）。`cc-finish.sh` 输出转移摘要。
- **hook 事件 → state**：PreToolUse/PostToolUse→TOOL · Notification→IDLE（含 permission→BLOCKED）· UserPromptSubmit→RECEIVED · Stop→COMPLETED · SessionStart→ACTIVE · SessionEnd→GONE。这些 hook **能第一时间知道** CC 在干什么；capture-pane 的 **6 状态机**（SHELL > WAITING_AGENTS > IDLE > TOOL > THINKING > STARTING）现在只是无 status 文件时的 fallback + 纯思考冻结探测（hook 不写 THINKING，那是它唯一的盲区）。
- **状态转移即时可见** — 每个 📡 块内联 `🔀 PREV → STATE`，随块**原样转发**，不得攒着批量补报。
- **Token 冻结检测** — 基于 THINK_TIME（CC 思考计时器每秒递增）+ TOKENS 双信号：计时器在走 → 不告警；双停 → 真告警。WAITING_AGENTS >120s / THINKING >180s 超时告警。
- **崩溃检测** — CC 回落 shell（无 bypass 横幅 + shell 提示符）→ SHELL 状态告警。

看到的关键信号（已编码在脚本中，但知道这些有助于理解 📡 输出）：
- `⏺/●` 工具调用 · `❯ 空` 空闲/可能完成 · `✻/✳/✶` 思考态
- `Waiting for N background agents` + token 冻结 >120s → 假死告警

**⚠️ 状态检测盲区**（v1.3.1 原始问题 → v1.18.0 已从主路径降级为窄 fallback）：
**历史问题**：早期 `cc-monitor.sh` 的 6 状态机靠 `tmux capture-pane` 抓屏正则判定，会在 CC 的 `✢ Julienning` / `⏺` 工具调用 / `✻ Cogitated` 等阶段全部误报 `IDLE`（changed=false），让 📡 块看不到真实的 TOOL→THINKING→TOOL 转移。

**v1.18.0 起已不再是主路径盲区**：hook 事件**直接写** `/tmp/cc-status-<session>.json` 成为状态第一真源，`cc-monitor.sh` 心跳新鲜时**优先读它**（fast-path），抓屏正则降级为 fallback。PreToolUse/PostToolUse/Notification/Stop 等 hook 第一时间分辨 TOOL/IDLE/COMPLETED，不再依赖抓屏。

**残留盲区只剩一处**：hook **不写 THINKING**——只有当 CC 处于**纯思考态**（无工具调用）**且** status 文件缺失/陈旧时，fallback 抓屏才可能把思考误判为 IDLE。**应对仅限这一窄场景**（status 文件不可用 + 疑似纯思考）才需 `tmux capture-pane` 人工兜底：
- 屏上有 `✢/✻/⏺` → CC 工作中，继续等（token 冻结检测仍是真死的权威判据，见上）
- ❯ 空 + 产物目录已有文件 → CC 可能已完成
- ❯ 空 + 产物目录为空 → CC 未开始或失败，查 pane 历史

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
2. **监控间隙审计** — 心跳 >120s 陈旧 / 从未有心跳 → reject（exit 2，锁不释放、session 不杀）。加 `--force` 可覆盖监控 gap（不能覆盖残留 gate）。（v1.9.0：心跳现在由 hook 事件驱动持续刷新，正常不会陈旧；turn-done 标记存在时心跳陈旧不拒绝。）
3. **状态转移摘要** — 从 JSONL 日志读取：抓屏次数、转移次数、最大间隙、状态序列。
4. **Hard Gate** — 监控未达标 → 拒绝收尾。
5. **产物验证** — `find -L /tmp`（macOS symlink 兼容），0 字节文件标 ⚠️。
6. **释放锁** — `--release-lock`。
7. **杀 session** — `--kill-session`，同步清理心跳 + 状态文件 + `cc-turn-done-<s>` + `cc-freeze-<s>` + `cc-status-<s>.json` + `cc-watch-<s>.log` + watcher PID。**R9b（v1.22.0）**：默认 `--keep-topic-map`（保留 topic 映射，下次同 topic 来发现 session 死→自动 unset+新建）；加 `--clean-topic-map` 则 kill 时反查删该 session 的 topic 映射。

### 维护 · 垃圾回收 — `scripts/cc-gc.sh`（PRD R9c/R9d）

当 tmux 里堆了一堆 `hermes-cc-*` session 不知哪个能杀时跑它。纯 bash+tmux+文件系统，**可独立运行**（不依赖 cc-monitor / iii Engine）。

```bash
bash .../scripts/cc-gc.sh --mode scan      # 全量扫描摘要（默认）
bash .../scripts/cc-gc.sh --mode suggest   # 一行简洁建议
bash .../scripts/cc-gc.sh --mode gc        # 列候选+建议（干运行·只读）
bash .../scripts/cc-gc.sh --mode gc --apply  # 仅清【僵尸孤儿文件】（死 session 的锁+state）
```

**R9c 堆积检测**：残留 `hermes-cc-*` >3 → `heap_warn`。
**R9d 4 触发**（按优先级）：① 僵尸=锁目录指向已死 session ② 完成=turn-done+存活+IDLE ③ IDLE>2h=心跳陈旧 >7200s ④ 总数>8=超限列最旧。
**3 安全规则**：① **绝不自动杀存活 session**——只建议，kill 必须 Alex 确认；② **活跃不碰**——TOOL/THINKING/WAITING_AGENTS 永不入候选（`kind=active-skip`）；③ **先归档后清理**——completed 候选附 `cc-output/<s>/` 产物计数，提醒先确认已归档/commit 再 kill。

> 裁断：`--apply` 是唯一会改文件系统的开关，且**只删已死 session 的孤儿锁+state**（绝不碰活 session）；默认所有模式只读。机器断言行走 stderr（`GCMETA`/`GCITEM`/`GCAPPLY`/`GColdest`），stdout 是 📡 relay 块。锁的真实约定是**锁目录 `/tmp/cc-lock-<target>/` + `session` 文件**（非扁平文件）。

### 狗粮监测 — `scripts/cc-dogfood-report.sh`（v1.27.0）

每次 `cc-finish.sh` 收尾时自动追加一条 JSON 记录到 `/tmp/cc-dogfood.jsonl`（残留/间隙/turn-done/状态序列/退出码）。Hermes 在每次 cc-finish 后跑 `cc-dogfood-report.sh`——累计 ≥5 条新记录时自动输出摩擦摘要，<5 条时静默积累。

```bash
bash .../scripts/cc-dogfood-report.sh             # ≥5 条新记录 → 输出摘要，否则静默
bash .../scripts/cc-dogfood-report.sh --force       # 强制输出（即使 < 阈值）
bash .../scripts/cc-dogfood-report.sh --reset       # 清空计数（标记全部已报）
bash .../scripts/cc-dogfood-report.sh --threshold 3 # 自定义阈值
```

摘要包含：摩擦率、残留触发/监控间隙/危险残留/turn-done 缺失明细、状态序列分布、排查建议。`exit_code==10` 的危险残留记录在 completion audit 前 emit，其 `turn_done_missing=true` 只是代码顺序 artifact，report 端会排除，不计入 Stop hook 缺失。路径可通过 `CC_DOGFOOD_LOG` / `CC_DOGFOOD_STATE` 环境变量覆盖（测试隔离）。

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

> **与 R2.1 增强版 context 模板的关系（v1.20.0）**：复杂任务用 `templates/r2.1-context-template.md`（6 段上下文富化：任务简报/记忆/路标/Skill/红线/澄清指令）做**首轮派发**，与本委派包**分离但配套**——模板负责「让 CC 查证理解、对齐方向」，委派包负责「验收契约」。流程：R2.1 模板派发 → CC 只读查证 + 澄清讨论 → 对齐后**执行阶段那一条 `cc-send` 仍必含委派包 criterion**。两者不合并：模板是上游理解对齐，委派包是下游验收。详见 §3 节点① R2.1 与 `references/r2.1-clarification-protocol.md`。

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
| 12 | （历史）`cc-finish.sh` 拒绝收尾：监控未达标（心跳间隙 >120s） | 旧模型下 Hermes 手动 `capture-pane` 但忘了同时跑 `cc-monitor.sh` 刷心跳。 | **✅ 已被 v1.9.0/Phase 2 消除**：hook（PreToolUse/PostToolUse/Notification）自动刷心跳，手动 `capture-pane` 不再需要补跑 cc-monitor；且 `cc-finish.sh` 现以 `cc-turn-done-<s>` 标记为**完成权威**，心跳新鲜度退为辅助 backstop。只要 Stop hook 正常落地，正常收尾不会再被监控间隙拒绝。 |
| 13 | CC 报告「已完成/N 个测试通过」但**磁盘上没有任何产物** | CC 在长时间的 xhigh 思考后，有时会在**思考态内部形成「已经做过」的幻觉**——它在对话流里描述了完成状态和结果，但从没用 Write/Bash 工具真正写过文件。验证方法：**不要信 CC 说的任何完成声明，必须 `ls -la` / `find` / `stat` 独立取证**。这与 SOUL 委派审核规则「禁止采信执行方自报」完全一致。 | ① 听到「已完成」→ 立刻 `ls -la` 查产物目录 ② 若文件不存在 → `tmux send-keys C-c` 中断 + 「用 Write 工具写文件，不要只说不做」③ 每次验证后汇报文件路径 + size + 行数。**Hermes 永远不代信 CC 的自报，必须亲眼看到磁盘文件**。 |
| 14 | CC xhigh effort 陷入 >5min 思考冻结（token/screen 完全不更新，spinner 静止） | xhigh effort 在工程实现类任务上极度易冻结。CC 不报错、不崩溃、不会自己挣脱。**v1.8.1 冻结检测已改用 THINK_TIME 计时器**：token=? 但计时器每秒递增 → 不误报。双停（计时器+token 全不动 >3min）→ 真告警。见 Pitfall #16。 | ① 发现 THINK_TIME 停止 + token 完全不动 >3min → C-c ② 发 /effort high + 缩小范围 ③ 预防：工程实现类任务地板用 high |
| 15 | CC hook 被误判为不触发，实际产物全堆 unknown/ 目录 | CLAUDE_SESSION_ID 在 hook 执行环境中为空（CC v2.1.178 实测）。所有 hook 脚本用兜底值 → 产物归入 unknown/。验证时按 session 名找产物找不到 → 误判。根因不在 hook 配置，在 session ID 来源。修复：从 hook 的 stdin JSON 中提取 session_id 字段。关键：stdin 只能读一次——必须先 in=$(cat) 保存，再从 $in 中提取 sid 和 tool_response。见 references/cc-hook-deployment-20260617.md。 | ① 不引用 CLAUDE_SESSION_ID 环境变量 ② stdin JSON → jq 取 session_id ③ in=$(cat) 先保存——禁止分两次读 stdin |
| 16 | cc-monitor.sh 在 CC 正常长思考时误报 token 冻结 >3min，打断正在产出的 CC | 冻结检测只看 TOKENS（token 计数字符串）是否变化。CC 写文件/深度思考时 token 显示为 ?（不可读），连续多轮 ? → TOKENS 不变 → 冻结时钟累计 → >180s 误报。但 CC 自己的思考计时器 THINK_TIME（如 4m 13s）每秒递增——这个信号之前被忽略了。修复 (v1.8.1)：冻结重置条件增加 THINK_TIME 变化检测。? 但计时器在走 → 不告警；双停（计时器 + token 都不动）→ 真告警。计时器提取**锚定到 spinner 行**（避免 tool 输出里的随机 `5s`/`3m` 误重置而掩盖真冻结）且**放宽格式**覆盖全部渲染：`2m 3s`（完整）/ `49m ·`（分钟制，本 Pitfall 的 xhigh 形态）/ `37s`（不足 1 分钟）。新测试 tests/test-monitor-freeze.sh 6/6 覆盖。 | ① token 在涨 / spinner 在动 / pane 有新输出 → CC 活跃，不要 C-c ② 判准是双停（THINK_TIME + TOKENS 全不动 >3min），不是时间长 ③ 用户明确要求「只要他持续在思考，就先别干预他」 |
| 17 | Hermes 反复违反「每 30-60s 跑 cc-monitor.sh」的轮询纪律，沉默 >2min、心跳间隙 >120s、cc-finish 拒绝收尾 | **根因是架构性的，不是 prompt 能修的**：LLM 不擅长定时重复执行——长思考中一定会忘。 | **✅ 已修复 (v1.9.0 / Phase 2)**：节律义务从 LLM 搬到 hook 事件驱动 + watcher 守护进程 + turn-done 标记——Hermes 只需被动读文件。详见 `references/hook-evolution-plan-20260617.md`。 |
| 18 | `cc-send.sh` 返回 `✓ Sent` 且消息出现在 ❯ 后，但 CC 长时间不处理——消息残留 >8s 无 spinner | Pitfall #5 的特化高频形态：Enter 未生效时消息**原样显示**在 ❯ 后而非被 CC 消化。Hermes 可能误以为 CC「在思考这段指令」，实际 CC 根本没开始。**2026-06-17 单 session 触发 2+ 次。** | **加固存活验证**：`cc-send.sh` 后等 4-6s 抓屏——① 若 ❯ 后有残留文字且无 spinner（✻/✽/✶/⏺）→ Enter 未生效，**立即** `tmux send-keys Enter`；② 5s 后仍残留 → 再补一次 Enter。**宁多补一次 Enter 不白等一轮。** 存活验证失败时不要假定「CC 会自己消化」——它不会。 |
| 19 | 用户问「你在轮巡吗？Hook 没有效果吗？已经 20 分钟了，一点反应都没有」 | **被动模型的结构性缺陷**：Hermes 不轮询、不主动查 turn-done 标记，turn-done 早已写好但 Hermes 不知道——用户在等 Hermes 汇报，Hermes 在等用户发消息，双方互等。CC 已经完成 20 分钟了但没人知道。**2026-06-17 实发——turn-done 09:41 写好，用户 09:51 质问才被发现。** | **根治**：用事件驱动唤醒（`terminal(background=true, notify_on_complete=true)` 后台子进程等 marker）替代纯被动等待——让 CC 完成时自动触发 Hermes 新 turn，而不是等用户发现沉默再问。详见 `references/event-driven-wakeup.md`。**在此之前**：用户发消息时立刻查 turn-done 标记，不要假定「还没完成」。
| 20 | in-turn wait 循环里第二轮 `cc-wait-marker.sh` 立即返回旧 marker，没等到 CC 新一轮完成 | **mtime 比较陷阱**：marker 是同一个文件 `/private/tmp/cc-turn-done-<s>`，CC 每轮 Stop hook 覆盖它（mtime 刷新）。若第二轮仍复用上一轮的 `--after` 基线，waiter 看到的 marker（mtime=上一轮）已 > 旧基线 → 立即 exit 0，把**上一轮的旧结果**误判成本轮完成。 | **每轮发指令前重记基线**：`AFTER=$(stat -f %m /private/tmp/cc-turn-done-$S 2>/dev/null \|\| echo 0)` → `cc-send` → `cc-wait-marker.sh --after $AFTER`。脚本用**严格 `mtime > after`**，基线必须是「你上一轮 wait 返回时那一版 marker 的 mtime」，不能复用更早的值。`--after 0` 仅第一轮（尚无任何 marker）用。覆盖测试 `tests/test-wait-marker.sh`（Test 3/12）。 |
| 21 | in-turn wait 全程沉默——派了 CC 就闷头 `process(action=wait)`，wait 超时就再 wait，直到 turn-done 才冒头。用户只看到「开始」和「结束」，看不到 CC 状态、Hermes 判断、和 CC 的讨论。**或反过来**：判断 CC 走偏后**不讨论直接 `C-c`**，事后才说「我中断了它」。**同类还包括**：写好任务就 send、不等 CC 读完不看理解就放任跑；turn-done 后把产物原样转发给用户、不讨论不把关。 | 「等一下就好了 / 让它先跑」**不是汇报**——它把中间过程变黑盒。**四个反模式（一一对应三段协议节点）**：① 写好任务直接 send、不等读完/不看理解就放任跑（节点①）；② wait 超时静默再等，用户以为卡死（节点②）；③ 在判断环节直接中断，绕过用户、可能误杀正常思考的 CC（节点②）；④ turn-done 后把产物原样转发给用户、不讨论不把关（节点③）。 | **三段协议（见 §3 in-turn wait）**：① 发任务前等 CC 读完 → 抓屏看理解 → 偏了先讨论再开干；② wait 超时 → 抓屏 + 📡 块汇报状态与判断，**不静默**；③ 判断走偏 → **先汇报用户等确认，再 `C-c`**，不在判断环节直接中断。每次读状态都用 📡 块（`## 📡 Progress Reporting`）输出「总览 + 树形详情 + Hermes 自主判断」。CC 正常思考（THINK_TIME 递增）时按用户偏好不打断。 |
| 22 | CC 弹出 AskUserQuestion 交互式选择题进入 BLOCKED 状态，Hermes 没及时发现 → 用户问「你在巡吗？」**变种**：选项超时消失后，Hermes 发送的确认消息在 ❯ 排队但 CC 不消费——看起来 IDLE，实际在等输入。**2026-06-24 累计触发 4 次，最严重一次排队 30+ 分钟。** | xhigh effort + Opus 在实现类任务上易触发深度思考 → 问出方案选择问题 → 选项超时消失后 CC ❯ 空闲但不再继续。变种根因：multi-select 被 dismiss 后，CC 停在等待输入态但无任何视觉提示，Hermes 的确认消息在 ❯ 排队不执行。 | **主动巡检**：等 turn-done 期间每 2-3min 查 `cc-status` 的 state + `capture-pane` 看 ❯ 是否有残留文字。`BLOCKED` 或 ❯有残留 → 立即响应。解除：① 选项还在 → `send-keys \"<n>\" Enter`；② 已消失 → `Escape` + 纯文本告知；③ **❯ 有残留排队 → 直接 `send-keys Enter`**（最常见、最高频、最简单）。详见 `references/cc-askuserquestion-unblock-pattern.md`。**预防**：实现类任务用 high（非 xhigh）；context 末尾加「禁用 AskUserQuestion，有决策点直接用纯文本提问」。 |
| 23 | `grep -iEf pattern-file.txt` 把**空行和注释行**当匹配模式 → 空行（空 ERE）= 匹配一切 → 无害输入被误判为危险残留 | `grep -f` 不跳过空行/注释行——文件里的每一行都是 ERE。空行 = 空正则 = 匹配任何输入。`# 这是一条注释` 也是 ERE，`#` 是字面量（ERE 无注释语法），虽通常不匹配但语义错误。**2026-06-24 实发**：`residue-danger-patterns.txt` 行 8 空行导致 `ls -la /tmp` 被误判 exit 10。 | 用 `<()` process substitution 过滤：`grep -iEf <(grep -v '^[[:space:]]*#' "$FILE" \| grep -v '^[[:space:]]*$')`。**注释行和空行必须显式过滤**——不要依赖 grep 的 `-E` 或 `-f` 替你跳过。 |
| 24 | `cc-finish.sh` 检出 ❯ 非危险残留，但 `C-u` / `Escape+C-u` / `C-a C-k` 仍清不掉输入框 | Claude TUI 输入框不一定接受 tmux 发来的 readline 清行键；有时残留是 TUI 内部状态而不是普通 shell 行缓冲。2026-06-25 真实任务中多种清行组合均未生效。 | **绝不按 Enter**。先汇报「残留清除失败，未执行」，保留 session 证据；只可释放锁/记录 dogfood，不要假设机械清行成功。若必须继续复用该 session，先新建/重启或让用户明确确认处置策略。 |

### 额外红线：路径纠偏与接管边界（2026-06-25 实发）

> 详见 `references/cc-delegation-path-and-takeover-pitfall-20260625.md`。

当 CC 读错目录、卡住或产物不对时，**先审 delegator 的委派包，不要把问题简化成“CC 不可信”**。路径敏感任务（Obsidian vault、monorepo、同名旧目录、多 profile）必须在首轮抓屏里核对 CC 实际读取的绝对路径；发现读错目录立即纠偏，不要只看“它在读文件/思考”。

如果用户明确要求“让 CC 修改/让 CC 直接改”，Hermes 不得在 CC 失败后擅自接管写目标文件。正确流程是：暂停/停止 CC → 报告真实状态 → 修正委派包 → 重启/继续 CC；只有用户明确同意“改由你接管”后，Hermes 才能直接写文件。

如果承诺“每 2-3 分钟报进度”，必须用 in-turn wait 循环落实；不能只挂 `notify_on_complete` 后结束 turn，让用户继续追问进度。

### 下游项目文档同步（cc-tmux 更新后）

> 详见 `references/downstream-doc-sync-after-skill-update-20260625.md`。

当 cc-tmux skill / OB 文档在另一个 topic 更新后，依赖它的项目文档（如 agent-hub）必须同步更新**边界语言**：cc-tmux 负责单 CC session 裸金属编排；下游 hub 只负责多 session / 多 CLI / 多机的 Catalog、NATS 转发、生命周期与事件收敛。先搜索旧版本、旧监控口径、旧桥接机制，再 patch PRD/架构/AGENTS/Spec。不要只改版本号，也不要保留已定案的旧矛盾作为 warning。

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
- [ ] **（新）** 发完任务后，等 `cc-turn-done-<s>` 标记出现即读产物——不再盲目轮询
- [ ] **（新）** 是否检查过 `cc-freeze-<s>` 告警标记？（被动读，无节律义务）
- [ ] turn-done 标记出现后，是否**立刻**读产物并汇报？（这是新的及时性红线——不是定时轮询，而是事件响应）
- [ ] 🔀 状态转移是否即时可见、随 📡 块转发？（非事后补报）
- [ ] 结束前是否跑了 `cc-finish.sh`？（检查 ❯ 残留 + 监控间隙 + 释放锁 + 清理 watcher + turn-done）
- [ ] 产物是否经磁盘校验（`ls -la` 确认 size > 0）？
- [ ] `cc-finish.sh` 是否通过（exit 0）？（exit 2 = 监控未达标被拒）

**Every box must honestly pass. If unchecked, go back.**

---

> 📦 **设计依据**：`references/design-principles.md`（6 原则 + 4 组件架构）
> 💿 **Claude CLI 安装**：`references/claude-cli-install.md`（npm 安装 + 验证 + PATH 排障）
> 🔍 **审核 Agent 槽位**：`references/audit-agent-slot-design-20260616.md`（通用 audit 槽位契约 + 独立性四档 + 灰度扩展）
> ⚖️ **三问题裁决**：`references/audit-three-issue-verdict-20260616.md`（去 regent 化 / 切 auditor 身份机制 / 脚本物理落点）
> 🔍 **审核 gate 脚本**：`scripts/gate/`（基质无关红线：gate-verify / gate-danger / gate-counter，零 tmux 耦合，遇第 2 消费者提升为独立 skill），见 5.0 / 5.5。
> 📋 **Phase 分解**：`references/phases.md`（4 phase × ~7 义务）
> 📊 **合规度量**：`scripts/eval-compliance.sh`（机器判定，同任务对比 v4 vs cc-tmux）
> 🐛 **CC Hook Bug Registry**：`references/cc-hook-bug-registry.md`（4 个已知开放 bug）
> 🐶 **狗粮监测设计**：`references/dogfood-design-notes.md`（每次使用回写 + 累积触发摘要，待实现）
> 🧠 **CC 写作任务超长思考**：`references/cc-overthinking-writing-tasks.md`（xhigh 在文档任务上易冻结，恢复 Ctrl+C→重定向，预防用 high）
> 📊 **V4 对比**：`references/v4-comparison-findings.md`（功能矩阵 + 尺寸对比 + 使用场景）
> 🔄 **多轮 CC 设计迭代**：`references/multi-round-design-pattern.md`（4 轮模式：设计→优化→产出→终审）
> 🔗 **源仓库**：`~/code/jz-skills/hermes/cc-tmux/`
> 📡 **Relay Contract**：`references/relay-contract.md`（机械执行细则 + 反模式）
> 📡 **Progress Reporting**：`references/progress-reporting.md`（中间过程可视化：6 状态机 emoji 映射 + 4 场景模板 + 信息密度原则 + in-turn wait 三段协议对应；搬运适配自 claude-code skill）
> 📝 **CC 文档修改委派坑点**：`references/cc-doc-edit-delegation-pitfalls-20260625.md`（context 写好但未启动、同名目录读错、mtime 验收、用户指定 CC 时 Hermes 不越权代写）
> 🔄 **下游文档同步**：`references/downstream-doc-sync-after-skill-update-20260625.md`（cc-tmux 更新后同步 agent-hub 等依赖项目：改边界语言、清旧口径、同步 PRD/架构/AGENTS/Spec）
> ⏱️ **delegate_task checkpoint 巡检**：`references/delegate-task-checkpoint-monitoring.md`（Hermes v0.17 异步 delegation 作为 one-shot 回叫闹钟；起步 in-turn control、稳态 checkpoint、异常主会话接管）
> 🧪 **R4c 真实烟测流程**：`references/r4c-real-smoke-test-pattern.md`（真实 CC 只读 smoke test：起步校验、残留输入恢复、checkpoint dispatch、磁盘产物验证、runtime/source drift 对齐、monitor 崩溃 fallback）
> 🚑 **进度催问与监控降级**：`references/progress-request-and-monitor-fallback.md`（用户催进度时立即汇报；`cc-monitor.sh` 失败时 fallback 到 `tmux capture-pane`，不可静默）
> 🧪 **测试复现**：`references/test-repro-2026-06-16.md`（cc-send Enter 未生效 + monitor 盲区复现步骤）
> 🔀 **路由对照**：`references/hermes-deck-routing-comparison.md`（hermes-deck Primer + AgentRouting 块 vs cc-tmux 长会话模型对照分析）
> 🔍 **CC 审核模式**：`references/cc-audit-cross-evaluation-pattern.md`（用 CC 做多文档交叉审核：典型发现层级、常见误判、输出格式）
> 📦 **Obsidian 重构**：`references/obsidian-restructuring-pattern.md`（CC 驱动的 vault 文件重组：批量重命名 + 合并 + wikilink 全局更新 + 库外断链修复 + perl 编码坑）
> 🚀 **Ultracode Dynamic Workflow**：`references/ultracode-workflow-pattern.md`（用 CC 原生 ultracode 模式做 13-agent 并行深度调研的完整流程：触发方式、编排设计、监控、产出验收、适用/不适用场景）
> 📊 **用量汇报**：`references/usage-reporting-pattern.md`（CC 无法自理 `/usage` 的根因 + 方案 3 实现细节 + npx ccusage 使用）
> 📋 **优化方案（2026-06-16）**：Obsidian `02-Plan&CQI/cc-tmux优化方案_20260616.md`（ultracode 13-agent 深度调研产出：P0 脚本修复 + P1 CC hook 混合架构 + 基质无关内核收敛 + CQI 闭环 + 6 决策点）
> 🧪 **TDD 测试套件(21/21 文件, 203/203 断言, 2026-06-25 实跑核实)**
> 🪝 **CC Hook 脚本**：`hooks/cc-posttool.sh`（§3.3 PostToolUse 归档）· `hooks/cc-stop-check.sh`（§3.7 Stop 软门）· `templates/settings.runtime.json`（§3.4/3.5 Notification+SessionStart 内联 + 两脚本路径经 `$CC_TMUX_HOOK_DIR` 自定位，**单一事实源**，由 cc-start `--settings` 会话级注入；stdin-jq + D-4 键统一 `${CC_TMUX_SESSION:-<stdin session_id>}`；**全局 hooks 已摘**避免 R1 双触发）· `hooks/README.md`（§3 `--settings` 部署 + D-4 + smoke 清单）
> 🧪 **测试结果记录**：`references/test-results-33of33-20260617.md`（历史文件名；现为 **203/203**，含 D-4 键统一 + 冻结检测修复 + dogfood exit10 false-positive 排除 + R4c smoke 流程记录）
> 🔬 **Hook 部署验证 (2026-06-17)**：`references/cc-hook-deployment-20260617.md`（部署流程 · CLAUDE_SESSION_ID 空值根因 · stdin 消费陷阱 · 验证方法 · 修复记录）
> 📋 **状态审计 (2026-06-17)**：Obsidian `88-审计/cc-tmux 状态审计 20260617.md`（CC 自主审计：Readiness 6→8 · D-4 键分裂 · 测试失真 · 三步修复落地全记录）
> 🚀 **Hook 演进方案 (2026-06-17)**：`references/hook-evolution-plan-20260617.md`（部署自动化 `--settings` 注入 + 事件驱动监控混合架构 + 4 阶段路线图，Pitfall #17 治本方案）
> 🔬 **Hook 实测事实表 (2026-06-17)**：`references/cc-hook-facts-v2.1.178-20260617.md`（Phase 0 冒烟：R1 ACCUMULATE/R2 PASS/R3 async可靠/R4 每调用触发/R5 事件全过；CLI 事实 + 未验证清单 + 月度复查节奏）
> ⚡ **事件驱动唤醒 (2026-06-17)**：`references/event-driven-wakeup.md`（CC 深度调研：Hermes 内置后台进程→gateway watcher→合成消息注入机制；零代码改动唤醒方案；行业共识验证；不可行方案清单）
> 🧩 **CC Nohup 后台编排模式**：`references/cc-nohup-orchestration-pattern.md`（CC 写脚本→nohup 后台跑→等待器监听 REPORT→醒来消化；适用独立批量验证，避开 xhigh 长思考冻结）
