# Cross-skill: UniFi physical layer ↔ OpenWrt/iStoreOS router layer

Use this reference when a network issue may sit between physical Wi-Fi/switching and router services.

## Owns what

- `unifi-ops`: AP/switch/Controller, SSID/VAP, Wi-Fi signal/channel/DFS, PoE, LLDP, switch ports, client-to-AP association.
- `openwrt-router`: OpenWrt/iStoreOS gateway, WAN/LAN, DHCP leases, DNSMasq, NAT/firewall, LuCI/uHTTPd/rpcd, Dropbear SSH, opkg/UCI.
- `surge-gateway`: proxy/routing policy above the router layer.

## Common split

- Client cannot see SSID / poor signal / connected to wrong AP → `unifi-ops`.
- Client connects to Wi-Fi but gets no IP / wrong gateway / cannot reach LAN gateway → `openwrt-router`.
- Client reaches gateway but a domain/app routes incorrectly or proxy TLS fails → `surge-gateway`.

## Safety

Do not use UniFi tools to modify OpenWrt config. Do not restart OpenWrt network/firewall/dropbear from a UniFi investigation unless the user explicitly authorizes router-layer action.
