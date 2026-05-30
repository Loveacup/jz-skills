# Cron 模块架构

## 双层设计

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1: LaunchAgent (系统级)                            │
│  ─────────────────────────────                            │
│  进程: collector-daemon.py (每 10 分钟)                    │
│  职责: 数据采集 → SQLite + 阈值告警 + 异常检测              │
│  配置: ~/.hermes/inspection/config.json                  │
│  数据: ~/.hermes/inspection/history.db                   │
│  零 LLM token 消耗，纯 Python                             │
├──────────────────────────────────────────────────────────┤
│  Layer 2: Hermes Cron (智能调度)                          │
│  ─────────────────────────────                            │
│  调度: cron-worker profile 的 cronjob 工具                │
│  职责: 定时巡检 + 评分报告 + Telegram 推送                 │
│  依赖: Layer 1 的 history.db（供趋势分析）                 │
└──────────────────────────────────────────────────────────┘
```

## Layer 1: 系统级采集

### 安装

```bash
cd ~/.hermes/skills/apple/mac-doctor
bash scripts/install-daemon.sh
```

### 管理

| 命令 | 作用 |
|------|------|
| `launchctl list com.hermes.inspection-collector` | 查看状态 |
| `launchctl unload ~/Library/LaunchAgents/com.hermes.inspection-collector.plist` | 停止 |
| `launchctl load ~/Library/LaunchAgents/com.hermes.inspection-collector.plist` | 启动 |
| `tail -f /tmp/hermes-inspection-collector.log` | 查看日志 |
| `python3 scripts/collector-daemon.py` | 手动执行一次 |

### 卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.hermes.inspection-collector.plist
rm ~/Library/LaunchAgents/com.hermes.inspection-collector.plist
# 数据保留在 ~/.hermes/inspection/，手动删除:
# rm -rf ~/.hermes/inspection/
```

### 数据采集频率

- 默认 10 分钟/次（600 秒）
- 修改 `~/.hermes/inspection/config.json` → `collection.interval_seconds`
- 修改后需 reload LaunchAgent

### 告警类型

| 触发条件 | 级别 | 安静时段 |
|---------|:---:|:---:|
| CPU >80% | 🔴 | 不受限 |
| 内存 critical | 🔴 | 不受限 |
| 磁盘 <10% | 🔴 | 不受限 |
| Swap >4GB | 🟡 | 遵守 |
| 电池 <80% | 🟡 | 遵守 |
| 异常检测 | 🟡 | 遵守 |

安静时段默认 23:00-07:00，致命告警（前 3 项）不受限。

---

## Layer 2: Hermes Cron 定时巡检

### 配置的 Cron Jobs

通过 `cronjob` 工具在 cron-worker profile 中配置。详见 SKILL.md Tier 0-3 的决策树。

### 建议调度

| Job | 频率 | 说明 |
|-----|------|------|
| inspection-quick | 每 30 分钟 | Tier 1 快速巡检 + 健康分，推 Telegram |
| inspection-deep | 每天 03:00 | Tier 2 全量审计（安全+硬件+网络），推 Telegram |
| inspection-weekly | 每周一 09:00 | 周报汇总，引用 history.db 趋势数据 |

### 添加 Cron Job 示例

```
# 通过小黄在 cron-worker session 中执行:
cronjob create:
  name: inspection-quick
  schedule: "30m"
  prompt: "加载 mac-doctor skill，执行 Tier 1 快速巡检并输出健康评分"
  deliver: "origin"
  skills: ["mac-doctor"]
```

---

## 配置参考

### `~/.hermes/inspection/config.json`

```json
{
  "collection": {
    "interval_seconds": 600,
    "retention_days": 90,
    "quiet_hours": {"enabled": true, "start": 23, "end": 7}
  },
  "alerts": {
    "cpu_threshold": 80,
    "memory_pressure_threshold": "high",
    "swap_threshold_gb": 4,
    "disk_threshold_percent": 10,
    "battery_health_threshold": 80
  },
  "anomaly": {
    "enabled": true,
    "baseline_days": 7,
    "sigma": 2.0
  }
}
```

### DB Schema

见 `references/tier4-history-tracking.md`。
