# upkeep 15-Phase Audit 参考

来源: [KyleNesium/upkeep](https://github.com/KyleNesium/upkeep)

upkeep 是一个 Claude Code skill，15 阶段 macOS 磁盘审计。我们取其检查组合理念，但不在 Hermes 中强依赖外部 CLI 工具。

## 阶段总览

| # | 阶段 | macOS | Linux/WSL2 | 巡检适用 |
|:-:|------|:-----:|:----------:|:-------:|
| 1 | Baseline | ✅ | ✅ | ✅ 必做 |
| 2 | 包管理器 (brew/apt/dnf/pacman) | ✅ | ✅ | ✅ |
| 3 | Dev 工具缓存 | ✅ | ✅ | ✅ |
| 4 | 孤儿 App 数据 | ✅ | ❌ | ⚠️ 高危 |
| 5 | LaunchAgents / systemd | ✅ | ✅ | ✅ |
| 6 | Docker | ✅ | ✅ | 可选 |
| 7 | Xcode | ✅ | ❌ | 可选 |
| 8 | Electron 缓存 | ✅ | ✅ | ✅ |
| 9 | 构建产物 | ✅ | ✅ | 可选 |
| 10 | Shell 配置 | ✅ | ✅ | 可选 |
| 11 | 日志 | ✅ | ✅ | ⚠️ |
| 12 | 大文件 | ✅ | ✅ | 可选 |
| 13 | iOS 备份 | ✅ | ❌ | ⚠️ |
| 14 | pipx 工具 | ✅ | ✅ | 可选 |
| 15 | macOS 更新缓存 | ✅ | ❌ | ⚠️ |

## 关键借鉴点

1. **Phase 1 Baseline 的 diskutil 用法** — 不是 df -h，而是 `diskutil info / | grep -E "Free|Available|Purgeable"`。我们改为 Container 级别 `Container Free Space`。

2. **Phase 4 孤儿 App 数据** — upkeep 通过 mdfind 交叉对比已安装 app 和 ~/Library/Application Support 残留。巡检中我们跳过这一步（高危），但清理时可用 `ls ~/Library/Application\ Support/` 手动比对。

3. **Phase 5 LaunchAgents 死链检查** — `/usr/libexec/PlistBuddy -c "Print :ProgramArguments:0"` 读取 plist，检查 binary 是否存在。我们纳入 Tier 2。

4. **Phase 3/8/9 缓存分层** — upkeep 分开检查 `~/Library/Caches`、`~/.cache`、Electron blob_storage、Xcode DerivedData。我们简化为 Tier 2 的 du 扫描 + 判断。

## 与 machine-doctor 的对比

| 维度 | upkeep | machine-doctor |
|------|--------|---------------|
| 定位 | 磁盘清理 | 系统健康 |
| 深度 | 15 阶段全覆盖 | 3 级分诊 |
| 平台 | macOS + Linux + WSL2 | macOS + Linux |
| 清理 | ✅ 可执行清理 | 只诊断，不清理 |
| 形式 | Claude Code skill | Claude Code skill |
| 输出 | 详细报告 | 表格 |

两者互补：machine-doctor 侧重进程/资源健康，upkeep 侧重存储空间回收。我们融合二者做 macOS 设备巡检。
