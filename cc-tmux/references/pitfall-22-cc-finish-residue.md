# Pitfall #22 — cc-finish.sh 残留 gate 清行失败

## 症状
`cc-finish.sh` exit 1，报 `⚠️ ❯ 残留输入: <文字>`。`C-u` / `Escape` 清行无效。

## 根因
CC 在 ❯ 留了未发送文字（如建议/追问）。`--force` **只覆盖监控间隙 gate，不覆盖残留 gate**——残留是硬门，`cc-finish.sh:10` 明确 `never the residual gate`。

`C-u` 在某些 CC 状态下不生效：
- CC 处于队列模式（Pitfall #1）
- CC 已进入下一个渲染帧，send-keys 时机错误

## 修复（已验证有效）
```bash
# ① 发无害短命令消耗残留文字
tmux send-keys -t <session> "echo ok" Enter
sleep 2

# ② 确认 ❯ 干净后重跑
bash .../scripts/cc-finish.sh --session <s> --target <t>
```

## 不要做的事
- 反复 `C-u`——两条没清掉就改用消耗法
- `--force`——它绕不过残留 gate
- 直接 `tmux kill-session`——绕过 cc-finish 安全门，锁/心跳/状态文件残留

## 触发频率
2026-06-23 实测：两轮任务都触发。CC 在 turn-done 后常会在 ❯ 留一条建议/追问。
