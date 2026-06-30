# cc-wait-marker mtime 不可信模式（2026-06-28 实发）

## 症状

`cc-wait-marker.sh --after <timestamp> --timeout 1500` 持续 timeout 25 分钟，但**实际 CC 已经 turn-done 5-10 分钟前**（产物文件已写、CC pane 显示 IDLE、`cc-status-*.json` 显示 `state=COMPLETED`）。

## 根因

`/private/tmp/cc-turn-done-<session>` 由 **Stop hook** 写入。但 `touch` / `>` / `>>` 写入时，**如果文件已存在，mtime 行为不保证更新**：

- **POSIX `touch` 语义**只更新 atime + mtime（前提是 touch 显式带 `-m` 或无 flag）
- **shell 重定向 `> file`** 在某些 hook 包装下，**只重写内容不刷新 mtime**（特别是 `cat > file` 或 `tee > file`）
- **macOS HFS+/APFS + Stop hook 时序**：hook 启动前 mtime 已存在 → 写入失败/成功但 mtime 不刷

mac-doctor 项目 P2/P3/P4 三次 waiter timeout（25min 全部 timeout）但 CC 实际已完成。debug 发现 marker 文件 mtime **早于 wait start time 2-5 分钟**。

## 4 步诊断（waiter timeout 后立即跑）

```bash
S="hermes-cc-default-<target>-<ts>"

# ① 看状态文件（最权威，hook 直接写）
cat /private/tmp/cc-status-$S.json
# 看 state (ACTIVE/IDLE/COMPLETED/GONE), last_event, last_tool, seq

# ② 看 marker 文件 mtime + 内容
stat -f "%Sm  %N" /private/tmp/cc-turn-done-$S
cat /private/tmp/cc-turn-done-$S  # 应该是 JSON

# ③ 看 pane 实际状态
tmux capture-pane -t $S -p | tail -10

# ④ 交叉对比 cc-status.json vs marker mtime
echo "status mtime: $(stat -f %Sm /private/tmp/cc-status-$S.json)"
echo "marker mtime: $(stat -f %Sm /private/tmp/cc-turn-done-$S)"
```

**判定**：
- `state=COMPLETED` + `last_event=Stop` + `seq` 增长 + 产物文件存在 → **CC 真完成**（marker mtime 失真）
- `state=TOOL` + `last_event=PostToolUse` + mtime 持续刷新 → **CC 还在跑**（mtime 应该涨）
- `state=IDLE` + `last_event=Notification` + seq 稳定 → **CC 可能在 IDLE 等回复**（mtime 不涨是 expected）

## 修复

### 短期：waiter 加 fallback（推荐）

`scripts/cc-wait-marker.sh` 加 `--state-fallback COMPLETED`：timeout 后读 `cc-status-$S.json` 判定 → exit 0。

### 中期：Stop hook 用 `printf > file` 强制刷新 mtime

`hooks/settings.runtime.json` Stop hook 改为：
```bash
# Before (可能不刷 mtime)
echo '{"ts":"..."}' > /tmp/cc-turn-done-$S

# After (printf 显式 truncate + 写入，POSIX 保证 mtime 更新)
printf '{"ts":"%s","event":"turn_done","session":"%s"}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" "$S" > /tmp/cc-turn-done-$S
```

### 长期：cc-wait-marker 接受 seq 参数

`cc-wait-marker.sh --after-seq <n>` 替代 `--after <ts>`，比较 `cc-status-$S.json` 的 `seq > n` 作为真完成判据。mtime 永远不参与。

## 临时绕过（mac-doctor P3 实测有效）

```bash
# 不依赖 mtime：直接轮询 cc-status state
while true; do
  state=$(jq -r '.state' /private/tmp/cc-status-$S.json 2>/dev/null)
  if [ "$state" = "COMPLETED" ]; then
    echo "✓ CC done via state check"
    break
  fi
  sleep 5
done
```

## 与 Pitfall #20 的关系

- **Pitfall #20**：`--after` 基线要用「上一轮 wait 返回时 marker 的 mtime」——避免 mtime 比较陷阱
- **本 reference**：`--after` 本身不可信，因为 Stop hook 不保证刷 mtime——必须用 `cc-status-$S.json` 的 `state` 或 `seq` 作为真判据

## 相关

- Pitfall #20 in cc-tmux SKILL.md（mtime 比较陷阱，已知问题）
- `references/cc-wait-marker-base-stamp-routine.md`（仪式化 4 步）
- mac-doctor P2/P3 audit reports 2026-06-28（waiter 误判背景）
- `references/event-driven-wakeup.md`（事件驱动唤醒也是用 marker，是误判多发场景）
