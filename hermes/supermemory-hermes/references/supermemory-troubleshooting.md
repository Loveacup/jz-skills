# Supermemory Troubleshooting & Support Communication

> How to diagnose Supermemory issues and draft effective support emails.
> Created from the 2026-06-01 Pro upgrade memory-graph-wipe incident.

## Diagnostic Commands

### 1. Check API health (stdlib urllib, no SDK)

```python
import os, json, urllib.request

api_key = "<from .env>"
headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

# Test all endpoints
for url in [
    "https://api.supermemory.ai/v3/documents?containerTag=hermes-cabinet&limit=3",
    "https://api.supermemory.ai/v3/profile?containerTag=hermes-cabinet",
    "https://api.supermemory.ai/health",
]:
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"OK {resp.status}: {url}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='ignore')
        print(f"ERROR {e.code}: {url} → {body[:300]}")
```

### 2. Search agent logs for Supermemory events

```bash
# Store timeouts and failures
grep -i 'supermemory_store.*timeout\|Failed to store\|timed out' \
  ~/.hermes/logs/agent.log | tail -30

# Search successes (for timeline)
grep -i 'supermemory_search completed' ~/.hermes/logs/agent.log | tail -20

# Gateway inbound (for user-reported timeline)
grep -i 'supermemory\|container.tag\|duplicate.*pool' ~/.hermes/logs/gateway.log | tail -30
```

### 3. Check Supermemory configuration

```bash
# Active profiles using Supermemory
find ~/.hermes/profiles -name 'supermemory.json' -exec echo {} \; -exec cat {} \;

# Memory provider config
grep -A 5 'memory:' ~/.hermes/config.yaml
grep -A 5 'memory:' ~/.hermes/profiles/regent/config.yaml

# Pool inventory — search for container_tag across all configs
grep -r 'container.tag\|container_tag' ~/.hermes/profiles/*/supermemory.json 2>/dev/null
```

## Support Email Template

### Structure (bilingual: English + Chinese)

1. **Subject line** — Plan + symptom summary + pool count
   - `Pro Plan Upgrade — Account-Level Memory Graph Wipe (3 Pools)`

2. **Body — English then Chinese**
   - Problem statement (what broke, account-level confirmation)
   - Symptom table (pool × status)
   - Account details (email, plan, affected pools)
   - Impact statement (blocking production use)
   - Three specific investigation requests
   - Configuration details appendix (Hermes version, provider, container_tag, profiles, pool config, flush settings, API endpoint, sink method)
   - Timeline table (date × event, with log timestamps)
   - API test results (endpoint × HTTP status)
   - Notable error signatures from logs

### Pitfalls

- **Get the upgrade date right** — ask user or check logs; don't assume
- **Mention `/health` returning 404** — this is abnormal for production APIs and signals infrastructure issues, not just data corruption
- **Include all pools** — scan `supermemory.json` across profiles to find all container tags
- **Log timestamps in UTC** — gateway logs use local time; label clearly

### Example sections

**Timeline table:**
```
| Date | Event |
|------|-------|
| May 29 | First noticed pool separation |
| May 30 | Duplicate container tags observed |
| May 31 | Re-tag + Pro upgrade. Store begins timing out (5.26s) |
| Jun 1 05:29 | Last successful search (1.81s, 1593 chars) |
| Jun 1 08:15 | All endpoints 404. Graph shows documents only |
```

**API test block:**
```
GET /v3/documents?containerTag=hermes-cabinet&limit=3 → HTTP 404
GET /v3/profile?containerTag=hermes-cabinet → HTTP 404
GET /health → HTTP 404
```

**Error signatures:**
```
- supermemory_store timeout: "Failed to store memory: Request timed out." (5.26s)
- All 3 endpoints unreachable (404), not just data-missing
- /health returning 404 is unusual for production API
```
