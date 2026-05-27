# Surge for Mac CLI cheatsheet

## Location

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
```

Use the absolute path because the CLI is bundled inside Surge.app and may not be on `PATH`.

## Read-only inspection

- `environment` — current runtime environment, proxy mode, feature switches, policy-group selections.
- `dump policy` — available policies/proxies and policy groups.
- `dump request` — recent request history; useful for “which rule/policy did this app/domain use?”
- `dump active` — currently active connections; useful for bandwidth/connection diagnosis.
- `dump dns` — DNS cache.
- `dump rule` — effective rules.
- `dump event` — recent event log.
- `dump profile original` — configured profile before modules/effective transformations.
- `dump profile effective` — effective profile after modules.
- `test-network` — baseline DNS/network latency.

Most `dump` commands support `--raw` for JSON-like output:

```bash
"$SURGE_CLI" dump request --raw
```

## Active diagnostics

- `watch request` — realtime request tracing. Use briefly; stop after collecting evidence.
- `test-policy <policy-name>` — test one proxy/policy.
- `test-group <group-name>` — retest a policy group.
- `test-all-policies` — broad test; can be noisy/slow.
- `diagnostics` — Surge network diagnostics.

## Maintenance / mutation

- `flush dns` — clear Surge DNS cache. Lower risk than reload/profile switching, but still affects current resolution.
- `reload` — reload main profile; can disrupt routing if config has issues.
- `switch-profile <profile-name>` — switch active profile; high impact.
- `set <key-path> <value>` — modify runtime environment; high impact if policy selections are changed.
- `external-resource list` — list external resources.
- `external-resource update <key>` — update one subscription/ruleset.
- `external-resource update all` — update all external resources; can introduce upstream breakage.
- `kill <connection-id>` — terminate one active connection.
- `stop` — shuts down Surge; avoid unless explicitly requested because this Surge is the household gateway.

## Output interpretation notes

- `ProxyMode` in `environment` indicates the running mode. Report the value and surrounding context rather than guessing user-facing labels unless verified.
- `ProxyGroupSelection` maps policy group names to selected policies/nodes. For app-specific questions, check both this map and recent requests.
- If the user asks about a domain/app, prefer evidence from `dump request` over only reading static rules.

## Example safe probe

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" test-network
"$SURGE_CLI" environment
"$SURGE_CLI" dump request --raw
```
