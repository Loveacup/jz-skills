# Surge Config Audit Checklist

Use when the user asks "review my Surge config" or "is there anything wrong with my config."

## Quick Scan

1. Read `~/Library/Application Support/Surge/Profiles/mine.conf`
2. Check each section below

## [General] Section

| Check | Signal | Severity |
|-------|--------|----------|
| `test-timeout` ≤ 2 | Too aggressive — slow but usable nodes get falsely marked down | 🟡 |
| `proxy-test-url` uses Google (gstatic.com) | Nodes that block Google show as timeout, even if good for other traffic. Replace with `http://cp.cloudflare.com/` | 🟡 |
| `internet-test-url` uses HTTP not HTTPS | Redirects may skew connectivity check | ⚪ |
| `hijack-dns` mismatches `dns-server` | DNS leak when apps hardcode Google DNS | ⚪ |
| `dns-server` includes `8.8.8.8` when `hijack-dns` active | Surge uses 8.8.8.8 as upstream (not hijacked); from China this is slow/polluted. Hijack only affects downstream devices. Keep `114.114.114.114, 223.5.5.5, system` instead. | 🟡 |
| `dns-server` includes `system` | Adds OS-level DNS (often router); generally fine but less predictable | ⚪ |
| `external-controller-access` on `0.0.0.0` | LAN-accessible controller, password-protected but wider attack surface | 🟡 |

## [Proxy Group] Section

| Check | Signal | Severity |
|-------|--------|----------|
| Smart group `update-interval=0` | Nodes drop but group never re-evaluates; stale selection persists | 🟡 |
| Policy group in `environment` but no matching RULE-SET | Traffic not explicitly routed, relies on fallback/GFW list | 🟡 |
| `select` group default is a proxy (not DIRECT) when service works fine directly | Unnecessary proxy overhead for services accessible direct | ⚪ |

## [Rule] Section

| Check | Signal | Severity |
|-------|--------|----------|
| Duplicate RULE-SET (same source, same policy) | Wasted fetch, redundant processing | 🔴 |
| RULE-SET ordering conflicts (e.g., `SteamCN.list` DIRECT should be before `Steam.list` proxy) | Downloads/stores mixed incorrectly | 🔴 |
| Missing `no-resolve` on IP-based rules that don't need DNS | Unnecessary DNS lookups | ⚪ |

## Steam-Specific Pattern

The classic ACL4SSR/blackmatrix7 Steam config creates a split:
- `SteamCN.list` → DIRECT: catches `steamcontent.com`, `steamchina.com` etc. (download CDNs)
- `Steam.list` → `🎮 Steam`: catches `steampowered.com`, `steamcommunity.com` etc. (store/community)

**Check:** `SteamCN.list` appears BEFORE `Steam.list` in rule order. If reversed, downloads go through proxy.

**Known issue:** `SteamCN.list` uses `DOMAIN-SUFFIX,steamcontent.com` which catches ALL CDN nodes (Chinese + foreign). When Steam selects a foreign CDN (e.g., HK), direct cross-border can be throttled.

## Known Issues Found in This User's Config

- Duplicate Disney rule (blackmatrix7 pulled twice with different URL variants)
- `test-timeout = 2` (aggressive)
- `proxy-test-url = Google` (false negatives for Google-blocking nodes)
- Smart groups `update-interval=0` (no auto-refresh)
- No Discord RULE-SET despite having `💬 Discord` policy group
