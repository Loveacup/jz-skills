# 第二轮 GitHub 搜索（2026-05-30）

> 搜索范围：macOS system health / inspection / monitor / cleanup / Apple Silicon 工具
> 已有 7 个已吸收项目（mac_audit, macmonica, macguard-audit, system-monitor, machealth, Mac-Health-Check, check-mac）

## 新发现

### 1. tw93/mole ⭐ 高推荐

- **仓库**: https://github.com/tw93/mole
- **语言**: Rust（二进制分发）
- **核心能力**: 智能 App 卸载、磁盘空间分析器、实时系统状态仪表盘（含健康评分）、进程 CPU 阈值告警条
- **机器可读**: `--json` 输出
- **mac-doctor 缺失**: App 卸载逻辑、磁盘视觉分析、持续进程 CPU 告警
- **建议吸收**: 健康评分算法参考、App 卸载模式、`--json` 输出范式

### 2. metaspartan/mactop 🍎

- **仓库**: https://github.com/metaspartan/mactop
- **语言**: Go
- **核心能力**: Apple Silicon 原生监控 — GPU 频率、ANE 利用率、功耗（瓦特）、内存带宽、风扇转速/控制、Thermal 状态
- **机器可读**: `--headless` + `--json`
- **mac-doctor 完全缺失**: GPU/ANE/功耗/内存带宽 指标
- **建议吸收**: 新增 Tier 2e 硬件传感器子层

## 不考虑

| 项目 | 原因 |
|------|------|
| exelban/stats (24k⭐) | GUI 菜单栏 App（Swift），非 CLI |
| mac-cleanup/mac-cleanup-py | Python 清理脚本，已被 Tier 3 覆盖 |
| gccszs/disk-cleaner | Claude Code skill，跨平台，非 macOS 专精 |
| btop | Linux 通用资源监控器 |
