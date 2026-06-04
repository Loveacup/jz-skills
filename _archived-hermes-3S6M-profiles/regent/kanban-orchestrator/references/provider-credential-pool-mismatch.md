# Provider / Credential Pool Mismatch

Session reference: 2026-05-18, multi-agent Kanban workflow debugging.

## Symptom

Kanban worker crashes immediately on startup with:
```
Provider resolver returned an empty API key. Set OPENROUTER_API_KEY or run: hermes setup
```

Or the worker log shows a completely different provider than what the config specifies:
```
🔌 Provider: openai-codex  Model: gpt-5.5
```

Even though `config.yaml` says:
```yaml
model:
  default: kimi-k2.6
  provider: moonshot
```

## Root cause

Hermes resolves the runtime provider through a credential pool lookup. If `config.provider = "moonshot"` but the credential pool has **zero entries for "moonshot"**, Hermes falls back to whichever provider *does* have a pooled credential. In this case, `openai-codex` had an entry (from a previous OAuth login), so the worker silently switched to it — and then hit the rate limit.

The `moonshot` and `kimi-coding` provider slugs are **not interchangeable** for credential-pool purposes. They have separate pools even though both route to Moonshot's API.

## Diagnostic steps

1. Check what the config thinks the provider is:
   ```bash
   hermes -p <profile> config | grep -A3 "^model:"
   ```

2. Check what credentials actually exist for that provider:
   ```bash
   hermes auth list <provider>
   # e.g. hermes auth list moonshot
   ```

3. Check all providers with entries in the pool:
   ```bash
   python3 -c "
   from hermes_cli.auth import read_credential_pool
   import json
   # read_credential_pool without arg returns all, but the API varies by version
   # Safer: check auth.json directly
   import json, os
   auth_path = os.path.expanduser('~/.hermes/auth.json')
   if os.path.exists(auth_path):
       with open(auth_path) as f:
           data = json.load(f)
       pool = data.get('credential_pool', {})
       print('Providers with credentials:', list(pool.keys()))
   "
   ```

## Fix

Option A — change config to match the provider that has credentials:
```bash
hermes config set model.provider kimi-coding
```

Option B — add credentials for the configured provider:
```bash
hermes auth add
# or edit ~/.hermes/.env and add KIMI_API_KEY=...
```

Option C — if using profile-scoped configs, ensure the profile's config and its credential pool are consistent:
```bash
hermes -p <profile> config set model.provider <provider-with-creds>
```

## Format mismatch error signature (NEW — 2026-05-18)

When a profile is configured with an Anthropic-format model (e.g. `claude-opus-4-7`) but the provider API endpoint expects OpenAI-format messages, the crash error is distinctive:

```
⚠️  API call failed (attempt 1/3): BadRequestError [HTTP 400]
   🔌 Provider: custom  Model: claude-opus-4-7
   🌐 Endpoint: https://api.oaipro.com/v1
   📝 Error: HTTP 400: messages.5.content.0.text.text: Field required
```

The key diagnostic phrase is **`messages.X.content.0.text.text: Field required`** — this means the API received an Anthropic-format `content` block (array of `{type: "text", text: "..."}`) but expects OpenAI format (`"content": "string"`). This is NOT a credential or quota issue; it's a model-provider format incompatibility.

**Root cause:** The profile config pairs a model designed for the Anthropic Messages API with an OpenAI-compatible provider endpoint. The provider slug (e.g. `custom:oaipro`) routes to an OpenAI-format endpoint, but the model name triggers Anthropic-format request construction.

**Fix:** Switch either the model or the provider so they're format-compatible:
- If you want the model: switch provider to one that speaks Anthropic Messages API
- If you want the provider: switch model to one the provider supports (e.g. any OpenAI-format model)

In the 三省六部 planner case, the fix was:
```yaml
# Before (WRONG — Anthropic model on OpenAI endpoint)
model:
  default: claude-opus-4-7
  provider: custom:oaipro

# After (CORRECT — kimi-k2.6 on its native provider)
model:
  default: kimi-k2.6
  provider: kimi-coding
```

After fixing the config, `kanban unblock` + `kanban dispatch` to retry.

## Prevention

- Before creating Kanban tasks, verify the target profile's provider has credentials
- When switching models via `hermes model` or `hermes config set`, the setup wizard usually warns about missing credentials — pay attention
- If a provider name is ambiguous (e.g. `moonshot` vs `kimi-coding`), check which one your credential was stored under
- **Format check:** If the model name starts with `claude-*`, the provider MUST speak the Anthropic Messages API — not an OpenAI-compatible proxy. The `HTTP 400: Field required` error is the telltale signature of this mismatch.
