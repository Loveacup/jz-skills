# macOS 设备巡检

> 一键检查你的 Mac 健康状况 — 从 CPU 到安全，从磁盘到隐私。

## 这是什么？

一个 **六级巡检体系** 的 macOS 系统健康检查工具。不是那种"装个菜单栏 App 看看 CPU 温度"的玩具 — 它会：

- 🔍 **全面检查**：资源 / 安全 / 硬件 / 网络 / 隐私，共 50+ 项
- 📊 **健康评分**：0-100 分，一眼看出你的 Mac 状态
- 🧹 **安全清理**：npm/uv/brew/Chrome 缓存一键回收空间
- 📈 **历史追踪**：趋势对比 + 异常检测，不是看完就忘的快照
- 🔔 **智能告警**：磁盘满了、CPU 飙了 → 自动弹通知
- ⏰ **全自动**：装好就不用管，后台默默采集 + 定时报告

## 快速开始

```bash
# 1. 安装后台采集器（一次性）
cd ~/.hermes/skills/apple/mac-doctor
bash scripts/install-daemon.sh

# 2. 手动跑一次快速巡检
python3 -c "
from hermes_tools import terminal
# 加载 skill 跑 Tier 1
"
```

装好后每 10 分钟自动采集快照，每 30 分钟推一次健康评分到 Telegram。

## 六级体系

```
Tier 0  🏃 即时评分  →  "你的 Mac 82 分，良好"
Tier 1  ⚡ 快速巡检  →  CPU / 内存 / Swap / 磁盘 / 大户进程
Tier 2  🔍 深度审计  →
  ├ 2a: Dev 缓存 + Homebrew + 启动项
  ├ 2b: 安全检查 (FileVault/防火墙/SSH/SIP...)
  ├ 2c: 硬件健康 (电池/SMART/热节流)
  └ 2d: 网络审计 (端口/DNS/Wi-Fi/蓝牙)
Tier 3  🧹 安全清理  →  缓存 + 臃肿检测 + 隐私扫描
Tier 4  📈 历史追踪  →  趋势对比 + 异常检测 + 电池预测
Tier 5  🔔 智能告警  →  CPU 飙了、磁盘满了 → 通知你
```

## 架构

```
┌─ Layer 1 (系统级) ─────────────────────┐
│  collector-daemon.py                   │
│  每 10 分钟采集 → SQLite 数据库         │
│  触发阈值 → macOS 原生通知              │
│  零 LLM token 消耗，纯 Python           │
└────────────────────────────────────────┘
         │
         ▼
┌─ Layer 2 (智能调度) ───────────────────┐
│  Hermes Cron Jobs                      │
│  每 30 分钟 → 快速巡检 + 评分 → Telegram │
│  每天凌晨   → 全量审计 → Telegram       │
│  每周一     → 趋势周报 → Telegram       │
└────────────────────────────────────────┘
```

## 自定义配置

所有阈值和行为都可以改。编辑 `~/.hermes/inspection/config.json`：

```json
{
  "alerts": {
    "cpu_threshold": 80,           // CPU 超过 80% 告警
    "disk_threshold_percent": 10,  // 磁盘低于 10% 告警
    "battery_health_threshold": 80 // 电池健康低于 80% 告警
  },
  "collection": {
    "interval_seconds": 600,       // 采集间隔
    "quiet_hours": { "enabled": true, "start": 23, "end": 7 }
  },
  "webhooks": {
    "slack": "",                   // 填上 Slack webhook URL 就推送到 Slack
    "discord": "",                 // 同上，Discord
    "ntfy": ""                     // 同上，ntfy.sh
  },
  "tiers": {
    "tier2b_security": true,       // 不需要安全检查？关掉
    "tier3_privacy": true          // 不需要隐私扫描？关掉
  }
}
```

完整配置模板在 `templates/config.json`，每个字段都有注释。

## 常见问题

**Q: 会不会很占资源？**
A: 采集器每 10 分钟跑一次，每次 < 0.1 秒 CPU，约 28MB 内存，数据库 ~5MB/月。

**Q: 数据存在哪？会不会上传？**
A: 全部本地 — `~/.hermes/inspection/history.db`。除非你主动配了 webhook，否则不出你的机器。

**Q: 我是台式机 (Mac mini/Studio/Pro)，电池检查怎么办？**
A: 自动识别桌面 Mac，跳过电池相关检查。

**Q: 能卸载吗？**
A: `launchctl unload ~/Library/LaunchAgents/com.hermes.inspection-collector.plist && rm ~/Library/LaunchAgents/com.hermes.inspection-collector.plist`。数据库留在 `~/.hermes/inspection/`，手动删。

**Q: 和 Stats/iStat Menus 有什么区别？**
A: 那些是实时仪表盘。我们是巡检 — 定期全量检查 + 评分 + 告警 + 趋势追踪。互补关系。

## 灵感来源

本项目吸收了以下开源项目的精华：

| 项目 | 学到的 |
|------|--------|
| [gfreedman/mac_audit](https://github.com/gfreedman/mac_audit) | 69 项检查 + 健康评分 |
| [hritikvalluvar/macmonica](https://github.com/hritikvalluvar/macmonica) | 历史追踪 + 异常检测 |
| [Neo23x0/macguard-audit](https://github.com/Neo23x0/macguard-audit) | SIEM 告警架构 |
| [TheSmilemakers/system-monitor](https://github.com/TheSmilemakers/system-monitor) | 隐私扫描 + 臃肿检测 |
| [tw93/Mole](https://github.com/tw93/Mole) | 清理 CLI 设计 |
| [exelban/stats](https://github.com/exelban/stats) | 菜单栏监控参考 |

## 许可

MIT
