---
name: cc-tmux
description: >
  Drive Claude Code via tmux with script-enforced safeguards.
  Thin skill — scripts do the enforcement, prose only tells you which script to call.
  Parallel version to claude-code skill for testing the simplified architecture.
  
  Use when: 调 CC, 用 claude, 拉 CC, delegate to CC, agent team, 重活调 CC.
  Do NOT use for: simple single-tool calls, grammar fixes, non-coding tasks.
type: routine
version: 1.35.0
author: "Hermes Agent + Claude Code (v1.35.0: R10 消息路由完整落地)"
license: MIT
---

# CC via tmux — Script-Enforced Orchestration

> **设计原则**：脚本做 gate，LLM 做决策。"能不能做"由代码判，"怎么做"由 LLM 判。
> **与 claude-code skill 的关系**：并行版本，不覆盖。v4 是 full prose，v5 (cc-tmux) 是 thin prose + fat scripts。
> **核心赌注**：把义务数从 80+ 砍到 ~10 per turn（curse of instructions），让合规=最省事。

## 🚦 消息路由（cc-route.sh + cc-active-sessions.sh · R10 · v1.35.0）

当 Hermes 收到用户消息且存在活跃 CC session 时，**必须**先走路由层再行动：

1. `cc-active-sessions.sh --json` — 查有无 CC、什么状态
2. 分类 intent：`status_query` | `continuation` | `redirect` | `new_task` | `unknown`
3. `cc-route.sh --session <s> --intent <type>` — 获取路由建议
4. 按 `.recommendation.action` 行动

完整操作流程见 `references/routing-guide.md`；决策矩阵见 `scripts/cc-route.sh` 头部注释。
5 类 intent × 10 种 CC state → 4 种 action：`handle_directly` | `queue` | `forward_now` | `interrupt`（confirm_required=true）。
测试：test-route.sh 21/21 + test-active-sessions.sh 10/10。

## ⚠️ Pitfall #47：bash `local` 只在函数内合法

`local sm` 写在脚本顶层（非函数内）+ `set -euo pipefail` = 脚本立即 exit 1，无任何 stdout/stderr 输出。
症状：`bash -x` trace 显示 `local: can only be used in a function`。
**规则**：顶层用普通赋值（`sm=...`），仅在 `func() { ... }` 内用 `local`。
