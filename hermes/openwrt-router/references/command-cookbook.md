# OpenWrt Command Cookbook

All commands assume `HOST=${OPENWRT_HOST:-<internal IP redacted>}` and `USER=${OPENWRT_USER:-root}`. For password auth, pass password at runtime with `OPENWRT_PASSWORD` and `sshpass`; never write it to a file.

## SSH wrappers

Key auth (preferred):

```bash
ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$USER@$HOST" '<command>'
```

If password auth is required, inject it at runtime without putting the secret in the command line:

```bash
read -rs OPENWRT_PASSWORD
export OPENWRT_PASSWORD
sshpass -p "$OPENWRT_PASSWORD" ssh \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
  "$USER@$HOST" '<command>'
unset OPENWRT_PASSWORD
```

## Read-only baseline

```sh
echo SSH_OK
cat /etc/openwrt_release 2>/dev/null || true
ubus call system board 2>/dev/null || true
ubus call system info 2>/dev/null || true
uptime
df -h
free 2>/dev/null || cat /proc/meminfo | head
ip addr show
ip route show
```

## Network

```sh
uci show network
ubus list 'network.interface.*'
ubus call network.interface.wan status 2>/dev/null || true
ubus call network.interface.lan status 2>/dev/null || true
ip -4 addr show br-lan
ip route get 8.8.8.8 2>/dev/null || true
```

## Wi-Fi

```sh
uci show wireless
wifi status 2>/dev/null || true
ubus call network.wireless status 2>/dev/null || true
logread | grep -Ei 'hostapd|wpa|wifi|wireless' | tail -80
```

## DHCP / DNS

```sh
uci show dhcp
cat /tmp/dhcp.leases 2>/dev/null || cat /var/dhcp.leases 2>/dev/null || true
logread -e dnsmasq | tail -80
```

## Firewall

```sh
uci show firewall
fw4 print 2>/dev/null | sed -n '1,120p' || iptables -L -n -v
logread | grep -Ei 'firewall|nft|iptables' | tail -80
```

## Services and logs

```sh
service list 2>/dev/null || ls /etc/init.d
/etc/init.d/<service> status
logread | tail -120
```

## UCI safe change pattern

```sh
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p /tmp/hermes-backup-$TS
cp -a /etc/config /tmp/hermes-backup-$TS/config
uci show <config>
uci set <config>.<section>.<option>=<value>
uci changes <config>
uci commit <config>
/etc/init.d/<service> reload
```

Rollback while current SSH session still works:

```sh
cp -a /tmp/hermes-backup-$TS/config/* /etc/config/
/etc/init.d/<service> reload
```

## Packages

```sh
df -h /overlay /tmp
opkg update
opkg info <package>
opkg install <package>
opkg list-installed | grep '^<package> '
opkg remove <package>
```

Avoid blanket `opkg upgrade`; if a package upgrade is necessary, inspect overlay free space and upgrade only named packages.

## LuCI / uHTTPd / rpcd

```sh
/etc/init.d/uhttpd status 2>/dev/null || true
/etc/init.d/rpcd status 2>/dev/null || true
uci show uhttpd 2>/dev/null | sed -n '1,120p'
netstat -lntp 2>/dev/null | grep -E ':(80|443)\b' || ss -lntp 2>/dev/null | grep -E ':(80|443)\b'
logread | grep -Ei 'uhttpd|rpcd|luci|ssl|certificate' | tail -100
df -h /overlay /tmp
```

Restart only after reporting impact:

```sh
/etc/init.d/rpcd restart
/etc/init.d/uhttpd restart
```

## Dropbear SSH key auth

```sh
uci show dropbear 2>/dev/null || true
/etc/init.d/dropbear status 2>/dev/null || true
logread | grep -i dropbear | tail -100
ls -ld /etc /etc/dropbear
ls -l /etc/dropbear/authorized_keys 2>/dev/null || true
sed -n '1,20p' /etc/dropbear/authorized_keys 2>/dev/null
```

Do not restart Dropbear unless password fallback or another management route is confirmed.

## Network-change rollback guard

For risky network/firewall changes, keep the current SSH session open and schedule an automatic rollback before applying:

```sh
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p /tmp/hermes-backup-$TS && cp -a /etc/config /tmp/hermes-backup-$TS/config
(sleep 90; cp -a /tmp/hermes-backup-$TS/config/* /etc/config/; /etc/init.d/network reload; /etc/init.d/firewall reload) >/tmp/hermes-rollback-$TS.log 2>&1 & echo $! >/tmp/hermes-rollback-$TS.pid
# apply intended change, verify connectivity, then cancel rollback:
kill $(cat /tmp/hermes-rollback-$TS.pid)
```

## Firmware/sysupgrade — high risk

Only after explicit authorization:

```sh
cat /etc/openwrt_release
cat /etc/board.json
sysupgrade -T /tmp/firmware.img
sha256sum /tmp/firmware.img
sysupgrade -v /tmp/firmware.img       # keep settings
# or sysupgrade -n /tmp/firmware.img  # reset settings; destructive
```
