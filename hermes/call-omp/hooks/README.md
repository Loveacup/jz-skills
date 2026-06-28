# hooks/ —— 预留：未来 MCP/ACP/omp-hook 事件驱动监控

当前 omp skill 的监控是**轮询式**：`omp-send --async` 后台跑 omp，`omp-monitor` 轮询状态文件 +
raw JSONL 增长 + pid 存活。这够用且零依赖，但不是事件驱动。本目录为未来事件驱动监控预留。

## 现状（无需 hooks）

```
omp-send --async → 记 pid 到状态文件 → omp-monitor 轮询（pid 存活 / raw 行数 / turn_end）
干预：kill <pid>
```

## 未来事件驱动的三条真实路径

1. **omp `--hook <file>`（v16.2.2 已支持）**
   omp 可加载 JS hook/extension（`omp --hook hook.js` / `-e ext.js` / `--plugin-dir`）。
   未来可注入一个 hook，在 omp **工具调用 / turn 结束 / 错误**时回写
   `${OMP_TMPDIR}/omp-event-<task_id>.jsonl`，让 `omp-monitor` 改读**事件**而非 diff 整个 raw，
   实现近实时、低开销监控。需先验证 omp hook 的事件 API 与回调时机。

2. **MCP server 事件**（待验证）
   若 OMP 暴露 MCP server，Hermes MCP client 可订阅工具事件。当前未见对应子命令。

3. **ACP `delegate_task` 回调**（待 Hermes #32401）
   `omp acp`（server over stdio）已在；ACP 委派的进度/结果回调字段待 #32401 合入后接线。

## 与 cc-tmux/hooks 的对照

cc-tmux 用 Claude Code 的 hook（`cc-posttool.sh` / `cc-status-writer.sh` / `cc-stop-check.sh`）
把监控从 LLM 轮询移到守时 shell。omp 这边的等价物将是上面的 **omp `--hook` JS 回调**——
但需先冒烟验证事件 API，未验证前不落地（不得把待验证写成已实现）。

## 约定（落地时遵守）

- 事件文件键名与状态文件同源：`omp-event-<task_id>`，与 `omp-state-<task_id>` / `omp-raw-<task_id>` 对齐。
- 事件回写必须原子（tmp + mv），与 `lib/omp-lib.sh::atomic_write` 一致。
- 事件驱动**不替代** gate；任何通道的输出仍须过 gate-verify / gate-danger / gate-counter。
- 清理纳入 `omp-gc.sh`（按 task_id 一并回收）。
