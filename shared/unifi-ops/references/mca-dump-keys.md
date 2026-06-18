# mca-dump JSON 关键字段

UniFi AP 的 `mca-dump` 输出完整 JSON 状态。以下是常用字段：

## 设备信息

| Key | 类型 | 说明 |
|-----|------|------|
| `hostname` | string | 设备名 |
| `model` / `model_display` | string | 型号 |
| `version` | string | 固件版本 |
| `ip` | string | IP 地址 |
| `mac` | string | MAC 地址 |
| `uptime` | int | 运行秒数 |
| `satisfaction` | int | 客户端满意度 (0-100) |
| `state` | int | 状态 (1=在线 0=离线 2=待采纳) |

## 射频信息

| Key | 类型 | 说明 |
|-----|------|------|
| `radio_table` | array | 射频接口列表 (2.4G + 5G) |
| `radio_table[n].radio` | string | 频段名 (如 `ng`=2.4GHz, `na`=5GHz) |
| `radio_table[n].name` | string | 接口名 (如 `ra0`, `rai0`) |
| `radio_table[n].athstats.cu_total` | int | 信道总利用率 % |
| `radio_table[n].athstats.cu_self_tx` | int | 自身发送利用率 % |
| `radio_table[n].athstats.cu_interf` | int | 干扰利用率 % |
| `radio_table[n].athstats.satisfaction` | int | 该 radio 满意度 (0-100) |
| `radio_table[n].athstats.noise_floor` | int | 噪声底 (dBm) |
| `radio_table[n].max_txpower` | int | 最大发射功率 |
| `radio_table[n].is_11ac` | bool | 是否 802.11ac |

## VAP (虚拟 AP / SSID)

| Key | 类型 | 说明 |
|-----|------|------|
| `vap_table` | array | SSID 列表 |
| `vap_table[n].essid` | string | WiFi 名称 |
| `vap_table[n].num_sta` | int | 连接客户端数 |
| `vap_table[n].rx_bytes` / `tx_bytes` | int | 流量统计 |

## 系统统计

| Key | 类型 | 说明 |
|-----|------|------|
| `sys_stats.mem_total` / `mem_used` | int | 内存 (KB) |
| `sys_stats.cpu` | int | CPU 使用率 % |
| `sys_stats.loadavg_1` / `_5` / `_15` | float | 系统负载 |

## 客户端（需用 `mca-sta <mac>` 或从 `vap_table` 推导）

`mca-dump` 不直接含客户端列表。获取客户端：
- `mca-sta <mac>` — 单个客户端详情
- `iw dev <iface> station dump` — 内核级客户端列表
- Controller MongoDB: `db.user.find()` — 全局客户端
