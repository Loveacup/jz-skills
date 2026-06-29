# CC Pane Stuck-Input-Box Unblock Pattern

> 2026-06-28 · CC v2.1.178+ · cc-tmux 实战 · 与 AskUserQuestion 模式**不同**

## 两种残留：启动提交失败 vs 旧输入框残留

### A. 启动提交失败（v1.38 已脚本化）

场景：你刚发出 `按 /tmp/task.md 执行... Enter`，马上调用 `cc-wait-marker.sh`，但 CC 仍是 IDLE，pane 显示的正是**刚才那句任务指令**。

处理：`cc-wait-marker.sh` startup gate 默认 **exit 4 fail-fast**，避免 900s 空等；不会自动 Enter。只有调用方明确知道残留就是刚发送的任务行时，才可显式启用：

```bash
CC_WAIT_AUTO_SUBMIT_RESIDUAL=1 cc-wait-marker.sh --session <s> --timeout 600
```

若仍未离开 IDLE，仍 exit 4。

```bash
cc-wait-marker.sh --session <s> --timeout 600
# exit 4 = 任务未真正提交；不要继续等，清理/重发
```

### B. 旧输入框残留（本文件原始模式）

场景：CC 已完成上一轮并 IDLE，pane 中残留的是**旧任务/旧 follow-up**，不是你刚刚发送的文本。

处理：不要直接 Enter；先 `/clear`。

## 症状

CC session 已 IDLE（turn-done 已发生，CC 在等你下一步），但 `tmux capture-pane` 显示 ❯ 提示符后**有文字残留**：

```
❯ P2 派活           ← 上一次的指令文本卡在输入框
```

不是 `AskUserQuestion` 选项 UI，也不是 `Press up to edit queued messages` queue banner——只是**普通纯文本输入但没提交**。

### 触发场景

1. **上一次 `tmux send-keys "MSG" Enter` 的 Enter 被吞**——Pitfall #18/#31 已知场景
2. **CC 在某次 turn 末尾把上一个未发送的文本保留在输入框**——CC UI 偶尔的行为
3. **`cc-send.sh --message` 之前没清空**——本 session 实发

### 为什么必须解决

如果你现在发新指令（`cc-send.sh --message "..."`）：
- `send_to_pane` 会把新消息**追加**到输入框末尾 → 拼成 `"跑独立 L1 验收Q4: 选 Spec-list..."` 这种混乱文本
- 或按 send_to_pane 的 §3.2 防护：看到 ❯ 后有残留就重发 Enter → **把你之前的"跑独立 L1 验收"当真发了**，触发误判

## 解除方法（按优先级）

### ✅ 方法 1：`/clear` 通过 cc-send.sh（推荐）

```bash
bash ~/.hermes/skills/autonomous-ai-agents/cc-tmux/scripts/cc-send.sh \
  --session <session-name> \
  --message "/clear"
sleep 2
tmux capture-pane -t <session-name> -p | tail -5
# 预期：❯ 空（无残留）
```

`/clear` 是 CC 内置 slash 命令，会清空输入框 + 不触发任何 LLM 调用。`cc-send.sh --message` 走 §3.2 send_to_pane 防护管道（自动补 Enter + 重试 4 次），比裸 `tmux send-keys` 稳。

**实测**：本 session 17:18 用 `/clear` 成功清掉了"P2 派活"残留。

### ❌ 方法 2：`Escape` 或 `C-u`（不可靠）

```bash
tmux send-keys -t <session> Escape
tmux send-keys -t <session> C-u
```

**不要依赖这两个键**：
- R4c 实施记录 §7.1 / Pitfall #24 已记录：`C-u` / `Escape+C-u` / `C-a+C-k` 在 Claude TUI 下**未必清掉**输入框残留
- 本 session 17:18 实测：Escape 和 C-u 都对"P2 派活"无效

只有 `/clear` 真的有效。

### ❌ 方法 3：直接按 Enter（严禁）

```bash
tmux send-keys -t <session> Enter  # ❌ 严禁
```

**绝对不要按 Enter**——会把输入框里的旧文本当真发送给 CC。CC 会以为是新任务，结果你之前已经发过的指令又被重复执行一次。

## 验证流程

```bash
# 1. 发送 /clear
bash cc-send.sh --session <s> --message "/clear"
sleep 2

# 2. 抓屏确认 ❯ 空
tmux capture-pane -t <s> -p | tail -3
# 预期输出：
# ❯
# ────────────────────────────────────────
# ⏵⏵ bypass permissions on ...

# 3. 然后才发真消息
bash cc-send.sh --session <s> --context /tmp/new-context.md --no-prefix
```

## 预防

1. **每次 `cc-send.sh` 之前先抓屏确认 ❯ 空**（Pitfall #18 / §3.2 已要求，作为防御深度）
2. **不要用裸 `tmux send-keys` 发 follow-up**——Pitfall #31 已修（cc-send.sh `--no-prefix`）
3. **如果 send_to_pane 看到 ❯ 后有残留**（它的 §3.2 防护会重发 Enter），**先 `/clear` 再发**

## 与 AskUserQuestion 模式的区别

| 维度 | Stuck-Input-Box（本模式） | AskUserQuestion（已有）|
|------|---------------------------|-------------------------|
| Pane 表现 | ❯ 后有纯文本 | ❯ 后**没有**文本，但有选项 UI（`Enter to select`）|
| cc-status state | IDLE | BLOCKED, last_tool=AskUserQuestion |
| 解决方法 | `/clear` | 选选项号 / Escape + 纯文本决策 |
| 触发原因 | 上一次 send 没提交 | CC 主动提问 |

不要混淆——**两种模式都常见，但解法完全不同**。

## 本 session 实例

2026-06-28 17:18 · mac-doctor P2 验收后，CC pane ❯ 残留"P2 派活"（来自更早 send-keys Enter 卡顿）：

1. 先试 `tmux send-keys Escape` → ❌ 无效，文本仍在
2. 再试 `tmux send-keys C-u` → ❌ 无效，文本仍在
3. 改用 `cc-send.sh --session hermes-cc-default-mac-doctor-0628-1601 --message "/clear"` → ✅ 输入框清空
4. 再用 `cc-send.sh --session ... --context /tmp/cc-p3-context.md --no-prefix` → ✅ P3 context 正确发送

## 关联

- Pitfall #18（Enter 未生效）—— 症状不同，**根因相同**（CC TUI 输入处理）
- Pitfall #24（清残留失败）—— 记录了 C-u/C-a C-k 不可靠
- Pitfall #31（Hermes 裸 send-keys 绕过 §3.2 防护）—— 与本模式互补
- `references/cc-askuserquestion-unblock-pattern.md` —— 不同模式