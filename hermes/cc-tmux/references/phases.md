# Phase 分解 — cc-tmux 工作流

> 每 phase ≤10 条义务。脚本处理机械化操作，agent 只做需要判断的事。
> 总义务数：~26 条 / 4 phases = 平均 6.5 条/phase。

## Phase 1: PREFLIGHT（启动前）

| # | 义务 | 类型 |
|---|------|------|
| 1 | 判断任务是否真需要 CC（简单任务自己干） | 判断 |
| 2 | 选 effort：没信号→high，多文件→xhigh，架构→max | 判断 |
| 3 | 跑 `cc-start.sh --target X --effort Y --task Z` | 脚本 |
| 4 | 检查 exit code：2=BUSY → 汇报用户等待 | 判断 |
| 5 | 捕获 stdout 的 session 名 | 机械 |
| 6 | 等 5s，跑 Dialog 1：`Enter` | 脚本 |
| 7 | 等 2s，跑 Dialog 2：`Down → Enter` | 脚本 |
| 8 | 验证 pane 显示 `⏵⏵ bypass permissions on` | 验证 |

**退出条件**：session 存在 + bypass on → 进 SEND

## Phase 2: SEND（发送任务）

| # | 义务 | 类型 |
|---|------|------|
| 1 | 写 context 到 `/tmp/cc-context-{session}.md` | 机械 |
| 2 | 跑 `cc-send.sh --session X --context file` | 脚本 |
| 3 | 等 15s，首次 capture-pane | 机械 |
| 4 | 检查 ❯ 处有文字但无 ● → 补发 `Enter` | 判断 |
| 5 | ❯ 处无文字 → 重新 send-keys | 判断 |

**退出条件**：看到 ● 或 ✻ → 进 MONITOR

## Phase 3: MONITOR（监控）

| # | 义务 | 类型 |
|---|------|------|
| 1 | 每 30-60s 跑 `cc-monitor.sh --session X` | 脚本 |
| 2 | 每次 capture 后立即发 📡 块给用户（1:1 成对） | 强制 |
| 3 | ● 工具调用 → 汇报工具名 + 描述 | 判断 |
| 4 | ❯ 空闲且上方无 ● → 检查任务是否完成 | 判断 |
| 5 | ✻/✳/✶ 思考态 + token 在增长 → 继续等 | 判断 |
| 6 | ✻ 思考态 + token 冻结 >3min → `Ctrl+C` → 缩小范围重问 | 判断 |
| 7 | 沉默 >2min → ⏰ 自标超时并解释 | 强制 |

**退出条件**：❯ 空闲 + 上方无 ● + 任务产出可见 → 进 FINISH

## Phase 4: FINISH（收尾）

| # | 义务 | 类型 |
|---|------|------|
| 1 | 跑 `cc-finish.sh --session X --target Y --release-lock` | 脚本 |
| 2 | 若 ❯ 有残留命令 → 绝不按 Enter，先 `C-u` 清行 | 强制 |
| 3 | 验证产物：`ls -la` 确认文件存在 + size > 0 | 验证 |
| 4 | 若产物缺失 → 回到 MONITOR，告诉 CC "文件未落盘" | 判断 |
| 5 | 若用户确认阶段结束 + 产物完好 → `--kill-session` | 判断 |
| 6 | 最终报告：完成什么 + 改了什么 + 怎么验证的 + 注意事项 | 强制 |

**退出条件**：lock 释放 + session killed（或用户要求保留）→ 阶段结束

---

## 义务分类统计

| 类型 | 数量 | 说明 |
|------|:--:|------|
| 脚本调用 | 5 | start/send/monitor/finish/eval — 脚本自己保证正确 |
| 机械操作 | 4 | 等 N 秒、捕获 stdout、写文件 |
| 判断 | 11 | agent 需要思考的——这是 LLM 擅长的事 |
| 强制规则 | 4 | 不可违反的红线（📡1:1、沉默<2min、❯残留、最终报告） |
| 验证 | 2 | bypass on、产物落盘 |

**关键设计**：19/26 条（73%）是脚本或红线——不需要 agent "记住"。agent 真正需要判断的只有 11 条。
