---
name: mac-doctor
description: |-
  macOS 设备巡检 v2.0 — 评分/巡检/审计/清理/追踪/告警六层。Use when:
  check my mac, system health, mac slow, disk full, cleanup mac, 设备巡检,
  系统评分, 健康检查, 磁盘空间, 内存压力, swap, 清理缓存, brew/npm/uv cache,
  CPU 大户, 安全检查, 电池健康, 网络配置审计, 历史趋势, 异常检测, 臃肿/隐私扫描。
  Do NOT use for: GUI 操作, 实时网络诊断 (ping/traceroute), 清理孤儿 App 数据。
version: 2.0.0
author: Hermes Agent
platforms: [macos]
metadata:
  hermes:
    tags: [macos, system-inspection, disk-audit, cache-cleanup, health-check, apfs,
           security-audit, hardware-audit, network-audit, history-tracking, smart-alerts]
    category: apple
---

# macOS 设备巡检 v2.0

六级体系：看分 → 快查 → 深挖 → 清理 → 追踪 → 告警。

## 🚨 Red Flags: 不要跳过的理由

| 借口 | 为什么错 |
|------|---------|
| "我直接用 df -h 看磁盘" | **APFS 上 df 显示的 % 是卷视图，不是真实用量。** 本机 df 显示 28%，实际 Container 级别 80% 已用。差 3 倍。 |
| "我各个命令零散跑就行" | 巡检的价值在对比和趋势。单条命令看不出 swap 压力 + 内存 + 磁盘的联动。 |
| "缓存删了系统还会重建，没用" | npm 5.7G、uv 4.3G 的缓存删一次就省出 10G。有意义。 |
| "brew upgrade exit 1 就是更新失败了" | 39/40 包成功但 1 个非核心包（如 memo）失败也会 exit 1。看输出底部那行。 |
| "安全检查太麻烦，下次再说" | FileVault 关闭 + Firewall 禁用 = 裸奔。 |
| "历史追踪需要数据库，太重了" | SQLite ~5MB/月，CPU <0.1s/次。比每次手动对比轻得多。 |

---

## 🔀 决策树

```
用户说"巡检/检查/清理/健康/安全"?
├── Tier 0: 即时健康分 → 一句话结论 + 评分
│   └── 退出条件: 评分 ≥80 且无 🔴 → 收工；否则进入 Tier 1
├── Tier 1: 快速巡检 → CPU + 内存 + 磁盘 + Swap + Top 进程
│   └── 退出条件: 4 项指标全绿且无进程 >20% CPU → 收工；否则问用户是否深挖
├── Tier 2a: Dev 审计 → 缓存 + Homebrew + LaunchAgents + APFS
│   └── 详见 references/macos-commands.md（命令速查）+ references/upkeep-phases.md（保养节奏）
├── Tier 2b: 安全审计 → 20 项 → references/tier2b-security-audit.md
├── Tier 2c: 硬件审计 → 电池/磁盘/热节流/TimeMachine → references/tier2c-hardware-audit.md
├── Tier 2d: 网络配置审计 → 端口/DNS/Wi-Fi/蓝牙 → references/tier2d-network-audit.md
│   └── 退出条件: 无未知监听端口 + DNS 已知 + 无开启的高危共享
├── Tier 3: 安全清理 → 缓存 + 臃肿检测 + 隐私扫描
│   └── 退出条件: 清理前后做 diskutil 对比，回收 ≥1GB 才算成功
├── Tier 4: 历史追踪 → 趋势对比 + 异常检测 + 电池预测
└── Tier 5: 智能告警 → 阈值通知 + LaunchAgent 调度
```

---

## Tier 0: 即时健康评分

运行全部检查后，输出 0-100 综合评分。

**扣分规则** (详见 `references/health-scoring.md`):
- 🔴 Critical（安全/系统）-15，其他 -10
- 🟡 Warning（安全/系统）-4，其他 -3

**评分带**: 95+卓越 / 85+很好 / 70+良好 / 55+一般 / <55差

**Exit Code**: 0=健康(80+) / 1=降级(50-79) / 2=危险(<50)

**子系统权重**: Security 25% / Memory 20% / Disk 15% / CPU 15% / Hardware 10% / Network 10% / Dev Env 5%

---

## Tier 1: 快速巡检

### 1a. CPU

```bash
top -l 1 -n 0 | head -4
```

解读：关注 Load Avg 是否超 CPU 核心数、idle 是否 <20%。

### 1b. 内存 + Swap

```bash
sysctl hw.memsize | awk '{printf "Total: %.1f GB\n", $2/1073741824}'
memory_pressure
vm_stat | awk '/Pages free/{printf "Free: %.0f MB\n", $3*16384/1048576}'
```

Swap 关键指标：`sysctl vm.swapusage`。>2GB 说明内存偏紧。

### 1c. 磁盘 ⚠️ 必须用 diskutil，不要用 df

```bash
# ✅ 正确做法 — Container 级别
diskutil info / | grep -E "Container (Total|Free) Space"
# 真实用量 = Container Total - Container Free
```

**`df -h /` 在 APFS 上是卷视图，不是物理占用。** 本机案例：df 28% → 实际 80%。

### 1d. Top CPU 进程

```bash
# 原始 PID 视图
ps -eo pid,%cpu,%mem,comm -r | head -12

# 归一化聚合（Chrome Helper×30 → Chrome×N；列：CPU% MEM% 进程数 名称）
ps -eo %cpu,%mem,comm -r 2>/dev/null | awk 'NR>1 {
  gsub(/ (Helper( \([A-Za-z]+\))?|Renderer|Web Content( \(Prewarmed\))?|Worker|\(GPU\)|\(Plugin\))$/,"",$0)
  n=split($0,f,/[ \t]+/); k=f[n]; c[k]+=$1; m[k]+=$2; n_[k]++
} END { for (k in c) printf "%6.1f %6.1f %3d  %s\n",c[k],m[k],n_[k],k }' | sort -rn | head -10
```

### Tier 1 输出格式

| 检查项 | 状态 | 详情 |
|--------|------|------|
| CPU | idle% + Load Avg | 是否超核数 |
| RAM | total / wired / compressed | memory_pressure |
| Swap | used / total | >2GB → 🔴 |
| 磁盘 | Container Free | <15% → 🔴 |
| Top 进程 | >20% CPU | — |

---

## Tier 2a: Dev 审计

### Dev 缓存

```bash
du -sh ~/.cache/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/Library/Caches/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/.npm 2>/dev/null
```

判断：npm/uv >2G 可清。qmd/huggingface 模型不删。

### Homebrew

```bash
brew outdated | wc -l
brew cleanup --dry-run
brew autoremove --dry-run
```

**`brew upgrade` exit 1 ≠ 失败。** 看输出底部升级数。

### LaunchAgents（死链检查）

```bash
for plist in ~/Library/LaunchAgents/*.plist; do
  # 兼容两种 key: ProgramArguments[0] 和 Program (后者也合法)
  program=$(/usr/libexec/PlistBuddy -c "Print :ProgramArguments:0" "$plist" 2>/dev/null) \
    || program=$(/usr/libexec/PlistBuddy -c "Print :Program" "$plist" 2>/dev/null)
  [ -n "$program" ] && [ ! -e "$program" ] && echo "DEAD: $(basename "$plist") → $program"
done
```

### APFS 快照

```bash
tmutil listlocalsnapshots /
```

---

## Tier 2b/2c/2d: 安全 + 硬件 + 网络审计

| 子层 | 内容 | 参考 |
|------|------|------|
| 🔐 2b 安全 | SIP/Gatekeeper/FileVault/防火墙(+log+allowsigned)/SSH/屏幕锁/Secure Boot(bputil)/SystemExtensions/MDM Profiles/NTP/Hibernate/Sharing/AirDrop/`/etc/hosts` — 27 项 | `references/tier2b-security-audit.md` |
| 🖥 2c 硬件 | 电池循环+温度/SMART/热节流(`pmset -g therm`)/Kernel Panic/TimeMachine/Wake-Sleep 解析 — 9 项 | `references/tier2c-hardware-audit.md` |
| 🌐 2d 网络 | TCP+UDP 监听端口（含 22/23/445/5900/3389 风险分类）/DNS/代理/Wi-Fi(动态+RSSI/Noise/TX Rate)/蓝牙/Wake-on-Network — 10 项 | `references/tier2d-network-audit.md` |

**执行原则**: 先快速巡检(1a-1d) + Dev审计(2a)，发现问题后再按需展开 2b/2c/2d。

---

## Tier 3: 安全清理

### 清理规则

| 项目 | 命令 | 安全? | 注意事项 |
|------|------|:-----:|---------|
| npm | `npm cache clean --force` | ✅ | 纯缓存 |
| uv | `uv cache clean` → `--force` | ✅ | 先 `lsof ~/.cache/uv` |
| brew | `brew cleanup` | ✅ | 通常 300-400MB |
| Chrome | `rm -rf ~/Library/Caches/Google/Chrome/*` | ✅ | 运行中可能超时 |
| qmd models | **不删** | ❌ | 生产模型 |
| huggingface | **不删** | ❌ | Whisper/embedding |
| Xcode | 需确认 | ⚠️ | DerivedData |
| iOS backups | 需确认 | ⚠️ | 不可恢复 |

### 臃肿检测 & 隐私扫描

详见 `references/bloatware-privacy.md`:
- 臃肿软件（CleanMyMac/杀软残留/Adobe 后台）
- Electron 应用审计 + 重复浏览器
- TCC 权限审计（辅助功能/屏幕录制/摄像头/麦克风）
- 可疑进程检测

### 清理陷阱

| 陷阱 | 表现 | 解法 |
|------|------|------|
| `du ~/*/` 超时 | 15s+ 不返回 | 加 `-d 1` |
| `uv cache clean` 卡住 | "Cache is currently in-use" | `lsof` → `--force` |
| `brew upgrade` exit 1 | 以为是失败 | 看底部升级数 |
| 磁盘误判 | df 显示 28% | 用 `diskutil info` |

### 清理后验证

```bash
diskutil info / | grep "Container Free Space"
```

清理节奏 & 优先级见 `references/upkeep-phases.md`。

---

## Tier 4: 历史追踪

SQLite 数据库 `~/.hermes/inspection/history.db`，10 分钟/次快照（~5MB/月）。

| 能力 | 参考 |
|------|------|
| 趋势对比 (24h vs 7d)、异常检测 (±2σ)、电池预测、周期报告 | `references/tier4-history-tracking.md` |

---

## Tier 5: 智能告警

阈值触发 macOS 通知。23-07 安静时段（致命告警除外）。

| 条件 | 级别 | 参考 |
|------|:---:|------|
| CPU >80% 持续 5min / 内存 critical / 磁盘 <10% | 🔴 | `references/tier5-smart-alerts.md` |
| Swap >4GB / 电池 <80% / 异常触发 | 🟡 | 同上 |

通过 LaunchAgent 或 Hermes Cron Job 调度。

---

## ⏰ Cron 模块

**双层架构**，覆盖从数据采集到定时报告的完整链路。

| 层 | 技术 | 职责 | 频率 |
|---|------|------|:---:|
| Layer 1 | LaunchAgent + `scripts/collector-daemon.py` | 后台采集 + 阈值告警 + 异常检测 | 每 10 分钟 |
| Layer 2 | Hermes cron jobs | 定时巡检 + 评分报告 + Telegram 推送 | 每 30 分钟 / 每天 |

### 快速开始

```bash
# 1. 创建配置目录并复制标准化配置模板
mkdir -p ~/.hermes/inspection
cp templates/config.json ~/.hermes/inspection/config.json
# 2. 按需修改阈值和开关
# 3. 安装 Layer 1 采集 daemon
bash scripts/install-daemon.sh
# 4. 检查运行状态
launchctl list com.hermes.inspection-collector
```

配置模板见 `templates/config.json`。CI 用 `python3 scripts/collector-daemon.py --json | jq '.alerts'`（schema: `{schema_version,timestamp,snapshot,alerts[]}`）。详见 `references/cron-module.md`。

---

## 参考来源

| 项目 | 吸收内容 |
|------|---------|
| gfreedman/mac_audit | 69项检查、健康评分、Fix模式、Profile |
| hritikvalluvar/macmonica | 历史追踪、异常检测、电池预测、智能告警 |
| Neo23x0/macguard-audit | LaunchDaemon调度、SIEM集成、测试套件 |
| TheSmilemakers/system-monitor | 臃肿检测、隐私扫描(TCC) |
| lu-zhengda/macos-toolkit | machealth 8子系统权重评分 |
| dan-snelson/Mac-Health-Check | MDM合规检查 |
| N4M3Z/check-mac | 48项安全检查 |

全部详见 `references/community-skills-reference.md`。

---

## ✅ Verification Checklist

- [ ] 磁盘用了 `diskutil info` 而非 `df -h /`？
- [ ] Swap 状态检查了？
- [ ] 健康评分计算正确（扣分规则见 `references/health-scoring.md`）？
- [ ] 深度审计按需加载了对应 reference（2b/2c/2d）？
- [ ] 缓存清理前判断了生产模型（qmd/huggingface 不删）？
- [ ] 清理后做了前后磁盘对比？
- [ ] LaunchAgents 检查了死链？
