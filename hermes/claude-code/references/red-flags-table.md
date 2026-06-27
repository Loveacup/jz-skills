# Red Flags: DO NOT SKIP THIS SKILL — 完整借口反驳表

> 从 `SKILL.md ## 🚨 Red Flags` 下沉（v4.2.0 slim）。SKILL.md 只保留 2 行指针，完整 16 条反驳留此。

| agent 会找的借口 | 为什么是错的 |
|-----------------|-------------|
| "我直接用 terminal 调 claude 就行" | 不加载 skill = 不知道 PTY 对话框处理、不知道 `--max-turns` 防止失控、不知道 background 超时会被杀 |
| "任务太简单，print mode 就行" | 简单任务也有坑：`--max-turns` 不设 = 可能无限循环烧钱；`--model` 不指定 = 开销不可控 |
| "我用 tmux 不需要这个 skill" | PTY 有两个对话框需要精确按键序列。权限对话框默认是"No, exit"——你必须 Down+Enter。错过 = Claude 直接退出 |
| "agent team 就是普通 Task subagent" | Claude Code 的 agent team 是独立机制。用户明确说过不要用普通 Task subagent 冒充 team |
| "我设置 budget=$0.05 够了" | 系统 prompt cache 创建本身就 ~$0.05。更低 → 立即报错。烟雾测试用 `$0.2` |
| "我先静默检查 tmux，等 CC 有结果再汇报" | **2026-05-31/06-01 真实违规。** 发送任务后必须从第 15 秒起持续汇报 📡；**每次 `capture-pane`/poll 后都要立刻给用户一个进度块，即使只是 `✳ thinking`、未完成、或没有新结果**。不得把多轮 poll 藏在工具调用里等最终成果 |
| "我用简化格式 `📡 CC [~Xmin]` 汇报就行" | **2026-06-01 真实违规。** skill 规定模板是 `📡 CC Agent Team [Xmin]` + 状态 emoji + token 统计。简化格式 = 未汇报，即使内容正确。单 CC（无 worker）时仍需完整格式 |
| "用户骂我没监控，我先道歉解释一下" | **错。** 道歉必须伴随立即 `capture-pane`，把所有活跃/思考/等待输入的 CC session 用完整 📡 模板转发；若任务还在跑，立即恢复 30-60s 轮巡 + 完整 📡，**靠 Hermes 自身持续轮巡，不靠 watchdog 代劳**（父皇校准：不建 watchdog）。只道歉、不抓屏、不恢复轮巡 = 第二次违规 |
| "我已经报了一次 📡，等用户回复/等结果再继续" | **错。** 首次 📡 不是结束，是监控循环开始。用户回"好"不是暂停许可，而是继续推进信号。不要用一条"我会继续监控"结束回合后实际沉默 |
| "我在 📡 末尾写了'会持续轮巡'，这就算安排好了" | **错。** 口头承诺不是轮巡。用户要持续轮巡时，📡 回禀后必须立刻发起下一次轮巡工具调用（`capture-pane`），而不是结束 turn 等用户再催。详见 `references/manual-patrol-after-report.md` |
| "用户催我轮巡，我建个 cron/script/watchdog 自动报就行" | **错。** 用户要的是当前 Hermes agent 自己手动 `capture-pane → 📡`。未经明确要求建脚本/cron = 过度自动化 + 噪音，违背父皇"自己轮巡"校准 |
| "Hermes 设计 → Hermes 写代码，不用调 CC" | **2026-06-03 真实违规。** 用户说"要调用cc干活啊别自己干"。多文件架构改动、skill 编写、部署验证这些重活——Hermes 做好设计文档，CC agent team 执行 |
| "设计完直接部署就行，不需要审查" | **2026-06-03 真实违规。** 用户说"核心设计要让cc审查"。涉及多文件/架构/外包集成的设计，Hermes 写好方案后必须让 CC 审查再执行（曾发现致命缺陷：source-verification 不存在、降级链回环） |
| "CC 现在有忙/残留 session，所以我只能先不处理" | **错。** 先处理确定部分并推进可验证工作；不复用脏 session，但也不要把 CC 占用当停工理由。可新建隔离 CC 做 shadow-review；破坏性步骤仍等 CC `no blockers`。见 `references/direct-numbered-batch-shadow-review.md` |
| "我把 `sleep 30` 和 `capture-pane` 打包成一个 terminal 命令，更高效" | **2026-06-08 真实违规（2 次）。** `sleep 30 && capture-pane` 作为一个 tool call = 用户看到 45s 沉默 = 未监控。**正确节奏：`capture-pane`（无 sleep）→ 立即同轮 📡 → 下一轮再等。** 两操作分属两个 tool call 轮次，打包 = 违反红线①。详见 Pitfall #47 |
| "用户问 CC 的能力/功能/机制，我凭 memory 直接答" | **2026-06-01 真实违规。** CC 功能变化极快（一个月四版），training data 严重滞后。**任何关于 CC 能力/功能/机制/配置的问题，必须先搜 `code.claude.com/docs` + GitHub issues 再答，不准凭记忆** |
