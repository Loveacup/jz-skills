# Hermes Gateway plist 环境变量修复

> 读取时机：`config.yaml` 已配置 provider/fallback，但 launchd 启动的 gateway 仍认证失败或反复重启。

## 根因

`providers.<name>.key_env` 只声明要读取哪个环境变量。由 launchd 启动的 gateway 不继承交互式 shell 的 `~/.zshrc`；所需变量必须由 LaunchAgent 的 `EnvironmentVariables` 或受支持的 Hermes 配置机制提供。

## 诊断

1. 读取 `config.yaml`，确认 provider、`key_env` 和 fallback 引用关系。
2. 读取 LaunchAgent plist，仅检查变量名是否存在；不要回显值。
3. 查看 gateway 日志中的 provider/auth 错误和重启时间线。
4. 修改前备份 plist；修改环境变量或重载 LaunchAgent 属于外部副作用，必须得到明确授权。

## 修复原则

- 不把密钥写进 skill、任务包、日志或 Git。
- 优先使用 Hermes 官方配置/安装命令；必须改 plist 时，用 `plutil` 写入并保留备份。
- 重载后验证多个时间点的 health、PID 稳定性和 fallback 实际成功，不以“进程出现过”作为治愈证据。
- OMP 只能作为经授权的执行通道，不能绕过用户确认和危险操作 gate。
