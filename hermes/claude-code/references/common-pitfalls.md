# Claude Code Common Pitfalls — Full Detail

> 主文件 `SKILL.md` 的紧凑 Pitfall 表是速查。这里放完整诊断 + 恢复步骤。

## 1. Dialog 2 默认"No"

用 `--dangerously-skip-permissions` 时权限对话框默认选中 "No, exit"。**必须先 `Down` 再 `Enter`。**

```bash
sleep 3 && tmux send-keys -t <s> Down && tmux send-keys -t <s> Enter
```

## 2. HOME Override 认证失败

Hermes profile 将 `HOME` 重定向到 `~/.hermes/profiles/<name>/home/`。CC 在此找 `~/.claude.json`、`~/.claude/`、`~/.npm/`——如果不在 profile HOME 下则 `claude auth status` 返回 `Not logged in`。

**修复：** 始终 `HOME=/Users/alexcai claude ...`

**永久方案：** symlink auth 文件到 profile home：
```bash
ln -sf /Users/alexcai/.claude.json $PROFILE_HOME/.claude.json
ln -sf /Users/alexcai/.claude $PROFILE_HOME/.claude
```

## 3. Worker 假死（文件在磁盘）

**症状：** `Waiting for N background agents` + worker token >2min 不变，但 `ls -la` 发现目标文件存在且 size > 0。

**恢复：** `tmux send-keys 'Agent N is done. All files exist on disk. Continue.' Enter`

**不要：** 杀 worker（破坏 agent team 状态）、反复 `send-keys Enter`（CC 在等后台事件，不处理输入）。

## 4. Worker 真死（无磁盘产出）

**症状：** `Waiting for N background agents` + worker token >2min 不变，`ls -la` 目标文件不存在或 size == 0。

**恢复：** `tmux kill-session` → 手动接管。

**预防：** context file 写入 `timeout 10min per worker，超时视为失败，Leader 直接进入汇编`。

## 5. 多轮 Context 膨胀

Round 1 的 70k+ tokens 填满 context → Round 2 触发 `Spinning… (2m+)`。

**修复：** 每轮 agent team 后 `/clear`。已验证：Round 1 (70k tokens, 17min) → `/clear` → Round 2 (43k tokens, 24min)。

## 6. Fact-Forcing Gate

CC 编辑文件前要求陈述 (1) 用户指令原文 (2) 文件引用者 (3) 受影响函数/类 (4) 数据结构。停顿 5-10s 后自动重试。**正常流程，不是卡死。**

## 7. send-keys 不执行

超长 `send-keys` + `Enter` 有时 CC 不处理。15s 后 `capture-pane` 仍无 `●` → 补发空 `Enter`。提示符处输入不执行同理。

## 8. 进度监控沉默

**最常犯的 EXECUTION LAPSE。** 发送任务后必须每 30-60s polling 并向用户汇报 `📡` 进度块。沉默 >2min 不可接受。

## 9. Agent Team Schema 持久化

Worker 产出的新字段可能被 storage 静默丢弃（只存预定义列）。**验证方法：** Python subprocess curl → POST → sleep → GET → 检查 artifact 含预期字段。新字段写入 `artifact` dict（整存为 JSON），不写 task 顶层新列。

详见 `references/post-deploy-verification-pattern.md`。

## 10. macOS TCC 沙盒

`~/Documents/` `~/Desktop/` `~/Downloads/` 可能被拦截。Fallback：`cp` 到 `/tmp/` → CC 处理 → `cp` 回去。永久：系统设置 → 隐私与安全性 → 文件与文件夹 → 给终端授权。

## 11. Background Shell Stall

`Skedaddling…`/`Puzzling…` + token >3min 不变 + 后台 shell running → stall。发 redirect 指令 → 30s 无响应 → 手动接管。2026-05-28 复现：dispatcher 卡在 `cat` 后台 shell 5 分钟。

## 12. Token 脱敏破坏语法

Hermes 脱敏 `***` 可能删相邻字符。用字符串拼接不用 f-string：`'Bearer ' + token`。Shell 中避免直接引用 token。

## 13. TMUX Shift-Tab 无效

`tmux send-keys Shift-Tab` 在 macOS 下是窗口切换快捷键，被当作文本字面量。不用——直接 `Down → Enter` 处理权限对话框。

## 14. Scrollback 污染

复用 tmux 长会话时 `capture-pane -S -N` 显示旧任务。先确认 CC 空闲（`❯`），发 `pwd` 验证再派任务。

## 15. Print Mode 长文档不稳定

>15KB markdown 转 PDF 静默 >8 分钟。改用 Python + Playwright：`references/python-playwright-pdf-fallback.md`。

## 16. CC Agent Team Schema Unknown

Workers 不知道持久化 schema → 新字段被静默丢弃。Leader wiring 后验证：Python subprocess curl → POST → sleep → GET → 检查 artifact。

详见 `references/post-deploy-verification-pattern.md`。

## 17. Background Shell Stall (Full)

CC 显示 `Skedaddling…` + token >3min 不变 + 后台 shell `(ctrl+b ctrl+b to run in background)` → stall。**诊断：** 连续两轮 polling (~90s) token 无变化。**恢复：** 发 redirect 指令 → 30s 无响应 → 父 agent 手动执行。此模式 2026-05-28 复现。

## 18. 多 Agent Session 冲突 ★

**根因：** CC session 共享（`~/.claude/projects/<hash>/<uuid>.jsonl`）。官方文档明确："If you resume the same session in two terminals, messages interleave."

**Print 模式（已验证）：** `--session-id "$(uuidgen)"` 完全隔离。2026-05-30 实测两个 UUID 产生两个独立 `.jsonl`。

**交互模式：** `--session-id` 不可靠（Issue #44607）。必须：禁 `--continue`、独立 workdir、扫描占用（`§ Multi-Agent Coordination Protocol`）。

详情 → Obsidian `00-Inbox/CC tmux 多Agent 会话隔离问题.md`
