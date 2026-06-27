# Surge CLI — Full Command Reference

> Partially derived from Surge.app's built-in skill command reference.
> All commands are case-insensitive.

## Invocation

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" [--raw] [--remote password@host:port] <command> [args...]
```

- `--raw`: JSON output (use for every command)
- `--remote` / `-r`: connect to remote Surge instance
- `--check <path>`: validate profile file only
- `--help` / `-h`: print help
- No command → enters interactive mode

## Response Envelope

JSON responses include: `result`, `error`, payload fields. Streaming commands include `hasMore` (true = more chunks follow).

---

## Full Command Catalog

### State Inspection (`dump`)

| Command | Description | Notes |
|---------|-------------|-------|
| `dump active` | Currently active connections | Bandwidth/connection diagnosis |
| `dump recent` | Recent connection history | |
| `dump request` | Recent request log | See which rule/policy matched |
| `dump dns` | DNS cache | |
| `dump traffic` | Traffic statistics | |
| `dump policy` | Available policies + policy groups | |
| `dump rule` | Effective rules | |
| `dump map-remote` | Map remote entries | |
| `dump map-local` | Map local entries | |
| `dump profile` | Profile config (see note) | |
| `dump event` | Recent event log | |
| `dump summary` | Summary statistics | |
| `dump temp-rule` | Temporary rules | |
| `dump virtual-ip-db` | Virtual IP database | |
| `dump smart-group-info` | Smart group info | |
| `dump auto-test-group-result` | Auto test group results | |
| `dump policy-group-sub-policies` | Sub-policy details | |
| `dump traffic-stat [prefix]` | Traffic stats by prefix | Optional prefix filter |
| `dump traffic-stat-host` | Traffic stats by host | |

**Profile display modes:**
```bash
"$SURGE_CLI" dump profile original    # configured profile before modules
"$SURGE_CLI" dump profile effective   # effective profile after modules
```

### Environment

```bash
"$SURGE_CLI" environment              # full runtime environment dictionary
```

Key fields in output: `ProxyMode`, `ProxyGroupSelection`, `AutoPolicyGroupOverride`, `AllProxyModePolicyNameKey`, `MitMEnabled`, `RewriteEnabled`, `ScriptingEnabled`, `Replica`.

### Diagnostics (`test`)

| Command | Description |
|---------|-------------|
| `test v4-router` | IPv4 router test |
| `test dns` | DNS test |
| `test encrypted-dns` | Encrypted DNS test |
| `test external-ip` | External IP probe |
| `test nat-type` | NAT type probe |
| `test-network` | Baseline DNS/network latency |

### Policy Testing

| Command | Args | Description |
|---------|------|-------------|
| `test-policy` | `<policy...>` | Test one or more policies |
| `test-policy-udp` | `<policy...>` | UDP policy test |
| `test-policy-external-ip` | `<policy>` | External IP via policy (STUN) |
| `test-policy-nat-type` | `<policy>` | NAT type via policy (STUN) |
| `test-policy-bandwidth` | `download\|upload <policy>` | Bandwidth test (streaming) |
| `test-group` | `<group-name>` | Retest a policy group |
| `test-all-policies` | none | Retest all policies (noisy) |

### Runtime Mutation (`set`)

```bash
"$SURGE_CLI" set <key-path>=<value> [<key-path>=<value> ...]
```

Multiple pairs allowed in one command. `<nil>` and `(null)` treated as nil.

Key-path behavior:
- `ProxyGroupSelection.<group>` → map merge for select-group decisions
- `AutoPolicyGroupOverride.<group>` → map merge for auto-group overrides
- All others → direct key-path assignment

Top-level keys:

| Key | Type | Values |
|-----|------|--------|
| `ProxyMode` | int | `0`=Direct, `1`=Global Proxy, `2`=Rule |
| `AllProxyModePolicyNameKey` | string | Policy name in global proxy mode |
| `ProxyGroupSelection.<group>` | string | Selected policy for select group |
| `AutoPolicyGroupOverride.<group>` | string/nil | Override for auto group |
| `MitMEnabled` | bool | MITM switch |
| `RewriteEnabled` | bool | Rewrite switch |
| `ScriptingEnabled` | bool | Scripting switch |
| `Replica` | bool | HTTP capture switch |
| `ReplicaSessionParameters.*` | various | Capture session params (see below) |
| `InMemoryCaptureFilter.*` | various | In-memory capture filter |
| `OnDiskCaptureFilter.*` | various | On-disk capture filter |
| `PacketCaptureEnabled` | bool | Packet capture switch |
| `PacketCaptureParameters.*` | various | Packet capture params |
| `SGEnvironmentCellularModeEnabledKey` | bool | Cellular mode |

**Runtime behavior notes:**
- Successful `set` triggers environment-change notifications
- `MitMEnabled=1` auto-corrects to `0` if invalid under current runtime
- In global proxy mode, invalid `AllProxyModePolicyNameKey` falls back to a valid policy or `DIRECT`

**ReplicaSessionParameters fields:**
| Field | Type | Default |
|-------|------|---------|
| `sizeLimit` | int | 52428800 (50MB) |
| `requestCountLimit` | int | 100 |
| `timeLimit` | int (seconds) | 180 |
| `mitmOverride` | bool | 1 |
| `mitmOverrideHostnames` | array | built-in default |
| `mitmOverrideHostnamesDisabled` | array | empty |

**Capture filter fields** (InMemoryCaptureFilter / OnDiskCaptureFilter):
| Field | Type | Values |
|-------|------|--------|
| `httpOnly` | bool | |
| `hideCrashReporterRequest` | bool | default 1 |
| `hideAppleRequest` | bool | |
| `hideUDP` | bool | |
| `filterType` | int | 0=None, 1=Whitelist, 2=Blacklist, 3=Pattern |
| `keywordFilter` | array | keyword list |
| `disabledKeywordFilter` | array | disabled keywords |

### Streaming Commands

For `diagnostics`, `test-policy-bandwidth`, `test-ponte`:
1. Process incremental chunks
2. Respect `hasMore=false` as completion signal
3. Do not assume a single response frame

```bash
"$SURGE_CLI" diagnostics          # start event stream
"$SURGE_CLI" stop-diagnostics     # stop event stream
```

### Realtime Watch

```bash
"$SURGE_CLI" watch [event ...]    # subscribe to events
"$SURGE_CLI" watch                # unsubscribe
```

Available events: `real-time-speed`, `auto-test-group`, `traffic`, `request`, `request-update`, `summary`, `environment`, `dns`, `diagnostics`, `reload`, `shutdown`, `device-name-map`, `policy-benchmark`, `device-info`, `dns-flush`.

### Temporary Rules

```bash
"$SURGE_CLI" add-temp-rule <rule>
"$SURGE_CLI" del-temp-rule <rule>
"$SURGE_CLI" update-temp-rule <rule> <new-policy>
"$SURGE_CLI" flush-temp-rule
```

### Profile & Maintenance

| Command | Description | Impact |
|---------|-------------|--------|
| `reload` | Reload main profile | High — can disrupt routing |
| `switch-profile <name>` | Switch active profile | Very high |
| `flush dns` | Clear DNS cache | Medium — lower risk than reload |
| `kill <connection-id>` | Terminate a connection | Medium |
| `stop` | Shut down Surge | ⚠️ Gateways go offline |
| `unattended-upgrade` | Unattended upgrade | macOS only |
| `proxy-runtime-status <hash>` | Proxy runtime status | |
| `script evaluate <path> [mockType] [timeout] [engine] [arg]` | Evaluate script | CLI reads file, encodes Base64 |
| `get-resource device-icon <id>` | Fetch device icon (Base64) | |

**Script evaluate mock types:** `http-request`, `http-response`, `cron`, `event`, `rule`, `dns`, `generic`
**Script evaluate engines:** `auto`, `jsc`, `webview`

### External Resources

```bash
"$SURGE_CLI" external-resource list
"$SURGE_CLI" external-resource update <hash-key>
"$SURGE_CLI" external-resource update all       # can introduce upstream breakage
```

### Platform-Limited Commands (macOS only)

```bash
# DHCP device management
"$SURGE_CLI" set-dhcp-device <mac> takeover [0|1]
"$SURGE_CLI" set-dhcp-device <mac> disable-udp-fast-path [0|1]
"$SURGE_CLI" set-dhcp-device <mac> address [ipv4]
"$SURGE_CLI" set-dhcp-device <mac> name [display-name]
"$SURGE_CLI" set-dhcp-device <mac> icon [icon-name]

# Device records
"$SURGE_CLI" remove-device-record <identifier>

# Profile editing
"$SURGE_CLI" update-profile <base64-rule-section>

# Data channel
"$SURGE_CLI" retrieve-data <record-id> request|response [replica-dir]
```

### Ponte Diagnostics

```bash
"$SURGE_CLI" test-ponte <device-ponte-name>    # streaming output
```

---

## Safety Classification

### Read-only (safe to run anytime)

`environment`, `dump *` (all sub-types), `test-network`, `test-policy`, `test-group`, `test v4-router`, `test dns`, `test encrypted-dns`, `test external-ip`, `test nat-type`, `show-policy`, `proxy-runtime-status`, `external-resource list`, `get-resource`, `watch`

### Mutation (explain impact first)

`flush dns`, `reload`, `switch-profile`, `set`, `kill`, `external-resource update`, `add-temp-rule`, `del-temp-rule`, `update-temp-rule`, `flush-temp-rule`

### Dangerous (avoid unless explicitly asked)

`stop` — shuts down household gateway. `update-profile` — edits live profile.

---

## Output Interpretation

- `ProxyMode`: `0`=Direct, `1`=Global Proxy, `2`=Rule. Report the value, verify before labeling.
- `ProxyGroupSelection`: maps group names → selected policies. For app-specific questions, check both this AND recent requests.
- For domain/app questions, prefer evidence from `dump request` over static rule reading.
