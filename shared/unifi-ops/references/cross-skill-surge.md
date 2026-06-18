# Cross-skill: UniFi physical layer ↔ Surge proxy layer

Use this reference when a symptom could be caused by either Wi-Fi/physical infrastructure or Surge routing/proxy behavior.

## Routing table

- Wi-Fi association, AP satisfaction, channel/DFS, VAP/SSID, PoE, switch port, LLDP → `unifi-ops`
- Proxy mode, policy group, node latency, Surge DNS/cache, request logs, domain/app routing → `surge-gateway`
- Default gateway, DHCP/NAT/firewall/DNSMasq, OpenWrt/iStoreOS LuCI/opkg → `openwrt-router`

## Device offline sequence

1. `unifi-ops`: is the client associated to an AP? Which AP/channel/signal?
2. `openwrt-router`: did the client receive DHCP and default gateway?
3. `surge-gateway`: is traffic captured/routed by Surge and matching expected policy?
