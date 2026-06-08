# Core Rules（Hermes Agent 执行规则）— 完整 13 条

> 从 `SKILL.md ## ⚡ Core Rules` 下沉（v4.1.2 slim）。SKILL.md 只保留压缩版编号列表 + 本文件指针。

0. **🛑 发任务前必须扫描 CC 占用状态（🚦 Gate Stamp「占用检测」项的执行细则）** — 不同 agent 不知道彼此是否在用 CC。**每次调 CC 前，必须扫描所有 tmux session 的活跃状态**（`●` 工具调用 **+** `✻` 思考态——`❯` 不等于空闲，见 Pitfall #24）。**完整扫描脚本是唯一权威，见 `§ 🤝 Multi-Agent Coordination Protocol`（不再重复）。**

   - 有 `●` 或 `✻` → **必须汇报用户**："CC 正被 session `<name>` 占用，等待还是新建独立 session？"
   - 真正空闲 = `❯` + 无 `●` + 无 `✻/✶/✽/✳` + 无 `Waiting for N background agents`
   - ⚠️ **不要自作主张开新 session 绕过去**——用户可能不知道两个 CC 在同时跑，消耗翻倍
   - ✅ **但默认本就该新建独立 session**（`hermes-cc-{agent}-{ts}`）；占用检测是安全网，不是复用许可

1. **默认每次新建独立 session，不复用** — 每次调 CC 用独立 session 名 `hermes-cc-{agent}-{ts}`（**不复用**共享 `hermes-claude-longterm`）。**不用 `--continue`**（同一 workdir 下 CC 会自动 resume 最近 session → 串台）。需跨会话传上下文 → 写 `/tmp/cc-context-{task}.md`。
2. **复杂任务必须 agent team** — 多文件/多步骤/根因分析/实现+测试/架构判断 → 让 CC 自己 spawn subagent。**Agent 数量由 CC 按复杂度自定，context 文件只描述任务，不规定 team 规模。** 按关注点拆，不按文件拆 → 详见 `### 🧩 Agent 数量与拆分原则`。当任务拆分后各子任务产物相互独立（如多模块架构文档），优先用 **agent-direct-output 模式**（`references/agent-direct-output.md`）：agent 各自写文件、leader 只 cat，避免 max-effort 思考循环。
3. **Always set `workdir`** — 让 CC 聚焦正确项目目录。
4. **Always 带 `HOME=/Users/alexcai`** — 避免 Hermes profile HOME override 导致认证失败。
5. **不要杀慢会话** — 用 `capture-pane` 检查进度，确认卡死才 `Ctrl+C`。
6. **清理一次性 tmux 会话** — 用完就 `tmux kill-session`，避免泄漏。
7. **每轮 agent team 后 `/clear`** — 避免 context 膨胀。
8. **⚡ bypass permissions** — 启动后验证，通常默认已启用。
9. **📡 无条件持续汇报进度（🔴 红线① 执行细则）** — 每 30-60s polling，沉默 >2min 不可接受。**必须使用 Progress Reporting 段规定的 `📡 CC Agent Team [Xmin · 距上次 Xs]` 模板格式**，自由发挥 / 简化 / 合并多轮 = 违反红线①。**持续轮巡不是一句承诺：任务在跑就在发完 📡 后立即起下一轮轮巡（见 📡 Post-Send「手动轮巡 canonical」）。**
10. **Worker 假死先查磁盘** — `ls -la` → 文件存在则 `send-keys "Agent N done."` → 不存在则手动接管。
11. **🔴 违规自修正协议** — 一旦发现自己违反红线① 或 ②：**立即** (1) 显式标记「⚠️ 我刚违反红线 X」；(2) **当轮补做**——漏报就立刻补一个完整 📡 块，越权执行就停手退回讨论；(3) **禁止**用"下轮改正 / 抱歉以后注意"口头了事。说了不改 = 二次违规。
12. **🔍 完成前磁盘一致性校验（RA-06）** — agent team 完成摘要**不得只凭 tmux task board**（只显运行时间，不显真实产出）。宣布完成前必须 `find <workdir> -newer /tmp/cc-marker -type f` 或 `ls -la <预期产物>` 校验文件真实存在且 size>0；摘要里写明"已磁盘校验：N 个文件落盘"。task board 显示 done ≠ 文件已写盘（Pitfall #37 socket error 静默失败）。
