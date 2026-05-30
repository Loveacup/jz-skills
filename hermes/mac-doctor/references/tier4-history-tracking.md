# Tier 4: 历史追踪

> 来源：hritikvalluvar/macmonica

## 架构

`~/.hermes/inspection/history.db`（SQLite）

## Schema

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    cpu_percent REAL,
    memory_pressure TEXT,
    swap_used_mb REAL,
    disk_free_gb REAL,
    battery_health REAL,
    battery_cycles INTEGER,
    thermal_throttled INTEGER,
    load_avg_1min REAL,
    top_cpu_process TEXT,
    top_mem_process TEXT
);
```

## 分析

- `history --period 7d` — 趋势折线
- `compare 24h 7d` — 周期对比
- `anomaly-detect` — 7 天基线 ±2σ 异常检测
- `battery-forecast` — 线性回归预测电池降到 75% 天数
- `disk-forecast` — 线性回归预测磁盘耗尽天数（<30 天 → 🔴）

## 资源

| 指标 | 值 |
|------|---|
| 采集频率 | 10 分钟/次 |
| CPU 开销 | <0.1s/次 |
| 磁盘 | ~5MB/月 |
| 保留 | 90 天 |
