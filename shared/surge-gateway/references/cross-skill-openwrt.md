# Cross-skill: Surge proxy layer ↔ OpenWrt/iStoreOS router layer

Use this reference when symptoms may sit below Surge, at the router/gateway service layer.

## Owns what

- `surge-gateway`: Surge proxy mode, policy groups, nodes, rules, request logs, Surge DNS/cache, target-domain proxy diagnostics.
- `openwrt-router`: WAN/LAN, DHCP leases, DNSMasq, NAT/firewall, default gateway, LuCI/uHTTPd/rpcd, Dropbear SSH, opkg/UCI.
- `unifi-ops`: AP/switch/Controller and physical Wi-Fi.

## Decision shortcuts

- Domain/app routes wrong, ChatGPT/Codex TLS through proxy, node latency, fake-IP cache → `surge-gateway`.
- Client has no IP, wrong gateway, DNSMasq/DHCP broken, NAT/firewall/port-forward problem, LuCI/opkg issue → `openwrt-router`.
- Client not associated to AP or poor signal/channel/PoE issue → `unifi-ops`.

## Full offline sequence

1. `unifi-ops`: physical association and AP health.
2. `openwrt-router`: DHCP/default route/DNSMasq/NAT/firewall.
3. `surge-gateway`: policy/rule/node/request path.
