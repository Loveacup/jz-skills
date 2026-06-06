# Desensitization Audit — Comprehensive Methodology

> Use when: auditing a repo (especially `jz-skills`) for sensitive data before making it public, after a sync-back, or before a push. This is the manual complement to `sync-back.sh`'s automated sanitization.

## sync-back.sh Coverage (What's Auto-Handled)

| Pattern | Sanitized? | Mechanism |
|---------|-----------|-----------|
| `$HOME/` → `~/` | ✅ | `awk` gsub |
| Emails | ✅ | `sed` regex |
| Private IPs (`192.168.x`, `10.x`, `172.16-31.x`) | ✅ | `sed` regex |
| API keys (`gho_`, `sk-`, `sk-ant-`, `hf_`) | ✅ | `sed` regex |
| `ENV_VAR=value` style secrets | ✅ | `sed` regex |

## sync-back.sh Blind Spots (Requires Manual Audit)

| Pattern sync-back.sh MISSES | Real-world example | Why missed |
|------------------------------|-------------------|------------|
| **Obsidian vault names** | `~/Documents/Obsidian/AlexCai/` | Contains real name, regex only strips `$HOME/` not subpaths |
| **Personal names in content** | `Alex Cai` in PDF footer, `AlexCai` as TTS voice | Email regex catches `@` patterns only |
| **Cron job IDs** | `1ca6e7d692fa`, `458bec58ee72` | Not in any regex |
| **App instance/bundle IDs** | `5ZSL2CJU2T.com.dingtalk.mac` + instance `c42eb52018ab1e103951_v3` | Not in any regex |
| **Local service ports** | Surge `6152`, SearXNG `32080`, TTS `8088` | `127.0.0.1` not matched (not private-range IP) |
| **Hardcoded usernames in scripts** | `~/...` in `.sh` files | Not run through sync-back? Or committed before sanitize |

## Full Audit Checklist (28 Patterns)

Run these in order. Exit code 0 + no output = clean.

### 1. Credential files
```bash
find . -name ".env" -o -name "*.pem" -o -name "*.key" -o -name "credentials*" -o -name "id_rsa*" | grep -v '.git/'
```

### 2. API keys / tokens (known prefixes)
```bash
rg -n --no-heading -g '!/.git/' '(ghp_|gho_|ghu_|ghs_|ghr_|xox[bprs]-|sk-[A-Za-z0-9]{20,}|sk-ant-|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z\-_]{35})' .
```

### 3. Generic secret patterns
```bash
rg -n --no-heading -g '!/.git/' '(api_key|apikey|api_secret|secret_key|access_token|auth_token|private_key|client_secret)\s*[=:]\s*[\x27\x22]?[A-Za-z0-9_\-]{16,}' .
```

### 4. Private IPs (RFC 1918)
```bash
rg -n --no-heading -g '!/.git/' '(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})' .
```

### 5. All IP addresses (broader)
```bash
rg -n --no-heading -g '!/.git/' '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' . | grep -v '0\.0\.0\.0\|127\.0\.0\.1\|255\.255\|\.git/'
```
Filter out false positives: User-Agent strings, version numbers.

### 6. Personal emails
```bash
rg -n --no-heading -g '!/.git/' '[a-zA-Z0-9._%+-]+@(foxmail|qq|gmail|163|126|outlook|hotmail|proton|icloud|me)\.[a-z]+' .
```

### 7. Phone numbers (Chinese mobile)
```bash
rg -n --no-heading -g '!/.git/' '1[3-9]\d{9}' .
```
Filter out false positives: Unix timestamps, fingerprint hashes.

### 8. SSH keys
```bash
rg -n --no-heading -g '!/.git/' '(-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----|ssh-rsa AAAA|ssh-ed25519 AAAA|ecdsa-sha2)' .
```

### 9. Password patterns
```bash
rg -in --no-heading -g '!/.git/' '(password|passwd|pwd)\s*[=:]\s*[\x27\x22][^\x27\x22]{4,}[\x27\x22]' .
```

### 10. AWS / cloud credentials
```bash
rg -n --no-heading -g '!/.git/' '(AKIA[0-9A-Z]{16}|aws_access_key|aws_secret|GCP_|AZURE_|ALIBABA_CLOUD)' .
```

### 11. Internal hostnames / LAN domains
```bash
rg -n --no-heading -g '!/.git/' '(\.local|\.lan|\.internal|\.home)' .
```

### 12. Platform-specific tokens (WeChat, DingTalk, Surge)
```bash
rg -in --no-heading -g '!/.git/' -g '*.{md,py,sh,yaml,json}' '(wxid_|dd_sid|cookie.*token|surge.*key|authorization.*Bearer)' . | grep -v 'references/' | grep -v 'templates/'
```
Look for actual values, not procedural instructions about how to use them.

### 13. Home directory paths with usernames
```bash
rg -n --no-heading -g '!/.git/' '/Users/[a-z]+' . | grep -v 'references/' | grep -v 'templates/'
```

### 14. Obsidian vault paths (contains real name)
```bash
rg -n --no-heading -g '!/.git/' 'Obsidian/[A-Z][a-z]+' .
```

### 15. Personal names in content
```bash
rg -n --no-heading -g '!/.git/' -i '<firstname> <lastname>' .
```
Customize per user.

### 16. Webhook / callback URLs with tokens
```bash
rg -n --no-heading -g '!/.git/' '(discord\.com/api/webhooks|oapi\.dingtalk|qyapi\.weixin|api\.telegram\.org/bot[0-9]+:[A-Za-z0-9_-]+)' .
```

### 17. Telegram bot tokens
```bash
rg -n --no-heading -g '!/.git/' 'bot[0-9]+:[A-Za-z0-9_-]{30,}' .
```

### 18. Database connection strings
```bash
rg -n --no-heading -g '!/.git/' '(mysql://|postgres://|mongodb://|redis://|DATABASE_URL|DB_PASSWORD|connectionString)' .
```

### 19. Container registry credentials
```bash
rg -n --no-heading -g '!/.git/' '(docker.io|ghcr.io.*:.*@|DOCKER_REGISTRY|kubeconfig)' .
```

### 20. Config files that shouldn't be committed
```bash
find . -name "*.json" -o -name "*.yaml" -o -name "*.toml" -o -name "*.ini" | grep -v '.git/' | grep -v 'templates/' | grep -v 'references/' | grep -v 'schemas/'
```
Review each file for hardcoded credentials, job IDs, or infrastructure details.

### 21. Surge / gateway configurations
```bash
rg -n --no-heading -g '!/.git/' -g '*.{md,py,sh,json,yaml}' '(surge.*proxy|surge.*policy|gateway.*token|:6152|:32080|:8088)' . | grep -v 'references/'
```

### 22. Crypto / signing keys (reverse-engineered)
```bash
rg -n --no-heading -g '!/.git/' '(DES_KEY|HEX_KEY|SECRET_KEY|SIGNING_KEY|B1_SECRET)' .
```
These are usually from reverse-engineered web clients (public knowledge) but flag for review.

### 23. Git history for removed secrets
```bash
git log -p --all -S 'gho_' --oneline | head -30
git log -p --all -S 'sk-' --oneline | head -30
```
Also check: `git log --all --oneline` for any commits that mention "remove secret" or "sanitize".

### 24. Hardcoded cron job IDs
```bash
rg -n --no-heading -g '!/.git/' '[0-9a-f]{12}' . | grep -v '.git/' | grep -v '__pycache__'
```
Filter for known job ID patterns. Hermes cron IDs are 12-char hex.

### 25. README stale sections
Check if README still references archived/deprecated content (e.g., 三省六部 after archiving).

### 26. Sync scripts consistency
Verify `deploy/sync-all.sh` and `deploy/sync-back.sh` both reference the same skill set. Missing entries in either = broken sync.

### 27. Sensitive data in templates/ and scripts/ (not just SKILL.md)
These directories often contain hardcoded paths and configuration that the main skill file abstracts away.

### 28. Profile-specific artifacts
Check for profile names, lane configurations, internal architecture names that shouldn't be public.

## Triage Matrix

| Severity | Pattern | Action |
|----------|---------|--------|
| 🔴 Critical | API keys, tokens, passwords, SSH keys in plaintext | Remove immediately, rotate if ever pushed |
| 🟠 High | Home paths with username, vault names with real name, personal emails, phone numbers | Replace with `~/` or `<redacted>` |
| 🟡 Medium | Cron job IDs, internal ports, app instance IDs, infrastructure details | Consider redacting; job IDs allow manipulation if combined with API access |
| 🟢 Low | Reverse-engineered crypto constants (from public web clients), public image references | Document but no action needed |
| ⚪ Informational | README stale sections, sync script gaps | Fix in separate cleanup commit |

## Post-Audit: Fixes

1. **Path sanitization**: Replace `/Users/<name>/` with `~/` in all files
2. **Name redaction**: Replace personal names with `<author>` or a chosen pseudonym
3. **Port removal**: Replace local service ports with `<port>` or use env vars
4. **Instance ID removal**: Replace DingTalk bundle IDs with `<bundle-id>`
5. **For `sync-back.sh` blind spots**: Add custom sed patterns or manually review before commit
6. **For git history leaks**: Use `git filter-branch` or `BFG Repo-Cleaner` if secrets were ever pushed
