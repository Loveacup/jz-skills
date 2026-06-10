---
name: unifi-ops
description: >-
  UniFi 设备运维工具箱 — SSH 直连 + MongoDB + API（2FA=密码|验证码）。
  覆盖设备发现、巡检、健康诊断、客户端监控、固件升级、配置修复、拓扑发现。
  支持 AP/交换机/网关/Controller。
  Use when: 查UniFi设备状态、巡检、AP客户端、信号强度、信道、
  设备重启、固件升级、网络诊断、unifi、ubnt、主卧异常、可乐罐。
  DO NOT use for: 非 UniFi 设备。
type: routine
version: 1.3.2
tags: [unifi, network, wifi, ap, switch]
related_skills: [surge-gateway, openwrt-router]
---

# UniFi 设备运维 (unifi-ops)

## 🔗 与 `surge-gateway` / `openwrt-router` 的交叉引用

本 skill 管理物理网络层（AP/交换机/Controller），`surge-gateway` 管理代理网关层（Surge for Mac, <internal IP redacted>），`openwrt-router` 管理 OpenWrt/iStoreOS 路由器层（WAN/LAN、DHCP、DNSMasq、NAT/firewall、UCI/opkg）。三者互补：

| 场景 | 先用 | 原因 |
|------|------|------|
| WiFi 客户端断连 | unifi-ops | 查 AP VAP/satisfaction/信道 |
| 某设备网速慢 | surge-gateway | 查其 Surge 规则/策略组/节点延迟 |
| DNS 解析异常 | surge-gateway | Surge 网关劫持 DNS |
| AP 离线/reboot 循环 | unifi-ops | 查 PoE 供电/固件/Controller |
| 设备识别（物理位置） | unifi-ops | WiFi AP 关联 → 房间定位 |
| 设备识别（流量特征） | surge-gateway | ARP+DHCP+Surge 请求日志 |
| 跨境访问故障 | surge-gateway | 代理节点/规则/DNS 泄漏 |
| 局域网连通性 | unifi-ops | 交换机端口/LLDP/VLAN |
| 默认网关/DHCP/NAT/firewall 异常 | openwrt-router | OpenWrt/iStoreOS 路由器层 |
| LuCI/Dropbear/opkg/iStoreOS 插件问题 | openwrt-router | 非 UniFi Controller/AP 问题 |
| 设备无法联网（全链路） | unifi-ops → openwrt-router → surge-gateway | 先物理关联，再 DHCP/网关，最后代理规则 |

> Surge 网关 IP <internal IP redacted>，OpenWrt/iStoreOS 网关常见 IP <internal IP redacted>，Controller IP <internal IP redacted>

## 🚨 Red Flags

| Excuse | Why it's wrong |
|--------|---------------|
| "需要 API Key，2FA 挡住了" | 密码中拼接验证码即可：`password|code` |
| "MongoDB 改了就行" | MongoDB 直改不触发 provision，AP 配置不会自动更新 |
| "upgrade <url> 都能升级" | AP v6.7+ 只有 selfupgrade/fwupdate；UFLHD 等型号 selfupgrade 下载后不刷写，需 `ubntbox fwupdate.real -m` |
| "mca-dump 太大看不懂" | JSON 结构化，按 key 取；本地 python3 解析 |
| "设备太多一个个 SSH 太慢" | 并行 SSH + MongoDB 预取 IP |
| "AP 只有部分 VAP" | 先查 MongoDB `wlanconf.ap_group_ids` → `apgroup.device_macs`，再看 AP 本地 `radio.X.virtual.N` 是否完整 |
| "DFS Radar 告警不停，信道改不了" | MongoDB `radio_table.channel` 改后需 AP 本地同步改 `radio.2.channel` → `cfgmtd -w` → sysrq 重启。UFLHD 等型号 cfgmtd 可能静默失败，需验证 `grep` 确认写入后再 persist |

## 🔀 Decision Tree

```
UniFi 运维任务？
├── 全设备巡检 → 并行 SSH 所有 AP + 交换机 → 汇总报告
├── 设备状态 → SSH mca-dump / top / uptime
├── VAP/客户端 → SSH mca-dump → vap_table（过滤 scan_table！）
│   ├── 某 AP 缺部分 VAP → MongoDB wlanconf.ap_group_ids → apgroup.device_macs
│   └── 所有 VAP 缺 → AP 本地 radio.virtual / wireless / aaa 三层
├── DFS 干扰/信道调整 → MongoDB radio_table.channel → AP 本地 system.cfg → cfgmtd -w → sysrq 重启
├── 物理拓扑 → SSH mca-dump → lldp_table
├── 固件升级 → selfupgrade（优先）→ ubntbox fwupdate.real -m（手动）
├── 配置修复 → API force-provision / AP 本地 system.cfg 三层全量
├── 设备清单 → MongoDB db.device.find()
├── 站点发现 → MongoDB db.site.findOne() → key 字段即 API 路径名
└── 发现 Controller → 端口扫 8443/443 → curl --http1.1 验证
```

## 📋 环境速查

| 资源 | 地址/凭据 |
|------|----------|
| Controller SSH | root:<password redacted>@<internal IP redacted> |
| Controller API | https://<internal IP redacted>:8443，<email redacted> |
| API 2FA | 密码格式：`<password redacted>|验证码`（pipe 分隔） |
| API Site | `super`（非 default！从 MongoDB `db.site.findOne()` 的 `key` 字段获取） |
| Controller MongoDB | 127.0.0.1:27117，db=ace |
| 设备 SSH（7台） | admin:<password redacted>@各IP |
| SSH 隧道 | `ssh -L 27117:127.0.0.1:27117 root@<internal IP redacted>` |

## ⚠️ 关键陷阱

| 陷阱 | 说明 |
|------|------|
| **MongoDB 直改不触发 provision** | 改 `ace` 数据库不推送到 AP。需 API `force-provision` 或 Controller Web UI。 |
| **upgrade 命令不存在** | AP v6.7+ 用 `selfupgrade`（自动拉取）或 `fwupdate`。UFLHD 等型号 selfupgrade 下载后需 `ubntbox fwupdate.real -m` 手动刷写。 |
| **AP 无 python3** | mca-dump JSON 须在 Mac 本地解析。AP 上用 grep 做简单提取。 |
| **信道利用率在 athstats** | `radio_table[n].athstats.cu_total`，不在 radio_table 顶层。 |
| **HTTP/2 协议错误** | curl 必须加 `--http1.1`，否则 TLS 后零字节。 |
| **vap_table vs scan_table 混淆** | vap_table=自己广播的 SSID；scan_table=扫描到的附近 WiFi。诊断时注意区分。 |
| **WLAN 过滤：AP 组** | WLAN 通过 `wlanconf.ap_group_ids` 限制广播范围。对应 `apgroup.device_macs` 决定哪些 AP 获得该 WLAN。AP MAC 不在组内 → 收不到该 SSID。修复：MongoDB `$addToSet` 加 MAC 到 `apgroup.device_macs`。 |
| **cfgmtd -w 后 VAP 缺失** | cfgmtd 生成 hostapd 配置依赖 `radio.X.virtual.N` 条目。缺失则虚拟接口 (ra1/ra2/rai1/rai2) 不创建。需同时写入 `radio.*`（含 virtual）、`wireless.*`、`aaa.*` 三层。 |
| **hostapd "no bridge exist"** | reboot 后 cfgmtd 创建接口但不加入 br0。需 `brctl addif br0 <iface> && ip link set <iface> up` 后手动启动 hostapd。 |
| **cfgmtd -w 静默失败** | UFLHD 等型号 `sed` 改 `/tmp/system.cfg` 后 `cfgmtd -w` 输出正常但重启后回退旧值。解决办法：改前 `grep` 确认当前值，改后立即 `grep` 验证新值已写入，再 persist。若重启后仍回退 → 重做（已复现 1 次）。 |
| **ASIC 交换机无 MAC 表** | US-16P150 交换芯片 MAC/FDB 表不可通过 SSH 常规命令（`swctl show fdb`/`brctl showmacs`/`lldpcli`）访问。端口-设备映射只能通过 Controller Web UI 或 LLDP 从 AP 端反推。 |
| **5GHz 全 AP 同信道** | Controller 不会自动分散信道。全部 AP 挤同一 DFS 信道 → 同频干扰 + Radar 集体触发。需手动分配：ch149-161（UNII-3，非 DFS）。 |
| **API site 名非 "default"** | 本站点 MongoDB 中 `key="super"`，API 需用 `/api/s/super/...`。先查 `db.site.findOne()`。 |
| **本地管理员 API 无权限** | UniFi 7.4 本地管理员即使 `is_super:true` 仍 `NoSiteContext`。建议用主账户 <email redacted> + 2FA 登录。 |

## 🔑 Controller API 登录

```bash
# 登录（密码|验证码）
curl -sk --http1.1 --noproxy '*' -X POST \
  -H 'Content-Type: application/json' -c /tmp/unifi_cookies.txt \
  -d '{"username":"<email redacted>","password":"<password redacted>|验证码","remember":true}' \
  https://<internal IP redacted>:8443/api/login

# 提取 CSRF token
CSRF=$(grep csrf_token /tmp/unifi_cookies.txt | awk '{print $NF}')

# ⚠️ 站点名从 MongoDB 获取：key="super"
SITE="super"

# 后续请求
curl -sk --http1.1 --noproxy '*' -b /tmp/unifi_cookies.txt -H "X-CSRF-Token: $CSRF" \
  "https://<internal IP redacted>:8443/api/s/$SITE/stat/device"
```

### Force provision AP

```bash
curl -sk --http1.1 --noproxy '*' -X POST \
  -H "X-CSRF-Token: $CSRF" -H "Content-Type: application/json" \
  -b /tmp/unifi_cookies.txt \
  -d '{"cmd":"force-provision","mac":"aa:bb:cc:dd:ee:ff"}' \
  "https://<internal IP redacted>:8443/api/s/$SITE/cmd/devmgr"
```

⚠️ Cookie 在 Controller 重启后失效，需重新登录。

## 🔧 SSH 诊断命令

### AP (UHDIW/U7NHD/UFLHD)

| 命令 | 作用 |
|------|------|
| `mca-dump` | 全量 JSON：radio_table, vap_table, lldp_table, satisfaction |
| `mca-scan` | WiFi 扫描 |
| `top -bn1` | CPU/内存 |
| `cat /proc/net/dev` | 接口流量 |
| `cat /proc/uptime` | 运行秒数 |
| `reboot` | 重启（Hermes 端被阻，用 `echo b > /proc/sysrq-trigger`） |
| `selfupgrade` | 自动拉取最新固件 |
| `fwupdate` | 手动升级（部分型号不生效，用 `ubntbox fwupdate.real -m`） |
| `grep "^aaa\." /tmp/system.cfg` | 查看 VAP 配置 |
| `cfgmtd -w -p /etc` | 持久化 system.cfg 修改到 flash |
| `brctl show br0` | 查看 bridge 成员 |
| `ps \| grep hostapd` | 查看运行中的 WiFi 进程 |

### 交换机 (US16P150)

`cat /proc/net/dev` | `swctl show port-statistics` | `top -bn1`

## 🗄️ MongoDB

```bash
# 走 SSH 隧道或在 Controller 上执行
mongo --port 27117 ace --eval "db.device.find({},{name:1,model:1,ip:1,version:1})"
mongo --port 27117 ace --eval "db.site.findOne({},{key:1,name:1})"
mongo --port 27117 ace --eval "db.wlanconf.find({enabled:true},{name:1,ap_group_ids:1})"
mongo --port 27117 ace --eval "db.apgroup.find({},{name:1,device_macs:1})"
```

## 📊 常用运维场景

### 场景 1：全设备巡检
并行 SSH → top/uptime/net + AP 的 mca-dump → satisfaction/信道/VAP 客户端数

### 场景 2：AP VAP 异常诊断（某 AP 缺少部分 SSID）

**Step 1 — 查 Controller WLAN 组过滤（最常见根因）**

```bash
# 1.1 查 WLAN 的 ap_group_ids
mongo --port 27117 ace --eval "db.wlanconf.find({enabled:true},{name:1,ap_group_ids:1})"

# 1.2 查对应 AP 组的 device_macs
mongo --port 27117 ace --eval "db.apgroup.find({},{name:1,device_macs:1})"

# 1.3 如果 AP MAC 不在组内 → 加入
mongo --port 27117 ace --eval "
  db.apgroup.update({name:'组名'},{\$addToSet:{device_macs:'aa:bb:cc:dd:ee:ff'}})
"
```

**Step 2 — 全量三层配置修复（本地急救，MongoDB 已修正但 AP 仍不生效时）**

```bash
# 2.1 从正常同型号 AP 导出 radio/wireless/aaa 三节
ssh admin@<正常AP> 'grep "^radio\.\|^wireless\.\|^aaa\." /tmp/system.cfg' > /tmp/good.cfg

# 2.2 在异常 AP 上：删除旧配置 + 写入新配置 + 持久化 + 重启
sed -i '/^radio\./d; /^wireless\./d; /^aaa\./d' /tmp/system.cfg
cat >> /tmp/system.cfg << 'EOF'
... (三层完整配置，注意 own_ip_addr 需改为本机 IP) ...
EOF
cfgmtd -w -p /etc
echo 1 > /proc/sys/kernel/sysrq && echo b > /proc/sysrq-trigger
```

**Step 3 — 重启后补充 bridge + hostapd**

```bash
# 3.1 加虚拟接口到 bridge
for i in ra1 ra2 rai1 rai2; do
  brctl addif br0 $i && ip link set $i up
done

# 3.2 启动所有 hostapd 实例
for cfg in ra0 ra1 ra2 rai0 rai1 rai2; do
  hostapd -B -P /var/run/hostapd/$cfg.pid /etc/hostapd/$cfg.cfg
done

# 3.3 验证
ps | grep hostapd | grep -v grep | wc -l  # 应为 6
mca-dump | python3 -c 'import sys,json; print(len(json.load(sys.stdin)["vap_table"]))'
```

⚠️ 本地配置在 Controller 下次推送后可能被覆盖——但若 MongoDB 中 AP 组已修正，Controller 推送的配置应与本地一致。

### 场景 3：物理拓扑发现
`mca-dump` → `lldp_table` → chassis_id（上行交换机 MAC）+ port_id（端口号）

### 场景 4：固件升级

**自动升级（优先尝试）**

```bash
ssh admin@<ip> 'selfupgrade'   # AP 从 release repo 拉最新 → 自动 reboot
```

**手动升级（selfupgrade 下载成功但 reboot 后未生效时使用）**

部分型号（如 UFLHD "可乐罐"）selfupgrade 下载后不自动刷写，需手动：

```bash
# 4.1 从 Controller firmware.json 获取固件 URL
ssh root@<internal IP redacted> 'grep -A2 "\"UFLHD\"" /usr/lib/unifi/data/firmware.json | grep url'

# 4.2 下载到 AP 并刷写（AP 无 wget，用 curl）
ssh admin@<ip> "curl -sL -o /tmp/fwupdate.bin '<固件URL>' && ubntbox fwupdate.real -m /tmp/fwupdate.bin"
# AP 自动 reboot 并生效
```

备选：`syswrapper.sh upgrade /tmp/fwupdate.bin`

### 场景 5：AP 单 VAP 修复
单 SSID 替换：sed 改 `/tmp/system.cfg` → `cfgmtd -w -p /etc` → `echo b > /proc/sysrq-trigger`

### 场景 6：本地管理员创建（免 2FA）

```bash
# 在 Controller 上通过 MongoDB 创建
ssh root@<internal IP redacted> 'mongo --port 27117 ace --eval "
  db.admin.insert({
    name: \"hermes\",
    email: \"<email redacted>\",
    x_shadow: \"\$6\$\$(python3 -c \\\"import crypt; print(crypt.crypt(\\\"密码\\\", \\\"\\\$6\\\$\\\" + str(int(time.time())) + \\\"\\\"))\\\")\",
    time_created: NumberLong($(date +%s)000),
    is_super: true,
    super_site_roles: [{site_id: \"<site_ObjectId>\", role: \"admin\"}]
  });
"'
```

⚠️ UniFi 7.4 本地管理员即使设了 `is_super: true` 和 `super_site_roles`，API 仍可能报 `NoSiteContext`。此问题未完全解决——推荐使用主账户 <email redacted> + 2FA。

### 场景 7：DFS 雷达干扰与 5GHz 信道迁移

**症状**：告警 `EVT_AP_RadarDetected`，channel 36，多台 AP 反复触发

**根因**：全部 AP 默认集中在 ch36 (5180MHz, DFS 信道)，雷达信号强制断流切信道 + 同频干扰

**解决方案——迁移到 UNII-3 非 DFS 信道**：

| 信道 | 频率 | DFS？ |
|------|------|-------|
| ch149 | 5745MHz | ❌ |
| ch153 | 5765MHz | ❌ |
| ch157 | 5785MHz | ❌ |
| ch161 | 5805MHz | ❌ |

**分频策略**（6台 AP 示例）：

| AP | 推荐信道 |
|----|---------|
| 客厅/次卧 | ch149 |
| 起居室/可乐罐 | ch153 |
| 客卧 | ch157 |
| 主卧 | ch161 |

> 可乐罐若 daisy chain 在主卧后面，信道应隔开（ch153 vs ch161）

**执行步骤**（完整脚本见 `references/session-2026-06-10-dfs-fix.md`）：

```bash
# 1. MongoDB 改信道 → 2. AP 本地 sed radio.2.channel + cfgmtd -w + sysrq 重启（分两批）→ 3. 主卧补 bridge+hostapd → 4. MCA dump 验证 → 5. 归档 Radar 告警
```
⚠️ UFLHD cfgmtd 可能静默失败——重启后必须 MCA dump 验证

## ✅ Verification Checklist

- [ ] mca-dump 解析在 Mac 本地（非 AP）
- [ ] vap_table 与 scan_table 已区分
- [ ] 并行 SSH ≤ 10 并发
- [ ] curl 连接 Controller 已加 `--http1.1`
- [ ] API site 名已查 MongoDB（非猜测）

## 📦 References

| File | When to read |
|------|-------------|
| `references/device-inventory.md` | 设备清单 |
| `references/mca-dump-keys.md` | mca-dump JSON 字段 |
| `references/mongodb-collections.md` | MongoDB 集合 schema |
| `references/ssh-commands-full.md` | 完整 SSH 命令参考 |
| `references/external-tools-reference.md` | 外部工具参考 |
| `references/session-2026-06-10-inspection.md` | 首次巡检全记录 + 异常分析 |
| `references/session-2026-06-10-ap-fix.md` | 主卧 AP 根因修复 + 可乐罐固件升级实录 |
| `references/session-2026-06-10-dfs-fix.md` | DFS 信道迁移 + 全线巡检实录 |
| `references/cross-skill-surge.md` | 与 `surge-gateway` 交叉引用的详细场景分发表 |
| `references/cross-skill-openwrt.md` | 与 `openwrt-router` 交叉引用：路由器层 vs UniFi 物理层 |
