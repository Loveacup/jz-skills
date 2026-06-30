# Windows SSH + PowerShell 远程命令效率问题（2026-06-27）

## 触发场景

通过 SSH 连接到 Windows 设备（OpenSSH_for_Windows_9.5）执行远程命令时，出现：
- 命令无输出（执行后没有任何返回）
- 命令超时（长时间无响应后超时）
- 效率低下（简单命令需要数秒才能返回）

## 环境信息

| 项目 | 值 |
|------|-----|
| 设备 | Windows 7800x3d (192.168.2.31) |
| SSH 服务端 | OpenSSH_for_Windows_9.5 |
| 默认 Shell | `cmd.exe` (非 PowerShell) |
| PowerShell 执行策略 | CurrentUser: RemoteSigned |
| OMP 版本 | 16.2.0 (运行中) |

## 根因分析

### 1. PowerShell 启动慢

PowerShell 启动需要 5-10 秒，超过默认超时时间。

**症状**：
```bash
# 这个命令会超时
timeout 5 ssh windows 'powershell -Command "Write-Host test"'
# → command timed out or failed
```

**解决方案**：
- 使用 `cmd /c` 代替 PowerShell 执行简单命令
- 将 PowerShell 脚本写入文件再执行
- 增加超时时间到 15-30 秒

### 2. OMP 命令阻塞

`omp` 命令直接执行会阻塞 SSH 会话（需要交互式环境）。

**症状**：
```bash
# 这个命令会阻塞 60 秒
timeout 60 ssh windows 'omp --version'
# → 超时无输出
```

**解决方案**：
- 使用 `Start-Process -Wait` 执行 OMP
```bash
ssh windows 'powershell -Command "Start-Process omp -ArgumentList ''--version'' -NoNewWindow -Wait"'
# → omp/16.2.0
```

### 3. 命令长度限制

过长的命令（特别是包含多个引号转义的 PowerShell 命令）会被截断或解析错误。

**症状**：
```bash
# 长命令无输出
ssh windows 'powershell -Command "Write-Host \"Searching...\"; $paths = ..."'
# → 无输出
```

**解决方案**：
- 将复杂命令写入 `.ps1` 文件再执行
```bash
ssh windows 'echo Write-Host "test" > %TEMP%\script.ps1 && powershell -File %TEMP%\script.ps1'
```

## 推荐执行模式

| 场景 | 推荐方式 | 示例 |
|------|----------|------|
| 简单命令 | `cmd /c` | `ssh windows 'cmd /c "echo test"'` |
| 文件操作 | `cmd` 内置 | `ssh windows 'dir /b %APPDATA%\Obsidian'` |
| 复杂 PowerShell | 写入文件 | `ssh windows 'echo ... > %TEMP%\script.ps1 && powershell -File ...'` |
| OMP 命令 | `Start-Process -Wait` | `ssh windows 'powershell -Command "Start-Process omp ..."'` |
| 读取文件 | `more` 或 `type` | `ssh windows 'more %APPDATA%\Obsidian\obsidian.json'` |

## 已验证成功的命令

```bash
# 读取 Obsidian vault 路径
ssh windows 'more %APPDATA%\Obsidian\obsidian.json'
# → {"vaults":{"8ea116bdfaf894f9":{"path":"D:\\Obsidian知识库\\Alex Cai\\AlexCai",...}}

# 使用 OMP 获取版本
ssh windows 'powershell -Command "Start-Process omp -ArgumentList ''--version'' -NoNewWindow -Wait"'
# → omp/16.2.0

# 检查进程
ssh windows 'tasklist | findstr omp'
# → omp.exe 3900 Console ...
```

## 注意事项

1. **避免长命令**：超过 200 字符的命令容易出问题
2. **避免嵌套引号**：PowerShell 的引号转义容易出错
3. **使用文件中转**：复杂命令先写入文件再执行
4. **设置合理超时**：简单命令 10 秒，复杂命令 30-60 秒
