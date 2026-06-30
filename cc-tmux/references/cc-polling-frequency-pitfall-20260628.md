# Pitfall #43: 轮询频率过高导致用户刷屏投诉

## 事件

2026-06-28，WRR 社区搜索链路优化任务。

CC session `hermes-cc-default-wrr-p2-p3-0628-1850` 进入 STARTING 状态（seq=42），后台 `cc-wait-marker.sh` 已运行。Hermes 使用 `process(action=poll)` 每秒轮询后台进程状态，连续发送 60+ 条"CC 正在启动中（Ns）"消息。

用户连续质问：
- "为什么你一直在刷屏？？？？？"
- "你怎么又在刷屏了？？？？？？？"
- "要定时轮询，但是也不能这么频繁啊一分钟几十次！！！！"

## 根因分析

1. **误解事件驱动原则**：cc-tmux v1.31.0 引入"事件驱动唤醒"后，Hermes 将"不再定时轮询"理解为"完全不能轮询"，但用户实际需求是"定时轮询但不要太频繁"。

2. **`process(action=poll)` 滥用**：该工具每秒返回一次，即使状态无变化也产生输出，导致消息洪水。

3. **无状态变化检测**：每次轮询输出"CC 正在启动中（Ns）"，N 递增但实质状态未变（STARTING→STARTING），属于无意义重复。

## 修复方案

### 立即修复
- 停止 `process(action=poll)` 轮询
- 改用 `process(action=wait, timeout=180)` 或后台 `cc-wait-marker.sh` + `notify_on_complete`
- 用户插话时立即响应，不等下一轮轮询

### 长期规范

**轮询频率约束**：
- **默认**：事件驱动（`cc-wait-marker.sh` + `notify_on_complete`），零主动轮询
- **用户明确要求"定时轮询"时**：间隔 **≥180s**（3分钟）
- **每次轮询必须有实质性状态变化**：状态转移（STARTING→THINKING→TOOL→IDLE）或新产物出现
- **禁止**：
  - 每秒/每10秒轮询
  - 同一状态重复汇报（如"CC 正在启动中"连续 10+ 次）
  - 将同一状态用不同措辞反复发送

**正确姿势**：
```
# 事件驱动（首选）
terminal(background=true, notify_on_complete=true)
  → cc-wait-marker.sh --session $S --after $AFTER --timeout 1800

# 用户要求定时轮询时
process(action=wait, timeout=180)  # 3分钟一次
  → 超时后读 cc-status + capture-pane
  → 有状态变化才汇报，无变化则继续 wait
```

## 验证

- [ ] 轮询间隔 ≥180s
- [ ] 同一状态不重复汇报
- [ ] 用户插话时立即响应（不等待下一轮轮询）
- [ ] 事件驱动唤醒为主，轮询为 fallback

## 关联

- cc-tmux SKILL.md §3 "事件驱动唤醒"
- cc-tmux SKILL.md Pitfall #43
