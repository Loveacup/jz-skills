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

`allowed_paths` 只是授权声明，不是 OS 沙箱。需要强隔离时，由上层提供临时目录、容器或独立 worktree，并保持单 writer。

## 启动映射与身份绑定

校验后的 grant 映射到 OMP 原生参数：

- `tools` → `--tools`
- `approval=non_interactive` → `--approval-mode yolo`（不再叠加 legacy `--auto-approve`）
- `cwd` → `--cwd`
- `add_dirs[]` → 重复 `--add-dir`

resolved contract 会写入 `state.run.capability`。启动指纹绑定 tools、approval、cwd、add_dirs、skills、system prompt，以及 OMP binary 的规范路径与 SHA-256；任一变化都会改变指纹。RPC 仅保留给无 grant 的 legacy 只读路径，其 daemon 复用前必须匹配该完整指纹。

## 结果边界

`execute` 不强制审计 verdict schema，但仍必须满足真实 exit code、完整 `turn_end`、`stopReason=stop` 和输出未截断。写入结果必须由协调层或当前 agent 重新读取 diff/产物并独立运行测试；OMP 自报成功不是验收证据。
