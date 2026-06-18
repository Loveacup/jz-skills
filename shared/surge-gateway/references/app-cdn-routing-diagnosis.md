# App CDN Routing Diagnosis

When an app's downloads/transfers feel slow, the instinct is to blame Surge routing. But the CDN
might be serving files from outside China even for Chinese apps (WeChat, DingTalk, etc.) — causing
unexpected proxy routing. This reference covers the diagnostic workflow to determine if routing
is the real bottleneck.

## The Workflow

### 1. Find the app's active connections

```bash
# All active connections through Surge
/Applications/Surge.app/Contents/Applications/surge-cli dump active

# Filter for a specific app's connections by device IP
surge-cli dump active | grep '<device_ip>'
```

Look for CDN-like domains in the host field: `c2c.cdn.wechat.com`, `cdn.dingtalk.com`, etc.

### 2. Geo-locate the CDN IPs

```bash
for ip in <ip1> <ip2> <ip3>; do
  curl -s "https://ipinfo.io/$ip/json" | python3 -c "
import json,sys; d=json.load(sys.stdin)
print(f'{d.get(\"ip\")}: {d.get(\"country\")} {d.get(\"city\")} — {d.get(\"org\")}')"
done
```

### 3. Determine Surge routing for those IPs

Check the active config:
```bash
grep -n 'GEOIP\|FINAL' ~/Library/Application\ Support/Surge/Profiles/mine.conf
```

- If `GEOIP,CN` → IPs inside China go DIRECT, everything else falls to FINAL
- FINAL usually routes to a proxy group → check `environment` for the current selection

### 4. Compare direct vs proxy bandwidth

**Don't trust latency alone** — a 200ms direct connection can outrun a 50ms proxy path.
Measure actual throughput:

```bash
# Direct (bypass Surge HTTP proxy layer — note: TUN mode may still intercept)
curl -o /dev/null -s -w "Speed: %{speed_download} B/s\n" \
  --connect-timeout 5 --max-time 15 \
  "https://<cdn-ip>/path-to-test-file"

# Via proxy
curl -o /dev/null -s -w "Speed: %{speed_download} B/s\n" \
  --connect-timeout 10 --max-time 20 \
  -x http://127.0.0.1:6152 \
  "https://<cdn-ip>/path-to-test-file"
```

**Use Cloudflare speed test as a neutral benchmark:**
```bash
# 5MB download from nearest CF edge
curl -o /dev/null -s -w "Speed: %{speed_download} B/s\n" \
  --connect-timeout 5 --max-time 15 \
  "https://speed.cloudflare.com/__down?bytes=5000000"
```

### 5. Interpret results

| Direct faster | Proxy faster | Implication |
|--------------|-------------|-------------|
| ✅ | ❌ | Routing IS the problem — add DIRECT rule for the CDN domain |
| ❌ | ✅ | Routing is NOT the problem — ISP's international transit is worse than proxy's transit |
| ~same | ~same | Bottleneck is app/server, not network — look at client-side or server throttling |

### 6. Common pitfalls

- **Proxy can be faster than direct** — Japan proxy transit to Singapore CDN beat China Telecom direct in real test (11.4 MB/s vs 6.0 MB/s). Don't assume DIRECT is always better.
- **CDN IP geo can surprise you** — WeChat serves files from Singapore Tencent Cloud nodes, not China. These don't match GEOIP,CN but adding DIRECT rules won't necessarily help.
- **Idle connections ≠ slow routing** — WeChat often opens many connections to the same CDN with most sitting at 0 B/s. This is client behavior, not routing failure.
- **HTTP proxy bypass doesn't bypass TUN** — Surge in TUN mode intercepts all traffic. `--noproxy '*'` only affects HTTP_PROXY env var. To truly test direct, you need a different network path.

## Real Case: WeChat Singapore CDN (2026-06-07)

- WeChat file transfer → `c2c.cdn.wechat.com` → Singapore Tencent Cloud IPs (101.32.x.x, 43.160.x.x)
- GEOIP classified as non-CN → routed through 🇯🇵 Japan proxy
- Direct bandwidth: 6.0 MB/s | Proxy bandwidth: 11.4 MB/s → **proxy was faster**
- WeChat actual download: 1.6-2.1 MB/s → bottleneck is server/client, not routing
- Conclusion: don't add DIRECT rule — wouldn't help and might hurt
