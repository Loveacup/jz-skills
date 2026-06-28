# Cron 模块架构

## v3 三层架构（2026-06-28 重构）

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
│  Layer 2: mac-doctor-watchdog (cron quick, 30min)          │
│  ─────────────────────────────                            │
│  进程: mac-doctor-watchdog.py (cron, no_agent)            │
│  职责: 阈值过滤 + 冷却去重 + 集成 preferences + 触发 L3     │
│  配置: ~/.hermes/profiles/cron-worker/state/              │
│        mac-doctor-watchdog-state.json (state file)       │
│  持久化: ~/.hermes/inspection/preferences.json            │
│  触发: ~/.hermes/inspection/.triage-trigger               │
├──────────────────────────────────────────────────────────┤
│  Layer 3: mac-doctor-triage (cron triage, 12h+触发)       │
│  ─────────────────────────────                            │
│  进程: mac-doctor-triage.py (cron, LLM agent)            │
│  职责: LLM 解读趋势 + 写入 memory + 决定推送              │
│  配置: ~/.hermes/inspection/preferences.json              │
│        .interpretations[] + suppressions[]               │
│  触发: quick 推送触发 + 12h 兜底                          │
└──────────────────────────────────────────────────────────┘
```

## 双层设计（v2.5 → v3 演进）

```
v2.5 (旧)                    v3 (新)
─────────────────────────    ─────────────────────────
Layer 1: collector            Layer 1: collector (不变)
─────────────────────────    ─────────────────────────
Layer 2:                     Layer 2:
  mac-doctor-quick             mac-doctor-watchdog
  + system-health-watchdog    (整合三检 + preferences)
  + MCP cleanup               写 preferences + trigger
─────────────────────────    ─────────────────────────
                              Layer 3: mac-doctor-triage
                                LLM agent 诊断
```

## Layer 1: 系统级采集（v2.2 不变）

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

## Layer 2: mac-doctor-watchdog（v3 升级）

### 职责

- 读 collector stdout JSON → 阈值过滤
- 附加检查：Kanban 完整性 / 僵尸进程 / MCP 孤儿清理
- **集成 `preferences.load()`**（v3 新增）
- **known_short_running_tools 白名单**（v3 新增）—— ccusage / npm install 等短跑工具 CPU 100% 标 transient
- **冷却去重**（v3 升级）—— 3 类 signature（磁盘 free / 僵尸 PID 集合 / MCP cleaned）3h TTL
- **写 preferences.suppressions**（v3 新增）—— 同 signature 累积写入
- **写 `.triage-trigger` 文件**（v3 新增）—— 触发 Layer 3 LLM 诊断
- 有异常 → stdout 输出 → Telegram

### 安装（v3）

不再独立配置 watchdog cron，**通过 `mac-doctor install` 一键注册**：

```bash
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor install
```

这会自动：
1. 检查 L1 collector 存在
2. 跑 install-daemon.sh（幂等 load-if-missing LaunchAgent）
3. 注册 4 个 cron（见 §3 注册表）
4. 验证 `launchctl list | grep inspection && cronjob list | grep mac-doctor`

### 管理

```bash
# 看 cron 状态
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor status

# 看 preferences
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor preferences show

# 验证 7 项 checklist
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor verify

# 卸载（默认 dry-run）
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor uninstall --dry-run

# 真卸载
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor uninstall --force
```

### 静默看门狗模式 (v2.3 → v3 保留)

高频巡检（30min）推荐用 `no_agent + script` 替代 LLM agent，节省 token：

```
Watchdog 脚本 → collector-daemon.py --json → 检查 alerts
  ├── 无 hard alert + diagnosis 健康 → 静默
  └── 有 hard alert 或 diagnosis 有问题 → 推送 + 写 .triage-trigger
```

| 对比 | LLM Agent | Silent Watchdog |
|------|:---:|:---:|
| Token 消耗 | ~3000/次 | **0** |
| 响应延迟 | 5-15s | <2s |
| 静默支持 | ❌ | ✅ |
| 分析深度 | 可解读趋势 | 仅阈值判断 |

### 去重冷却 (v3 升级)

3 类 signature 走 3h TTL 冷却：

| Signature 类型 | 写入字段 | 判定 |
|---------------|---------|------|
| 磁盘 free | preferences.last_disk_free_gb | ±1GB 内 |
| 僵尸 PID 集合 | preferences.zombie_sig | 排序后集合相等 |
| MCP cleaned msg | preferences.mcp_cleaned_msg | 字符串相等 |

State file: `~/.hermes/profiles/cron-worker/state/mac-doctor-watchdog-state.json`

---

## Layer 3: mac-doctor-triage（v3 新增）

### 职责

- LLM agent 解读 L2 watch + L1 collector 趋势
- 区分 **transient**（瞬时）/ **persistent**（持续）/ **critical**（严重）
- 写 `preferences.interpretations`（持久化解读）
- 静默 stdout = 不推送
- 异常 → stdout 输出 → Telegram

### 触发机制（v3）

| 触发 | 时机 |
|------|------|
| L2 watchdog 推送 | L2 写 `.triage-trigger` 时 |
| 12h 兜底 | 每 12h cron 跑一次确保不漏 |

### 数据流

```
L2 mac-doctor-watchdog.py (no_agent)
  └── 异常时 → 写 .triage-trigger

L3 mac-doctor-triage.py (LLM agent)
  ├── 读 .triage-trigger
  ├── 读 preferences.json
  ├── 读 history.db (最近 24h trend)
  ├── 组装 LLM prompt
  ├── LLM 解读 → 写 interpretations
  └── should_push → stdout 输出
```

### 输出 schema (Spec §2.3)

```json
{
  "verdict": "transient|persistent|critical",
  "diagnosis": "单行根因",
  "recommendation": "建议行动 (1-3 条)",
  "memory_write": {
    "key": "facts.add|interpretations.add",
    "value": ...
  },
  "should_push": true|false,
  "push_message": "若 should_push=true 的推送内容"
}
```

---

## 4 个 cron 注册表（v3）

**单一 source of truth**：`mac-doctor install` 注册这 4 个 cron job：

| Job ID | schedule | mode | 脚本/skill | prompt 摘要 |
|--------|----------|------|----------|------------|
| `mac-doctor-quick` | `every 30m` | no_agent + script | `mac-doctor-watchdog.py` | (无 prompt，no_agent) |
| `mac-doctor-triage` | `every 12h` | LLM agent | skills=[apple/mac-doctor] | "加载 mac-doctor skill。读 .triage-trigger + preferences.json + history.db 最近 24h。判断并输出结构化 JSON（verdict/diagnosis/recommendation/memory_write/should_push/push_message）。should_push=true → 推送，否则静默。" |
| `mac-doctor-deep` | `0 3 * * *` | LLM agent | skills=[apple/mac-doctor] | "加载 mac-doctor skill。执行 Tier 2 全量审计（安全 + 硬件 + 网络）。详见 SKILL.md Tier 2a/2b/2c/2d。" |
| `mac-doctor-weekly` | `0 9 * * 1` | LLM agent | skills=[apple/mac-doctor] | "加载 mac-doctor skill。生成周报：读 history.db 最近 7 天趋势 + preferences.interpretations + suppressions 摘要。输出 Markdown 周报到 stdout。" |

### cron 注册（v3 唯一入口）

```bash
~/.hermes/skills/apple/mac-doctor/scripts/mac-doctor install
```

**不要**手工用 `cronjob create` 注册（绕过 `register_cron_jobs` 的幂等保证）。

### cron 升级/迁移

如果 cron job 需要改 schedule 或 prompt：
1. 先 `mac-doctor uninstall`（pause 4 cron + unload LaunchAgent）
2. 改 `mac-doctor` CLI 的 `JOB_IDS` 或 prompt
3. `mac-doctor install`（重新注册）

---

## 错误模式与兜底

| 模块 | 失败场景 | 兜底行为 |
|------|---------|---------|
| L1 collector | subprocess 超时 / 异常 | watchdog 捕获 → collector=error 状态推送 |
| L2 watchdog | preferences.json 损坏 | load 返回 DEFAULT + stderr + 备份 .broken |
| L2 watchdog | MCP cleanup 抛异常 | 单 try/except, 不影响其他检查 |
| L2 watchdog | 触发 triage 失败 | stderr log, 不阻塞本次推送 |
| L3 triage | LLM 超时/异常 | stdout 空 + stderr 警告 + 写 preferences.error |
| L3 triage | preferences 写失败 | stdout 空 + stderr, 不阻塞后续 |
| M4 CLI | install 失败 | 提示 rollback 已完成的步骤 |

---

## 跨 Profile 配置陷阱 ⚠️ (v3 保留)

`collector-daemon.py` 使用 `Path.home() / ".hermes" / "inspection"` 路径。
**在 cron-worker profile 下 `HOME` 指向 profile home**，**不是用户真实的 home**。

**存在两份 config.json，修改阈值时必须同步：**

| 路径 | 谁读 |
|------|------|
| `~/.hermes/inspection/config.json` | LaunchAgent / 手动执行 / 非 cron 环境 |
| `~/.hermes/profiles/cron-worker/home/.hermes/inspection/config.json` | cron job 执行时 |

不同步的后果：手动测试和 cron job 看到不同的阈值，行为不一致。

---

## Anomaly Detection 参数 (v3 保留)

| 参数 | 值 | 说明 |
|------|:--:|------|
| `anomaly.sigma` | **3.0** | 3σ ≈ 0.3% 误报率 |
| `anomaly.baseline_days` | 7 | 基线窗口 |
| `anomaly.enabled` | true | 保留开启——配合 watchdog 的 threshold-vs-anomaly 静默策略 |

---

## 演进历史

| 版本 | 日期 | 关键变化 |
|------|------|---------|
| v2.4 | 2026-06-15 | state-file dedup（仅磁盘） |
| v2.5 | 2026-06-28 | 六检统一看门狗 + MCP cleanup |
| **v3.0** | **2026-06-28** | **三层架构 + 操作偏好记忆 + Skill CLI 总入口** |

---

## 参考

- `references/tier5-smart-alerts.md` — 阈值告警原始定义
- `references/tier4-history-tracking.md` — history.db schema
- `references/upkeep-phases.md` — 清理节奏
- `/tmp/codex-p1-plan.yaml` 至 `codex-p4-plan.yaml` — Codex 规划历史
- OB `20-Areas/20_技术项目/mac-doctor/PRD/` — 项目 PRD/Spec/Plan/Audit
