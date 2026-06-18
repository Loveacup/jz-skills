# ChatGPT/Codex TLS Diagnosis Through Surge

Case study distilled from 2026-06-11 debugging of `chatgpt.com/backend-api/codex` TLS failures via Surge HTTP proxy (`127.0.0.1:6152`).

## Trigger

Use this reference when:

- `chatgpt.com`, `chat.openai.com`, or Codex OAuth endpoints fail with `SSL_ERROR_SYSCALL`, `UNEXPECTED_EOF`, or HTTP `000` through Surge.
- `hermes auth add openai-codex` fails during OAuth device-code/token refresh, but other API calls with an existing token may still work.
- The suspected path is `✴️ Ai → 🌐 独立 IP 节点 → DIP/Akamai/other node`.

## Critical lessons

### 1. Do not infer target-domain exit from generic IP checkers

`curl -x http://127.0.0.1:6152 https://ipinfo.io` or `ifconfig.me` may match a different Surge rule than `chatgpt.com`.

Correct evidence hierarchy:

1. `dump request --raw` for the actual target domain — especially `notes`, `policyName`, `originalPolicyName`, `remoteAddress`, `outBytes`, `inBytes`, and `timingRecords`.
2. Target-domain self-observation when available, e.g. `https://chatgpt.com/cdn-cgi/trace` (`ip`, `colo`, `loc`, `tls`, `http`).
3. `dump active` for hung 0 B/s TLS connections.
4. Generic IP checkers only after confirming they route through the same policy path.

### 2. Check the effective profile, not only the local config file

Local `~/Library/Application Support/Surge/Profiles/mine.conf` can be a short/stale base profile. The live policy groups may be injected via `policy-path` in the effective profile.

Use:

```bash
SURGE="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE" dump profile effective | grep -n -E '(^✴️ Ai =|^🌐 独立 IP 节点 =|Akamai|USA Seattle 0[89]|RULE-SET.*OpenAi|RULE-SET.*AI\.list)'
```

Do not conclude that a group is missing until it is absent from `dump profile effective`.

### 3. Distinguish three TLS layers

A successful proxy tunnel does not prove the target TLS works.

From `dump request --raw` notes:

- `[Socket] Connected to address ...` — Surge reached the proxy server.
- `[TLS] Proxy TLS handshake completed ...` — the proxy protocol layer is up.
- Target-domain TLS success requires downstream bytes from `chatgpt.com`. If `outBytes > 0` but `inBytes = 0`, the target TLS Client Hello was likely dropped upstream.

### 4. 0 B/s active connections are evidence of hung target TLS

```bash
"$SURGE" dump active | grep -i 'chatgpt'
```

Interpretation:

- `HTTPS chatgpt.com:443 (Up: 0 B/s, Down: 0 B/s)` lingering after a failed curl = stuck/hung TLS path.
- Successful `cdn-cgi/trace` requests usually show non-zero down bytes and finish quickly.
- Old hung connections may remain after a route fix; do not treat stale active rows as proof that new requests still fail. Re-test with a fresh curl and compare timestamps.

### 5. DIP is not automatically better than Akamai / premium nodes

Dedicated IP nodes can be effective, but they are not immune to ChatGPT/Cloudflare throttling. In the 2026-06-11 case:

- `🇺🇸 USA Seattle 08 [DIP USA-Boston]` and `09` both routed correctly, but `chatgpt.com` TLS returned `SSL_ERROR_SYSCALL`.
- `🇺🇸 Akamai` succeeded: `chatgpt.com/cdn-cgi/trace` returned `HTTP/2`, `TLSv1.3`, `loc=US`, `colo=SEA`, and a US IPv6 exit.
- The final working runtime selection was `✴️ Ai → 🌐 独立 IP 节点 → 🇺🇸 Akamai`.

Do not recommend “DIP fixes it” blindly. Test candidate nodes against the actual target domain.

## Read-only diagnostic sequence

All commands below are read-only **except** candidate switching (`set`). Because this Surge is a household gateway, do not run any `set`, `add-temp-rule`, `reload`, `flush`, or `kill` without explicit user confirmation.

### A. Inspect live config and runtime selections

```bash
SURGE="/Applications/Surge.app/Contents/Applications/surge-cli"

"$SURGE" dump profile effective \
  | grep -n -E '(^✴️ Ai =|^🌐 独立 IP 节点 =|^✈️ 我的节点 =|Akamai|USA Seattle 0[89]|DOMAIN-SUFFIX,chatgpt.com|RULE-SET.*OpenAi|RULE-SET.*AI\.list)'

"$SURGE" environment | python3 -c '
import json,sys
env=json.load(sys.stdin)
g=env.get("ProxyGroupSelection",{})
for k in ["✴️ Ai","🌐 独立 IP 节点","✈️ 我的节点","🚀 节点选择1","🚀 节点选择2","🐟 漏网之鱼"]:
    print(f"{k}: {g.get(k)}")
'
```

### B. Test current route against the actual target

```bash
curl -sS --connect-timeout 10 --max-time 15 \
  -x http://127.0.0.1:6152 \
  https://chatgpt.com/cdn-cgi/trace

for i in 1 2 3; do
  curl -sS -o /dev/null \
    -w "#$i http=%{http_code} connect=%{time_connect} ssl=%{time_appconnect} total=%{time_total} err=%{errormsg}\n" \
    --connect-timeout 10 --max-time 15 \
    -x http://127.0.0.1:6152 \
    https://chatgpt.com/backend-api/codex
  sleep 0.5
done
```

Expected:

- `cdn-cgi/trace` returns `tls=TLSv1.3` and `http=http/2` when healthy.
- Codex endpoint may return `403` without auth; that is application-layer success for TLS diagnosis.
- `HTTP 000` + `SSL_ERROR_SYSCALL` means TLS failed before HTTP.

### C. Capture request-path evidence

```bash
"$SURGE" dump request --raw | python3 <<'PY'
import json, sys

data = json.load(sys.stdin)
for r in data.get("requests", []):
    if "chatgpt" in str(r).lower():
        print("URL:", r.get("URL") or r.get("remoteHost"))
        print("policyName:", r.get("policyName"))
        print("originalPolicyName:", r.get("originalPolicyName"))
        print("remoteAddress:", r.get("remoteAddress"))
        print("status:", r.get("status"), "failed:", r.get("failed"), "completed:", r.get("completed"))
        print("bytes out/in:", r.get("outBytes"), r.get("inBytes"))
        for n in r.get("notes", []):
            if any(x in n for x in ["Policy decision path", "Sub-rule matched", "Rule matched", "TLS", "Socket"]):
                print(n)
        for t in r.get("timingRecords", []):
            print(f"{t.get('name')}: {t.get('durationInMillisecond')}ms")
        print("---")
PY
```

Look for a line like:

```text
Policy decision path: ✴️ Ai -> 🌐 独立 IP 节点 -> 🇺🇸 Akamai
```

or:

```text
Policy decision path: ✴️ Ai -> 🌐 独立 IP 节点 -> 🇺🇸 USA Seattle 09 [DIP USA-Boston]
```

### D. Candidate-node comparison (requires confirmation)

Switching policies is mutation. Ask first. If confirmed, test candidates one at a time:

```bash
"$SURGE" set "ProxyGroupSelection.🌐 独立 IP 节点=🇺🇸 USA Seattle 08 [DIP USA-Boston]"
# test B + capture C

"$SURGE" set "ProxyGroupSelection.🌐 独立 IP 节点=🇺🇸 USA Seattle 09 [DIP USA-Boston]"
# test B + capture C

"$SURGE" set "ProxyGroupSelection.🌐 独立 IP 节点=🇺🇸 Akamai"
# test B + capture C
```

Restore the user’s original selection after testing, unless the user explicitly confirms a new selection.

## Reporting pattern

Report conclusions only after reconciling contradictory evidence. Use this structure:

- **Route correctness**: exact `Policy decision path` from request notes.
- **Proxy-layer health**: socket/proxy TLS notes and timing.
- **Target TLS health**: curl result + `outBytes/inBytes`.
- **Candidate comparison**: per-node result against `chatgpt.com`, not generic IP checker.
- **Residuals**: old hung connections, if any, with timestamp caveat.

## Failure classification from this case

- Misusing `ipinfo.io` to infer `chatgpt.com` exit: **execution lapse** against existing domain-based-routing guidance.
- Reading only local `mine.conf` and ignoring `dump profile effective`: **skill defect** — now fixed by this reference.
- Treating DIP as categorically superior: **optimization defect** — now replaced by target-domain candidate testing.
- Running `set` / `add-temp-rule` without explicit confirmation: **execution lapse** against Safety Posture. Do not change the safety rule; follow it.