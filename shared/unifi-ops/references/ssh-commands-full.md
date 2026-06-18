# 完整 SSH 命令参考

## 通用 Linux 命令（所有设备）

```bash
# CPU/内存
top -bn1 | head -5
free -m
cat /proc/loadavg

# 磁盘
df -h
cat /proc/uptime    # 运行时间（秒）

# 网络
ifconfig -a
ip addr
cat /proc/net/dev   # 接口流量统计
arp -a              # ARP 表
route -n            # 路由表

# 进程
ps aux | head -20

# 日志
logread | tail -50           # 系统日志
dmesg | tail -30             # 内核日志
tail -f /var/log/messages    # 实时日志

# 系统
uname -a
cat /etc/version             # 固件版本（非 AP）
```

## AP 专用 MCA 命令

```bash
# 完整状态 dump (JSON)
mca-dump

# WiFi 信道扫描
mca-scan

# 客户端详情（需 MAC）
mca-sta <mac>

# CLI 交互式
mca-cli-op info     # 设备信息
mca-cli-op reboot   # 重启

# 监控模式
mca-monitor

# 控制命令
mca-ctrl -t dump    # 统计 dump
```

## AP WiFi 诊断

```bash
# 查看无线接口
iw dev

# 查看接口详情
iwinfo <iface>

# 客户端列表（内核级）
iw dev <iface> station dump

# 信道信息
iw dev <iface> info
iwlist <iface> channel

# 扫描周边 AP
iw dev <iface> scan | grep -E "SSID|signal|freq"
```

## 交换机专用

```bash
# 端口统计
swctl -d switch show port-statistics
cat /proc/net/dev | grep -E "eth|port"

# PoE 状态（如果有）
swctl -d switch show poe-status

# VLAN
swctl -d switch show vlan
```

## 设备运维

```bash
# 重启
reboot
# 或
mca-cli-op reboot

# 固件升级（需指定 URL）
upgrade https://dl.ubnt.com/unifi/firmware/xxx.bin
# 或
fwupdate --url https://dl.ubnt.com/unifi/firmware/xxx.bin

# 恢复出厂
syswrapper.sh restore-default
set-default

# 查看 inform 地址
info
mca-cli-op info | grep -i inform

# 手动设 inform 地址
set-inform http://<internal IP redacted>:8080/inform
```

## 更新设备 SSH 凭据

设备 SSH 凭据在 Controller 的 `ace.setting` 集合中：
```javascript
db.setting.find({key: "ssh_auth"})
```

或通过 Controller Web UI：
Settings → Site → Device Authentication

## 一键批量脚本

```bash
#!/bin/bash
# 批量 SSH 执行命令
PASS="<password redacted>"
USER="admin"
CMD="$1"

for ip in 192.168.2.{137,138,139,140,141,98,169}; do
  echo "=== $ip ==="
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$USER@$ip" "$CMD" 2>/dev/null &
done
wait
```
