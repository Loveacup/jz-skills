# Agent Team 全队冻结恢复模式

> 2026-06-08 SIL v5.0 (17 Agent · 10 Stage) 全 roster 复现。6 worker 中 5 个弹窗冻结 + longform-writer 未 spawn，Leader 空等 20min。

## 症状识别

```
⚡ Leader: ❯ continue — 继续等待 longform-writer 完成 S6 成文
  ├─ 🔴 Pane 2: ✻ Sautéed for 29s — 冻结，"❯ 1. Continue" 弹窗
  ├─ ✅ Pane 3-7: ❯ 空闲
  └─ 🔴 Pane 8: ✻ Cogitated for 16s — 冻结
```

**判定标准（全部满足 = 全队已死）：**
1. Leader 显示同一等待消息 >5min
2. 所有 worker pane 无 `●` 工具调用
3. Worker 状态行 token/时间完全冻结（如 ✻ Sautéed for 29s 持续 >3min 不变）
4. 无磁盘产出（`find <workdir> -newer /tmp/cc-marker -type f` 为空）

## 恢复（三步）

### Step 1：不抢救，直接杀

```bash
tmux kill-session -t <session-name>
```

**不要做的事：**
- ❌ 逐个 pane send-keys Enter — 可能解了弹窗但 worker 已无上下文，产出无意义
- ❌ 反复 Ctrl+C + 重发指令 — Leader 不会自行发现 worker 已死
- ❌ 等更久 — 20min 经验表明不会自行恢复

### Step 2：降复杂度重启

原任务如果用全 roster（如 SIL 17 Agent），重启时：
- 减少 worker 数量（目标 3-5 个，而非 6+）
- 缩小任务范围（写清楚「完成这些就输出，不等更多」）
- Context file 开头写：「遇到任何权限弹窗一律选 Accept/Continue/Yes」

### Step 3：Post-Send 加强监控

- 发送任务后 15s 首次 polling
- 每次 capture-pane 后立即 📡，**不把 capture 和 sleep 打包成一个 terminal 调用**
- 每轮扫描所有 pane 底部，发现 "Enter to confirm" 立即 send-keys Enter

## 根因分析

CC agent team 的 worker 本质是子进程，无交互能力。当 CC 内部触发 settings 确认弹窗时：

1. Worker 尝试修改 settings（如 MCP server 配置、文件权限）
2. CC 弹出 "The values listed above were skipped... ❯ 1. Continue"
3. Worker 无 UI 交互能力，永久挂起
4. Leader 不知道 worker 已死，持续等待
5. 超时机制（context file 里的 `timeout 10min per worker`）可能未生效或 worker 不算"超时"（它确实在运行，只是弹窗阻塞）

**预防优于抢救：** Context file 里写入 settings 接受策略比事后 send-keys 更可靠。
