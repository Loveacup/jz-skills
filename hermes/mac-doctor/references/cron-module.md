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

### 告警类型 (v2.2)

| 触发条件 | 级别 | 安静时段 |
|---------|:---:|:---:|
| CPU 单进程持续 ≥5min 超阈值（E1 窗口告警） | 🔴 | 不受限 |
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

### 当前配置（5 Jobs）

| Job ID | 频率 | 模式 | 说明 |
|--------|:--:|:--:|------|
| `mac-doctor-quick` | 30min | 🔇 Watchdog | 静默看门狗 — 问题才推送，0 tokens |
| `check-skill-copies` | 1h | 🔇 Watchdog | cron-worker 本地副本扫描 — 残留才推送 |
| `system-health-watchdog` | 1h | 🔇 Watchdog | 三检合一看门狗：Kanban 完整性 + 僵尸进程 + SWAP 防崩 |
| `mac-doctor-deep` | 每日 03:00 | 🤖 LLM | Tier 2 全量审计（安全+硬件+网络） |
| `mac-doctor-weekly` | 周一 09:00 | 🤖 LLM | 周报 + history.db 趋势分析 |

#### system-health-watchdog 三检

| 检查项 | 方法 | 阈值 | 来源 |
|--------|------|------|------|
| Kanban 完整性 | `sqlite3 PRAGMA integrity_check` | ≠ `ok` 报警 | Kanban 损坏根因报告 |
| 僵尸进程 | `ps aux` 查 `Z` 状态 | >0 报警 | A2A BUG-006 / P2-12 |
| SWAP 防崩 | `sysctl vm.swapusage` | >5GB 或 >80% | Swap 危机事件报告 05-30 |

脚本：`~/.hermes/profiles/cron-worker/scripts/system-health-watchdog.py`

### 静默看门狗模式 (v2.3) 🆕

高频巡检（≤30min）推荐用 `no_agent + script` 替代 LLM agent，大幅节省 token：

```
Watchdog 脚本 → collector-daemon.py --json → 检查 alerts
  ├── 无 hard alert + diagnosis 健康 → 静默
  └── 有 hard alert 或 diagnosis 有问题 → 推送
```

| 对比 | LLM Agent | Silent Watchdog |
|------|:---:|:---:|
| Token 消耗 | ~3000/次 | **0** |
| 响应延迟 | 5-15s | <2s |
| 静默支持 | ❌ 每次都输出 | ✅ 自动静默 |
| 分析深度 | 可解读趋势 | 仅阈值判断 |

脚本位置：`~/.hermes/profiles/cron-worker/scripts/mac-doctor-watchdog.py`

#### 配置示例

```bash
# 通过 Hermes cronjob 工具配置:
cronjob update:
  job_id: <quick-job-id>
  no_agent: true
  script: "mac-doctor-watchdog.py"
  skills: []  # 清空 skills，纯脚本模式
```

#### 原理 (v2.3)

`cronjob` 的 `no_agent=True` 模式：
- **stdout 非空** → 内容作为消息体推送到 Telegram
- **stdout 为空** → 完全静默，不消耗任何消息
- **exit ≠ 0** → 发送错误通知

Watchdog 脚本调用 `collector-daemon.py --json`，**区分两种告警**：

| 类型 | 判断 | 行为 |
|------|------|------|
| **threshold alert** | `is_anomaly=False` | 硬伤 — 不管 diagnosis 说什么都推送 |
| **anomaly alert** | `is_anomaly=True`（z > σ 统计偏差）| 软信号 — 仅当 diagnosis ≠ "All clear" 时附带 |

```python
threshold_alerts = [a for a in alerts if not a.get("is_anomaly", False)]

if not threshold_alerts and diagnosis == "All clear":
    sys.exit(0)  # 静默：diagnosis 说健康，无硬伤
```

> ⚠️ **为什么不能只用 `not alerts`：** 纯统计异常（如 CPU 从夜间安静基线 15% 跳到早晨 28%，z=2.2 > σ 但绝对值健康）不是系统问题。`diagnose()` 综合判断比 anomaly 单指标更可靠。旧逻辑 `not alerts` 会把这类低信号推送出去。

> ⚠️ **容错：** 脚本使用显式 `is not None` 判断而非 `dict.get(key, default)`。`get()` 只在 key 不存在时用 default，但 key 存在且 value 为 `null` 时返回 `None`，会导致 `NoneMB`/`NoneGB` 脏数据。

> ⚠️ **sysctl swapusage 正则陷阱：** `sysctl vm.swapusage` 输出格式为 `total = 3072.00M  used = 1741.44M` — **`total` 在 `used` 前面**，不是直觉中的 `used 在 total 前`。正则必须匹配 `total.*used` 顺序，否则永远匹配不到。

---

## 跨 Profile 配置陷阱 ⚠️ (v2.3)

`collector-daemon.py` 使用 `Path.home() / ".hermes" / "inspection" / "config.json"` 读取配置。
**在 cron-worker profile 下 `HOME` 指向 profile home**（如 `.../profiles/cron-worker/home/`），不是 `/Users/alexcai`。

**存在两份 config.json，修改阈值时必须同步：**

| 路径 | 谁读 |
|------|------|
| `~/.hermes/inspection/config.json` | LaunchAgent / 手动执行 / 非 cron 环境 |
| `~/.hermes/profiles/cron-worker/home/.hermes/inspection/config.json` | cron job 执行时 |

不同步的后果：手动测试和 cron job 看到不同的阈值，行为不一致。

---

## Anomaly Detection 参数 (v2.3)

| 参数 | 值 | 说明 |
|------|:--:|------|
| `anomaly.sigma` | **3.0** | 3σ ≈ 0.3% 误报率。旧值 2.0 对新基线（<7 天数据）过于敏感 |
| `anomaly.baseline_days` | 7 | 基线窗口 |
| `anomaly.enabled` | true | 保留开启——配合 watchdog 的 threshold-vs-anomaly 静默策略，纯异常不推送 |

### 基线成熟度陷阱

新装 collector 的前几周，baseline 不具代表性——夜间数据多、白天少。此时即使 σ=3.0，白天正常活动仍可能触发异常 z-score。

**缓解方案：** watchdog 已区分 threshold/anomaly，纯异常静默。anomaly detector 作为"趋势指示器"而非告警源——当 diagnosis 也认为有问题时，anomaly 数据提供佐证。

---

### 添加 Cron Job 示例（LLM Agent 模式）

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
  "cpu_sustained": {
    "enabled": true,
    "threshold": 80,
    "window_minutes": 5
  },
  "anomaly": {
    "enabled": true,
    "baseline_days": 7,
    "sigma": 3.0
  },
  "cleanup_safety": {
    "oplog_enabled": true
  }
}
```

### DB Schema

见 `references/tier4-history-tracking.md`。
