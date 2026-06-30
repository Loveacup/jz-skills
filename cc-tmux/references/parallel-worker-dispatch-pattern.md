# Parallel Worker Dispatch Pattern（2026-06-28 · H6 实战）

> **适用**：需要并行触发多个 iii worker（cc/codex/review/...）并聚合结果。核心约束：一 worker 失败不能影响其他 worker。

## 核心模式

```javascript
// parallel-runner.mjs — pure logic, no IO
export async function runParallelCalls(calls, { triggerIii } = {}) {
  const results = await Promise.allSettled(   // ← allSettled, not all
    calls.map(call => runOne(call, triggerIii, timeout_ms))
  );
  // Aggregate with per-worker { lane, action, status, data?, error?, duration_ms }
  // Summary: { total, ok, error, timeout, total_duration_ms }
}
```

## 关键设计决策

| 决策 | 理由 |
|---|---|
| `Promise.allSettled` 非 `Promise.all` | 一 worker 失败不炸掉其他——这是并行的唯一价值 |
| `triggerIii` 注入 | 测试用 fake trigger，生产用真实 `iii-client.mjs` |
| 每 worker 独立超时 | `runOne()` 内部 `Promise.race(runPromise, timeoutPromise)` |
| `TIMEOUT` Symbol 作 reject 标记 | 区分 timeout vs 真错误 |
| 超时后 `clearTimeout(timer)` | finally 块清理，避免 timer 泄漏 |
| `runOne()` 永不 throw | catch 全部返回 `{ status: 'error/ok/timeout' }` |

## fakeTriggerIii 测试模式

```javascript
function fakeTriggerIii(behaviors) {
  // behaviors: Map of `action → { delay_ms?, result?, error? }`
  return async ({ action, payload }) => {
    const b = behaviors.get(action);
    if (!b) throw new Error(`unexpected: ${action}`);
    if (b.delay_ms) await sleep(b.delay_ms);
    if (b.error) throw b.error;
    return b.result;
  };
}
```

`delay_ms` 是关键：不同 worker 设不同延迟 → 证明并发（`total_duration_ms ≈ max(delays)`，非 `sum(delays)`）。

## CLI 契约

```bash
call-parallel.mjs --plan plan.json
```

`plan.json`：
```json
{
  "calls": [
    {"lane": "cc-worker", "action": "cc::execute", "payload": {...}},
    {"lane": "codex-worker", "action": "codex::exec", "payload": {...}}
  ],
  "timeout_ms": 120000
}
```

## 测试覆盖（必须 ≥8）

1. 2 workers 并行成功 → 结果正确 + summary.ok=2
2. 3 workers 一失败 → 2 ok + 1 error，互不影响
3. timeout 处理 → 慢 worker 返回 timeout status
4. 空 calls / null / undefined → total=0，不抛
5. 单 worker 调度 → duration_ms > 0
6. 错误隔离 → worker1 错误不影响 worker2
7. 并行时间证明 → 3×50ms = total < 150ms（非 150ms 串行）
8. 重复 lane → 都执行，都独立
9. summary 统计 → ok/error/timeout 计数精确

## 与现有架构的关系

- **不改 routing**：`review-worker/src/routing.js` 保持单 lane 决策，并行是调度层的事
- **不改 worker**：CC/codex/review 代码零触碰
- **不改 iii-client.mjs**：只注入使用
- **Promise.allSettled 是接口契约**：不是实现细节

## 何时用

- 需要 Codex 规划 + CC 执行 + review 审计同时跑
- 多个独立分析任务可并行
- agent team 拆分为并行子任务

## 何时不用

- 有依赖关系（A 产出 → B 消费）→ 串行
- 单 worker 任务 → 用 `run-cc-task.mjs`
- 实时交互式 CC 会话 → 用 cc-tmux 直驱
