# Domain-Based Routing Detection

## Problem

A Surge node with "DIP" or dedicated-IP labeling may use per-domain traffic splitting. Testing against a generic IP-check service (`ifconfig.me`, `ipinfo.io`) or a different domain than the one you care about can show the wrong exit IP. This is because some nodes route different destination domains through different upstream paths.

## Detection Pattern

### 1. Test the target domain directly

Cloudflare-proxied services expose the exit IP in `cdn-cgi/trace`:

```bash
export https_proxy=http://127.0.0.1:6152
curl -s --connect-timeout 5 --max-time 8 \
  "https://<target-domain>/cdn-cgi/trace" | grep "^ip="
```

Compare `ip=` across multiple domains routed through the same Surge policy group to detect splitting.

### 2. Cross-reference with Surge request logs

Verify the request actually hit the expected policy group:

```bash
surge-cli dump request --raw | python3 -c "
import json, sys
data = json.load(sys.stdin)
for r in data.get('active-requests', []):
    host = r.get('remoteHost', '')
    policy = r.get('policyName', '')
    notes = r.get('notes', [])
    rule_path = ''
    for n in notes:
        if 'Policy decision path' in n:
            rule_path = n.split('Policy decision path:')[-1].strip()
    if 'chatgpt' in host or 'target-domain' in host:
        print(f'{host} → {policy} | {rule_path}')
"
```

### 3. Use a known-anchor domain for DIP verification

Find a domain that UNIQUELY routes through the target policy group (no overlap with other RULE-SETs). In Surge configs, custom `DOMAIN-SUFFIX` rules before generic RULE-SETs are reliable anchors:

```bash
# Example: perplexity.ai is directly mapped to ✴️ Ai before any RULE-SET
curl -s "https://perplexity.ai/cdn-cgi/trace" | grep "^ip="
```

### 4. ipquality.sh for geo assessment

```bash
curl -sL "https://raw.githubusercontent.com/xykt/IPQuality/main/ip.sh" -o /tmp/ipquality.sh
# Requires bash ≥4.0 (macOS: brew install bash)
export https_proxy=http://127.0.0.1:6152
/opt/homebrew/bin/bash /tmp/ipquality.sh -n -E -j -o /tmp/ipquality_result.json
```

Key fields to check: `Info.RegisteredRegion` (where IP is registered) vs `Info.Region` (physical location). Geo-discrepant IPs show `Info.Type: Geo-discrepant`.

## Real-World Example (2026-06-04)

Node labeled `🇺🇸 USA Seattle 09 [DIP USA-Boston]`:

| Test method | Exit IP | CF Edge | Conclusion |
|:------------|:--------|:--------|:-----------|
| `ifconfig.me` (generic) | 23.249.17.28 | — | Tokyo, shared path |
| `chatgpt.com/cdn-cgi/trace` | 23.249.17.29 | NRT (Tokyo) | Also Tokyo — **BUT**: RULE-SET bug caused this to route through `🚀 节点选择2 → 🇯🇵 日本节点` instead of `✴️ Ai → DIP` |
| `perplexity.ai/cdn-cgi/trace` | 149.52.108.191 | SEA (Seattle, US) | **Actual DIP exit** — matched `✴️ Ai` correctly |

**Root cause**: AI.list and OpenAi.list RULE-SET URLs used `github.com/blob` instead of `raw.githubusercontent.com`, so they loaded empty. `chatgpt.com` fell through to ProxyGFWlist → 日本节点. The DIP was working fine — we were just never routing through it.

## Common Pitfalls

- **Testing with the wrong domain**: A node's DIP exit may only be used for specific destination domains. Test against the actual target, not a generic IP checker.
- **RULE-SET silent failures**: Broken RULE-SET URLs cause domains to fall through to later rules without any error. Verify with `dump profile effective`.
- **`cdn-cgi/trace` colo field**: `colo=NRT` means the nearest Cloudflare edge is Tokyo, NOT that the exit IP is in Tokyo. The edge is selected by BGP anycast based on the exit IP's network location.
- **HTTP proxy vs VIF routing**: Connections from `127.0.0.1` (HTTP proxy) and `198.18.0.1` (VIF) may hit different rules. Check `sourceAddress` in request logs.
