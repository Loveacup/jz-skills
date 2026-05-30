# Tier 5: 智能告警 & 自动化

> 来源：hritikvalluvar/macmonica + Neo23x0/macguard-audit

## 告警规则

| 条件 | 级别 | 动作 |
|------|:---:|------|
| CPU >80% 持续 5 分钟 | 🔴 | macOS 通知 |
| 内存压力 = critical | 🔴 | macOS 通知 |
| Swap >4GB | 🟡 | macOS 通知 |
| 磁盘 <10% | 🔴 | macOS 通知 |
| 电池健康 <80% | 🟡 | 单次通知 |
| 异常检测触发 | 🟡 | 通知 + 日志 |

## 实现

### macOS 通知

```bash
osascript -e 'display notification "CPU 持续 85%+ 超过 5 分钟" with title "⚠️ 系统巡检" sound name "Glass"'
```

### 调度方式

LaunchAgent (`~/Library/LaunchAgents/com.hermes.inspection-collector.plist`) 每 10 分钟执行 `scripts/collector-daemon.py`。一键安装：`bash scripts/install-daemon.sh`。

### 安静时段

23:00-07:00 不发非紧急通知。致命告警（kernel panic、磁盘 <5%）不受限制。
