# Cross-skill: OpenWrt/iStoreOS router layer ↔ Surge ↔ UniFi

Use this reference when a home-network symptom spans more than one layer.

## Layer ownership

- `unifi-ops` — physical Wi-Fi/switch layer: AP/switch/Controller, SSID/VAP, signal, channel/DFS, PoE, LLDP, switch ports, client-to-AP association.
- `openwrt-router` — router service layer: OpenWrt/iStoreOS gateway, WAN/LAN, DHCP leases, DNSMasq, NAT/firewall, default route, LuCI/uHTTPd/rpcd, Dropbear SSH, UCI/opkg.
- `surge-gateway` — proxy policy layer: Surge mode, policy groups, nodes, rules, request logs, Surge DNS/cache, target-domain proxy diagnostics.

## Decision shortcuts

- Cannot see/connect to Wi-Fi, poor signal, AP offline, SSID missing → `unifi-ops`.
- Connected to Wi-Fi but no IP, wrong gateway, DNSMasq/DHCP broken, NAT/firewall/port-forward issue, LuCI/opkg problem → `openwrt-router`.
- Has IP/gateway but one app/domain/proxy route is slow/broken, fake-IP/cache/policy/node issue → `surge-gateway`.

## Device offline sequence

1. `unifi-ops`: confirm physical association and AP health.
2. `openwrt-router`: confirm DHCP lease, default gateway, DNSMasq, route, NAT/firewall.
3. `surge-gateway`: confirm request log, matched rule, policy group, node/TLS path.

## Safety boundary

Do not restart OpenWrt network/firewall/dropbear while diagnosing a Surge or UniFi symptom unless router-layer evidence justifies it and the user explicitly authorizes the disruptive action.
