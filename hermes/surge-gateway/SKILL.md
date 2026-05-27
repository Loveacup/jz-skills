---
name: surge-gateway
description: "Use when controlling or troubleshooting the household Surge for Mac gateway via surge-cli and HTTP/API concepts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
---

# Surge Gateway

Use this skill when the user asks about Surge, home gateway/network routing, proxy policy groups, DNS/cache issues, node latency, recent requests, or family device traffic controlled by Surge.

## Context

The user's **Surge for Mac is the household network gateway**. Actions may affect the whole family's internet access. Treat it as a high-impact network control plane.

Local CLI path:

```bash
/Applications/Surge.app/Contents/Applications/surge-cli
```

The binary is not necessarily on `PATH`; call it by absolute path or set a shell variable:

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" environment
```
## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just run reload — it's fast and safe" | reload affects the whole household's internet. Always explain impact first, especially for family-shared gateways |
| "The device inventory looks fine, no need to refresh" | Inventory can be stale (wrong IP, mislabeled MacBook). If user corrects a device, immediately re-probe with corrected target |
| "I'll skip the backup — this is a minor profile edit" | Surge config edits without backup are irreversible. Always make a timestamped backup before editing |
| "I'll just test-all-policies, it's the fastest way to check" | test-all-policies triggers latency checks on every node, disrupting active connections. Use targeted test-policy when possible |


## Safety posture

### Safe/read-only commands — OK to run when useful

```bash
"$SURGE_CLI" environment
"$SURGE_CLI" dump policy
"$SURGE_CLI" dump request
"$SURGE_CLI" dump active
"$SURGE_CLI" dump dns
"$SURGE_CLI" dump event
"$SURGE_CLI" dump rule
"$SURGE_CLI" test-network
```

### Higher-impact commands — be cautious

These can affect household connectivity or routing. Prefer explaining intended impact first and only run when the user's request clearly calls for it.

```bash
"$SURGE_CLI" flush dns
"$SURGE_CLI" reload
"$SURGE_CLI" switch-profile <profile-name>
"$SURGE_CLI" set <key-path> <value>
"$SURGE_CLI" test-policy <policy-name>
"$SURGE_CLI" test-all-policies
"$SURGE_CLI" test-group <group-name>
"$SURGE_CLI" kill <connection-id>
"$SURGE_CLI" external-resource update <key|all>
```

### Dangerous commands — avoid unless explicitly requested

```bash
"$SURGE_CLI" stop
```

`stop` may interrupt the family's internet access.

## Common workflows

### 0. Keep household device inventory fresh

User preference: whenever a task uses Surge CLI for household network/device inspection, refresh the device inventory too, unless the task is an urgent narrow one where extra reads would distract.

Read-only refresh sources:

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" dump request --raw > /tmp/surge_requests_latest.json
arp -a > /tmp/arp_a.txt
```

Then update `~/.hermes/notes/household-network-device-inventory.md` by merging Surge recent/active requests, Surge DHCP leases, ARP, and MAC OUI/vendor hints. Do not notify the user solely because the inventory was refreshed; mention it only when relevant to the answer.

### 1. “What mode / what node is X using?”

1. Run `environment`.
2. Inspect `ProxyMode`, `AllProxyModePolicyNameKey`, and `ProxyGroupSelection`.
3. If a domain/app is mentioned, use `dump request` to find recent matching requests and report the matched rule/policy if present.

### 2. “Network is slow / family internet is weird”

1. Run `test-network` for baseline DNS/network latency.
2. Run `dump active` to inspect active connections.
3. Run `dump event` for recent Surge errors.
4. Only flush DNS/reload after identifying a likely reason.

### 3. “Which node should I use?”

1. Run `dump policy` to identify candidate policy names/groups.
2. Use targeted `test-policy` or `test-group` rather than `test-all-policies` when possible.
3. Summarize latency and recommend a low-impact switch; avoid changing the policy unless asked.

### 4. “A site/app is broken”

1. Ask the user to reproduce, or use `watch request` briefly if actively debugging.
2. Use `dump request` to find the domain and policy/rule.
3. Check `dump dns` if it looks like a DNS issue.
4. If DNS cache appears stale, `flush dns` is usually lower risk than `reload` or profile switching.

### 4.5 “Split routing for two similar domains”

When the user wants closely related domains routed differently (for example `.com` via a proxy but `.com.cn` direct), avoid broad `DOMAIN-KEYWORD` rules because they will catch both. Use specific `DOMAIN-SUFFIX` rules ordered before any broader match, then validate with the effective rules and a fresh request.

Read/diagnose:

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" dump rule | grep -i -E 'domain1|domain2'
"$SURGE_CLI" dump profile original > /tmp/surge_profile_original.conf
"$SURGE_CLI" dump profile effective > /tmp/surge_profile_effective.conf
grep -n -i 'domain-keyword-or-suffix' /tmp/surge_profile_original.conf
```

Edit the actual profile file, not just `/tmp/surge_profile_original.conf`; if needed, find it by searching for a nearby unique rule string. Make a timestamped backup before editing. Replace broad keyword rules with explicit suffix rules, e.g.:

```conf
# Example: international site via selected proxy, China site direct
DOMAIN-SUFFIX,example.com.cn,DIRECT
DOMAIN-SUFFIX,assets.example.com.cn,DIRECT
DOMAIN-SUFFIX,example.com,"🇯🇵 自定义日本"
DOMAIN-SUFFIX,assets.example.com,"🇯🇵 自定义日本"
```

Verify and apply:

```bash
"$SURGE_CLI" --check "/path/to/profile.conf"
"$SURGE_CLI" reload
"$SURGE_CLI" dump rule | grep -i -E 'example|assets\.example'
```

Finally generate a fresh request with `curl -I -L --max-time 15 https://...` or have the user reload the page, then inspect `dump request --raw` for `policyName` and `rule`. Report the final matched rule and policy, not just the intended config.

### 4.6 “Can you wake a sleeping Mac / SSH into a LAN Mac?”

When the user asks whether a MacBook/Mac on the household LAN can be woken or reached over SSH, treat this as a network-device task and use read-only discovery first.

1. Identify the candidate device from `~/.hermes/notes/household-network-device-inventory.md`, ARP, DHCP leases, and mDNS names. Record IP, hostname, and MAC. Apple private Wi-Fi addresses may make identity fuzzy. **Pitfall**: the inventory can be stale or mislabel MacBooks; if the user corrects the IP/hostname, immediately pivot to the corrected target and re-run probes rather than defending the old inventory.
2. Check reachability before waking:
   ```bash
   ping -c 1 -W 1000 <ip> || true
   nc -vz -G 2 <ip> 22 || true
   arp -a | grep -i '<ip>\|<mac>' || true
   ```
3. If SSH is open, test non-interactive login without prompting for a password:
   ```bash
   ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new <user>@<ip> 'echo SSH_OK; hostname; whoami'
   ```
   `Permission denied` means SSH is reachable but key/user auth is not configured; `Operation timed out` / `Host is down` means the host or port is not reachable. If the inventory IP is stale or the user corrects it, immediately probe the corrected IP; a quick subnet TCP/22 scan can also reveal candidate Macs when DHCP names are stale.

   When auth fails but port 22 is reachable, provide the local public key to add on the remote Mac:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
   Then ask the user to add it to the remote user's `~/.ssh/authorized_keys` and retry `ssh -o BatchMode=yes ... 'echo SSH_OK; hostname; whoami; sw_vers -productVersion'`.
4. For Wake-on-LAN, send magic packets to both subnet broadcast and the last-known IP using the last-known MAC:
   ```bash
   python3 - <<'PY'
   import socket, binascii, time
   mac='<mac-address>'.replace(':','').replace('-','')
   packet=b'\xff'*6 + binascii.unhexlify(mac)*16
   targets=[('<subnet-broadcast>',9),('<subnet-broadcast>',7),('<last-known-ip>',9),('<last-known-ip>',7)]
   for _ in range(3):
       for target in targets:
           s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
           s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
           try:
               s.sendto(packet,target)
               print('sent', target)
           except Exception as e:
               print('failed', target, e)
           finally:
               s.close()
       time.sleep(1)
   PY
   ```
5. Poll for 30–90 seconds with `nc -vz -G 2 <ip> 22`, `ping`, and ARP. If it still fails, explain likely macOS causes: Wi‑Fi sleep/deep sleep, not plugged in, “Wake for network access” off, AP/router not forwarding WoL, or Bonjour Sleep Proxy unavailable.
6. Setup advice for reliable future access: enable **Remote Login**, add the agent host's SSH public key to `~/.ssh/authorized_keys`, enable `sudo pmset -a womp 1`, keep the Mac plugged in for wake reliability, and reserve/fix the DHCP address.

### 5. “What devices are online / what is this iPad?”

Use read-only sources and triangulate; Surge request logs alone often lack device names.

1. Capture recent/active requests: `"$SURGE_CLI" dump request --raw > /tmp/surge_requests.json`.
2. Capture local neighbor table: `arp -a`.
3. Parse Surge's DHCP lease file if present: `~/Library/Application Support/com.nssurge.surge-mac/dhcpd/lease`.
4. Merge by IP/MAC and report confidence levels:
   - DHCP `client-hostname` and ARP name are strong identity hints.
   - MAC OUI/vendor helps classify Apple, UniFi/Ubiquiti, Aqara/Lumi, Xiaomi, Terncy, etc.
   - Apple private/random MAC devices may show only generic names like `iPhone`, `Watch`, or no name; identify them as candidates, not certainties.
   - Recent request domains help distinguish active Apple system traffic (`time.apple.com`, `courier.push.apple.com`, `gateway.icloud.com.cn`, `itunes.apple.com`) from user app/web activity.
5. For an exact iPad match, ask the user to unlock the iPad and open a webpage/app, then re-run the request capture and match the new source IP.

- See `references/device-inventory-triangulation.md` for a compact parser pattern and reporting notes.

### 6. “Can you wake / SSH into the MacBook?”

When a household Mac is asleep or SSH is timing out:

1. Use the device inventory to identify likely IP/MAC.
2. Probe `ping`, `nc -vz <ip> 22`, and `arp -a` to distinguish asleep/offline from SSH-auth failure.
3. Send Wake-on-LAN magic packets to the LAN broadcast and target IP.
4. Poll SSH for ~60 seconds.
5. If wake fails, report likely MacBook sleep/Wi-Fi limitations and suggest `pmset womp 1`, Wake for network access, power/Power Nap, Remote Login, and SSH key setup.

See `references/wake-on-lan-macbook.md` for exact commands and interpretation.

## References

- See `references/cli-cheatsheet.md` for command details and output interpretation notes.
- See `references/device-inventory-triangulation.md` for identifying household devices by merging Surge requests, DHCP leases, ARP, and MAC vendors.
- See `references/wake-on-lan-macbook.md` for waking household Macs/MacBooks and verifying SSH reachability.
- See `references/macbook-ssh-auth-triage.md` for the case where the user corrects a stale IP and TCP/22 is reachable but SSH auth fails.
## ✅ Verification Checklist (RUN AFTER SURGE CHANGES)

- [ ] Did I make a timestamped backup before editing the profile?
- [ ] Did I validate the config with `--check` before reload?
- [ ] Did I verify the change took effect (`dump rule` or `dump policy`)?
- [ ] Did I test the specific use case (curl / user reload page) and report the actual matched rule?
- [ ] Did I refresh the device inventory if this was a network/device task?

**If any box is unchecked, go back.**
