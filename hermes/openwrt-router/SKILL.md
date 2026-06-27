---
name: openwrt-router
description: "Operate OpenWrt/iStoreOS routers over SSH/LuCI: connect, diagnose network/system state, read UCI config, manage opkg packages cautiously, back up before changes, and avoid lockout. Use when the user asks to connect to, inspect, configure, troubleshoot, or package-manage an OpenWrt/iStoreOS router. Do NOT use for UniFi-only controllers/devices unless the router is explicitly OpenWrt/iStoreOS."
type: routine
version: 1.1.0
tags: [openwrt, istoreos, router, ssh, luci, uci, opkg, dropbear, network]
related_skills: [ssh-setup, web-research-router, surge-gateway, unifi-ops]
metadata:
  hermes:
    tags: [openwrt, istoreos, router, ssh, luci, uci, opkg, dropbear, network]
    related_skills: [ssh-setup, web-research-router, surge-gateway, unifi-ops]
---

# OpenWrt Router Operations

## 🚨 Red Flags: DO NOT SKIP SAFETY

| Excuse your brain will make | Why it's wrong |
|---|---|
| "It's just one router command" | Router mistakes can cut off the user's network and your SSH session. Probe/read first. |
| "I'll run `opkg upgrade` like apt" | OpenWrt package upgrades are not a full firmware upgrade path and can consume overlay space; prefer targeted installs/removes only. |
| "I'll edit `/etc/config/*` directly" | Use UCI for config where possible; commit/apply deliberately and back up first. |
| "Reboot/restart is fine" | Restarting network/firewall/dropbear can lock you out. Ask unless the user explicitly requested it or you have a rollback path. |
| "The password can go in the skill" | Never store router passwords/API secrets in SKILL.md, references, scripts, or memory. Use env vars or prompt-time credentials only. |

## Decision Tree

1. **Identify target**
   - Default local gateway candidate: `route -n get default`, `netstat -rn -f inet`, or user-provided IP.
   - Verify OpenWrt/iStoreOS: HTTP LuCI redirect/title, SSH banner `dropbear`, or `/etc/openwrt_release`.
2. **Connect safely**
   - Load `ssh-setup` for SSH auth/host-key issues.
   - Prefer key auth. If password is supplied, use `sshpass -p "$OPENWRT_PASSWORD"` with the password in an environment variable, not shell history text.
3. **Classify operation**
   - **Read-only diagnostics**: safe to run after connection.
   - **Config/package changes**: create backup first; show diff/changed values; verify after apply.
   - **Disruptive actions**: network restart, firewall restart, dropbear restart, reboot, sysupgrade → ask for explicit confirmation unless already ordered.
4. **Verify and report**
   - Every success claim needs command output: `SSH_OK`, version, UCI value, service status, package state, or backup path.

## 🔗 Cross-Skill Routing: OpenWrt vs Surge vs UniFi

This skill owns the **OpenWrt/iStoreOS router layer**: WAN/LAN, DHCP, DNSMasq, NAT/firewall, UCI, opkg, LuCI, and Dropbear SSH. Route other layers explicitly:

- **Surge/proxy layer** → load `surge-gateway`: proxy mode, policy groups, nodes, Surge DNS/cache, request logs, cross-border app/site routing.
- **UniFi physical layer** → load `unifi-ops`: AP/switch/Controller, SSID/VAP, Wi-Fi signal/channel/DFS, PoE, switch ports, physical device location.
- **OpenWrt router layer** → stay here: default gateway, DHCP leases, NAT/firewall, WAN/PPPoE, LAN bridge, DNSMasq, LuCI/uHTTPd/rpcd, opkg packages.

If a device is offline: check UniFi association first → OpenWrt DHCP/default gateway second → Surge rule/proxy path third.

## Capability Boundaries

- `opkg install/remove <named-package>`: allowed after `opkg update`, `opkg info`, and overlay-space check.
- Blanket `opkg upgrade`: do **not** run as an apt-style system upgrade. Convert to named-package review or recommend firmware/sysupgrade planning.
- `sysupgrade`, reboot, network/firewall/dropbear restart: high-risk. Require explicit authorization, backup, firmware/board/checksum validation, and rollback/console plan.
- Unknown router vendor: only run non-invasive identification (HTTP title/banner, SSH banner). Do not apply OpenWrt commands until `/etc/openwrt_release`, LuCI, or dropbear/OpenWrt identity is verified.

## LuCI / uHTTPd / rpcd Down Triage

Read-only checks before any restart:

```sh
/etc/init.d/uhttpd status 2>/dev/null || true
/etc/init.d/rpcd status 2>/dev/null || true
uci show uhttpd 2>/dev/null | sed -n '1,80p'
netstat -lntp 2>/dev/null | grep -E ':(80|443)\b' || ss -lntp 2>/dev/null | grep -E ':(80|443)\b'
logread | grep -Ei 'uhttpd|rpcd|luci|ssl|certificate' | tail -80
df -h /overlay /tmp 2>/dev/null
```

Only restart `uhttpd`/`rpcd` after reporting impact; these are lower risk than network/firewall/dropbear but still affect management access.

## Dropbear Key Auth Troubleshooting

Load `ssh-setup`, then inspect the OpenWrt side:

```sh
uci show dropbear 2>/dev/null || true
/etc/init.d/dropbear status 2>/dev/null || true
logread | grep -i dropbear | tail -80
ls -l /etc/dropbear /etc/dropbear/authorized_keys 2>/dev/null || true
grep -n 'ssh-' /etc/dropbear/authorized_keys 2>/dev/null | sed -n '1,20p'
```

Do not stop/restart Dropbear until password fallback or another management path is confirmed.

## Safe Read-Only Probe

```bash
HOST=${OPENWRT_HOST:-<internal IP redacted>}
USER=${OPENWRT_USER:-root}
ssh -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "$USER@$HOST" '
  echo SSH_OK
  cat /etc/openwrt_release 2>/dev/null || true
  ubus call system board 2>/dev/null || true
  uptime
  df -h
  ip -4 addr show br-lan 2>/dev/null | sed -n "1,6p"
  ip route show
'
```

If password auth is required, inject it without writing the secret into the command text/history:

```bash
read -rs OPENWRT_PASSWORD
export OPENWRT_PASSWORD
sshpass -p "$OPENWRT_PASSWORD" ssh \
  -o PreferredAuthentications=password -o PubkeyAuthentication=no \
  -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new \
  root@<internal IP redacted> 'echo SSH_OK; cat /etc/openwrt_release; uptime'
unset OPENWRT_PASSWORD
```

## Read-Only Diagnostics Menu

- System: `ubus call system board`, `ubus call system info`, `cat /etc/openwrt_release`, `uptime`, `df -h`, `free`
- Network: `ip addr show`, `ip route show`, `uci show network`, `ubus call network.interface.wan status`
- Wi-Fi: `wifi status`, `ubus call network.wireless status`, `uci show wireless`
- DHCP/DNS: `cat /tmp/dhcp.leases`, `uci show dhcp`, `logread -e dnsmasq`
- Firewall: `uci show firewall`, `fw4 print 2>/dev/null || iptables -L -n -v`
- Logs/services: `logread | tail -80`, `/etc/init.d/<service> status`, `service list 2>/dev/null`
- Packages: `opkg list-installed`, `opkg info <pkg>`, `opkg list-upgradable`

## Change Protocol

Before changing UCI, packages, firewall, wireless, network, or SSH:

```bash
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p /tmp/hermes-backup-$TS
cp -a /etc/config /tmp/hermes-backup-$TS/config
uci changes || true
```

UCI pattern:

```bash
uci show <config>                 # inspect
uci set <config>.<section>.<opt>=<value>
uci changes <config>              # review pending diff
uci commit <config>               # persist
/etc/init.d/<service> reload      # or restart only when safe/approved
```

Package pattern:

```bash
opkg update
opkg info <package>
opkg install <package>            # targeted install only
opkg list-installed | grep '^<package> '
```

## Local Known Router Snapshot

- LAN gateway observed in this profile: `<internal IP redacted>`
- Device verified by SSH: `iStoreOS 24.10.2 2025071110`, Linux `6.6.93`, `aarch64`, LAN `br-lan <internal IP redacted>/24`
- Credential policy: do **not** store the password in this skill; use prompt-time credential or env variable.

## References

- `references/source-research.md` — external prior art and official-doc findings used to design this skill.
- `references/command-cookbook.md` — expanded diagnostics/change commands.
- `references/trigger-tests.md` — should-trigger and should-not-trigger examples.
- `references/cross-skill-network-stack.md` — routing among `openwrt-router`, `surge-gateway`, and `unifi-ops`.
- `scripts/openwrt_probe.sh` — reusable read-only SSH probe using env vars.

## ✅ Verification Checklist

- [ ] Did I verify the target is OpenWrt/iStoreOS before using this skill's commands?
- [ ] Did I avoid storing or echoing credentials in files/memory?
- [ ] Did I run read-only diagnostics before any change?
- [ ] For changes, did I create a backup and inspect `uci changes` or package state?
- [ ] Did I avoid disruptive actions unless explicitly authorized?
- [ ] Did I verify completion with command output before reporting success?
