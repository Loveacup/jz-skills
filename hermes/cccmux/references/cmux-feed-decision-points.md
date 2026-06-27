# cmux Feed —— 决策点处理（取代 PTY 对话框导航）

> **核心改造点：** raw-tmux 版要手工 `send-keys Down → Enter` 导航 CC 的 PTY 对话框（Trust folder / "Yes, I accept" / 权限菜单），且 Pitfall #26 警告 tmux 下 AskUserQuestion 表单不可靠。**cmux 把权限 / ExitPlanMode / AskUserQuestion 全部收编进 Feed**——一个结构化决策面板（侧栏 `Ctrl-4`），用户点选即可，orchestrator 也能经 socket 回复。PTY 导航整章作废。

## 1. Feed 是什么

cmux 的 agent 决策内联面板。机制链：

```
CC 触发 hook(权限/计划/提问)
   → cmux claude wrapper 注入的 hook 把它推成 socket `feed.push` 帧
   → FeedCoordinator 把 hook **阻塞在按 request_id 的信号量上(≤120s)**
   → 用户在 Feed 侧栏点击 / orchestrator 经 socket 回复
   → feed.{permission|question|exit_plan}.reply 唤醒 hook
   → hook 在 stdout 吐决定 JSON → CC 继续
```

**软等待，永不死锁**：120s 超时吐 `{}`，CC 回落到自己的 TUI 提示。

## 2. 三类可操作决策项

| 类型 | 触发 | 可选项 |
|---|---|---|
| **Permission** | CC 要用受限工具 | Once / Always / All tools / **Bypass** / Deny |
| **ExitPlanMode** | teammate plan approval | Ultraplan / Manual / Auto / Deny |
| **AskUserQuestion** | CC 问用户（多选） | 多选后 Submit |

其余（tool use、assistant msg、TodoWrite、session start/stop）作为**信息流存档**，不阻塞。

## 3. orchestrator 怎么处理决策点（🔴 红线①的一半）

监控订阅里收到 `feed.item.received` →**先分类,不要把所有 feed 都当阻塞决策点**。

实测:SessionStart / UserPromptSubmit / Stop 也会产生成对的 `feed.item.received/completed` 归档项,并不阻塞。只有 Feed TUI 或 payload 显示为 Permission / ExitPlanMode / AskUserQuestion,或 lifecycle 进入 `needsInput`,才是需要用户处理的🔴决策点。

1. 对事件分类:普通 hook 归档项只记录；Permission / ExitPlanMode / AskUserQuestion 才进入决策流程。
2. **立即**抓取真正决策项内容（`cmux feed tui` 看，或从事件 payload）。
3. **立即转发用户 + 发讨论简报**——CC 在等人决定，静默 = 卡住 + 用户不知情。
4. **绝不代答**架构/方案类问题（红线②：方案审定前是讨论不是执行）。
5. 纯机械的安全权限（如读文件、team 内部协作工具）→ 可按 context 预设策略放行（Allow/Always/Bypass）。
6. 用户给出决定后，引导用户在 Feed 侧栏点击，或（若 orchestrator 有 socket 权限）经 reply 方法回传。

## 4. 与权限模式的关系

- cmux 的 claude wrapper 用 `--allow-dangerously-skip-permissions` 启动 CC —— 这**不默认开 bypass**，但允许后续 `PermissionRequest` 把会话切到 `bypassPermissions`。
- 所以 raw-tmux 版「grep 标题栏 `⏵⏵ bypass permissions on` 验证」这条**作废**；权限态由 Feed 的 Permission 决策驱动。
- 启动 team 前可在 context 文件声明默认放行策略（如「读类工具一律 Allow，写/外发走 Feed 让用户决定」），减少打断。

## 5. 净效果:这些 Pitfall 直接作废

- **Pitfall #1**（Dialog 2 默认 "No"，要 Down→Enter）→ 无 PTY 导航,作废。
- **Pitfall #13 / Shift-Tab 权限切换坑** → Feed 接管,作废。
- **Pitfall #26**（tmux 下 AskUserQuestion 表单不可靠 → 只能走纯文本）→ **解禁**:cmux Feed 原生支持 AskUserQuestion 点选。讨论协议里「提问走纯文本」可放宽为「决策点可用 Feed 表单，Hermes 侧仍发讨论简报」。

## 6. 副作用:很多 worker 假死本质是权限弹窗阻塞

raw-tmux 版 `agent-team-full-stall-recovery.md` 的根因之一:teammate 卡在权限弹窗等不到人导航。cmux 把弹窗收编进 Feed + 软超时后,**这类假死大幅减少**。context 预填「弹窗一律 Accept」那条 → 换成「权限默认策略(读 Allow / 写走 Feed)」。
