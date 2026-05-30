---
name: surge-gateway
description: >-
  Control and troubleshoot the user's household Surge for Mac gateway via surge-cli.
  Use when the user asks about Surge, proxy mode/group/selection, network routing,
  DNS/cache, node latency, recent requests, household device identification, waking
  or SSH-ing into LAN Macs, or split-routing config. Do NOT use for general networking
  questions unrelated to Surge.
version: 2.0.0
---

# Surge Gateway

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse | Why it's wrong |
|--------|---------------|
| "I know how surge-cli works, I don't need the skill" | This Surge is the family gateway. Generic CLI knowledge misses household context: device inventory, safety posture, impact radius. |
| "The command looks safe, I'll just run it" | A `stop` or `reload` during active traffic disrupts everyone. Every command has a safety classification — check it first. |
| "I'll test all the nodes to find the fastest" | `test-all-policies` floods the network. Use targeted `test-policy` or `test-group`. |
| "The inventory is stale, I'll skip refreshing it" | Stale IPs/MACs lead to wrong device targeting (wrong Mac for WoL, wrong DHCP lease). Refresh when it matters. |

## 🔀 Decision Tree

```
Network/routing/proxy/DNS/device task?
├── YES → This skill
│   ├── Read-only diagnostic? → Use safe commands freely
│   ├── Mutation (set/reload/switch/flush)? → Explain impact, confirm, then act
│   ├── Device identification? → Refresh inventory → triangulate (ARP+DHCP+Surge requests)
│   ├── Wake/SSH to LAN Mac? → references/lan-access.md
│   ├── Split routing for similar domains? → references/split-routing.md
│   └── "Which command to X?" → references/cli-cheatsheet.md
└── NO → General networking? → Don't load
```

## Context

The user's **Surge for Mac is the household network gateway**. Actions may affect the whole family's internet access — treat it as a high-impact control plane.

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
```

The binary is bundled inside Surge.app and not necessarily on `PATH`. Always call by absolute path.

## Safety Posture

### Read-only — OK to run

`environment`, `dump policy/request/active/dns/event/rule/summary`, `test-network`, `test-policy`, `test-group`, `external-resource list`

### Mutation — explain impact first

`flush dns`, `reload`, `switch-profile`, `set`, `kill`, `external-resource update`, `test-all-policies`, `add/del/flush-temp-rule`

### Dangerous — avoid unless explicitly requested

`stop` — shuts down the household gateway. `update-profile` — edits live profile.

## Core Workflows

### 0. Refresh device inventory

When using Surge CLI for household network tasks, refresh the inventory unless it's a narrow urgent request where extra reads distract:

```bash
"$SURGE_CLI" dump request --raw > /tmp/surge_requests_latest.json
arp -a > /tmp/arp_a.txt
```

Merge into `~/.hermes/notes/household-network-device-inventory.md`. Don't notify the user just because inventory was refreshed — mention only when relevant.

### 1. "What mode / node is X using?"

1. `environment` → inspect `ProxyMode`, `AllProxyModePolicyNameKey`, `ProxyGroupSelection`
2. If a domain/app is mentioned, `dump request` for recent matching requests → report the matched rule/policy

### 2. "Network is slow / family internet is weird"

1. `test-network` for baseline latency
2. `dump active` for active connections
3. `dump event` for Surge errors
4. Only flush DNS/reload after identifying a likely reason

### 3. "Which node should I use?"

1. `dump policy` to identify candidate policy names/groups
2. Use targeted `test-policy` or `test-group` — NOT `test-all-policies`
3. Summarize latency; don't change policy unless asked

### 4. "A site/app is broken"

1. Ask user to reproduce, or use `watch request` briefly to capture
2. `dump request` → find domain, rule, and policy
3. `dump dns` if DNS issue suspected
4. `flush dns` is lower risk than `reload` or profile switching

### 5. Detailed workflows → see references

- **Split routing**: `references/split-routing.md`
- **Wake/SSH to LAN Mac**: `references/lan-access.md`
- **Device identification**: `references/device-inventory-triangulation.md`
- **Full command catalog**: `references/cli-cheatsheet.md`

### 6. UDP / video call / real-time traffic issues

When a device behind the Surge gateway has stuttering video calls, game lag, or VoIP dropouts:

1. **Check the UDP fallback setting** in the active profile:
   ```bash
   grep 'udp-policy-not-supported-behaviour' ~/Library/Application\ Support/Surge/Profiles/mine.conf
   ```
   - `reject` → UDP packets silently dropped when proxy doesn't support UDP. This is the **default in many Surge configs** and is a common root cause.
   - `direct` → falls back to direct connection. **Recommended for household gateways.**

2. **If `reject`, change to `direct`:**
   ```bash
   sed -i '' 's/udp-policy-not-supported-behaviour = reject/udp-policy-not-supported-behaviour = direct/' ~/Library/Application\ Support/Surge/Profiles/mine.conf
   "$SURGE_CLI" reload
   ```

3. **Verify the target IP's routing:**
   - If the destination IP matches `GEOIP,CN` → routes to `🎯 全球直连` (DIRECT), UDP is unaffected by the `reject` setting
   - If the destination is foreign → may hit a proxy policy, and UDP gets rejected if node doesn't support it

4. **Check Surge events log** for UDP-related errors:
   ```bash
   "$SURGE_CLI" dump event | python3 -c "import json,sys; [print(e['content']) for e in json.load(sys.stdin)['events'] if 'udp' in str(e).lower() or 'UDP' in str(e).lower()]"
   ```

5. **If UDP rejection is confirmed but not the root cause**, the issue is likely server-side throttling (WeChat, TikTok, etc. rate-limit UDP uploads).

**Key insight:** Even if the current target routes to DIRECT, keep `direct` as the fallback — any future rule change that routes a UDP service through a proxy would silently break with `reject`.

## References

| File | When to read |
|------|-------------|
| `references/cli-cheatsheet.md` | Need to find the right command or understand output |
| `references/device-inventory-triangulation.md` | Identifying household devices by IP/MAC/traffic |
| `references/lan-access.md` | Waking or SSH-ing into a household Mac |
| `references/split-routing.md` | Configuring different routes for similar domains |

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I check safety classification before running any command?
- [ ] Did I use read-only commands first before any mutation?
- [ ] Did I explain impact before `set`/`reload`/`switch-profile`?
- [ ] Did I refresh device inventory when relevant to the task?
- [ ] Did I use targeted `test-policy`/`test-group` instead of `test-all-policies`?

---

## 🔄 Deployment & Sync

**Local:** `~/.hermes/skills/devops/surge-gateway/`
**GitHub:** `jz-skills/hermes-3S6M-profiles/gongbu/surge-gateway/`
**Sync:** `deploy/sync-all.sh` (forward) + `deploy/sync-back.sh` (reverse)

**Profiles consuming this skill:**
- `default` (小黄) — primary household assistant
- `regent` (监国太子) — governance overlay
- `gongbu` (工部) — infrastructure & devops owner
