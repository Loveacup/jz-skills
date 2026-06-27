# Household device inventory triangulation

Use this when the user asks which devices are online or asks to identify an iPad/iPhone/IoT device on the Surge gateway network.

## Data sources

Read-only sources that worked well together:

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" dump request --raw > /tmp/surge_requests.json
arp -a > /tmp/arp_a.txt
LEASE="$HOME/Library/Application Support/com.nssurge.surge-mac/dhcpd/lease"
```

Optional vendor lookup for ambiguous OUIs:

```bash
curl -sS --max-time 4 "https://api.macvendors.com/AA:BB:CC"
```

Avoid invasive scans unless the user explicitly wants deeper discovery; ARP + DHCP + Surge request logs are usually enough for a safe household inventory.

## Interpretation notes

- DHCP `client-hostname` is usually the best label when present.
- ARP hostnames can reveal local names (`iphone`, `nushi-8`, `zhuwo`, etc.) but may be stale or absent.
- Surge `dump request` only covers recent/active requests; absence of traffic does not mean the device is offline.
- Apple devices frequently use private/random MAC addresses. Report `iPad/iPhone candidate` rather than a definitive identification unless the hostname or live request test confirms it.
- Apple background/system domains include:
  - `time.apple.com` — NTP/time sync
  - `*-courier.push.apple.com:5223` — Apple Push Notification service
  - `gateway.icloud.com.cn` — iCloud China gateway
  - `bag.itunes.apple.com`, `itunes.apple.com` — App Store/iTunes metadata
  - `gdmf.apple.com`, `swallow.apple.com`, `ocsp*.apple.com` — updates/config/cert checks
- A device that only hits the above domains may be idle/backgrounding, not actively browsing.

## Minimal Python merge pattern

```python
import re, json, urllib.parse, collections

lease_txt = open(lease_path, errors="ignore").read()
leases = {}
for m in re.finditer(r"lease\s+([0-9.]+)\s*\{(.*?)\n\}", lease_txt, re.S):
    ip, body = m.group(1), m.group(2)
    d = {"ip": ip}
    hm = re.search(r'hardware ethernet\s+([0-9a-f:]+);', body, re.I)
    nm = re.search(r'client-hostname\s+"([^"]+)";', body)
    sm = re.search(r'binding state\s+(\w+);', body)
    if hm: d["mac"] = hm.group(1).lower()
    if nm: d["hostname"] = nm.group(1)
    if sm: d["state"] = sm.group(1)
    leases[ip] = d  # keep latest block per IP

arp = {}
for line in open('/tmp/arp_a.txt', errors='ignore'):
    m = re.search(r'^(.*?)\s*\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-f:]+|\(incomplete\))', line, re.I)
    if m and m.group(3) != '(incomplete)':
        arp[m.group(2)] = {"arp_name": m.group(1).strip('? '), "mac": m.group(3).lower()}

def host(req):
    url = req.get('URL') or ''
    if '://' in url:
        return urllib.parse.urlsplit(url).netloc.split(':')[0]
    return (req.get('remoteHost') or req.get('remoteAddress') or '').split(':')[0]

data = json.load(open('/tmp/surge_requests.json'))
by_ip = collections.defaultdict(list)
for r in data.get('recent-requests', []) + data.get('active-requests', []):
    if r.get('sourceAddress'):
        by_ip[r['sourceAddress']].append(r)

ips = set(arp) | {ip for ip, d in leases.items() if d.get('state') == 'active'} | set(by_ip)
for ip in sorted(ips, key=lambda x: tuple(map(int, x.split('.'))) if x.count('.') == 3 else (999,)):
    row = {"ip": ip, **leases.get(ip, {}), **arp.get(ip, {})}
    top = collections.Counter(host(r) for r in by_ip.get(ip, [])).most_common(5)
    print(ip, row.get('hostname') or row.get('arp_name') or '', row.get('mac') or '', row.get('state') or '', top)
```

## Reporting shape

Group results by confidence/type:

1. Network infrastructure: router/gateway, UniFi CloudKey, switches/APs.
2. Personal devices: Macs, iPhones, iPads, Watch, Apple TV, HomePod.
3. Smart home/IoT: cameras, hubs, speakers, vacuum, appliances.
4. Unknowns: list IP, MAC, vendor, current evidence, and how to confirm.

When the user asks specifically for an iPad, list likely candidates and explain why. The best confirmation method is a live test: ask the user to unlock/open something on the iPad, immediately re-run `dump request --raw`, and match the new source IP and domains.
