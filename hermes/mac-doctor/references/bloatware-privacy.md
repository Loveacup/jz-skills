# 臃肿检测 & 隐私扫描

> 来源：TheSmilemakers/system-monitor

## 臃肿检测

```bash
# 已知臃肿软件签名检查
bloatware=("CleanMyMac" "MacKeeper" "MacBooster" "Avast" "AVG" "Norton" "McAfee"
  "AdobeCreativeCloud" "Adobe Desktop Service")
for app in "${bloatware[@]}"; do
  pgrep -i "$app" &>/dev/null && echo "🔴 Bloatware: $app running"
done

# Electron 应用数 + 内存
ps aux | grep -iE "Electron|Chromium\.framework" | awk '{sum+=$6; c++} END {printf "Electron: %d apps, %.0f MB\n", c, sum/1024}'

# 重复浏览器 ⚠️ 不能用 pgrep -i 模糊匹配
# pgrep -i "Arc" 会匹配 searchpartyd/trialarchivingservice 等系统进程名含 "arc" 的
# pgrep -i "Edge" 同理误匹配 dataedge/knowledge 等
# 必须用 -x 精确匹配 + .app 路径验证
browsers_apps=(
  "Safari:/Safari.app"
  "Google Chrome:/Google Chrome.app"
  "Firefox:/Firefox.app"
  "Arc:/Arc.app"
  "Brave Browser:/Brave Browser.app"
  "Microsoft Edge:/Microsoft Edge.app"
)
running=0
for entry in "${browsers_apps[@]}"; do
  name="${entry%%:*}" path="${entry##*:}"
  # 用 pgrep -x 精确匹配进程名，再验证二进制路径含 .app
  pid=$(pgrep -x "$name" 2>/dev/null | head -1)
  [ -n "$pid" ] && ps -p "$pid" -o comm= 2>/dev/null | grep -qF "$path" && {
    echo "  $name ✅"
    ((running++))
  }
done
[ $running -gt 1 ] && echo "🟡 $running 个浏览器同时运行" || echo "✅ 仅 $running 个"

# 启动项
echo "LaunchAgents:"; ls ~/Library/LaunchAgents/ 2>/dev/null
```

## 隐私扫描

```bash
# TCC 权限审计（要求 Full Disk Access — 否则 sqlite3 返回 "unable to open database"）
TCC="/Library/Application Support/com.apple.TCC/TCC.db"
if ! sqlite3 "$TCC" "SELECT 1" >/dev/null 2>&1; then
  echo "⚠️ 需要授予终端/Claude Code 完整磁盘访问 (System Settings → Privacy & Security → Full Disk Access)"
else
  # 结构化分类输出：按权限类别聚合，优先看高敏感类
  for svc in \
    "kTCCServiceSystemPolicyAllFiles:完整磁盘访问" \
    "kTCCServiceScreenCapture:屏幕录制" \
    "kTCCServiceAccessibility:辅助功能" \
    "kTCCServicePostEvent:键盘模拟" \
    "kTCCServiceMicrophone:麦克风" \
    "kTCCServiceCamera:摄像头" \
    "kTCCServiceListenEvent:键盘事件监听" \
    "kTCCServiceAppleEvents:控制其他应用" \
    "kTCCServiceLocation:位置"; do
    code="${svc%%:*}"; label="${svc##*:}"
    echo "── $label ──"
    sqlite3 "$TCC" "SELECT client FROM access WHERE service='$code' AND auth_value=2" 2>/dev/null \
      | sed 's/^/  /'
  done
fi

# 可疑进程
suspicious=("keylogger" "spyware" "sniffer" "rat_" "trojan" "cryptominer")
for s in "${suspicious[@]}"; do
  ps aux | grep -i "$s" | grep -v grep && echo "🔴 Suspicious: $s"
done
```

### TCC 解读

- `kTCCServiceSystemPolicyAllFiles` / `kTCCServiceScreenCapture` / `kTCCServiceAccessibility` 是**高危三件套**——任何陌生 bundle id 必须人工审视
- `kTCCServicePostEvent` + `kTCCServiceListenEvent` 同时存在 = 可模拟+监听键盘（典型键盘记录器能力）
- `auth_value` 取值：`0`=denied / `2`=allowed / `3`=allowed (limited)
