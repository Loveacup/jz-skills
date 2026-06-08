# Claude Code Skill — Changelog

> All notable changes to `claude-code` skill for Hermes Agent.

---

## v4.2.0 (2026-06-08) — Salience slim：主体 685→446 行，长表/树/规格下沉 references/

> 根因：SKILL.md 膨胀到 685 行，healthcheck T2（≤450 行 salience 门）持续 FAIL——主体被完整坑表、红旗反驳表、Core Rules 全文、ASCII 决策树、60+ 条 References 目录、CQI 完整规格撑爆，高频规则被淹没。本版按 progressive-disclosure 把 block 正文下沉到 references/，主体只留高频骨架 + 指针。**纯结构搬移，零行为变更、零内容丢失。**

### Changed（下沉，主体只留指针 + 高频骨架）
- **⚠️ Critical Pitfalls** — 完整 39 条坑表 → `references/critical-pitfalls-table.md`，主体留最高频 3 坑（#1/#2/#7）
- **🚨 Red Flags** — 完整 16 条「借口→反驳」表 → `references/red-flags-table.md`，主体留 3 条
- **⚡ Core Rules** — 完整 #0–#12 → `references/core-rules-detail.md`，主体留高频骨架（#0/#1/#2/#4/#9/#11/#12）
- **🔀 Decision Tree** — 三棵 ASCII 树 + 单CC/Team/并行对照表 → `references/decision-trees.md`，主体留选型口诀
- **🤝 占用检测脚本** — `for s in ...` 扫描脚本 → `references/occupancy-scan.sh`（唯一权威），主体留调用
- **📦 References** — 60+ 条目录 → `references/index.md`，主体留最常用入口
- **§CQI 事件吐出** — 完整规格（字段/自判/三步链/cron）→ `references/cqi-event-emission.md`，主体留 type 枚举铁律
- **📡 Progress Reporting** — 三段冗余 blockquote 压缩为 2 段（红线① 复述 + 磁盘验证/输出定位指针）
- **🔌 MCP Bridges** — Claude Octopus + tmux-bridge 两小节合并为一节

### Added
- 7 个新 reference 文件（上述下沉目标）+ `references/index.md` 总索引
- `references/healthcheck-tdd-loop.md` 从运行端导回源仓库（DP1 de-fork，消除 T5 孤儿）

### Metrics
- SKILL.md 685 → 446 行（−239，−35%），healthcheck T2 由 FAIL → PASS
- healthcheck 7/7 自动测试全绿（T1 md5 / T5 file-set 经 `cp` 同步后一致，70 文件两端相同）
- 红线①/②、Gate Stamp、§0、canonical 段（patrol / Final Input-Line Gate / tmux-bridge / drift hook）全部保留在主体

---

## v4.1.1 (2026-06-04) — 三路合并去分叉 + CQI 诊断吸收（Phase 0）

> 根因：v4.1.0 红线宪法 commit 进源仓库却**从未部署到运行端**——源(524)/运行(647)双向分叉、同标 `4.1.0` 但 md5 不一致（CQI 事件 #3）。2026-06-04 的监控违规实为**加载端缺红线①**，非 CC 不听话。本版三路合并去分叉 + 落地 CQI 诊断改进。

### Fixed（去分叉）
- **双向分叉消除** — 以源端红线宪法/Gate Stamp/effort 下沉为主干，吸收运行端「连续推进模式 + Pitfall #20/★33」，统一 v4.1.1，`cp` 后两端 md5 一致
- **RA-03 Pitfall 编号** — ★30 去重（曾重复 2 次）、修 ★38 markdown（`\n` 字面量）、★33 排到数字顺序位、表头注明 #16/#17/#29/#32/#34/#35 为历史废弃不重用

### Added（CQI 诊断吸收）
- **§0 通用性声明** — 本 skill 被所有 Hermes agent 加载（不限小黄）；加载者=Hermes / 被驱动方=CC / CC 不读此 skill（父皇纠正）
- **§0 read hook 防漂移** — 加载时校验 runtime md5 vs 源 provenance，取代纸面化漂移 cron
- **🔗 跨 skill 规格透传（RA-08）** — 调另一 skill 时强制把其核心验收标准原样写入 CC context
- **🧠 任务记忆同步（RA-09）** — 任务交接时把 Hermes 侧相关记忆摘要写入 CC context
- **Core Rule #12 完成前磁盘一致性校验（RA-06）** — 宣布完成前 `find -newer`/`ls` 确认文件真实落盘
- **Session GC（RA-12）** — 残留 session 按命名/age/假空闲三条回收，阶段未结束不杀

### Changed
- **Gate Stamp 4→5 项** — 增「该调 CC？重活别自己扛」（2026-06-03 教训）
- **讨论协议** — 加 #7 思考保护（token 增长=活跃思考不打断，仅冻结 >3min 才中断，RA-07）+ 讨论简报强制产物段
- **watchdog 移除** — 删「未监控后装 no-agent watchdog」指令，改为 Hermes 自身持续轮巡（父皇校准：不建 watchdog）
- **Pitfalls 富集** — 补 ★28/★36/★37/★38（含「context 未交代 skill 架构背景致 CC 误解角色」）
- **Progress Reporting 增强** — 加「capture-pane=用户可见事件」「TG 工具调用≠可见」「投递失败也算未汇报」硬规则

### Metrics
- 行数：源 524 / 运行 647（分叉）→ 统一 **600**（≤600 阈值）；两端 md5 一致
- 红线维持 **2 条**（防 MUST 通胀；effort/session/占用/调 CC 留 Gate Stamp）

---

## v4.1.0 (2026-06-01) — Instruction-Following Enforcement: 红线宪法 + Gate Stamp

> 聚焦「指令遵循」的一轮优化。根因：旧 skill 规则全但约束力弱——MUST 通货膨胀 + 软 checklist + salience 与违规频率倒挂，agent 能合理化跳过 📡 汇报与讨论协议。经 3-lens 审查（规则强制力 / 可检测性 / 简洁vs完整）+ 4 轮 Hermes↔CC 讨论收口。

### Added
- **🔴 不可协商红线（Non-Negotiable）置顶区** — 仅 **2 条**红线（① 📡 汇报、② 讨论协议「优化 = 讨论非执行」）。分级声明消解 MUST 通货膨胀（红线 = 违反即停+用户介入，其余皆 best practice）。每条配**反合理化微表**（per-rule「借口→为什么错」），封死「空闲不用报 / 模板太繁 / 用户说优化=让我改」
- **🚦 执行前 Gate Stamp** — 开 team / 改文件前必打印硬门签章（方案审定 / effort / session 隔离 / 占用检测），任一 ✗ 即阻断执行。借鉴 china-legal-optimized output-gate「五项硬检查，任一不过即 block」，软 checklist → 硬门
- **Core Rule #11 违规自修正协议** — 发现违规立即 (1) 显式标记「⚠️ 刚违反红线 X」(2) 当轮补做 (3) 禁止「下轮改」口头了事
- **`references/effort-routing.md`** 新建 — 接收主体下沉的 effort 完整体系（五级表 / 三档路由表 / 自检决策树 / 实战配置 / 成本换算 / `/effort` 切换陷阱）

### Changed
- **📡 汇报硬绑定** — 「持续汇报」抽象要求改为机械配对「`capture-pane` 与 📡 **1:1 成对**，缺一即违规」；模板头加 `[距上次 Xs]`，>120s 自标 `⏰超时`；Rule #9 标注为红线① 执行细则
- **effort 路由下沉** — `## Model & Effort` 从 ~110 行精简到 ~14 行（地板 high + 一句话路由 + 启动即定档），详细体系移至 `references/effort-routing.md`
- **占用检测去重** — Rule #0 删重复 bash 脚本，唯一权威保留在 `§ Multi-Agent Coordination Protocol`
- **Verification Checklist** — 重定位为「事后总检」，删与 Gate Stamp 重复的前置项（占用检测 / session 隔离 / workdir），加事前硬门指引；Progress 项升级为红线①

### Design
- **红线 vs Gate Stamp 零重叠分流**：红线管「agent 主动跳过的行为铁律」（📡 / 讨论），Gate Stamp 管「技术陷阱误判的前置状态」（session / 占用 / effort）。占用检测不进红线（已 4 处强化 + 本质是假空闲被骗而非主动跳过）
- **净行数**：effort 下沉（−96）+ 占用去重（−8）+ 红线/Gate/微表/自修正新增（+40）= **净 −64**，主体 588 → 524（实测）

---

## v4.0.0 (2026-06-02) — Discussion Protocol + Debt Cleanup + Architecture

### Added
- **🔥 讨论协议章节（Discussion Protocol）** — Hermes↔CC 双向拷问：grill pattern（逐问 / 带推荐答案 / 先查事实）+ 多轮辩证立场更新 + 共识终止条件 + 讨论简报模板。吸收自 `mattpocock/skills` 的 grill-me/grill-with-docs 与 Du et al. 2023 multiagent debate、Wang et al. 2023 self-consistency
- **References 收编** — home-and-sandbox / cc-agent-team-document-audit / hermes-research-to-cc-strategic-insight / claude-octopus-upstream / literary-rewrite-pattern 5 个孤儿纳入 References 表

### Changed
- **🏗️ 废除共享 longterm session** — Decision Tree、Session 命名表、Core Rule #1、决策矩阵全面改为「默认每次新建独立 `hermes-cc-{agent}-{ts}`，不复用」；跨会话上下文走 `/tmp/cc-context-{task}.md`。占用检测保留作安全网
- **占用检测统一** — Rule #0 与 Multi-Agent 段统一为含 `✻/✶/✽/✳` 思考态的单一权威逻辑
- **Pitfall 编号重排** — 消除重复的两个 ★23（「自动恢复旧会话」重编为 #27），#18–#27 连续无重复

### Fixed
- **Pitfall #2 HOME 回归** — 修正 `HOME=~`→`HOME=/Users/alexcai`（字面绝对路径，profile override 下 `~` 会失效），并标注 sync 脱敏豁免
- **2 个坏链接** — 新建 `post-deploy-verification-pattern.md` + `cc-agent-team-parallel-implementation.md`
- **teammate-mode 去重** — 删除孤儿 `teammate-mode-verified.md`（`tmux-verified` 子集）

### Execution
- CC agent team：2 个 background subagent（搜索 grill+论文 / references 清债，sonnet）+ leader 串行改 SKILL.md（opus）。按关注点拆，SKILL.md 单文件由 leader 独占避免写冲突

---

## v3.5.2 (2026-06-01) — Session Hijack + Permission Form Pitfalls

### Added
- **Pitfall #25** — Session 被另一 agent 的 /clear 劫持：共享 session 竞争写入导致任务覆盖，修复方案：专用 session 名 `hermes-cc-{task}`
- **Pitfall #26** — CC 权限表单 tmux 不可靠：复选框/单选框 Tab/Enter/Down 失效，解法：Escape + 纯文本决策消息
- **Pitfall #27** — CC 自动恢复旧会话：workdir 有 `.claude/` 时 `claude` 默认 resume，需 `--new-session` 干净启动
- **`references/post-deploy-verification-pattern.md`** — 新建：部署后 Python subprocess curl 验证模式（POST→sleep→GET→检查 artifact 字段）+ token 脱敏陷阱 + artifact dict 写入规范
- **`references/cc-agent-team-parallel-implementation.md`** — 新建：并行实施模式 Leader-wiring 策略、context 文件模板、schema 验证集成

### Changed
- **Pitfall #16** — 压缩为交叉引用「见 #9」，消除与 #9 的重复
- **Pitfall #17** — 压缩为交叉引用「见 #11」，消除与 #11 的重复

---

## v3.5.1 (2026-06-01) — Fake-Idle Detection Enhancement

### Added
- **Pitfall #24** — CC 假空闲：`❯` 可见但深度思考中（`✻/✶/✽/✳` 思考态）；与 #25 组成完整劫持攻击链

### Changed
- **Pitfall #18** 占用检测增强 — 除 `●` 工具调用检测外，新增 `✻/✶/✽/✳/Sublimating/Zigzagging/Billowing/…` 思考态检测；完整空闲条件扩展为 5 项同时满足

---

## v3.5.0 (2026-05-31) — Effort Routing + Agent Team Enhancement

### Added
- **🧭 Smart Effort Routing** — signal-based decision tree replacing simple "策略建议"; default floor = `high`
- **🧩 Agent Count & Splitting Principles** — "let CC decide count, break by concern not by file"
- **🚦 Execution Mode Selection** — single CC vs Agent Team vs parallel multi-CC decision table
- **⚙️ Effort Practical Config** — CLI flag mapping, `/effort` pitfalls, cost ratios (max≈3×high)

### Changed
- **Core Rule #2** enhanced — agent count self-determined, concern-based splitting
- **`## 🧠 Model & Effort Level`** section restructured: startup → five levels → in-session switch → smart routing → practical config

### Execution
- 3 parallel agents drafting independent content blocks → Leader serialized integration to avoid file conflicts
- Opus 4.8 max effort · 10m40s · ↓42.5k tokens

---

## v3.4.0 (2026-05-31) — Opus 4.8 + Model & Effort

### Added
- **`## 🧠 Model & Effort Level`** — Opus 4.8 support, five effort levels (`low`–`max`), `/effort` in-session switching
- **`references/two-phase-review-polish.md`** — 两阶段审查→优化模式: Phase 1 agent team review → Phase 2 single CC polished output
- **`references/taste-skill-mobile-prototype.md`** — CC + taste-skill 移动端原型图快速生成

### Changed
- Version bump 3.3.0 → 3.4.0
- References table updated with two new patterns

---

## v3.3.0 (2026-05-30) — Stability Optimization

### Added
- **Rule #0: 🛑 占用检测** — mandatory CC occupancy scan before every invocation
- **Multi-Agent Coordination Protocol** (§ 🤝) — occupancy detection, decision matrix, session naming convention
- **Enhanced Progress Reporting** — `references/progress-reporting-enhanced.md` with visual state emojis, worker tree, token tracking
- **Session isolation rules** — per-agent `hermes-cc-{profile}-{ts}` naming, independent workdirs

### Changed
- **Decision tree redesigned** — removed print mode branch; only tmux + agent team
- **Core Rules rewritten** — 10 stability-first rules (was 10 mixed-mode rules)
- **Pitfalls compressed** — 60+ lines of verbose pitfalls → 16-line compact table with one-liner fixes
- **SKILL.md slimmed** — 402 → 290 lines (-28%)
- **Bypass permissions** — simplified from 16 lines to 3

### Removed
- Print Mode - One-Shot Tasks section
- PR Review Pattern section
- Old Interactive Mode example (Shift-Tab / hermes-claude-longterm)
- Smoke test connectivity script (kept basic version check)
- Verbose pitfall explanations (moved to references)

### Fixed
- **Pitfall #18** — revised from "daemon singleton" theory to verified "session sharing" root cause, with `--session-id UUID` validation
- **Workdir isolation** — confirmed that same workdir CC auto-resumes session (2026-05-30 test)

---

## v3.2.0 (2026-05-29) — Session Isolation

### Added
- `--session-id` UUID print-mode isolation (verified with 2x test)
- `--fork-session` for interactive mode branching
- `--dangerously-skip-permissions` bypass documentation
- CC session storage mechanism: `~/.claude/projects/<hash>/<uuid>.jsonl`

### Fixed
- HOME override for profile isolation (`HOME=/Users/alexcai`)
- TCC sandbox fallback (`cp` to `/tmp/`)

---

## v3.1.0 (2026-05-28) — Initial Stability

### Added
- Worker stall detection (fake-dead vs truly-dead)
- Fact-Forcing Gate recognition
- Progress reporting protocol (📡 30-60s polling)
- Agent team context file standards
- Schema persistence verification pattern
- Multi-round `/clear` protocol

### References Created
- `worker-stall-detection.md`
- `worker-true-stall-no-disk-output.md`
- `cc-agent-team-content-research.md`
- `cc-agent-team-parallel-implementation.md`
- `post-deploy-verification-pattern.md`
- `cc-session-isolation.md`
- `home-and-sandbox.md`
