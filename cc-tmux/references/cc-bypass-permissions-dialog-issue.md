# CC Bypass Permissions Dialog — tmux 交互阻塞问题

> 2026-06-27 · CC v2.1.178 · cc-tmux v1.29.0 · 实发 session: hermes-cc-default-skill-orchestration-design-0627-1436/1452

## 症状

CC 启动后 pane 底部持续显示权限对话框：

```
⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt · ← for agents
```

**关键特征**：
- 对话框不是阻塞 modal——CC 仍在后台运行（显示 `✻ Germinating…` / `✢ Julienning…`）
- 但 CC **不消费 ❯ 输入框的新任务输入**——发送的文本显示在 ❯ 后但 CC 不处理
- `tmux send-keys` 发送的 Down/Enter、Tab/Enter、Space/Enter、y/Enter、S-Tab/Enter 均无法与对话框交互
- 权限对话框持续存在，即使 CC 已进入思考态

## 复现路径

1. `cc-start.sh --target X --effort max --model claude-opus-4-8`
2. CC 启动后 pane 显示 `❯` + 底部权限对话框
3. `cc-send.sh` 发送任务文件路径
4. CC 读取任务文件内容（显示在 pane 中）
5. CC 开始思考（`✻ Germinating…`）
6. 底部权限对话框 **仍在**
7. 后续 `tmux send-keys` 发送的指令 CC 不消费

## 尝试过的方案（均失败）

| 方案 | 发送的 keys | 结果 |
|------|------------|------|
| A | `Down Enter` | 对话框仍在 |
| B | `Tab Enter` | 对话框仍在 |
| C | `Space Enter` | 对话框仍在 |
| D | `y Enter` | 对话框仍在；CC 收到 `y` 但无对应操作 |
| E | `S-Tab Enter` | 对话框仍在 |
| F | `Escape` | 对话框仍在；CC 被中断（`Interrupted · What should Claude do instead?`）|
| G | `C-c` | CC 退出到 shell；对话框消失 |

## 根因分析

Claude Code 的权限对话框使用 **非标准终端输入处理**——不是 readline/ncurses 的标准键盘事件，而是 TUI 框架（可能是 Ink/blessed 类似物）的内部事件循环。`tmux send-keys` 发送的键序列被终端模拟器正确接收，但 Claude TUI 的事件分发器不将其映射到对话框的交互逻辑。

这与 Pitfall #10（`/usage` TUI 全屏面板）不同：
- #10 是 `/usage` 命令进入的 **全屏 TUI 面板**，`Escape` 可退出
- #26 是启动时 persistent **底部权限横幅**，非全屏、非 modal、不响应标准键序列

## 修复 ✅ (2026-06-27)

**方案：启动时添加 `--allow-dangerously-skip-permissions` 参数**

```bash
claude --allow-dangerously-skip-permissions --model ${MODEL} --effort ${EFFORT} ...
```

**验证**：
- 启动后底部仍显示 `⏵⏵ bypass permissions on` 横幅，但状态已经是 "on"（无需确认）
- CC 正常消费 ❯ 输入框的任务输入
- 任务正常执行（`what is 2+2?` → `⏺ 四`）

**实施**：`cc-start.sh` 第 228 行已添加 `--allow-dangerously-skip-permissions`

**注意**：`--dangerously-skip-permissions`（不带 `allow`）会显示一个 **不可 pre-seed 的安全警告对话框**，仍需交互确认。`--allow-dangerously-skip-permissions` 直接跳过所有权限检查，无对话框。

## 关联 Pitfall

- #10: `/usage` TUI 全屏面板冻结
- #25: pane 空白（CC 未消费任务）——权限对话框可能是 #25 的 root cause 之一

## 监测

此问题应随 Claude Code 版本更新复查。若上游修复，cc-tmux 可移除 workaround 建议。
