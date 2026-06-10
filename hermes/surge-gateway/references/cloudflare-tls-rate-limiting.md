# Cloudflare TLS Rate-Limiting via Proxy IPs

## Symptom Pattern

When accessing a Cloudflare-protected API through a Surge proxy, TLS handshakes fail **intermittently** — typically 60-80% of connections time out while 20-40% succeed. The pattern:

- **First connection after a pause**: often succeeds
- **Subsequent rapid connections**: TLS Client Hello sent, no Server Hello received → timeout
- **Direct connection (no proxy)**: 100% success
- **Switching proxy nodes**: no improvement (same pattern persists)

## How to Test

### Step 1: Baseline — direct test

```bash
curl -so /dev/null -w '%{http_code}|%{time_connect}|%{time_total}' \
  --max-time 10 --noproxy '*' \
  https://<target-domain>/<path> \
  -H 'Authorization: Bearer ***  -H 'Content-Type: application/json' \
  -d '{"test": true}'
```

- `time_connect` in milliseconds → TLS succeeded
- `time_connect=0` + timeout → TLS failed

### Step 2: Proxy test (multiple samples)

Run 5 sequential requests to measure failure rate:

```bash
for i in $(seq 1 5); do
  curl -so /dev/null -w '%{http_code}|%{time_connect}|%{time_total}\n' \
    --max-time 10 \
    --proxy http://127.0.0.1:6152 \
    https://<target-domain>/<path> \
    -H 'Authorization: Bearer ***    -H 'Content-Type: application/json' \
    -d '{"test": true}'
  sleep 2
done
```

- **>50% HTTP 000**: strong signal of Cloudflare rate-limiting
- **100% HTTP 4xx**: auth/token issue, not TLS

### Step 3: Isolate — does another proxy node fix it?

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" set 'ProxyGroupSelection.<group>=<alternate-node>'
sleep 2
# Repeat Step 2
```

If failure rate stays high across nodes → Cloudflare is rate-limiting the proxy provider's exit IP range.

## Root Cause

Cloudflare's bot detection treats rapid TLS connections from the same IP (or IP range) as suspicious. Commercial proxy providers share exit IPs across many users, so the aggregate connection rate looks like an attack. The rate limit is **per-IP TLS connection rate**, not per-request.

This is distinct from:
- Token expiry (would be 100% 401, not intermittent)
- Proxy node downtime (would be consistent)
- DNS issues (DNS resolves; Surge fake-IP works)

## Fix: DIRECT Route for Affected Domains

Bypass the proxy for the specific API endpoint in Surge config:

```
DOMAIN-SUFFIX,chatgpt.com,DIRECT
```

Verify direct connectivity works first. Trade-off: home IP exposure, potential GFW latency for China users.

## Case: chatgpt.com/backend-api/codex (2026-06-04)

- **Target**: `https://chatgpt.com/backend-api/codex/responses`
- **Surge**: `RULE-SET OpenAI.list` → `✴️ Ai` → proxy nodes
- **Symptoms**: 80% TLS timeout rate (4/5); same across US and HK nodes
- **Root cause**: Cloudflare rate-limiting proxy exit IPs
- **Direct**: 3ms time_connect, 100% success
