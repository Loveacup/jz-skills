# Split Routing for Similar Domains

Use when the user wants closely related domains routed differently (e.g., `.com` via proxy but `.com.cn` direct).

## Reasoning

Broad `DOMAIN-KEYWORD` rules catch all matching domains — both `.com` and `.com.cn` variants. Use specific `DOMAIN-SUFFIX` rules ordered before any broader match.

## Step-by-step

### 1. Diagnose current state

```bash
SURGE_CLI="/Applications/Surge.app/Contents/Applications/surge-cli"
"$SURGE_CLI" dump rule | grep -i -E 'domain1|domain2'
"$SURGE_CLI" dump profile original > /tmp/surge_profile_original.conf
"$SURGE_CLI" dump profile effective > /tmp/surge_profile_effective.conf
grep -n -i 'domain-keyword-or-suffix' /tmp/surge_profile_original.conf
```

### 2. Read and back up the active profile

Find it by searching for a nearby unique rule string from the effective dump. Make a timestamped backup before editing.

### 3. Replace broad keyword rules with explicit suffix rules

```conf
# International site → proxy, China site → DIRECT
DOMAIN-SUFFIX,example.com.cn,DIRECT
DOMAIN-SUFFIX,assets.example.com.cn,DIRECT
DOMAIN-SUFFIX,example.com,"🇯🇵 自定义日本"
DOMAIN-SUFFIX,assets.example.com,"🇯🇵 自定义日本"
```

⚠️ Order matters: specific `.com.cn` rules must appear BEFORE any broader `.com` match.

### 4. Validate and apply

```bash
"$SURGE_CLI" --check "/path/to/profile.conf"
"$SURGE_CLI" reload
"$SURGE_CLI" dump rule | grep -i -E 'example|assets\.example'
```

### 5. Verify live behavior

Generate a fresh request and confirm the matched rule + policy:

```bash
curl -I -L --max-time 15 https://example.com
# or have the user reload the page
"$SURGE_CLI" dump request --raw | # check policyName and rule fields
```

Report the final matched rule and policy, not just the intended config.
