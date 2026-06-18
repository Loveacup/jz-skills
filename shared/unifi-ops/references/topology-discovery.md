# LLDP 拓扑发现

UniFi 设备通过 LLDP（Link Layer Discovery Protocol）自动发现邻居。

## mca-dump LLDP 表

```bash
ssh admin@<ap_ip> 'mca-dump 2>/dev/null' | jq '.lldp_table[]'
```

字段：
- `chassis_id` — 上层设备 MAC（通常是交换机）
- `chassis_id_subtype` — "mac"
- `is_wired` — true=有线连接
- `local_port_idx` — 本机端口号
- `local_port_name` — 端口名（如 eth0）
- `port_id` — 对端端口标识（如 "local Port 6"）
- `power_allocated` — PoE 分配功率（mW）
- `power_requested` — 请求功率

## 实战：主卧 AP 拓扑

```json
{
  "chassis_id": "18:e8:29:2a:0c:93",    // 交换机 MAC
  "port_id": "local Port 6",             // 交换机端口 6
  "is_wired": true,
  "local_port_name": "eth0",             // AP 的 eth0
  "power_allocated": 25500,               // 25.5W PoE
  "power_requested": 12950
}
```

同时发现可乐罐（68:d7:9a:46:5c:8b）通过主卧 AP 的 PoE 输出端口供电：
```
交换机 Port 6 → 主卧 AP (eth0) → PoE Out → 可乐罐
```

## 交换机端口映射

通过匹配设备 MAC 和 LLDP chassis_id 可构建完整拓扑：

```bash
# 获取所有 AP 的 LLDP 信息
for ip in 192.168.2.{137,138,139,140,141,98}; do
  echo "=== $ip ==="
  ssh admin@$ip 'mca-dump 2>/dev/null' | jq '{hostname, ip, lldp: .lldp_table}'
done
```
