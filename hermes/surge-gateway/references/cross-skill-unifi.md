# Cross-skill: Surge proxy layer ↔ UniFi physical layer

Use this reference when a symptom could be caused by either Wi-Fi/physical infrastructure or Surge routing/proxy behavior.

## Routing table

- Wi-Fi association, AP satisfaction, channel/DFS, VAP/SSID, PoE, switch port, LLDP → `unifi-ops`
- Proxy mode, policy group, node latency, Surge DNS/cache, request logs, domain/app routing → `surge-gateway`
- Default gateway, DHCP/NAT/firewall/DNSMasq, OpenWrt/iStoreOS LuCI/opkg → `openwrt-router`

## Escalation examples

- Surge shows no request from the device → check `unifi-ops` association and `openwrt-router` DHCP first.
- Device has strong Wi-Fi and valid DHCP, but one app/domain is slow or blocked → stay in `surge-gateway`.
- Many clients on one AP are slow regardless of domain → `unifi-ops` first.
