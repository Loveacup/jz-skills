# CC v1.40 residual prompt / autocomplete submit pattern（2026-06-30）

## 场景

用裸 tmux + 单行 `/tmp/task.md` 指令启动/续派 CC 后，`cc-wait-decision.sh` 返回：

- `wait_marker.exit_code=4`
- `decision.state=prompt_text_needs_clear` 或 `active_no_resend`
- pane 里能看到刚发的任务行，例如：`按 /tmp/wrr-cc-p1-task.md 执行...`
- artifact 还不存在

这不等于 CC 失败。v1.40 的 startup gate 对 CC autocomplete / residual prompt 保守处理：它看到输入框里有文本，但无法证明这行文本已提交。

## 判定

先看 `decision`：

- `active_no_resend` + monitor state `THINKING/TOOL`：**不要重发**，继续等 artifact / monitor。
- `prompt_text_needs_clear` 且 pane text 明确就是“本轮刚发送的单行任务指令”：可以手动 `Enter` 提交一次。
- 如果 pane text 不是本轮任务，或疑似旧残留：不要 Enter；`Escape/C-c` 清理后重新发单行 path 指令。

## 操作模板

```bash
# 看到刚发的单行任务仍停在 prompt 中时，仅提交一次 Enter
tmux send-keys -t <cc-session> Enter

# 随后不要重发任务，等 artifact
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-wait-decision.sh \
  --session <cc-session> --timeout 600 --expect /tmp/expected-result.md
```

若 `cc-wait-decision` 判断为 `active_no_resend`，可用轻量 artifact poll，避免重复注入：

```bash
for i in {1..30}; do
  test -s /tmp/expected-result.md && { cat /tmp/expected-result.md; exit 0; }
  sleep 10
done
```

## 反模式

- 不要连续 `send-keys Enter`；只提交一次。
- 不要在 `active_no_resend` 时重发同一任务；这会制造重复任务/队列污染。
- 不要把 `exit_code=4` 简化成“任务没提交”。必须看 `decision.state`、monitor state、pane tail 三者。

## 真实案例

WRR packaging/plugin 修复中，P1/P1b/P2/P1c 多次出现任务行可见但未提交。手动 Enter 后 CC 正常完成并写出结果文件；问题是 input submit gate 保守，不是 CC 实现失败。