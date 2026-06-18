# Multi-Region API Testing via Surge Proxy

Use Surge's proxy group switching to test API reachability from different geographic regions. Useful for distinguishing regional outages from global origin failures.

## When to Use

- Suspected API outage — need to confirm if it's regional or global
- Debugging Cloudflare-origin connectivity issues
- Vendor support diagnostics (providing multi-region evidence)
- Testing CDN/edge routing behavior

## Workflow

### 1. Identify candidate proxy groups

List available groups with geographic diversity:

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" environment | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k,v in d.get('ProxyGroupSelection',{}).items():
    print(f'{k} → {v}')
"
```

Pick groups that route through different regions. Common targets:
- `🚀 节点选择1` (Japan), `🚀 节点选择` (Hong Kong)
- `🇺🇲 自定义美国` (USA), `🇪🇺 欧洲节点` (Europe)
- `🇸🇬 自定义新加坡` (Singapore)

### 2. Find the catch-all group

The `🐟 漏网之鱼` group handles traffic that doesn't match any specific rule. Switch this to test different exits:

```bash
# Switch catch-all to a specific region
"$SURGE_CLI" set "ProxyGroupSelection.🐟 漏网之鱼=🇭🇰 香港节点"
sleep 2  # let routing settle

# Test the target API
curl -s -D - -o /dev/null --http1.1 --connect-timeout 10 --max-time 15 \
  "https://api.target-service.com/health" 2>&1 | grep -iE 'HTTP/|cf-ray'
```

### 3. Collect CF-RAY headers per region

For Cloudflare-proxied services, the `CF-RAY` header reveals which edge processed the request:

| CF-RAY suffix | Edge location |
|--------------|---------------|
| `-HKG` | Hong Kong |
| `-LAX` | Los Angeles |
| `-NRT` | Tokyo (Narita) |
| `-SIN` | Singapore |
| `-LHR` | London |
| `-FRA` | Frankfurt |

Different suffixes = different physical edges = independent tests.

### 4. Restore original routing

```bash
# Restore catch-all to default
"$SURGE_CLI" set "ProxyGroupSelection.🐟 漏网之鱼=🚀 节点选择1"
```

## Key Diagnostic Signals

**Global origin outage** (strongest evidence):
- Multiple CF edges (different `CF-RAY` suffixes, e.g. HKG + LAX) return same 404
- `Server-Timing: cfOrigin;dur=0` — CF spent zero ms with origin
- Main marketing site (different subdomain) returns 200 — rules out total CF outage
- `POST` to API returns 400 (not 404) — CF edge is processing, origin unreachable

**Regional issue**:
- Only one edge returns 404; others work
- Check if the failing proxy node has connectivity issues

**Client-side issue**:
- All edges return 200 but client still fails
- Check DNS, proxy rules, local firewall

## Example: Supermemory API Outage (2026-06-01)

```bash
# Test from 5 regions
for target in "🇭🇰 香港节点" "🇺🇲 美国节点" "🇯🇵 日本节点" "🇸🇬 狮城节点" "厄瓜多尔 01"; do
  "$SURGE_CLI" set "ProxyGroupSelection.🐟 漏网之鱼=$target"
  sleep 2
  result=$(curl -s -D - -o /dev/null --http1.1 --connect-timeout 10 --max-time 15 \
    "https://api.supermemory.ai/health" 2>&1 | grep -oP 'cf-ray:\s*\K[^\r]+')
  echo "$target → CF: $result"
done
```

Results proved global origin outage: HKG (Hong Kong edge) and LAX (Los Angeles edge) both returned 404.
