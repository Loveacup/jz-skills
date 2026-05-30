# Tier 2c: 硬件审计

> 来源：gfreedman/mac_audit + CodeGeekR/macOS-hardware-info

## 检查项

### 电池健康

**桌面 Mac 跳过**：Mac mini / Studio / Pro 没有电池，强制读会返回 `0/0` 触发误报。

```bash
# 0. 先判断机型（mini/Studio/Pro → 跳过电池检查）
MODEL=$(system_profiler SPHardwareDataType 2>/dev/null | awk -F': ' '/Model Name/{print $2}')
case "$MODEL" in
  *mini*|*Studio*|*Pro*)
    echo "Desktop Mac ($MODEL) — 无电池，跳过 1/2"
    ;;
  *)
    # 1. 电池详细数据（ioreg 比 SPPowerDataType 快 10×；优先用）
    ioreg -rc AppleSmartBattery 2>/dev/null | grep -E '"CycleCount"|"MaxCapacity"|"DesignCapacity"|"Temperature"'
    # 健康度 = MaxCapacity / DesignCapacity * 100
    # 温度 = Temperature / 100  → °C（>40°C 警告）

    # 2. 用户友好摘要（fallback）
    system_profiler SPPowerDataType 2>/dev/null | grep -E "Cycle Count|Condition|Maximum Capacity"
    ;;
esac
```

### 磁盘健康

```bash
# 3. SMART 状态（启动盘）
diskutil info / | grep "SMART Status"

# 4. 详细 SMART（需要 smartmontools）
if command -v smartctl &>/dev/null; then
  smartctl -a disk0 2>/dev/null | grep -E "SMART overall|Reallocated|Pending|CRC"
fi
```

### 系统稳定性

```bash
# 5. 热节流检测（snapshot，不要用 `pmset -g thermlog` — 那是流式订阅会挂起）
pmset -g therm 2>/dev/null
# 关键字: "CPU_Scheduler_Limit = 100" 健康；<100 即被限速
# "No thermal warning level has been recorded" → 健康

# 6. Kernel Panic（过去30天）
find /Library/Logs/DiagnosticReports/ -name "kernel*" -mtime -30 2>/dev/null | wc -l

# 7. TimeMachine 备份健康（数据韧性）
tmutil status 2>/dev/null | grep -E "Running|BackupPhase"
tmutil latestbackup 2>/dev/null
# 最新备份 >7 天 → 🟡；从未备份 → 🔴

# 8. 电池温度（笔记本，°C）— ioreg Temperature 字段除 100
if ! [[ "$MODEL" =~ (mini|Studio|Pro) ]] || [[ "$MODEL" =~ MacBook ]]; then
  TEMP_RAW=$(ioreg -rc AppleSmartBattery 2>/dev/null | awk -F' = ' '/"Temperature"/{print $2; exit}')
  [ -n "$TEMP_RAW" ] && awk -v t="$TEMP_RAW" 'BEGIN {printf "Battery: %.1f °C\n", t/100}'
  # >40°C 持续 → 🟡（散热问题/重负载）；>45°C → 🔴
fi

# 9. Wake/Sleep 事件（DarkWake 凶手定位）
pmset -g log 2>/dev/null | grep -E " Wake | DarkWake | Sleep " | tail -20
# 提取 "due to '...'" 凶手 top 10：常见 EC.LidOpen / UserActivity / BT.HID / WiFi.GTKRotation
pmset -g log 2>/dev/null \
  | grep "due to '" \
  | awk -F"due to '" '{print $2}' | awk -F"'" '{print $1}' \
  | sort | uniq -c | sort -rn | head -10
```

## 注意事项

- Apple Silicon 的 SMART 数据通过专有控制器，smartctl 可能无法读取全部指标
- 电池健康 <80% 且循环 >1000 → 建议更换
- 热节流偶尔出现是正常的，频繁出现 → 散热问题
- ⚠️ **不要用 `pmset -g thermlog`**：它是流式日志订阅，永不退出，会让脚本超时 15s。用 `pmset -g therm`（snapshot）。
- 桌面 Mac（mini/Studio/Pro）跳过电池检查；否则会返回 `MaxCapacity=0 / DesignCapacity=0` 导致 NaN 误报
