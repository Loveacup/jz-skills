# 多轨并行 Rollout 模式（fan-out/fan-in）

> 验证于 v0.8（三路 P0/P1/P2）和 v0.9（双路 司验院+A2A），均全链贯通。

## 模式结构

```
中书拟制路线图 → 门下封驳 → 尚书拆解为子任务图
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
            P0 子任务       P1 子任务       P2 子任务
           (串行或并行)    (fan-out 并行)   (fan-out 并行)
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                     御史全量稽核（自阻等全部子任务）
                              │
                              ▼
                         史馆归档
```

## 关键步骤

### 1. 中书拟制 → 多轨路线图 PRD

Planner 产出含：
- 各路优先级（P0/P1/P2）
- 各路子任务列表 + 验收标准
- 依赖关系图（fan-out/fan-in 标注）
- 不在范围内声明

### 2. 尚书拆解 → Kanban 子任务

Dispatcher 为每路创建独立的子任务卡，正确的 parent 依赖链：
- P0 子任务 → parent = dispatcher 任务（或独立，若为前置）
- P1/P2 子任务 → parent = P0（若 P0 为前置）或独立并行
- P2c（fan-in 任务，如 qmd/名册更新）→ parents = 所有前置子任务

### 3. 御史稽核自阻

Auditor（T4）的 parent = dispatcher（T3），但 auditor 应在稽核时检查所有子任务状态。若子任务未全部 done，应 `kanban_block` 自身，理由写明"X/Y 子任务未完成"。

**关键**：子任务全部完成后，auditor 不会自动恢复——需手动 `unblock` + `dispatch`。

```bash
# 解阻御史
hermes kanban unblock t_auditor
hermes kanban dispatch
```

### 4. 九子任务全通验证

确认所有子任务 done 后，解阻御史 → 稽核通过 → 史馆归档。

### 5. HITL 卡处理（子任务需人工决策时）

当 dispatcher 拆解的子任务卡需要人工决策时，worker 会 `kanban_block` 自身并注明 `review-required`：

**解阻流程**：
```bash
# 1. 批注决策
hermes kanban comment <hitl_task_id> "【父皇批示】决策内容..."

# 2. 解阻
hermes kanban unblock <hitl_task_id>

# 3. 派工
hermes kanban dispatch
```

**示例**（v0.9 tester profile 设计决策）：
- 卡 `t_67865e8b` 自阻，列出 3 项决策待确认
- Regent 向 Emperor 呈报并给出建议
- Emperor 批准后，comment → unblock → dispatch 推进

**HITL 监控增强**：监控脚本可加入 HITL 卡自动检测，若 HITL 卡已解阻则自动 `dispatch`。

**⚠️ 监控条件陷阱**（v0.9 实战教训）：以下条件在 T4 blocked 且 HITL 非 blocked 时**每次循环都触发**，导致 15+ 次不必要的 dispatch：
```bash
# ❌ 坏条件 — T4 可能因其他原因 blocked（如等子任务），与 HITL 无关
if [ "$s4" = "blocked" ] && [ "$s_hitl" != "blocked" ]; then
  hermes kanban dispatch 2>&1   # 每 20s 触发一次，制造噪音
fi
```
**正确做法**：HITL 解阻是一次性操作，应由 orchestrator 手动执行，不放入循环监控。监控只需检查终态（T5 done）或阻断（任一前置 blocked/failed）：
```bash
# ✅ 简洁正确
for i in $(seq 1 60); do
  sleep 20
  hermes kanban dispatch 2>&1 >/dev/null  # 让 dispatcher daemon 自然调度
  s5=$(hermes kanban show $T5 2>&1 | grep "status:" | awk '{print $2}')
  [ "$s5" = "done" ] && break
  # 检查阻断信号
  s_hitl=$(hermes kanban show $T_HITL 2>&1 | grep "status:" | awk '{print $2}')
  [ "$s_hitl" = "blocked" ] && echo "HITL needs decision: $T_HITL" && break
done
```

## 已验证案例

| 版本 | 轨数 | 子任务数 | 结果 |
|------|------|---------|------|
| v0.8 | 3（P0修复/P1新建三部/P2知识库） | 9 | ✅ |
| v0.9 | 2（司验院/A2A协议注入） | 7 | ✅ |
| v0.10 | 6（delegate咨询/TDD gate/巡检cron/拓扑校验/protocol+budget/将作监+兵部） | 13 | ✅ |

## 常见坑

- **Auditor 自阻后忘记解阻**：子任务全 done 后 auditor 仍是 blocked，必须手动 `unblock`
- **Fan-in 子任务 parent 过多**：如 P2c qmd 有 3 个 parent，只要有一个未 done 就不会 promote
- **Planner oaipro 崩殂**：见 `references/oaipro-claude-kanban-format.md`，unblock + dispatch 重试即可

## 监控脚本模板

```bash
for i in $(seq 1 60); do
  sleep 20
  hermes kanban dispatch 2>&1 >/dev/null
  s5=$(hermes kanban show $T5 2>&1 | grep "status:" | awk '{print $2}')
  if [ "$s5" = "done" ]; then echo "ALL DONE"; break; fi
  for tid in $T1 $T2 $T3; do
    s=$(hermes kanban show $tid 2>&1 | grep "status:" | awk '{print $2}')
    if [ "$s" = "blocked" ] || [ "$s" = "failed" ]; then echo "BLOCKED at $tid=$s"; break 2; fi
  done
done
```
