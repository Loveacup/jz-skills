# cc-wait-marker Base-Stamp Routine

> **问题**：Hermes 派 CC 长任务后用 `cc-wait-marker.sh --session X --after <TIMESTAMP> --timeout N` 等 `cc-turn-done-<session>` marker mtime > `<TIMESTAMP>` 才返回 0。Pitfall #20 已记录 mtime 比较陷阱，但实操中**最容易重复犯**的不是「忘了记基线」，而是「**记了一个过期基线**」——例如用上一轮 send 前的 mtime、或用这次 session 的 cc-start 时间，结果：CC 跑了几分钟，Stop hook 第一次写 marker（mtime > start_time 但 ≤ 上一轮旧基线）→ waiter 看到 marker mtime ≤ `--after` → 继续等 → CC 已完成但 Hermes 不知道。
>
> **2026-06-28 mac-doctor P3/P4 实发**：连续 3 次 waiter timeout（25min × 3），根因都是 `--after <fixed-timestamp>` 而不是 `--after 0`。CC 已完成，marker 早写了，但基线是 start_time + 几秒，结果 mtime > start_time 但不一定 > 启动那一刻的 mtime（取决于文件系统 mtime 精度）。

## The Ritual（3 步，10 秒）

每次准备 `cc-wait-marker.sh` 之前**机械执行**这 3 步，**不要思考**：

```bash
# Step 1: 取「此刻」作为基线 — NOT start_time, NOT previous round mtime
AFTER=$(stat -f %m /private/tmp/cc-turn-done-${S} 2>/dev/null || echo 0)
echo "baseline marker mtime: $AFTER (0 = no marker yet)"
# 如果 echo 0 → 第一轮，无 marker，可以用 --after 0
# 如果 echo 非 0 → 上一轮 mtime，必须用这个；不要重新 stat start_time

# Step 2: 派活（这一步 mtime 不变）
bash .../cc-send.sh --session "$S" --context /tmp/cc-context.md
# ↑ 此时 marker mtime 仍然是 $AFTER（CC 还没回话）

# Step 3: 等 — 用刚取的基线，不是固定值
terminal(background=true, notify_on_complete=true)(
  bash .../cc-wait-marker.sh --session "$S" --after "$AFTER" --timeout 1500
)
```

## 错误模式（4 种，最常见 → 最隐蔽）

### ❌ 错误模式 A: 用 session 启动时间

```bash
# mac-doctor P3 实发（21:25 CC 启动，21:32 CC 完成 → 21:55 仍 timeout）
START_TS=$(stat -f %m /tmp/cc-status-${S}.json)  # 启动时刻的 mtime
# ↑ Stop hook 在 21:32 写 marker，mtime ≈ 21:32
# ↑ 基线 21:25，21:32 > 21:25 → 应该返回啊？
# 实际：marker 文件 21:32 创建，stat -f %m 21:32，21:32 > 21:25 ✓
# 这条在 macOS APFS 上偶尔 work，**但 Linux ext4 上 mtime 精度 = 1 秒**
#   21:32 marker vs 21:25 baseline → 7 秒差 → 应该返回
# 真正失败的 case（2026-06-28 P4 实发）：
#   AFTER=$(stat -f %m /private/tmp/cc-turn-done-$S 2>/dev/null || echo 0)
#   ↑ baseline 18:30:25（旧的 turn-done 残留 marker 的 mtime）
#   ↑ CC 跑完写新 marker 18:32:01（Stop hook 触发）
#   ↑ 18:32:01 > 18:30:25 → 应该返回 0 啊
#   实际返回 1（timeout）→ why?
#   因为 cc-wait-marker.sh 用 `mtime > after` 严格大于，但**文件系统 mtime 精度不够**
#   或**两轮 marker 共享同一个 inode，Stop hook 覆盖写但 mtime 没刷新**（macOS APFS 已知 bug）
#   或 stat -f %m 在 race condition 下返回旧值
```

**正确**：用**当前时刻**作为基线（`date +%s` 或 `stat -f %m /tmp/cc-turn-done-$S`），**不要**用 start_time 或其他历史时间戳。

### ❌ 错误模式 B: 复用上次 wait 的 mtime

```bash
# 上次 waiter 返回时 mtime=X1
# 然后你又发了一条 follow-up → 应该取「这次发完后的 mtime」
# 但你直接 --after X1 → 如果新 CC 完成用了同一 mtime（同秒），严格大于失败
```

**正确**：**每轮 send 后必须重新取 AFTER**（哪怕只是一行 follow-up）。`--after` 是「我要等比这个时间更新的 marker」—— 你必须用**这条消息发出去那一刻**或之后的时刻。

### ❌ 错误模式 C: `--after 0` 被误用为「安全值」

```bash
# 错误：所有 round 都用 --after 0
bash cc-wait-marker.sh --after 0 --timeout 1500
# ↑ 这相当于「只要有 marker 就返回」
# ↑ 如果 CC **没** 完成但前一轮的 marker 还在（Stop hook 写完后 cc-finish 没清）→ 立即返回 0
# ↑ 把前一轮的旧产物误判为这轮的
```

**正确**：`--after 0` 只在**第一轮**（session 刚启动、还没有任何 marker）用。**之后每轮都必须 re-stat**。

### ❌ 错误模式 D: marker 被 hook 旋转写覆盖

```bash
# CC 跑完 → Stop hook 写 marker (mtime=T1)
# 同 session 复跑 → CC 又跑完 → Stop hook 覆盖写 marker (mtime=T2 > T1) ✓
# 但：如果你 --after T1 → 等 T2 → 返回 0 ✓
# 真正失败的是：marker 文件**没被覆盖写**，而是**同一个 inode 上 mtime 没刷新**
# 这在 macOS APFS 上 + 高 I/O 负载时**极罕见但确实发生过**（2026-06-28 P4）
```

**应对**：如果 timeout 后怀疑 marker 存在但 mtime 没刷新，**手动**：

```bash
# 1. 看 marker 文件本身
ls -la /private/tmp/cc-turn-done-$S
# 2. 看内容
cat /private/tmp/cc-turn-done-$S
# 3. 看 marker 内容时间戳（不是 mtime）
# ↑ marker 是 JSONL: {"ts": "2026-06-28T13:32:00Z", "event": "turn_done", "session": "..."}
# ↑ 看 ts 字段确认是否是这轮的新事件
# 4. 看 cc-status.json last_event 时间和 last_event_since
cat /private/tmp/cc-status-$S.json
```

## 实战诊断流程（waiter timeout 后必跑）

```bash
# Step 1: 看 CC 实际状态
cat /private/tmp/cc-status-${S}.json | jq '{state, last_event, last_event_since, seq, heartbeat}'
# ↑ 看 state=IDLE 还是 TOOL 还是 COMPLETED 还是 GONE
# ↑ seq 是否增长（增长 = CC 还在动）

# Step 2: 看 pane 最后 20 行
tmux capture-pane -t $S -p -S -20
# ↑ 看 ❯ 是否为空（空 = CC 完成等指令）
# ↑ 看是否有 spinner（✻/✽/✶ = CC 还在思考）

# Step 3: 看 marker 文件 mtime vs 内容
stat -f "%Sm %N" /private/tmp/cc-turn-done-$S
cat /private/tmp/cc-turn-done-$S
# ↑ mtime vs ts 字段 — 如果 ts 是这轮的 → CC 已完成，waiter 是 bug
# ↑ 如果 ts 是上轮的 → CC 没完成 → 真在等

# Step 4: 决策
# 情况 A: state=COMPLETED + marker 新 → waiter 漏了 → 读产物 + 验收（不等）
# 情况 B: state=IDLE + marker 新 → 同上
# 情况 C: state=TOOL/THINKING + seq 还在涨 → 真在跑 → 再 wait 一轮
# 情况 D: state=GONE → CC 死了 → 清理孤儿 + 派新 session
```

## 与 cc-tmux SKILL.md 的关系

- **Pitfall #20** 描述了「mtime 比较陷阱」—— 本文是**操作前 ritual**，让 Pitfall #20 在派活那一刻就被 catch，而不是 timeout 后才查
- **`scripts/cc-wait-marker.sh`** 的 `--after` 行为契约见 SKILL.md §3 「Turn 内等待模式」
- **事件驱动唤醒**（SKILL.md §3 标注）只在长任务**收尾**时替代 in-turn wait，不替代 wait-marker 本身

## 触发场景检查表

派 CC 任务后，如果使用 `cc-wait-marker.sh`，**先**回答这 3 个问题再写命令：

1. **「上一轮 wait 是什么时候返回的？返回时 marker mtime 是多少？」** → 取这个值作为 `--after`
2. **「这次 cc-send 是几秒前？marker 文件 mtime 可能落后于 cc-send 时间」** → 如果 mtime ≤ cc-send 时间，重新 stat
3. **「session 有没有复跑过同一个 session？」** → 如果复跑过，必须用**最近一次** send 后的 mtime

任意一个答不上来 → **用 `--after 0`**（兜底）。会浪费一点时间，但比 timeout 后再补强。

## 一句话总结

> **`AFTER=$(stat -f %m /private/tmp/cc-turn-done-$S 2>/dev/null || echo 0)`** —— 每轮 send 前 1 行重新取，**不要**复用、**不要**估算、**不要**用 start_time。