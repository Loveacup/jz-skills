# CC 审核任务中的循环陷阱（2026-06-28 实发）

## 现象

WRR 全项目审核任务中，CC 完成 turn 后等待 Hermes 发送下一条指令。Hermes 在以下循环中反复执行相同操作：

1. `cc-wait-marker.sh` 等待 turn-done → 返回
2. `tmux capture-pane` 读取 CC 状态 → 发现 CC 在等确认
3. `cc-send.sh` 发送确认 → 成功
4. 回到步骤 1

用户质问「你又陷入循环了？」时，Hermes 已重复执行该序列 5+ 次，未检查 CC 实际产出或状态变化。

## 根因分析

### 1. 旧 turn-done 复用陷阱

`cc-wait-marker.sh` 使用 `mtime > --after` 比较。若 `--after` 基线未在每轮正确更新，旧 turn-done 文件的 mtime 可能大于旧基线，导致 waiter 立即返回，误判为新轮完成。

**关键**：CC 的 Stop hook 每轮**覆盖** `/tmp/cc-turn-done-<s>` 文件（mtime 刷新），但 Hermes 的 `--after` 基线必须是「上一轮 wait 返回时那一版 marker 的 mtime」，不能复用更早的值。

### 2. 状态未变化即重复发送

CC 处于 `WAITING_AGENTS` / `THINKING` / `BLOCKED` 状态时，Hermes 未先 `capture-pane` 确认 CC 实际在等什么，就重复发送相同确认消息。消息进入队列但不执行（Pitfall #1 变种）。

### 3. 无产物检查

每轮循环中 Hermes 未检查 `/tmp/cc-output-<s>/` 是否有新产物。若产物未变化，说明 CC 没有新进展，不应继续发送确认。

## 修复方案

### 防循环三原则

1. **每次 wait 返回后先读产物**
   ```bash
   # 检查是否有新产物
   find /tmp/cc-output-$SESSION/ -type f -newer /tmp/cc-turn-done-$SESSION 2>/dev/null
   # 或检查产物目录是否有变化
   ls -lt /tmp/cc-output-$SESSION/ | head -5
   ```
   确认 CC 真的完成了新工作，而非旧 turn-done 被复用。

2. **CC 在 WAITING/THINKING/BLOCKED 时不要重复发送相同确认**
   ```bash
   # 先 capture-pane 看 CC 实际在等什么
   tmux capture-pane -t $SESSION -p -S -10 | tail -20
   # 若 CC 显示 "Waiting for your response" 或类似 → 发确认
   # 若 CC 显示 spinner 或工具调用中 → 继续等，不要发
   ```

3. **用户说「停」或质问循环时立即停**
   - 汇报当前状态（CC 在等什么、已执行几轮、产物状态）
   - 不要继续执行预设流程
   - 等待用户明确下一步指令

### 基线更新正确做法

```bash
# 每轮发指令前重记基线
AFTER=$(stat -f %m /private/tmp/cc-turn-done-$SESSION 2>/dev/null || echo 0)
# 发指令
cc-send.sh ...
# 等待新 turn-done（严格 mtime > AFTER）
cc-wait-marker.sh --session $SESSION --after $AFTER --timeout 300
```

`--after 0` 仅第一轮（尚无任何 marker）用。后续轮次必须用上一轮返回时的 marker mtime。

## 验证方法

1. 检查 `cc-wait-marker.sh` 的 `--after` 参数是否正确更新
2. 检查产物目录 `/tmp/cc-output-<s>/` 是否有新文件
3. 检查 `tmux capture-pane` 输出是否显示 CC 在等待确认（而非工作中）
4. 若用户质问循环，立即停止并汇报当前状态

## 关联

- cc-tmux Pitfall #36：本案例的 skill 级归档
- cc-tmux Pitfall #20：`cc-wait-marker.sh` mtime 比较陷阱
- cc-tmux Pitfall #1：CC 思考态时发送消息进队列不执行
- cc-tmux Pitfall #21：in-turn wait 全程沉默
