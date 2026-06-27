# OpenWrt Router Skill — Source Research

## Local-first checks

- Supermemory: attempted twice for `OpenWrt router operations UCI opkg LuCI SSH skill source`; both attempts timed out. No usable memory hit.
- Session search: no prior OpenWrt skill/router sessions found.
- qmd/Obsidian: `qmd search "OpenWrt UCI opkg LuCI router skill"` returned no results.
- Local skills: no existing OpenWrt skill; only UniFi skill mentions that LuCI means OpenWrt, not UniFi.

## External prior art

### jsebgiraldo/openwrt_ssh_mcp

- URL: https://github.com/jsebgiraldo/openwrt_ssh_mcp
- README describes a containerized MCP server for managing OpenWrt routers via SSH.
- Useful patterns adopted:
  - Keep SSH as the control plane.
  - Prefer key auth; password auth only when supplied at runtime.
  - Use command validation/allowlists.
  - Provide auditability and read-only probes.
  - Expose tools around system info, network interface restart, Wi-Fi status, DHCP leases, firewall rules, UCI config reads, opkg package management, firmware version/verification/flash.
- Security allowlist/blocked-pattern insights from `openwrt_ssh_mcp/security.py`:
  - Safe read-only examples: `ubus call system board`, `uci show network`, `cat /etc/openwrt_release`, `ip addr show`, `df -h`, `uptime`, `cat /tmp/dhcp.leases`.
  - Dangerous patterns explicitly blocked: `rm -rf`, `dd if=`, `mkfs`, `shutdown`, `reboot`, `halt`, `poweroff`, direct disk writes, `chmod 777`, `passwd`, stopping/killing dropbear, `wget|sh`, `curl|sh`, netcat piping, telnet.

## Web findings used as guardrails

- OpenWrt package docs/search snippets: OpenWrt 24.10 and older uses `opkg`; package install pattern is `opkg update && opkg install packagename`.
- OpenWrt/sysupgrade search snippets: sysupgrade requires verifying firmware checksum and enough free RAM; firmware flashing is disruptive and must be explicitly authorized.
- OpenWrt/dropbear search snippets: Dropbear config is handled via UCI and `/etc/config/dropbear`; public key locations may differ by version (`/etc/dropbear/authorized_keys` vs other legacy paths). Always inspect the target before changing SSH auth.
- UCI search snippets: `uci commit <config>` writes pending changes to config files; applying runtime effects often requires relevant service reload/restart, not just commit.
- Package-upgrade warnings from Unix/Linux/OpenWrt community results: `opkg upgrade` is not equivalent to full firmware upgrade and may consume overlay space; use targeted installs/upgrades and prefer sysupgrade for firmware.

## Retrieval caveats

- Exa/Brave/Tavily MCP calls failed with `ClosedResourceError` in this session.
- `web_extract` and direct curl to `openwrt.org/docs/*` encountered OpenWrt's Anubis anti-bot/challenge page, so final skill relies on search snippets plus GitHub raw source extraction and local router verification.
