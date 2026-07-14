# Gateway 救援与沙箱边界

> 读取时机：Hermes 自身拒绝 gateway 生命周期命令，或需要判断 OMP 是否适合作为受控外部执行通道时。

## 当前合同

- 当前兼容基线：OMP `16.3.2`；`omp --version` 只证明版本，不证明 model/provider 可用。
- 普通诊断优先使用 Hermes 自己的只读工具：`curl`、日志读取、进程与 launchd 状态查询。
- 只有用户明确授权重启/恢复 gateway，且 OMP bounded smoke 成功后，才允许 OMP 执行生命周期命令。
- 不把一次 health-check 失败视为真死；按多个时间点采样，区分启动中、重启循环和持续不可达。
- OMP 的 `--auto-approve`/`--approval-mode yolo` 不覆盖 call-omp 自己的 scope、rollback 与危险模式 gate。

## 受控流程

1. `omp --version`，确认 CLI 存在且版本符合当前兼容基线。
2. 运行一次不带写权限的 bounded smoke；失败即停止，不把 launchd 自愈误归因给 OMP。
3. 把实际命令写入单独脚本，人工检查 scope 与 rollback；不要把凭据写入 task/package。
4. call-omp 不开放 `bash`；把审定后的脚本交给明确授权的人工或 `cc-tmux` 执行，并保存 stdout/stderr。
5. 执行后重新采样 health 和日志；以真实 PID/HTTP/日志时间线判断结果。

## 已知 hardline

OMP 可能无条件拦截包含 `shutdown`、`reboot`、`halt`、`poweroff` 等字面量的输入，即使它们只出现在注释或日志过滤条件中。不要尝试绕过 hardline；改用只读诊断或人工路径。

## 历史归因订正

早期一次“OMP 救活 gateway”的结论后来证明是 launchd `KeepAlive` 自愈。任何成功声明都必须同时证明：OMP 确实执行了目标命令、命令退出码可见、执行前后 PID/health 时间线发生了相符变化。
