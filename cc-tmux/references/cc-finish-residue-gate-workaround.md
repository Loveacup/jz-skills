# cc-finish.sh 残留 Gate 绕过（Pitfall #22）

## 症状

```
⚠️  ❯ 残留输入: 把报告也复制一份到 Obsidian 项目目录
  → 先 C-u 清行再收尾，勿按 Enter。
```
`cc-finish.sh` exit 1，`--force` 无效。

## 根因

- CC 在 ❯ 输入框里留了未发送的文字（不是队列消息 Pitfall #1，而是**正常输入行残留**）
- `tmux send-keys C-u` 在 CC 的 TUI 模式下不一定生效——CC 在 composition 态时 C-u 可能被吞
- `--force` 只覆盖**监控间隙**拒绝，**不覆盖残留 gate**（硬门，设计如此）
- `Escape` 退出 composition 态也不能保证 C-u 生效

## 绕过：无害命令消费法

```bash
# 发一条无害命令吃掉残留文字
tmux send-keys -t <session> "echo done" Enter
# 等 2s CC 执行完，❯ 变干净
sleep 2
# 重跑 cc-finish.sh
bash .../cc-finish.sh --session <session> --target <target>
```

## 为什么用 `echo done`

- 不触发任何 side effect（不写文件 / 不发请求 / 不调工具）
- 不写 session-restore 状态（`/exit` 会写，不合适）
- 不依赖 CC 听 `C-u`（不依赖 = 不猜 TUI 模式）

## 适用条件

- CC 处于 IDLE（❯ 空闲），只是输入行有残留文字
- 残留文字 ≤ 一行（多行可能需要多次消费）
- 不是 Pitfall #1 的队列消息（队列消息 ❯ 会显示 "Press up to edit queued messages"）

## 记录

- 首次触发：2026-06-23，cc-tmux 全流程 smoke test
- session：`hermes-cc-default-cc-tmux-stats-0623-0222`
- CC 版本：v2.1.185
