---

name: mac-doctor
description: |-
type: routine
  macOS 设备巡检 v2.4 — 评分/巡检/审计/清理/追踪/告警六层。Use when:
  check my mac, system health, mac slow, disk full, cleanup mac, 设备巡检,
  系统评分, 健康检查, 磁盘空间, 内存压力, swap, 清理缓存, brew/npm/uv cache,
  CPU 大户, 安全检查, 电池健康, 网络配置审计, 历史趋势, 异常检测, 臃肿/隐私扫描。
  Do NOT use for: GUI 操作, 实时网络诊断 (ping/traceroute), 清理孤儿 App 数据。
version: 2.4.3
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

**评分输出格式 (v2.2)**:
```
Score: 72/100 (良好 🟡)
Root cause: Chrome high CPU (85% avg over 5min)
```
根因诊断由 `diagnose()` 函数自动生成（优先级：CPU > Memory > Disk > Battery > Thermal）。详见 `references/health-scoring.md`。

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

Swap 关键指标：`sysctl vm.swapusage`。>2GB 说明内存偏紧。>5GB 时**必须检查 gateway 存活**（swap 危机会触发 SIGTERM 杀进程），详见 `references/crash-diagnostic.md`。

**Swap 文件时间线**（追踪增速，定位磁盘失血主因）：
```bash
ls -lt /System/Volumes/VM/swapfile* 2>/dev/null | head -10
echo "总数: $(ls /System/Volumes/VM/swapfile* 2>/dev/null | wc -l) 个 × 1GB"
```
每个 swapfile = 1GB。文件创建时间戳揭示 swap 膨胀速度——今天 10 个文件 = 10GB 被 swap 吃掉。

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
  gsub(/ (Helper( \\([A-Za-z]+\\))?|Renderer|Web Content( \\(Prewarmed\\))?|Worker|\\(GPU\\)|\\(Plugin\\))$/,"",$0)
  n=split($0,f,/[ \\t]+/); k=f[n]; c[k]+=$1; m[k]+=$2; n_[k]++
} END { for (k in c) printf "%6.1f %6.1f %3d  %s\\n",c[k],m[k],n_[k],k }' | sort -rn | head -10
```

**僵尸进程:** 如发现 `defunct` (Z 状态) 进程，参见 `references/zombie-process-cleanup.md` — 杀父进程让 launchd 回收。

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

> ⚠️ **路径警告**: 在非 default profile（如 cron-worker）下，`~` 指向 profile home 而非用户 home。所有 `~/Library/` / `~/.cache/` 必须替换为绝对路径（如 `~/Library/Caches/`）。详见 Tier 3「清理陷阱 — 跨 Profile 路径陷阱」。

### Dev 缓存

```bash
du -sh ~/.cache/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/Library/Caches/*/ 2>/dev/null | sort -rh | head -10
du -sh ~/.npm 2>/dev/null
```

判断：npm/uv >2G 可清。qmd/huggingface 模型不删。

### Profile 缓存（Tier 2a 补充检查）

多 profile 架构下，每个 profile 的 `home/` 下各自累积 `.npm`、`Library/Caches`、`.cache/uv`。这些在用户级 `du ~/.cache` 中看不到（`~` 不指向 profile home），是常见的隐性磁盘大户。

```bash
# 检查各 profile home 缓存
for d in ~/.hermes/profiles/*/home/; do
  [ -d "$d" ] || continue
  total=$(du -sm "$d" 2>/dev/null | cut -f1)
  [ "$total" -gt 200 ] && echo "${total}M  $d"
done | sort -rn

# 逐个查看具体占用
du -sh ~/.hermes/profiles/*/home/.{npm,cache} 2>/dev/null
du -sh ~/.hermes/profiles/*/home/Library/Caches 2>/dev/null
```

> [!TIP] 💡 典型回收：regent home 的 .npm + Library/Caches + .cache 约 5G，cron-worker 约 2.3G。全部可安全清理。

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

### Hermes Profile 缓存重复 ⚠️

当多个 Hermes profile 存在时，每个 profile 的 home 目录会独立缓存模型（qmd/huggingface）和开发工具（npm/playwright/uv/pip），导致磁盘被静默膨胀。

**诊断**（见 `references/disk-space-patterns.md` §Hermes Profile 缓存重复）：
```bash
# 快速排查
for p in ~/.hermes/profiles/*/; do
  name=$(basename "$p")
  du -sh "$p/home/.cache/" 2>/dev/null
  du -sh "$p/home/.npm/" 2>/dev/null
done
```

**常见重复**：qmd 模型 ×3（用户 + regent + cron-worker = 5.6G，实际只需 2.3G）、ms-playwright ×2（1.5G）。

**安全清理**：见 `references/disk-space-patterns.md` §安全清理。**qmd/huggingface 模型不动**，只清 dev 缓存。

**根治**：`external_dirs` — 让 profile 共享用户级缓存。需 CC 审计后执行。

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
| npm | `npm cache clean --force` | ✅ | 纯缓存。⚠️ cron profile 下 npm 指向 `~/.hermes/profiles/cron-worker/home/.npm` → 系统缓存在 `~/.npm` |
| npm _npx | 保留当前用版本，删其余 | 🟡 | `ps aux \| grep` 找到在用 codegraph hash → 删 `_npx/` 下其他所有目录。1.7G+ 典型回收 |
| uv | `uv cache clean` → `--force` | ✅ | 先 `lsof ~/.cache/uv` |
| brew | `brew cleanup` | ✅ | 通常 300-400MB |
| Chrome | `rm -rf ~/Library/Caches/Google/Chrome/*` | ✅ | 运行中可能超时 |
| qmd models | **不删用户级**。Profile 副本 → `models/` symlink 去重。详见 `references/qmd-model-dedup.md` | 🟡 | 模型 2.1G/份。**不设 XDG_CACHE_HOME**（会合并索引导致 WAL 写冲突）。`external_dirs` 是 skills 专用，无效 |
| huggingface | **不删用户级** | ❌ | 生产模型。Profile 副本同理用 symlink 去重 |
| Profile dev 缓存 | `rm -rf .../home/.cache/{uv,puppeteer}` | ✅ | npm/uv/playwright/pip。见 disk-space-patterns §安全清理 |
| Profile npm | `rm -rf .../home/.npm/_cacache` | ✅ | 每 profile 一份，清完回收 2G+ |
| s6m/unused 归档 | `rm -rf ~/.hermes/archives/...` | ✅ | 旧 profile 残留，确认无用后直接删 |
| Xcode | 需确认 | ⚠️ | DerivedData |
| iOS backups | 需确认 | ⚠️ | 不可恢复 |

### 臃肿检测 & 隐私扫描

详见 `references/bloatware-privacy.md`:
- 臃肿软件（CleanMyMac/杀软残留/Adobe 后台）
- Electron 应用审计 + 重复浏览器
- TCC 权限审计（辅助功能/屏幕录制/摄像头/麦克风）
- 可疑进程检测

磁盘大户清单 & 轻量扫描技巧见 `references/disk-space-patterns.md`（Claude vm_bundles / Chrome / IDE 残留 / Discord 等）。

Profile 缓存重复诊断（profile home 下 `.cache/` 异常膨胀的根因与修复）：见 `references/profile-cache-duplication.md`。

### ⚠️ 跨 Profile 路径陷阱

当 session 运行在非 default profile（如 cron-worker）下时，`~` 指向该 profile 的 home（如 `~/.hermes/profiles/cron-worker/home/`），**不是用户真实的 home**。

| 写法 | cron-worker 下解析为 | 正确写法 |
|------|------|------|
| `~/Library/Caches/` | `.../profiles/cron-worker/home/Library/Caches/` ❌ | `~/Library/Caches/` |
| `~/.cache/` | `.../profiles/cron-worker/home/.cache/` ❌ | `~/.cache/` |
| `~/Library/LaunchAgents/` | profile 的 agents ❌ | `~/Library/LaunchAgents/` |

**Tier 2a 的所有 `~` 路径在非 default profile 下都无效。** 遇到 `du` 结果异常小（如 56M 总缓存）时，第一时间怀疑路径错误。

### 清理陷阱

| 陷阱 | 表现 | 解法 |
|------|------|------|
| **磁盘满时 `du`/`find` 全超时** | `du -sh ~/Library/` 60s 不返回，`find -size +100M` 30s 超时 | 磁盘 <15% 导致 I/O 拥塞。改用轻量方法：`ls -lht` 看指定目录、逐项 `du -sh <target>` 单目录扫描、先查已知大户再深挖。详见 `references/disk-space-patterns.md` §扫描技巧。 |
| **磁盘 <10% 时 `du`/`find` 超时（即使 swap 不高）** | `du -sh ~/Library/`、`find ~ -size +100M` 60s+ 不返回 | APFS 严重碎片化 + 低剩余空间导致 I/O 拥塞。**优先清理而非深挖**：先 thin TM 快照、清已知可删缓存，再重试 `du`。超时期间改用 `ls -lhS <已知大目录>` 逐个检查。 |
| **非 default profile 下 `~` 指向错误** | `~/Library/Caches/` 只显示 56M，实际用户缓存 1.4G | 全部改用绝对路径：`~/Library/Caches/`、`~/.cache/` |
| **Anomaly 误报：baseline 不成熟** | 新装 collector < 7 天，夜间基线被白天正常活动打破 → z > σ 但绝对值健康 | σ 提到 3.0。watchdog 区分 threshold/anomaly：纯异常 + diagnosis "All clear" → 静默 |
| **Profile 缓存隔离 → 磁盘膨胀** | 多 profile 各自克隆 qmd 模型（×3）、npm（×3）、playwright（×2）。.hermes 从 11G 膨胀到 32G+，其中 5.6G 的 qmd 模型只需 2.3G | 短期：清 dev 缓存（不动模型）— `references/disk-space-patterns.md` §安全清理。根治：配 `external_dirs` 让 profile 共享用户级缓存。每次新增 profile 后检查 `references/disk-space-patterns.md` §诊断命令。 |
| **跨 Profile config 不同步** | 手动改 `~/.hermes/inspection/config.json` 但 cron job 读的是 `.../profiles/cron-worker/home/.hermes/inspection/config.json` → 行为不一致 | 修改阈值时两份 config 同步改。详见 `references/cron-module.md` §跨 Profile 配置陷阱 |
| `du ~/*/` 超时 | 15s+ 不返回 | 加 `-d 1` |
| `uv cache clean` 卡住 | "Cache is currently in-use" | `lsof` → `--force` |
| `brew upgrade` exit 1 | 以为是失败 | 看底部升级数 |
| 磁盘误判 | df 显示 28% | 用 `diskutil info` |
|| **`npm cache clean --force` 无效** | 清理前后 `du -sh ~/.npm` 不变 | cron profile 下 `npm config get cache` 指向 profile home；系统缓存在 `~/.npm`。对 `_npx/` 直接 `rm -rf ~/.npm/_npx/<旧hash>` |
|| **macOS 沙盒 Container 删不动** | `rm -rf ~/Library/Containers/com.xxx.yyy` → `Operation not permitted` | macOS Container Manager 锁定沙盒目录。`sudo` 无终端不可用（cron/session），`xattr -rc` 无效，`osascript Finder delete` 弹 TCC 权限框超时。**解法：内容 <100KB 时忽略；否则在桌面端 Finder 手动拖废纸篓。** 卸载 App 优先用 App 自带的卸载器或 `AppCleaner` 等工具。 |
|| **Telegram Group Containers 误判为缓存** | `du` 显示 `~/Library/Group Containers/...Telegram/` 占 8GB，以为是可清理媒体缓存 | 8GB 在 `stable/account-*/postbox/db/` — 这是**消息数据库**，不是缓存。删 = 本地聊天记录全丢。媒体缓存（`postbox/media/`）通常只有几十 MB。真正的清理入口在 Telegram 客户端内：设置 → 数据和存储 → 存储用量。 |
| **TM 快照积压（磁盘急剧下降的主因）** | 磁盘从 70% → 90% 仅数小时；`tmutil listlocalsnapshots` 显示 20+ 快照 | 备份盘未连接时 macOS 每小时拍快照。`tmutil thinlocalsnapshots` 一次只薄一个，需 Python 批量 `tmutil deletelocalsnapshots`。详见 `references/tm-snapshot-cleanup.md`。 |

### 清理后验证

```bash
diskutil info / | grep "Container Free Space"
```

清理节奏 & 优先级见 `references/upkeep-phases.md`。

### 清理安全闸 (v2.2)

Tier 3 清理有三道安全闸，防止误删生产数据：**dry-run**（预估并确认）→ **whitelist**（自动跳过关键路径）→ **operation log**（审计记录）。详见 `references/tier3-cleanup-safety.md`。

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
| Swap >4GB / 电池 <80% / 异常触发（σ=3.0，纯异常不推送） | 🟡 | 同上 |

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

全部详见 `references/community-skills-reference.md`。第二轮搜索（2026-05）发现 tw93/mole 和 metaspartan/mactop，吸收方案共 13 项按 P0-P3 分级，详见 `references/github-search-round2.md` 和 `references/absorb-mole-mactop.md`。

---

## ⏰ Cron Architecture v3 (2026-06-28)

**v3 重构**：从 v2.5 单层 watchdog 升级为 **三层 L1/L2/L3 架构 + Skill CLI 总入口**。

```
┌────────────────────────────────────────────────────────────┐
│ L1 · collector-daemon.py (LaunchAgent, 10min)             │
│  · 数据采集 → ~/.hermes/inspection/history.db             │
│  · 阈值告警 + anomaly detection (macOS 本地通知)            │
│  · v2.2 不变                                              │
└────────────────────────────────────────────────────────────┘
                          ↓ stdout JSON
┌────────────────────────────────────────────────────────────┐
│ L2 · mac-doctor-watchdog.py (cron quick, 30min, no_agent) │
│  · 读 collector --json → 阈值过滤                          │
│  · 附加检查: Kanban/僵尸/MCP清理                           │
│  · 冷却去重 (3h 窗口):                                    │
│    - 磁盘: 同 free GB±1                                   │
│    - 僵尸: 同 PID 集合                                    │
│    - MCP: cleaned 状态                                    │
│  · 集成 preferences.load() + known_short_running_tools 白名单│
│  · 写 preferences.suppressions (3h TTL)                    │
│  · 写 ~/.hermes/inspection/.triage-trigger (触发 L3)        │
│  · 有异常 → 输出 → Telegram                                │
└────────────────────────────────────────────────────────────┘
                          ↓ trigger file
┌────────────────────────────────────────────────────────────┐
│ L3 · mac-doctor-triage.py (cron triage, 触发+12h兜底, LLM) │
│  · 加载 mac-doctor skill + preferences.json + history.db   │
│  · 组装 LLM prompt (snapshot + facts + interpretations +   │
│    suppressions + trend + output_schema)                  │
│  · LLM 判断: persistent / transient / critical             │
│  · 写 preferences.interpretations                         │
│  · 静默 stdout = 不推送                                    │
└────────────────────────────────────────────────────────────┘
```

**4 cron 注册表**（统一通过 `mac-doctor install` 注册）：

| Job ID | name | schedule | mode | 关联 skill |
|--------|------|----------|------|----------|
| mac-doctor-quick | quick | every 30m | no_agent + script | mac-doctor |
| mac-doctor-triage | triage | every 12h | LLM agent | mac-doctor |
| mac-doctor-deep | deep | 0 3 * * * | LLM agent | mac-doctor |
| mac-doctor-weekly | weekly | 0 9 * * 1 | LLM agent | mac-doctor |

详见 `references/cron-module.md` §3。

### L2 Zombie Auto-Kill Hook (driven by cron-worker watchdog, v2.4.3, 2026-07-02)

**问题背景**: Raycast Helper (`PPID 31909`) 长期累积 `<defunct>` 子进程,僵尸数常驻 1+。
`prefs.known_zombie_parents[ppid].auto_kill=true` 早就在 preferences.json 里,
但 L2 watchdog 没消费这个配置 — 第 3 次 triage 报告后才补钩子。

**实现**: `scripts/zombie_killer.py` (v1.0) 独立模块,被 cron-worker L2 通过
`importlib.util.spec_from_file_location` 动态加载。

**安全门** (按 Codex 评审, 4 层):
1. `user_preferences.auto_kill_zombies=False` 总开关 → 全程不杀 (gated)
2. `known_zombie_parents[ppid].auto_kill=true` 显式 opt-in
3. 3h 冷却 marker (`~/.hermes/inspection/.known-zombie-killed.json`) — 防 Raycast 反复自启被杀循环
4. `kill` 失败分桶 (cooldown / not_found / permission_denied / error), marker 健壮 fail-soft

**触发路径**: L2 `check_zombies()` 检出 >4 僵尸 → 调 `zombie_killer.kill_known_zombies()` →
重检集合大小 → 若成功 reap 降级为 ok。

**消费方**:
- `cron-worker/scripts/mac-doctor-watchdog.py` (动态加载)
- 未来 default profile 也可独立消费 (如果其他 cron job 看到类似模式)

**测试**: 20 个单测在 `tests/test_zombie_killer.py` (jz-skills),
2 个 smoke 集成在 `tests/test_watchdog_integration.py` (`test_watchdog_integrates_zombie_killer_hook`
+ `test_watchdog_line_count_stays_under_460`)。

---

## 🛠️ Skill CLI（v3 新增）

`scripts/mac-doctor` 可执行 Python 入口，6 个 subcommand：

```bash
mac-doctor install     # 一键安装 L1 LaunchAgent + 注册 4 个 cron job（幂等）
mac-doctor uninstall   # 反向卸载（默认 dry-run + --force 才真删）
mac-doctor status      # 三层表 + Prefs 摘要
mac-doctor triage      # 手动触发一次 L3 triage
mac-doctor preferences # show / edit / key-path 读取
mac-doctor verify      # 跑 PRD §2.3 七项 checklist 并输出 PASS/FAIL/PENDING
```

所有 cron 注册通过 `mac-doctor install`，**source of truth 在 cron-module.md §3**。

**操作偏好持久层**：`~/.hermes/inspection/preferences.json`
- `version: 1` + `facts` (known_short_running_tools / known_zombie_parents / known_mcp_cleanup_targets / user_preferences)
- `interpretations` (LLM triage 写入的历史解读)
- `suppressions` (3h TTL 的同 signature 静默)

---

## ✅ Verification Checklist

- [ ] 磁盘用了 `diskutil info` 而非 `df -h /`？
- [ ] Swap 状态检查了？
- [ ] 健康评分计算正确（扣分规则见 `references/health-scoring.md`）？
- [ ] 深度审计按需加载了对应 reference（2b/2c/2d）？
- [ ] 缓存清理前判断了生产模型（qmd/huggingface 不删）？
- [ ] 清理后做了前后磁盘对比？
- [ ] LaunchAgents 检查了死链？
- [ ] **（v3 新增）** L1 collector daemon + L2 watchdog cron + L3 triage cron 三层架构已通过 `mac-doctor verify` 验证？
- [ ] **（v3 新增）** `~/.hermes/inspection/preferences.json` 存在且 schema 正确（version + facts + interpretations + suppressions）？
- [ ] **（v3 新增）** `mac-doctor status` 输出三层表（Layer 1/2/3 + Prefs）？
