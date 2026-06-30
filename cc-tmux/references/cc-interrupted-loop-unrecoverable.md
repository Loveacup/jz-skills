# CC 不可自愈 Interrupted 循环：诊断与恢复

> 2026-06-28 实发：OMP skill ACP 实现任务，CC 运行 `omp acp` 后陷入自循环中断

## 症状

```
❯ continue
  ⎿  Interrupted · What should Claude do instead?

❯ continue
  ⎿  Interrupted · What should Claude do instead?

❯ continue
  ⎿  Interrupted · What should Claude do instead?
```

- 每个 "continue" 被中断，但 CC 又自动发下一个 "continue"
- 自循环持续 >3 分钟不破
- Token 停滞（如 17.6k 不再增长）
- 新消息（Escape→发纯文本、cc-send.sh、Ctrl+C）进入队列后被拼接或跳过
- 零磁盘产出

## 与 Pitfall #1 的区别

| | #1 (queued messages) | #41 (Interrupted loop) |
|---|---|---|
| CC 是否发消息 | 否（一次都不发） | **是**——反复发 "continue" |
| 消息是否被中断 | 被排队不执行 | **被中断后重新排队** |
| Escape 能否解决 | ✅ 有效 | ❌ 无效——队列清空后 CC 再发 "continue" |
| 底层状态 | ❯ 显示队列横幅 | Interrupted + "What should Claude do instead?" |

## 根因

底层 Bash 命令（如 `omp acp` 等待 stdin、或 `omp --mode rpc` 阻塞）被 CC 中断。CC 的默认响应是「continue」（重试被中断的操作），但 `continue` 也触发同一个中断 → 形成自循环。消息队列中积累的 "continue" 阻塞新指令。

## 三步干预（按序执行，≤3 轮）

### 步骤 1：清队列 + 终止阻塞进程

```bash
tmux send-keys -t <session> Escape C-c C-c C-u C-u C-u
sleep 4
tmux capture-pane -t <session> -p | tail -10
```

预期结果：❯ 纯空（无 "Interrupted"/"continue" 残留）。

若仍有残留 → 重复步骤 1。

### 步骤 2：发送简洁纯文本指令

**≤60 字符，不含 `continue` 一词**。

```bash
# 使用 cc-send.sh 而非裸 send-keys
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session <s> --message "简短任务描述"
```

等待 8-10s 后 `cc-monitor.sh --force-capture` 确认 CC 进入 THINKING/TOOL（非 RECEIVED/IDLE 自循环）。

### 步骤 3：判定退出

若 2 轮后仍回到 Interrupted 自循环 → **判定 session 不可自愈**。

两种退出路径：

| 条件 | 路径 |
|------|------|
| CC 有未保存的磁盘产物（`references/*.md` 等） | **Hermes 接管**：利用已有只读研究产出，自行完成剩余实现 |
| CC 纯思考 0 磁盘产出 | **重启 CC**：`cc-finish --force --kill-session` → 新 `cc-start`，缩小任务范围 |

## 本 session 实际情况

- 任务：OMP skill ACP 通道实现
- 触发命令：`omp acp`（等待 stdin 的交互式命令）
- 干预次数：Escape ×3, Ctrl+C ×2, Ctrl+D ×1, 新指令 ×4
- 结果：7 分钟仍未突破
- 退出路径选择：**Hermes 接管**——CC 已有完整 RPC 研究笔记（`references/omp-rpc-acp-notes.md`，97 行，含 `omp acp` 握手验证），可直接用于 ACP 实现

## 预防

- **避免让 CC 运行会阻塞等 stdin 的交互式命令**（如 `omp acp`、`omp --mode rpc`）
- **协议实测模式**：让 CC 写测试脚本 → Hermes 独立运行 → 结果回传给 CC 分析
- **context 末尾声明**：「不要运行交互式命令。如需实测协议，写脚本后告知我运行」
- ⚠️ **诊断期间不要碰 session rating widget**：CC 恢复后可能弹出 `● How is Claude doing this session? (optional) 1:Bad 2:Fine 3:Good 0:Dismiss`。**不要发送 `0` 试图 dismiss**——这会导致 CC session 直接被 kill（state → GONE）。正确做法：发送 `2` 或 `3` 使 widget 消失，或者忽略它让 CC 自动继续。
- ⚠️ **加载 cc-tmux 后再操作**：在未加载 cc-tmux skill 的情况下发送 `tmux send-keys "continue"` 给 THINKING 态的 CC → 触发了本应避免的 Pitfall #1 消息队列死锁。**先 `skill_view('cc-tmux')` 再碰 CC pane**——即使你觉得自己记得协议。
