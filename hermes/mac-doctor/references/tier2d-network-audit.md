# Tier 2d: 网络审计

> 来源：gfreedman/mac_audit

## 检查项

```bash
# 1a. TCP 监听端口
lsof -iTCP -sTCP:LISTEN -nP 2>/dev/null | awk '{print $1, $9}' | sort -u | head -20

# 1b. UDP 监听端口（mDNS / VPN / 蜂窝共享只在 UDP 暴露）
lsof -iUDP -nP 2>/dev/null | awk '/UDP/{print $1, $9}' | sort -u | head -20

# 2. DNS 配置
scutil --dns | grep "nameserver\[" | awk '{print $3}' | sort -u

# 3. 代理设置
scutil --proxy | grep -E "HTTPEnable|HTTPSEnable|SOCKSEnable" | grep "1 : 1"

# 4. 动态发现 Wi-Fi 接口（en0 在桌面 Mac 上是 Ethernet，不是 Wi-Fi）
WIFI_IF=$(networksetup -listallhardwareports 2>/dev/null | awk '/Wi-Fi/{getline; print $2; exit}')

# 5. 当前 Wi-Fi
[ -n "$WIFI_IF" ] && networksetup -getairportnetwork "$WIFI_IF" 2>/dev/null

# 6. 已保存 Wi-Fi 数量
[ -n "$WIFI_IF" ] && networksetup -listpreferredwirelessnetworks "$WIFI_IF" 2>/dev/null | tail -n +2 | wc -l

# 7. 蓝牙状态（system_profiler 替代 blueutil/已废弃的 defaults key，无需第三方）
system_profiler SPBluetoothDataType 2>/dev/null | grep -E "State:|Discoverable:" | head -2

# 8. 已知风险端口快速识别
for port in 22 23 445 5900 3389; do
  lsof -iTCP:$port -sTCP:LISTEN -nP 2>/dev/null | awk -v p=$port 'NR>1{print "port "p" ("$1") → "$9}'
done
# 22=SSH, 23=Telnet(明文!), 445=SMB, 5900=VNC, 3389=RDP

# 9. Wake-on-Network（womp）— 安全 + 功耗考量
pmset -g 2>/dev/null | awk '/womp/{print "womp = " $2}'
# womp = 1 且非台式机/服务器场景 → 🟡 建议关闭

# 10. Wi-Fi 信号质量（仅 Wi-Fi 已连接时；桌面+以太网时静默无输出）
WIFI_QUALITY=$(system_profiler SPAirPortDataType 2>/dev/null \
  | awk '/Current Network Information/,/Other Local Wi-Fi Networks/' \
  | grep -E "Signal / Noise|Transmit Rate|Channel|PHY Mode" \
  | sed 's/^[[:space:]]*//')
if [ -n "$WIFI_QUALITY" ]; then
  echo "$WIFI_QUALITY"
else
  echo "Wi-Fi 未连接或不可用（桌面 Mac + 以太网常见）"
fi
# RSSI <-75 dBm → 🟡；噪声 >-85 dBm → 干扰严重；TX Rate <50 Mbps + RSSI 好 → 协议/信道问题
```

## 注意事项

- 已保存 Wi-Fi >50 且含公开热点 → 隐私风险
- DNS 指向未知服务器 → ⚠️
- 蓝牙不使用时建议关闭
- 桌面 Mac（mini/Studio/Pro）`en0` 是 Ethernet；必须用 `-listallhardwareports` 动态发现 Wi-Fi 接口
- `blueutil` 是第三方 Homebrew 工具；`defaults read … ControllerPowerState` 在 macOS 26 已无效——统一使用 `system_profiler SPBluetoothDataType`
