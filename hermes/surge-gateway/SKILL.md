---

name: surge-gateway
description: >-
  Control and troubleshoot the user's household Surge for Mac gateway via surge-cli.
  Use when the user asks about Surge, proxy mode/group/selection, network routing,
  DNS/cache, node latency, recent requests, household device identification, waking
  or SSH-ing into LAN Macs, or split-routing config. Do NOT use for general networking
  questions unrelated to Surge.
type: routine
version: 2.5.2
tags: [surge, proxy, network, routing, dns, gateway]
related_skills: [unifi-ops, openwrt-router]
---

# Surge Gateway

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse | Why it's wrong |
|--------|---------------|
| "I know how surge-cli works, I don't need the skill" | This Surge is the family gateway. Generic CLI knowledge misses household context: device inventory, safety posture, impact radius. |
| "The command looks safe, I'll just run it" | A `stop` or `reload` during active traffic disrupts everyone. Every command has a safety classification — check it first. |
| "I'll test all the nodes to find the fastest" | `test-all-policies` floods the network. Use targeted `test-policy` or `test-group`. |
| "The inventory is stale, I'll skip refreshing it" | Stale IPs/MACs lead to wrong device targeting (wrong Mac for WoL, wrong DHCP lease). Refresh when it matters. |
| "I see RULE-SET errors in `dump event`, the config must be broken" | 🔴 **Event logs are historical — they may reflect an old config that has since been updated.** Always cross-reference with the actual config file first. `grep` the relevant RULE-SET URL in the active profile, then test the URL with `curl -sI`. Only report a config issue if the CURRENT config's URLs fail. The event log alone is not a reliable indicator of the active config's health. |
| "The group isn't in `mine.conf`, so it doesn't exist" | 🔴 **Wrong for policy-path profiles.** The local profile can be a short/stale base profile; remote policy groups are injected into the live effective profile. Always check `dump profile effective` before declaring a group/rule missing. |
| "DIP should fix ChatGPT, so if it fails the config must be wrong" | 🔴 **DIP is not magic.** Dedicated IP, Akamai, and shared/premium nodes must be tested against the actual target domain (`chatgpt.com`/Codex), not generic probes. Cloudflare can drop target TLS for one node while another works. |

## 🔀 Decision Tree

```
Network/routing/proxy/DNS/device task?
├── YES → This skill
│   ├── Read-only diagnostic? → Use safe commands freely
│   ├── Mutation (set/reload/switch/flush)? → Explain impact, confirm, then act
│   ├── Device identification? → Refresh inventory → triangulate (ARP+DHCP+Surge requests)
│   ├── Wake/SSH to LAN Mac? → references/lan-access.md
│   ├── Split routing for similar domains? → references/split-routing.md
├── "Review my Surge config for issues"? → references/config-audit-checklist.md
│   ├── Game download speed (Steam/Epic/etc.)? → references/game-download-speed-diagnosis.md
│   ├── App download/transfer slow (WeChat, DingTalk, etc.)? → references/app-cdn-routing-diagnosis.md
│   ├── Smart group behavior questions? → references/smart-group-nuances.md
│   ├── API intermittently fails through proxy (some succeed, some time out)?
│   │   → references/tls-connectivity-diagnostics.md — systematic multi-region TLS sweep
│   ├── ChatGPT/Codex OAuth TLS fails (`SSL_ERROR_SYSCALL`, `UNEXPECTED_EOF`, HTTP 000)?
│   │   → references/chatgpt-codex-tls-diagnosis.md — effective profile + actual target-domain route + candidate-node comparison
│   ├── Need to fix Hermes adapter for unstable proxy TLS? → references/adapter-keepalive-fix.md
│   ├── Node label says "USA-Boston" but `colo=NRT`? Geo discrepancy?
│   │   → references/domain-based-routing-detection.md — domain-based splitting, ipquality.sh
│   └── "Which command to X?" → references/cli-cheatsheet.md
└── NO → General networking? → Don't load
```

## 🔗 与 `unifi-ops` / `openwrt-router` 的交叉引用

本 skill 管理代理网关层（Surge for Mac, <internal IP redacted>），`unifi-ops` 管理物理网络层（AP/交换机/Controller），`openwrt-router` 管理 OpenWrt/iStoreOS 路由器层（WAN/LAN、DHCP、DNSMasq、NAT/firewall、UCI/opkg）。三者互补：

| 场景 | 先用 | 原因 |
|------|------|------|
| Surge 显示断网但 WiFi 信号正常 | unifi-ops | 可能是 AP 故障/信道干扰/固件问题 |
| 特定区域 WiFi 信号弱 | unifi-ops | 查 AP satisfaction + 信道利用率 |
| 设备物理位置定位 | unifi-ops | 查该设备连到哪个 AP |
| 新设备接入识别（MAC OUI） | unifi-ops | UniFi Controller 有完整设备清单 |
| 上传带宽跑满 | unifi-ops | 交换机端口流量统计 |
| 默认网关/DHCP/NAT/firewall 异常 | openwrt-router | Surge 位于代理层，不能修路由器底层服务 |
| LuCI/Dropbear/opkg/iStoreOS 插件问题 | openwrt-router | OpenWrt/iStoreOS 系统与包管理 |
| 设备无法联网（全链路） | unifi-ops → openwrt-router → surge-gateway | 先物理关联，再 DHCP/网关，最后代理规则 |

> Surge 网关 IP <internal IP redacted>，OpenWrt/iStoreOS 网关常见 IP <internal IP redacted>，Controller IP <internal IP redacted>

## Context

The user's **Surge for Mac is the household network gateway**. Actions may affect the whole family's internet access — treat it as a high-impact control plane.

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
```

The binary is bundled inside Surge.app and not necessarily on `PATH`. Always call by absolute path.

Config locations (check both — user may use iCloud sync):
- Local: `~/Library/Application Support/Surge/Profiles/mine.conf`
- iCloud: `~/Library/Mobile Documents/iCloud~com~nssurge~inc/Documents/*.conf`

When the active config isn't in the expected location, search: `find ~/Library/Mobile\ Documents -name "*.conf"`

> **Surge.app built-in skill**: Surge for Mac ships its own agent skill at `/Applications/Surge.app/Contents/Resources/Skills/surge/` (including `/Applications/Surge.app/Contents/Resources/Skills/surge/SKILL.md`, `/Applications/Surge.app/Contents/Resources/Skills/surge/references/command-reference.md`, and `/Applications/Surge.app/Contents/Resources/Skills/surge/agents/openai.yaml`). The `agents/openai.yaml` defines Surge's native OpenAI-compatible agent interface. This skill (`surge-gateway`) is the household-gateway-specific superset — it extends the built-in command reference with safety posture, device inventory, config auditing, and domain-specific diagnostic workflows.

## Safety Posture

### Read-only — OK to run

`environment`, `dump` (all types: `active`, `recent`, `request`, `dns`, `traffic`, `policy`, `rule`, `map-remote`, `map-local`, `profile`, `event`, `summary`, `temp-rule`, `virtual-ip-db`, `smart-group-info`, `auto-test-group-result`, `policy-group-sub-policies`, `traffic-stat`, `traffic-stat-host`), `test-network`, `test-policy`, `test-policy-udp`, `test-policy-external-ip`, `test-policy-nat-type`, `test-policy-bandwidth`, `test-group`, `test` (all types: `v4-router`, `dns`, `encrypted-dns`, `external-ip`, `nat-type`), `test-ponte`, `show-policy`, `proxy-runtime-status`, `retrieve-data`, `external-resource list`, `get-resource`, `watch`, `diagnostics`, `stop-diagnostics`

### Mutation — explain impact first, DO NOT execute until user confirms

`flush dns`, `reload`, `switch-profile`, `set`, `set-log-level`, `kill`, `external-resource update`, `test-all-policies`, `add-temp-rule`, `del-temp-rule`, `update-temp-rule`, `flush-temp-rule`

**CRITICAL**: When the user says anything resembling "别改" / "先商量" / "别急着动手" / "我们探讨一下", STOP immediately. Do not edit the config. Discuss the approach and wait for explicit confirmation like "修" / "改吧" / "可以". The user's Surge config is household-critical — even small changes warrant discussion first.

### Dangerous — avoid unless explicitly requested

`stop` — shuts down the household gateway. `update-profile` — edits live profile. `script evaluate` — executes arbitrary JS on the gateway. `unattended-upgrade` — upgrades Surge without supervision.

## Core Workflows

### 0. Refresh device inventory

When using Surge CLI for household network tasks, refresh the inventory unless it's a narrow urgent request where extra reads distract:

```bash
"$SURGE_CLI" dump request --raw > /tmp/surge_requests_latest.json
arp -a > /tmp/arp_a.txt
```

Merge into `~/.hermes/notes/household-network-device-inventory.md`. Don't notify the user just because inventory was refreshed — mention only when relevant.

### 1. "What mode / node is X using?"

1. `environment` → inspect `ProxyMode`, `AllProxyModePolicyNameKey`, `ProxyGroupSelection`
2. If a domain/app is mentioned, `dump request` for recent matching requests → report the matched rule/policy

### 2. "Network is slow / family internet is weird"

1. `test-network` for baseline latency
2. `dump active` for active connections
3. `dump event` for Surge errors
4. Only flush DNS/reload after identifying a likely reason
5. **If DNS-related**: load `references/dns-review.md` for full DNS parameter audit checklist

### 3. "Which node should I use?"

1. `dump policy` to identify candidate policy names/groups
2. Use targeted `test-policy` or `test-group` — NOT `test-all-policies`
3. Summarize latency; don't change policy unless asked
4. **Smart groups caveat**: `update-interval` is LESS critical for `smart` than for `url-test`/`fallback` — Smart groups do real-time dynamic optimization (handshake latency, packet loss, RTT) and adaptive retry. `update-interval` on Smart groups mainly controls periodic re-sync of member lists. Smart groups are designed to self-adapt without it.

### 4. "A site/app is broken"

1. Ask user to reproduce, or use `watch request` briefly to capture
2. `dump request` → find domain, rule, and policy
3. `dump dns` if DNS issue suspected
4. `flush dns` is lower risk than `reload` or profile switching

### 5. Detailed workflows → see references

- **Split routing**: `references/split-routing.md`
- **Wake/SSH to LAN Mac**: `references/lan-access.md`
- **Device identification**: `references/device-inventory-triangulation.md`
- **Full command catalog**: `references/cli-cheatsheet.md`
- **Smart group nuances**: `references/smart-group-nuances.md`

### 6. UDP / video call / real-time traffic issues

When a device behind the Surge gateway has stuttering video calls, game lag, or VoIP dropouts:

1. **Check the UDP fallback setting** in the active profile:
   ```bash
   grep 'udp-policy-not-supported-behaviour' ~/Library/Application\ Support/Surge/Profiles/mine.conf
   ```
   - `reject` → UDP packets silently dropped when proxy doesn't support UDP. This is the **default in many Surge configs** and is a common root cause.
   - `direct` → falls back to direct connection. **Recommended for household gateways.**

2. **If `reject`, change to `direct`:**
   ```bash
   sed -i '' 's/udp-policy-not-supported-behaviour = reject/udp-policy-not-supported-behaviour = direct/' ~/Library/Application\ Support/Surge/Profiles/mine.conf
   "$SURGE_CLI" reload
   ```

3. **Verify the target IP's routing:**
   - If the destination IP matches `GEOIP,CN` → routes to `🎯 全球直连` (DIRECT), UDP is unaffected by the `reject` setting
   - If the destination is foreign → may hit a proxy policy, and UDP gets rejected if node doesn't support it

4. **Check Surge events log** for UDP-related errors:
   ```bash
   "$SURGE_CLI" dump event | python3 -c "import json,sys; [print(e['content']) for e in json.load(sys.stdin)['events'] if 'udp' in str(e).lower() or 'UDP' in str(e).lower()]"
   ```

5. **If UDP rejection is confirmed but not the root cause**, the issue is likely server-side throttling (WeChat, TikTok, etc. rate-limit UDP uploads).

**Key insight:** Even if the current target routes to DIRECT, keep `direct` as the fallback — any future rule change that routes a UDP service through a proxy would silently break with `reject`.

### 7. Multi-region API testing via proxy switching

When diagnosing an API outage — especially for Cloudflare-proxied services — use Surge's proxy groups to test from different geographic regions. Different CF edges returning the same error = global origin outage. Different edges returning different results = regional issue.

1. **List available proxy groups** with geographic diversity (`environment` → `ProxyGroupSelection`)
2. **Switch the catch-all group** (`🐟 漏网之鱼`) to a specific region:
   ```bash
   "$SURGE_CLI" set "ProxyGroupSelection.🐟 漏网之鱼=🇭🇰 香港节点"
   sleep 2
   ```
3. **Test the target API** and capture `CF-RAY` header to identify which edge handled the request:
   ```bash
   curl -s -D - -o /dev/null --http1.1 --connect-timeout 10 --max-time 15 \
     "https://api.target.com/health" 2>&1 | grep -iE 'HTTP/|cf-ray'
   ```
4. **Check CF-RAY suffixes**: `-HKG` (Hong Kong), `-LAX` (Los Angeles), `-NRT` (Tokyo). Different suffixes = independent edge tests.
5. **Key diagnostic signals**: `cfOrigin;dur=0` → origin unreachable. POST 400 + GET 404 → edge processes, origin dead. Marketing site 200 + API 404 → CDN healthy, API-specific outage.
6. **Restore routing**: `"$SURGE_CLI" set "ProxyGroupSelection.🐟 漏网之鱼=🚀 节点选择1"`

Full workflow with edge location table and example: `references/multi-region-api-testing.md`.

### 8. Config Audit ("review my Surge config")

When the user asks to review their Surge configuration for issues:

1. Read `~/Library/Application Support/Surge/Profiles/mine.conf`
2. Scan for: duplicate RULE-SETs, aggressive `test-timeout`, `proxy-test-url` using Google (prefer `http://cp.cloudflare.com/`), smart group `update-interval=0`, missing RULE-SET for existing policy groups, `external-controller-access` on `0.0.0.0`
3. Report findings with severity (🔴 fix now / 🟡 consider / ⚪ note)
4. Do NOT edit the config unless the user explicitly asks

Full checklist: `references/config-audit-checklist.md`

### 9. Intermittent API TLS Failures (Cloudflare Rate-Limiting)

When an API behind Cloudflare intermittently times out through the proxy (sometimes works, sometimes doesn't):

**Key diagnostic signal**: first connection after a pause succeeds, subsequent rapid connections hang during TLS handshake. `time_connect=0` on failures.

1. **Confirm direct connectivity**: test with `--noproxy '*'` — if direct works 100%, the proxy is the bottleneck
2. **Measure proxy failure rate**: 5 sequential requests with 2s gaps → >50% HTTP 000 = Cloudflare rate-limiting
3. **Rule out node-specific issues**: switch proxy nodes and retest — if failure rate unchanged, it's the provider's IP range, not a single node
4. **Rule out token/auth**: if some requests return 4xx (not 000), the issue is auth, not TLS
5. **Fix**: add a `DOMAIN-SUFFIX,<domain>,DIRECT` rule for the affected endpoint

Full diagnostic workflow and case study: `references/cloudflare-tls-rate-limiting.md`.

### 10. ChatGPT/Codex OAuth TLS failures

When `chatgpt.com/backend-api/codex`, `hermes auth add openai-codex`, or ChatGPT endpoints fail with `SSL_ERROR_SYSCALL`, `UNEXPECTED_EOF`, or HTTP `000` through Surge:

1. **Do not use generic IP checkers as proof of target exit.** `ipinfo.io`/`ifconfig.me` may route through a different policy than `chatgpt.com`.
2. **Read the live effective profile, not just local `mine.conf`:** `dump profile effective` may include remote `policy-path` groups missing from the local base file.
3. **Use target-domain evidence:** test `https://chatgpt.com/cdn-cgi/trace` and inspect `dump request --raw` notes for `Policy decision path`, `policyName`, `remoteAddress`, `outBytes/inBytes`, and TLS/socket timing.
4. **Separate proxy TLS from target TLS:** `Proxy TLS handshake completed` only proves Surge reached the proxy server; `outBytes > 0` and `inBytes = 0` to `chatgpt.com` means target TLS is hung/dropped.
5. **Compare candidate nodes against `chatgpt.com` itself** (DIP 08/09, Akamai, etc.). DIP is not automatically superior; Akamai may work when DIP is dropped by Cloudflare.
6. **Respect mutation safety:** switching `ProxyGroupSelection.*` for tests is a mutation — ask for explicit confirmation and restore the original selection afterward.

Full case study and command sequence: `references/chatgpt-codex-tls-diagnosis.md`.

### 11. Game Download Speed Diagnosis

When game downloads (Steam, Epic, Battle.net) are slow:

1. `environment` → check the platform's policy group routing
2. `dump active` → find the CDN domain (e.g. `cache11-hkg1.steamcontent.com`)
3. `nslookup` → check if DNS resolves to Surge fake-IP (`198.18.x.x`) or real IP
4. Speed test to the CDN vs. general bandwidth (speedtest)
5. Cross-reference CDN location with routing: China + DIRECT = fast; overseas + DIRECT = slow (throttled)
6. Fix is usually client-side (download region setting), not Surge config

Full diagnostic workflow: `references/game-download-speed-diagnosis.md`

## References

| File | When to read |
|------|-------------|
| `references/cli-cheatsheet.md` | Need to find the right command or understand output |
| `references/device-inventory-triangulation.md` | Identifying household devices by IP/MAC/traffic |
| `references/lan-access.md` | Waking or SSH-ing into a household Mac |
| `references/split-routing.md` | Configuring different routes for similar domains |
| `references/multi-region-api-testing.md` | Testing API reachability from different geographic regions via proxy switching |
| `references/dns-review.md` | Auditing Surge DNS config (DoH, Host rules, leak prevention) |
| `references/config-audit-checklist.md` | Reviewing a Surge config for issues (duplicates, timeouts, missing rules) |
| `references/game-download-speed-diagnosis.md` | Diagnosing slow game downloads (Steam CDN selection vs routing) |
| `references/app-cdn-routing-diagnosis.md` | App download/transfer slow — geo-locate CDN IPs, compare direct vs proxy bandwidth, determine if routing is the bottleneck (WeChat, DingTalk, etc.) |
| `references/tls-connectivity-diagnostics.md` | Testing TLS handshake reliability across proxy regions — multi-round sweep methodology, root cause determination, Cloudflare rate-limit patterns |
| `references/cloudflare-tls-throttling.md` | Diagnosing intermittent TLS handshake timeouts through proxy (Cloudflare DDoS throttling of proxy exit IPs) |
| `references/smart-group-nuances.md` | Understanding Smart group behavior vs url-test/fallback, `update-interval` impact |
| `references/cloudflare-tls-rate-limiting.md` | API intermittently times out through proxy — Cloudflare rate-limiting proxy exit IPs |
| `references/chatgpt-codex-tls-diagnosis.md` | ChatGPT/Codex OAuth TLS failures — verify effective profile, real policy path, target-domain exit, DIP vs Akamai candidates |
| `references/adapter-keepalive-fix.md` | Fixing Hermes adapter layer for TLS-unstable proxy paths — reduce connect timeout, extend keepalive, enable HTTP/2 |
| `references/domain-based-routing-detection.md` | Detecting domain-based traffic splitting on nodes — test against target domain, ipquality.sh for geo assessment, colo vs physical location |
| `references/cross-skill-unifi.md` | When to escalate from Surge to UniFi layer: AP/signal issue, switch port mapping, device MAC OUI via Controller |
| `references/cross-skill-openwrt.md` | When to escalate from Surge to OpenWrt/iStoreOS router layer: DHCP/DNSMasq/NAT/firewall/LuCI/opkg |

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I check safety classification before running any command?
- [ ] Did I use read-only commands first before any mutation?
- [ ] Did I explain impact before `set`/`reload`/`switch-profile`?
- [ ] Did I refresh device inventory when relevant to the task?
- [ ] Did I use targeted `test-policy`/`test-group` instead of `test-all-policies`?
- [ ] 🔴 **Before reporting a config/RULE-SET issue based on `dump event`**: did I cross-reference with the actual config file and test the URLs? Event logs are historical — the current config may have already been fixed.
- [ ] 🔴 **Verifying node exit IP**: Did I use `curl -x proxy + ipinfo.io` to check a node's exit IP? **This is unreliable when Surge has domain-based rules.** `ipinfo.io` traffic may match a different rule than the target domain under investigation. If the target (e.g., `chatgpt.com`) routes through `✴️ Ai → DIP` but `ipinfo.io` matches `🐟 漏网之鱼 → shared proxy`, the reported IP is from the wrong node. **Correct method**: check `dump request --raw` or `dump active` for the ACTUAL domain's `OutboundIP`, or test the target domain itself and read `CF-RAY` / response headers for geo/colo info. For a full guide on detecting domain-based routing and verifying actual exit colocation: `references/domain-based-routing-detection.md`.
- [ ] 🔴 **Before saying a group/rule is missing**: did I check `dump profile effective`, not just local `mine.conf`? Remote `policy-path` groups can exist only in the effective profile.
- [ ] 🔴 **Before recommending DIP/shared/Akamai**: did I test each candidate against the ACTUAL target domain (`chatgpt.com`/Codex), and separate proxy-layer TLS success from target-domain TLS success?

### 🧠 Smart Group Detection Blind Spot

Smart groups use the configured `proxy-test-url` (commonly `http://cp.cloudflare.com/` on port 80) for health checks. This probe CANNOT detect TLS-level (port 443) drops from specific Cloudflare-protected endpoints like `chatgpt.com`. A smart group can route traffic to a node that passes the health probe but drops TLS Client Hello for the actual target service — causing intermittent timeouts while the group believes the node is healthy.

**Symptoms**: ~41-59% success rate across all nodes, random per-request, same node alternates between fast connect (<1ms) and 12-15s TLS timeout. No single node is consistently "bad."

**Diagnosis** (from 2026-06-04 GPT-5.5 investigation):
- 8 Surge regions tested, 39 total trials, 59% overall success
- All nodes showed random TLS failures, none >75% reliable
- Direct connection (no proxy) 100% successful — confirms it's Cloudflare dropping proxy-exit-IP TLS
- Smart group `🇺🇲 美国节点` rotated through ≥7 leaf nodes in 7 min; Seattle 08 had 4/4 consecutive failures then recovered

**Mitigations**: (1) route affected domain through a `select` group with a known-good node instead of `smart`; (2) change `proxy-test-url` to test HTTPS to the actual target; (3) reduce smart group candidate pool to minimize rotation across unknown-quality nodes; (4) apply adapter-layer keepalive fix — see `references/adapter-keepalive-fix.md`; (5) **use a Dedicated IP (DIP) node** — all shared proxy exit IPs (whether smart-rotated or fixed-select) suffer Cloudflare TLS throttling (15-59% success); a DIP node provides a dedicated exit IP with sub-400ms SSL latency when working (verified 2026-06-04, 8/8).

**⚠️ DIP is NOT immune to Cloudflare blocking**: Datacenter DIPs (e.g., Akari Networks in Singapore, sold as "USA-Boston") can still be intermittently blocked by Cloudflare's ChatGPT/Codex endpoints. Observed 2026-06-11: Seattle 08 DIP had 5/5 consecutive `SSL_ERROR_SYSCALL` failures, recovered after node switch + switch-back (typical temporary block window ~minutes). Unlike shared IPs that suffer perpetual partial throttling (40-60%), DIPs face binary intermittent blocks: they work 100% or 0% for the duration of the block window. Mitigation: maintain ≥2 DIP nodes in the select group for failover.

**⚠️ Fixed shared IP is not a fix**: Switching from smart group to a fixed shared-IP node (e.g., `🇺🇸 USA Seattle 03` at 15%, `LA 01` at 40%) does NOT solve the problem — only DIP does. Shared IP = shared Cloudflare throttling bucket regardless of routing mechanism.

**⚠️ OAuth auth is especially vulnerable**: `hermes auth add openai-codex` uses bare `httpx.Client(timeout=15.0)` without keepalive, proxy awareness, or HTTP/2. Each OAuth polling request independently risks TLS drops — with 40% per-poll success and 5-10 polls, total auth success probability is near zero on shared IPs. Always set up DIP before running `hermes auth add` for codex providers, or retry in a loop (16 attempts observed before one reached polling stage).

**Detecting intermittent node failures with `test-policy`**:
Single `test-policy` runs can miss transient failures. Run 4+ consecutive tests per candidate to catch intermittent issues:
```bash
# Test each candidate 4 times in a row
for node in "USA Seattle 03" "USA Seattle 07" "USA Seattle 08" "USA Los Angeles 01"; do
  echo "=== $node ==="
  for i in 1 2 3 4; do
    surge-cli test-policy "$node" 2>&1 | grep -E "RTT|Total|Failed|Error"
  done
done
```
Nodes that pass once but fail in subsequent rounds are prone to intermittent TLS drops and should not be used as fixed-node candidates.

## 🩺 Common Config Issues (audit checklist)

When reviewing any Surge config, scan for these recurring problems:

| Issue | Fix |
|-------|-----|
| `udp-policy-not-supported-behaviour = reject` (or missing) | Set to `direct` |
| `test-timeout = 2` | Bump to `4` (2s too aggressive, false negatives) |
| `proxy-test-url = http://connectivitycheck.gstatic.com/...` | Replace with `http://cp.cloudflare.com/` (more universally reachable) |
| `smart` groups with `update-interval=0` | Set to `3600` (hourly member re-eval; less critical for Smart than url-test but still useful) |
| Duplicate `RULE-SET` lines (identical or old+new URL) | Keep the `refs/heads/master` version; delete old |
| `dns-server` includes `8.8.8.8` | Remove — unreliable from China |
| Missing `encrypted-dns-follow-outbound-mode = true` | Add if using DoH (Surge v5+ renamed from `doh-follow-outbound-mode`) |
| Stale Host rules (e.g., `cloudflare-dns.com = server:1.1.1.1`) | Remove if no longer using that DoH provider |
| Using old DoH param names (`doh-follow-outbound-mode`, `doh-server`) | Rename to `encrypted-dns-follow-outbound-mode`, `encrypted-dns-server` (Surge v5+) |
| `domain-set:` used directly in `encrypted-dns-server` line | Use `[Host]` section: `DOMAIN-SET:<url> = server:<doh-url>` (per manual.nssurge.com) |
| `dns-server` includes `system` | Consider explicit DNS servers for predictability |
| RULE-SET URL uses `github.com/.../blob/...` instead of `raw.githubusercontent.com/...` | GitHub web UI pages return HTML, not rule content → RULE-SET silently loads empty. Replace `github.com` with `raw.githubusercontent.com` and remove `/blob` from path. Example: `https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/AI.list`. **Silent failure** — Surge won't error, rules just don't match. Check with `dump profile effective` → grep the RULE-SET URL → verify it starts with `raw.githubusercontent.com`. |

For full DNS audit workflow, see `references/dns-review.md`.
- [ ] Did I use targeted `test-policy`/`test-group` instead of `test-all-policies`?

---

## 🔄 Deployment & Sync

**Local:** `~/.hermes/skills/devops/surge-gateway/`
**GitHub:** `jz-skills/hermes/surge-gateway/`
**Sync:** `deploy/sync-all.sh` (forward) + `deploy/sync-back.sh` (reverse)

**⚠️ sync-back.sh HOME-override pitfall**: When running under a Hermes profile with `$HOME` redirected (e.g., `~/.hermes/profiles/regent/home`), `sync-back.sh` resolves `$HERMES_BASE` to the profile's home, not the real macOS home. This causes it to read from an empty/wrong source directory, silently **deleting files from the repo** that exist in the real shared pool but not the profile-local snapshot. Unlike `sync-all.sh` which uses `REAL_HOME`, `sync-back.sh` uses bare `$HOME`. **Mitigation**: after running sync-back from a profile session, always `git diff --stat` to verify no files were deleted. If deletions occurred: `git checkout HEAD -- <skill-dir>/` to restore. This is a known bug in `sync-back.sh` — fix by adding `REAL_HOME` resolution (same as `sync-all.sh`).

**Profiles consuming this skill:**
- `default` (小黄) — primary household assistant
- `regent` — multi-profile governance profile
- `gongbu` (工部) — infrastructure & devops owner
