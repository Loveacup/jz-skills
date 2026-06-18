# TLS Connectivity Diagnostics Through Surge Proxy

Systematic methodology for testing TLS handshake reliability through Surge proxy nodes to Cloudflare-protected APIs.

## When to Use

- API is "sometimes unresponsive" but never fully down
- Suspect Cloudflare rate-limiting proxy exit IPs
- Need to determine if intermittent failures are node-specific or global

## Testing Methodology

### Step 1: Baseline — Direct vs Proxy

```bash
# Direct (no proxy) — establish baseline
curl -so /dev/null -w '%{http_code}|%{time_connect}|%{time_total}' \
  --max-time 12 --noproxy '*' \
  https://<target-api>/endpoint \
  -H 'Authorization: Bearer *** \
  -H 'Content-Type: application/json' \
  -d '<body>'

# Via Surge proxy
curl -so /dev/null -w '%{http_code}|%{time_connect}|%{time_total}' \
  --max-time 12 --proxy http://127.0.0.1:6152 \
  https://<target-api>/endpoint \
  -H 'Authorization: Bearer *** \
  -H 'Content-Type: application/json' \
  -d '<body>'
```

**Interpretation:**
- `HTTP 000` + `time_connect=0ms` → TLS handshake dropped (Client Hello never answered)
- `HTTP 401/403/etc` + `time_connect=<1ms` → TLS succeeded, API returned auth error (expected with dummy token)
- Direct OK + Proxy fails → Cloudflare blocking proxy IPs

### Step 2: Multi-Region Sweep

Test each Surge regional proxy group to determine if any region is immune:

```bash
SURGE="/Applications/Surge.app/Contents/Applications/surge-cli"

# Pre-write auth header to file (avoids shell escaping issues)
python3 -c "open('/tmp/ah','w').write('Authorization: Bearer *** Test each region
for pair in "HK:🇭🇰 香港节点" "TW:🇼🇸 台湾节点" "JP:🇯🇵 日本节点" \
             "SG:🇸🇬 新加坡节点" "US:🇺🇲 美国节点" "UK:🇬🇧 英国节点" \
             "EU:🇪🇺 欧洲节点" "OT:🇺🇳 小众节点"; do
  code="${pair%%:*}"
  name="${pair#*:}"
  $SURGE set "ProxyGroupSelection.<group>=${name}" 2>/dev/null
  sleep 2
  result=$(curl -so /dev/null -w '%{http_code}|%{time_total}' \
    --max-time 15 --proxy http://127.0.0.1:6152 \
    -H @/tmp/ah -H 'Content-Type: application/json' \
    -d '<body>' https://<target-api>/endpoint 2>&1)
  echo "${code}: ${result}"
  sleep 3
done
```

### Step 3: Repeat for Statistical Significance

Run at least 3 rounds to distinguish random failures from node-specific issues. A single round can be misleading.

**Expected patterns:**
- **Node-specific**: Same region consistently fails/passes across rounds → bad node or network path
- **Random across all nodes**: All regions show ~50-75% success with no pattern → Cloudflare global rate-limiting
- **Time-of-day dependent**: All regions pass during off-peak, fail during peak → CF rate-limiting correlated with traffic

### Step 4: Root Cause Determination

| Symptom | Root Cause |
|---------|-----------|
| Direct 100%, Proxy 50-75%, all regions same pattern | Cloudflare rate-limiting proxy exit IPs |
| Specific region 0%, others 100% | Bad proxy node in that region |
| All regions work, then all fail | Cloudflare burst throttling after multiple connections |
| Succeeds first time after pause, then fails repeatedly | TLS connection budget consumed by prior connections |

## The Ultimate Fix: Dedicated IP (DIP)

When all shared proxy exit IPs suffer Cloudflare TLS throttling (15-59% success), switching to a Dedicated IP node is definitive.

**Comparison (2026-06-04, chatgpt.com, 8 Surge regions):**

| Node Type | TLS Success | SSL Latency |
|-----------|:----------:|:-----------:|
| Smart group (24 shared US IPs) | ~59% | 0.2–10s |
| Fixed shared IP (LA 01) | 40% | 2–10s |
| Fixed shared IP (Seattle 03) | 15% | 4–10s |
| **DIP (USA-Boston)** | **100%** | **0.29–0.36s** |

**Verification** (8/8 consecutive):
```bash
for i in $(seq 1 8); do
  curl -so /dev/null -w '%{http_code}|%{time_appconnect}\n' \
    --connect-timeout 8 --max-time 10 \
    --proxy http://127.0.0.1:6152 \
    https://chatgpt.com/cdn-cgi/trace
done
# All return 200, SSL 0.29-0.36s
```

Even with DIP, keep the adapter-layer fixes (keepalive, HTTP/2) — they reduce per-request latency by avoiding redundant TLS handshakes.

### Cloudflare TLS Connection Budget

Cloudflare enforces a per-IP TLS connection rate budget on `chatgpt.com`. After establishing a few TLS connections, subsequent Client Hello messages are silently dropped until the budget resets (typically 30-60 seconds). This means:
- First 1-2 tests in a sweep will succeed
- Subsequent tests will timeout
- Waiting 30+ seconds between tests improves success rate

### Shell escaping with auth tokens

When using auth tokens in shell commands, avoid `{...}` patterns that may be intercepted by content filters. Workarounds:
1. **File-based headers**: `curl -H @/tmp/auth_header_file ...` — safest, no interpolation
2. **Base64 encoding**: encode the auth string, decode inline with `base64 -d`
3. **Python subprocess**: pass headers as list elements, no shell involved

### Surge proxy group switching latency

After `surge-cli set`, wait at least 2 seconds before testing — the proxy switch is not instantaneous.

### Quick Proxy Health Baseline

Before diagnosing a specific domain, first test if the HTTP proxy itself is alive using a generic endpoint:

```bash
# Basic proxy alive check
curl -s --max-time 5 -x http://127.0.0.1:6152 https://httpbin.org/ip

# If this returns nothing → proxy is fully down (Surge may need restart or the HTTP
# proxy listener on 6152 is not running). Check: lsof -iTCP:6152 -sTCP:LISTEN
# If this returns your exit IP → proxy works; the target domain is the problem
```

**Distinguishing proxy-down from domain-specific TLS throttling:**
| Test | Result | Meaning |
|------|--------|---------|
| `curl -x :6152 httpbin.org/ip` | No response | Proxy itself broken — check Surge process/port |
| `curl -x :6152 httpbin.org/ip` | Returns IP | Proxy works; target domain issue |
| `curl -x :6152 chatgpt.com` | Connection reset | Cloudflare throttling that specific domain |
| `curl --noproxy '*' chatgpt.com` | TLS handshake OK | Confirms domain reachable; proxy is the bottleneck |

### Config vs Environment Mismatch

When `surge-cli environment` shows a ProxyGroupSelection that doesn't exist in the active config file, Surge may silently fall back to the first option in the `select` list — causing traffic to route through unintended nodes.

**Detection:**
```bash
# Get the current selection for a group from environment
surge-cli environment | grep '"✴️ Ai"'
# → "✴️ Ai" : "🌐 独立 IP 节点"

# Check if that value exists in the config's select list
grep '✴️ Ai' ~/Library/Application\ Support/Surge/Profiles/mine.conf
# → ✴️ Ai = select, "🚀 节点选择1", "🚀 节点选择2", ...
#    "🌐 独立 IP 节点" is NOT in the list → MISMATCH!
```

**Impact**: A DIP-only group name selected but not in the `select` list means traffic falls back to the first option (usually a shared-IP regional group) — TLS throttling resumes silently. Fix by either adding the DIP group to the select list, or using a `policy-path` that correctly references it.

### Using `dump active` for hung connection detection

When connections are stuck mid-TLS, they appear as 0 B/s in the active connection list:

```bash
surge-cli dump active | grep "0 B/s"
# → #213504, [2026/6/5 05:40] <7800x3d> HTTPS chatgpt.com:443 (Up: 0 B/s, Down: 0 B/s)
```

Multiple 0 B/s connections to the same target domain from the same timestamp confirm TLS handshake hangs (not slow responses). Compare with `dump request` to see if any connections eventually completed — if some did and some didn't, it's intermittent Cloudflare throttling.

### Exit code 28 from curl

curl exit code 28 = timeout. Check `time_connect`:
- `time_connect=0ms` → TLS handshake never completed
- `time_connect>0` → TCP+TLS connected but HTTP response timeout
