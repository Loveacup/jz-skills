# cc-tmux Test Reproduction — 2026-06-16

## 测试任务
虚构任务：编写 ASCII 复活节兔子 Python 脚本（三种尺寸 + 四种 ANSI 颜色 + argparse CLI）。
产出：`/tmp/cc-test-output/easter_bunny.py`（92 行，2220 字节）。

## 全流程时间线

| 时间 | 步骤 | 结果 |
|------|------|------|
| 00:33:21 | `cc-start.sh` | exit 0, session `hermes-cc-default-cc-test-bunny-0616-0033` |
| 00:33:27 | `cc-send.sh` | ✓ Sent |
| 00:33:27 | `cc-monitor.sh` #1 | IDLE (changed=true, from STARTING) |
| ~00:33:30 | 发现 ❯ 后残留文字，手动 `send-keys Enter` | — |
| ~00:33:45 | 抓屏确认：✢ Julienning… (19s) | CC 工作中 |
| 00:34:04 | `cc-monitor.sh` #2 | IDLE (changed=false) — 漏检 THINKING |
| 00:34:34 | `cc-monitor.sh` #3 | IDLE (changed=false) — 漏检 |
| 00:35:02 | 抓屏确认：⏺ 完成，❯ 空 | CC 已完成 |
| 00:35:11 | `cc-monitor.sh` #4 | IDLE (changed=false) |
| 00:35:22 | `cc-finish.sh` | exit 0, 全门通过 |

## Pitfall #5: cc-send.sh Enter 未生效

### 复现步骤
1. `cc-start.sh` 启动 session
2. `cc-send.sh --context /tmp/cc-test-bunny-task.md`
3. 脚本返回 `✓ Sent`
4. 等 5s 后用 `cc-monitor.sh` 检查 — 报 IDLE
5. `tmux capture-pane` 发现 ❯ 后残留 "Please read /tmp/cc-test-bunny-task.md — # Task:…"

### 根因假设
`send-keys` 键入文本后，Enter 键未在 CC 的 pty 中生效。可能原因：
- 时序竞争：文本键入未完成时 Enter 已发送
- pty 缓冲：Enter 被缓冲区吸收
- CC 对话框干扰：PTY dialog 仍处于过渡态

### 当前 Workaround
```bash
# 发送后验证
tmux capture-pane -t <session> -p -S -5
# 若 ❯ 后有残留文字 → 手动 Enter
tmux send-keys -t <session> Enter
```

## Pitfall #6: cc-monitor.sh 状态检测盲区

### 观察
4 次 `cc-monitor.sh` 全部报 `IDLE`，但 CC 实际经历了：
- TOOL: `⏺ mkdir -p /tmp/cc-test-output`
- THINKING: `✢ Julienning… (19s · ↓ 546 tokens)`
- TOOL: `⏺ 完成。脚本已创建并通过验证。`
- THINKING: `✻ Cogitated for 37s`

monitor 的状态转移日志：`状态序列: IDLE`（1 次转移，STARTING→IDLE）

### 根因（2026-06-16 实读源码后更正）

**不是**正则漏字符。实读 `cc-monitor.sh` line 91-92 确认正则已覆盖 `[✻✳✶✢✽]` 和 `⏺|●`。

**真根因 = 优先级 bug**。`IDLE` 检测（line 121-138）排在 `TOOL`/`THINKING`（line 91-92）**之前**。CC 干活时屏幕底部常驻空 ❯ → IDLE 抢先命中。证据：test-repro #2/#3 中屏上明有 `✢ Julienning` 却报 IDLE。

**修正方向**：反转优先级（TOOL/THINKING → IDLE）+ 收窄 TOOL/THINKING 取样窗口到活跃尾区（而非全 -40 窗口）。详见 `cc-tmux优化方案_20260616.md` §3.1。
