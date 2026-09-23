# Capability Grant v1

`call-omp` 是一次 OMP attempt 的机制适配器，不是授权签发者。协调层决定是否授权；本 skill 只校验并忠实映射能力，绝不静默扩大。

## 默认行为

缺少 `capability_grant` 时保持旧只读合同：

```text
read,grep,glob,lsp,web_search
```

废弃的 `--allow-write` 仍固定退出 2，不是授权入口。

## 合同

仅 `mode=execute` 且 `channel=shell` 可带。v1 暂不支持 RPC（无法为单 attempt 提供可信 exit code）或 ACP（不能保真传递 grant）：

```json
{
  "capability_grant": {
    "contract": "call-omp.capability-grant.v1",
    "tools": ["read", "write", "edit", "bash"],
    "approval": "non_interactive",
    "cwd": "/absolute/existing/workspace",
    "add_dirs": []
  }
}
```

支持的工具名由 `scripts/gate/resolve-capability-grant.py` 的 `KNOWN_TOOLS` 定义。未知字段、未知/重复工具、相对路径或不存在目录一律 fail-closed。

## 路径与写入约束

`write|edit|bash|python|notebook|browser|computer|task` 属于 host-affecting，但以下路径约束适用于所有显式 grant：

- 每个 grant 都必须声明现存绝对目录 `cwd`，避免进程继承调用者 cwd；
- `scope.cwd` 若存在，规范化后必须与 grant 的 `cwd` 相同；
- 任何显式 grant 的 `scope.allowed_paths` 都必须覆盖 `cwd` 与所有 `add_dirs`，包括只读 grant；
- `scope.denied_paths` 必须为空，因为 call-omp 不提供文件系统沙箱，不能假装可强制 deny；
- `bundle_only`、RPC 和 ACP 通道不接受 grant；
- `--no-auto-approve` 与显式 grant 冲突；非交互 attempt 不猜测审批语义。

`allowed_paths` 只是授权声明，不是 OS 沙箱。临时目录与独立 worktree 只隔离工作文件；强制限制恶意 worker 需要真正的容器或 OS 沙箱。私有状态文件与身份校验不能防御已获得同 UID 任意代码执行权限的 worker。

## 启动映射与身份绑定

校验后的 grant 映射到 OMP 原生参数：

- `tools` → `--tools`
- `approval=non_interactive` → `--approval-mode yolo`（不再叠加 legacy `--auto-approve`）
- `cwd` → `--cwd`
- `add_dirs[]` → 重复 `--add-dir`

resolved contract 会写入 `state.run.capability`。启动指纹绑定 tools、approval、cwd、add_dirs、skills、system prompt，以及 OMP binary 的规范路径与 SHA-256；任一变化都会改变指纹。RPC 仅保留给无 grant 的 legacy 只读路径，其 daemon 复用前必须匹配该完整指纹。

## 执行生命周期与取消

所有实际 Shell `execute` 路径使用 `execute_v1`，包括无 grant 的只读执行和允许的 RPC→Shell 回退；bundle-only 的既有 `verdict_v1` 路径不变。Python 缺少 `waitid/WNOWAIT`、信号屏蔽或必要的 POSIX 能力时，不启动 worker。

- 同一 task 的 START/SEND/MONITOR/FINISH/STOP 共用生命周期锁。每次实际启动分配 UUIDv4 `attempt_id`；完整启动指纹同时绑定身份、真实 argv 摘要、二进制、能力及资源路径。
- SEND 先持久化身份，再启动 supervisor。串行化或持久化失败不得启动；已启动后的发布失败必须请求取消，不能转无监督路径。
- 协调者保存 SEND 的固定身份，以 `omp-stop.sh --state "$STATE" --attempt-id "$ATTEMPT_ID" --launch-fingerprint "$LAUNCH_FINGERPRINT" --reason "reason" --timeout 10` 取消。STOP 不接受任意 PID/PGID，也不自行发送进程信号。
- supervisor 独占资源 receipt 与 identity sidecar，协调者只发布 `call-omp-cancel.v1` 请求。请求必须匹配 task/attempt/fingerprint；旧 watcher 与旧 FINISH 不能作用于 successor。
- stdout/stderr 分别有界捕获，不把流大小限制施加到 worker 创建的业务文件。保留真实 `worker_exit_code`（信号退出为负数）、`supervisor_exit_code`、`terminal_reason` 与 `cleanup_confirmed`。
- 正常完成、取消、超时、TERM/INT/HUP 和控制通道错误均进入有界 cleanup。leader 在最后一次进程组信号之前保持未 reap，避免数值 PID/PGID 重用时误杀。
- 终态决策在 cleanup 后屏蔽终止信号，纳入当时已送达/待处理信号并读取最后一个取消请求。该截止点早于 receipt 发布；其后的信号不撤销已经清理的执行结果。公开 STOP 仍通过主状态的 cancellation fence 阻止业务接受迟到结果。
- `cleanup_confirmed` 只覆盖实际观察到的进程组与 direct child，不证明任意 `setsid`/double-fork 且关闭继承管道的后代已停止。发现逃逸或无法确认时保留 unknown，不能自动启动替代者。
- supervisor 被 SIGKILL、遗留锁或无法证明停止时，需要人工调查；沉默、`worker_done`、超时都不是停止证明。
- task 复用保留逻辑任务的 round/reject 计数，不因换 attempt 重置预算。已接受且证据匹配的任务重复 monitor/stop 不撤销其历史终态。
- child 继承 `CALL_OMP_DEPTH`；递归 START/SEND 在计数、状态写入和启动前拒绝。该标记是防递归机制，不是对恶意 worker 的安全沙箱。

## 结果边界

`execute` 不强制审计 verdict schema，但仍必须满足真实 exit code、完整 `turn_end`、`stopReason=stop` 和输出未截断。写入结果必须由协调层或当前 agent 重新读取 diff/产物并独立运行测试；OMP 自报成功不是验收证据。
