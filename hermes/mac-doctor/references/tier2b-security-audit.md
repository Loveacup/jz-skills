# Tier 2b: 安全审计

> 来源：gfreedman/mac_audit + N4M3Z/check-mac + Neo23x0/macguard-audit

## 检查项列表（共 27 项）

### 核心安全

```bash
# 1. SIP 状态
csrutil status 2>/dev/null || echo "⚠️ SIP status unknown"

# 2. Gatekeeper
spctl --status 2>/dev/null

# 3. FileVault
fdesetup status 2>/dev/null

# 4. 防火墙（应用防火墙）
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null

# 5. 防火墙隐身模式
/usr/libexec/ApplicationFirewall/socketfilterfw --getstealthmode 2>/dev/null

# 6. XProtect 签名新鲜度（locale-safe stat -f "%m"，且兼容 macOS 15+ Cryptex 路径）
XP1="/Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Resources/XProtect.plist"
XP2="/private/var/protected/xprotect/XProtect.bundle/Contents/Resources/XProtect.plist"
for xp in "$XP1" "$XP2"; do
  if [ -e "$xp" ]; then
    mtime=$(stat -f "%m" "$xp" 2>/dev/null)
    age_days=$(( ($(date +%s) - mtime) / 86400 ))
    echo "XProtect: $xp → ${age_days}d old"
    break
  fi
done
# >30 天 → 🟡；>60 天 → 🔴

# 7. 自动安全更新（macOS 15+ 优先 DDM 持久化 plist；fallback 到 legacy preference）
DDM="/var/db/softwareupdate/SoftwareUpdateDDMStatePersistence.plist"
if [ -r "$DDM" ]; then
  sudo plutil -p "$DDM" 2>/dev/null | grep -iE "automatic|criticalupdate" | head -4
else
  softwareupdate --schedule 2>/dev/null \
    || defaults read /Library/Preferences/com.apple.SoftwareUpdate AutomaticCheckEnabled 2>/dev/null \
    || echo "无法读取自动更新设置（可能 MDM 管理）"
fi

# 8. Secure Boot Policy (Apple Silicon) — bputil 给出策略名（Full/Reduced/Permissive）
if [[ "$(sysctl -n machdep.cpu.brand_string)" == *"Apple"* ]]; then
  csrutil authenticated-root status 2>/dev/null
  sudo bputil -d 2>/dev/null | grep -E "Security Mode|Boot Mode|Secure Boot" | head -4
fi

# 8b. 防火墙自动放行已签名 App（macOS 26 已移除 --getloggingmode）
/usr/libexec/ApplicationFirewall/socketfilterfw --getallowsigned 2>/dev/null
# 若 ENABLED：所有 Apple 签名 App 自动绕过防火墙规则，建议关闭以提高严格度

# 8c. 系统扩展（System Extensions）清单
systemextensionsctl list 2>/dev/null | awk '/\[activated|enabled\]/' | head -10

# 8d. MDM Configuration Profiles（>0 → 受管设备；flag 警告时要带"可能 MDM 强制"提示）
PROFILES=$(sudo profiles -P 2>/dev/null | grep -c "attribute: name")
echo "Configuration Profiles: ${PROFILES:-0}"

# 8e. NTP 时间同步（错时钟 → TLS / Kerberos 失败）
# com.apple.timed 是 system 级服务，用户 `launchctl list` 看不见；macOS 26 没有可靠的 unprivileged 检查方式
sudo -n systemsetup -getusingnetworktime 2>/dev/null \
  || echo "NTP: 状态需 sudo 确认 — 运行 \`sudo systemsetup -getusingnetworktime\`"

# 8f. Hibernate Mode（仅笔记本：25 = 加密休眠；3 = 标准休眠；桌面无此设置）
HIB=$(pmset -g 2>/dev/null | awk '/hibernatemode/{print $2; exit}')
if [ -n "$HIB" ]; then
  echo "hibernatemode = $HIB"
else
  echo "hibernatemode: not applicable (desktop Mac)"
fi

# 8g. /etc/hosts 审计（非默认条目 → 可能被劫持/重定向）
awk '!/^#/ && !/^[[:space:]]*$/ && \
     !/^127\.0\.0\.1[[:space:]]+localhost/ && \
     !/^255\.255\.255\.255[[:space:]]+broadcasthost/ && \
     !/^::1[[:space:]]+localhost/ && \
     !/^fe80::1%lo0/' /etc/hosts 2>/dev/null
# 输出 = 非默认条目；>5 行需要人工审视
```

### 用户安全

```bash
# 9. 自动登录
defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser 2>/dev/null

# 10. Guest 账户
defaults read /Library/Preferences/com.apple.loginwindow GuestEnabled 2>/dev/null

# 11. 屏幕锁（空闲时间，秒）
sysadminctl -screenLock status 2>/dev/null || defaults -currentHost read com.apple.screensaver idleTime 2>/dev/null

# 12. 管理员权限
groups | grep -q admin && echo "Is admin" || echo "Standard user"
```

### 网络 & 共享

```bash
# 13. 远程登录 (SSH) — systemsetup 需 sudo；launchctl 无需 sudo
launchctl list 2>/dev/null | grep -q com.openssh.sshd && echo "SSH: listening" || echo "SSH: off"

# 14. 屏幕共享（无需 sudo）
launchctl list 2>/dev/null | grep -q com.apple.screensharing && echo "Screen Sharing: on" || echo "off"

# 15. 文件共享 SMB（无需 sudo）
launchctl list 2>/dev/null | grep -q com.apple.smbd && echo "SMB: on" || echo "off"

# 16. AirDrop 可见性（双 key：sharingd + finder，覆盖 macOS 13+ 新行为）
defaults read com.apple.sharingd DiscoverableMode 2>/dev/null
defaults read com.apple.finder ShareAirDropWithEveryone 2>/dev/null

# 17. Internet/Printer/AppleEvents Sharing
launchctl list 2>/dev/null | grep -q com.apple.NetworkSharing && echo "Internet Sharing: on"
cupsctl 2>/dev/null | grep -E "_share_printers"
launchctl list 2>/dev/null | grep -q com.apple.AEServer && echo "Remote AppleEvents: on"
```

### SSH & 密钥

```bash
# 26. SSH 密钥存在性
ls ~/.ssh/id_* 2>/dev/null | grep -v '.pub'

# 27. SSH 密钥强度检查
for key in ~/.ssh/id_*; do
  [[ "$key" == *.pub ]] && continue
  ssh-keygen -l -f "$key" 2>/dev/null
done
```

## 输出格式

Tier 2 汇总表中显示，每项标记 ✅/⚠️/❌/ℹ️

## 注意事项

- macOS 26+ 的 `defaults read` 可能对某些安全设置无效（Apple 转向 DDM）
- MDM 管理的 Mac 上，某些设置即使显示"未启用"也可能是故意的
- SSH 密钥强度 <2048 位标记为 ⚠️，<1024 位标记为 ❌
