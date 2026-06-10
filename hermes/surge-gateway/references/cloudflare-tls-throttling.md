# Cloudflare TLS Handshake Throttling Through Surge Proxy

## Symptom Pattern

When accessing Cloudflare-protected API endpoints (e.g., `chatgpt.com/backend-api/codex`) through Surge proxy:

- **~75% success rate**: 3 out of 4 connections complete TLS handshake and reach the API
- **~25% hard timeout**: remaining connections hang at TLS Client Hello, never receive Server Hello, timeout after 15s
- `time_connect=0ms` in curl output → TCP-level connection never completes
- `HTTP 000` status → curl never established an HTTP connection

## Root Cause

Cloudflare's DDoS protection treats proxy exit IPs as high-frequency clients. When multiple TLS connections originate from the same exit IP in rapid succession, Cloudflare randomly drops some TLS handshakes. This is NOT node-specific — testing across 8 geographic regions (HK, TW, JP, SG, US, UK, EU, Other) shows the same ~75/25 split on ALL nodes.

## Key Diagnostic Finding

**Auth header presence affects TLS completion.** Without any `Authorization` header in the request, Cloudflare drops the TLS handshake 100% of the time (HTTP 000). With ANY `Authorization` header (even bogus `Bearer *** the TLS handshake completes normally ~75% of the time. This suggests Cloudflare's edge performs header inspection at the TLS layer.

## Diagnosis Protocol

```bash
# 1. Confirm proxy routing for the target domain
SURGE="/Applications/Surge.app/Contents/Applications/surge-cli"
grep -i 'chatgpt\|openai' ~/Library/Application\ Support/Surge/Profiles/mine.conf

# 2. Test TLS success rate (5 samples, 2s apart)
for i in 1 2 3 4 5; do
  curl -so /dev/null -w '%{http_code}|%{time_connect}|%{time_total}\n' \
    --max-time 12 --proxy http://127.0.0.1:6152 \
    -H 'Authorization: Bearer ***    -d '{"model":"gpt-5.5"}' \
    https://chatgpt.com/backend-api/codex/responses
  sleep 2
done

# HTTP 000 + time_connect=0 = TLS throttled
# HTTP 4xx + time_connect>0 = TLS OK, auth/API issue

# 3. Eliminate node-specific theories: test multiple regions
# Switch proxy group and repeat the 5-sample test per region
# Pattern should be ~75% across ALL regions → CF edge throttling, not node issue

# 4. Confirm by testing direct (no proxy)
curl -so /dev/null -w '%{http_code}|%{time_connect}\n' \
  --max-time 12 --noproxy '*' \
  https://chatgpt.com/backend-api/codex/responses
# If this works 100%, proxy is the variable
```

## Mitigations

| Option | Effectiveness | Tradeoff |
|--------|-------------|----------|
| Route to DIRECT | 100% fix | Privacy/geo implications |
| Connection keepalive/pooling | Reduces handshake frequency | Requires client-side support |
| Dedicated clean-IP proxy node | High | Cost/complexity |
| Built-in retry with backoff | Masks the issue | Adds latency on retries |

Hermes' `codex_responses` adapter already has retry/backoff logic for this scenario (see `agent/conversation_loop.py` lines 2513-2521).

## Related

- `references/multi-region-api-testing.md` — testing API reachability from different proxy regions
- Hermes agent retry: `agent/conversation_loop.py` — `codex_responses` 401/000 handling
