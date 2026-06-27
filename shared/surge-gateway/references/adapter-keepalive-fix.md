# Adapter-Layer TLS Resilience Fix

> When the proxy exit IP faces random TLS handshake drops from Cloudflare (~41% in observed cases), the Hermes agent's HTTP adapter can amplify or mitigate the impact.

## Root Cause

Three factors multiply:
1. **Proxy**: Smart group rotates exit IPs → some get TLS-dropped by Cloudflare
2. **Adapter**: Each request creates a new TLS handshake (HTTP/1.1, keepalive_expiry=5s, connect timeout=5s)
3. **SDK retries**: 3 retries × 5s connect = worst-case 16s before user sees failure

## Fix: Three Changes to `_build_keepalive_http_client`

File: `run_agent.py`, function `_build_keepalive_http_client`

### A. Reduce connect timeout (5s → 2.5s)

```python
_timeout = _httpx.Timeout(
    connect=_f("HERMES_CODEX_CONNECT_TIMEOUT", 2.5),
    read=600.0, write=30.0, pool=30.0,
)
```

Setting explicit timeout ≠ httpx default means OpenAI SDK adopts ours.

### B. Extend keepalive expiry (5s → 300s)

```python
_limits = _httpx.Limits(
    max_connections=50,
    max_keepalive_connections=20,
    keepalive_expiry=_f("HERMES_CODEX_KEEPALIVE_EXPIRY", 300.0),
)
```

A successfully-established TLS session is reused across the entire conversation.

### C. Enable HTTP/2 multiplexing

```python
_transport = _httpx.HTTPTransport(
    socket_options=_sock_opts,
    http2=_want_h2,
    limits=_limits,   # MUST pass to Transport, not just Client
)
```

Requires `pip install h2`. Fallback to HTTP/1.1 if h2 not installed.

## Critical: Pass `limits` to HTTPTransport

Passing `limits` only to `httpx.Client()` does NOT affect a custom transport's pool:

```python
_transport = _httpx.HTTPTransport(..., limits=_limits)
client = _httpx.Client(transport=_transport, limits=_limits, ...)
```

## Verification

```python
pool = client._transport._pool
assert pool._keepalive_expiry == 300.0    # was 5.0
assert pool._max_connections == 50        # was 100
assert client.timeout.connect == 2.5      # was 5.0
```

## Combined Effect

| Metric | Before | After |
|--------|--------|-------|
| Failed TLS handshake wait | 5s × 3 = 15s | 2.5s × 3 = 7.5s |
| Keepalive expiry | 5s | 300s |
| Handshakes per conversation | 1 per request | 1 per connection |
| HTTP protocol | HTTP/1.1 | HTTP/2 |

## Pitfalls

- `h2` must be installed: `pip install h2` in the Hermes venv
- Must pass `limits` to Transport: only passing to `Client` leaves pool using defaults
- Auth commands use their own client: `hermes auth add` uses bare `httpx.Client(timeout=15.0)` without keepalive, proxy, or HTTP/2 — it's unaffected by this fix. With 40% TLS success on shared IPs, OAuth polling (5-10 polls) has near-zero probability of all polls succeeding. Observed: 16 retry attempts before one reached the polling stage (LA 01, 40% TLS). **Workaround**: use a DIP node before running `hermes auth add`, or retry in a loop.
- Not a replacement for proxy-level fix: still prefer fixed DIP node over smart group

## Verified with DIP (2026-06-04)

After switching to dedicated IP `🇺🇸 USA Seattle 08 [DIP USA-Boston]` (100% TLS success):

```
Try 1: HTTP 200 (6.7s)  — first TLS handshake
Try 2: HTTP 200 (3.0s)  — keepalive reuse
Try 3: HTTP 200 (1.5s)  — keepalive reuse, response time drops each call
```

Keepalive expiry=300s + HTTP/2 confirmed working — response times decreased as the same TLS connection was reused across calls. Even with 100% proxy TLS, the adapter fix provides latency improvement by avoiding per-request handshake overhead.
