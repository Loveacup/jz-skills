# Tier 5: 智能告警 & 自动化

> 来源：hritikvalluvar/macmonica + Neo23x0/macguard-audit + mole (E1 窗口告警 v2.2)

## 告警规则

| 条件 | 级别 | 动作 |
|------|:---:|------|
| CPU 单进程持续 ≥5min 超阈值 | 🔴 | macOS 通知（E1 窗口告警） |
| 内存压力 = critical | 🔴 | macOS 通知 |
| Swap >4GB | 🟡 | macOS 通知 |
| 磁盘 <10% | 🔴 | macOS 通知 |
| 电池健康 <80% | 🟡 | 单次通知 |
| 异常检测触发 | 🟡 | 通知 + 日志 |

## E1: CPU 持续窗口告警 (v2.2)

来源：mole `process_watch.go`。替代原来的瞬时 CPU 阈值告警，消除 Spotlight/编译等 30s 尖峰误报。

### 工作原理

1. `collect_cpu_processes(threshold)` — 每秒 ps 扫描 CPU 超阈值的进程
2. `check_cpu_sustained()` — 维护 `process_watch` 表，追踪 (pid, ppid, cmd) 三元组
3. 进程首次超阈值 → 记录 `first_above_ts`
4. 每次 daemon 调用（每 10min）检查 `elapsed ≥ window_minutes`
5. 窗口满 → 触发告警，标记 `triggered_ts` 防重复
6. 进程退出/降至阈值下 → 自动清理记录

### 配置

```json
"cpu_sustained": {
  "enabled": true,
  "threshold": 80,
  "window_minutes": 5
}
```

### 数据库

`process_watch` 表（`history.db`）：`pid, ppid, cmd, first_above_ts, triggered_ts`

## 实现

### macOS 通知

```bash
osascript -e 'display notification "Chrome CPU 持续 5min: 85%" with title "⚠️ 系统巡检" sound name "Glass"'
```

### 调度方式

LaunchAgent (`~/Library/LaunchAgents/com.hermes.inspection-collector.plist`) 每 10 分钟执行 `scripts/collector-daemon.py`。一键安装：`bash scripts/install-daemon.sh`。

### 安静时段

23:00-07:00 不发非紧急通知。致命告警（kernel panic、磁盘 <5%）不受限制。
