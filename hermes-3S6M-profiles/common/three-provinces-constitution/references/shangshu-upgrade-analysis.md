# 尚书省升级分析（与 edict 对比）

> 来源：2026-05-25 session，三省制度优化讨论。完整方案见 Obsidian: `40-Archives/尚书省升级方案_执行总枢AIAgent_待实施制度包_经三省审订+御史稽核通过_20260525.md`

## 核心发现

对比 [edict](https://github.com/cft0808/edict)（另一套三省六部多 Agent 框架）后，发现我们的尚书省被严重压缩：

| 职责 | edict | 我们 | 差距 |
|------|-------|------|------|
| 派发 | ✅ 智能判定 assignee | ⚠️ 需人工指定 --assignee | 缺智能匹配 |
| 协调 | ✅ 主动跟踪、发现阻塞、自动协调 | ⚠️ kanban-watcher-poll 只做机械恢复 | 缺 AI 判断 |
| 汇总 | ✅ 多任务结果合成呈太子 | ❌ 完全缺失 | 太子手动看板 |

## 升级方案（已批准，待实施）

三层能力模型 → 三阶段路径：

| 层 | 能力 | 阶段 |
|----|------|------|
| L1 智能派发 | 读任务→匹配能力映射表→自动判定 assignee | Phase 1（2-3天） |
| L2 主动协调 | 跟踪进度、发现阻塞、自动建恢复链 | Phase 2（1-2天） |
| L3 汇总呈报 | fan-in 多任务结果合成，主动呈太子 | Phase 3（2-3天） |

## 关键设计决策（D1-D4 已裁决）

- D1: 独立 profile（`shangshu`），不替代 dispatcher gateway——坐在上面做智能决策
- D2: cron `no_agent=false`（AI agent 模式），2min 轮询
- D3: 与 kanban-watcher 互补——watcher 通知，尚书决策
- D4: 能力映射表静态维护，P0 经验更新

## 与现有组件关系

```
kanban-watcher (通知)  ←→  尚书省 (决策)  ←→  kanban-watcher-poll (恢复)
        ↓                        ↓
   dispatcher gateway (机械执行层: promote/claim/spawn)
```

不改 Hermes core。所有工具用现有 kanban CLI。月成本 ≈ $0。
