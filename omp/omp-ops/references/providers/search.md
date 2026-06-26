# OMP Search Providers

Source: `docs/environment-variables.md` section 3 (Web search subsystem).

OMP supports multiple web-search backends. Each provider is selected by setting its auth variable and/or config key. Only set one provider at a time unless you intend fallback behavior.

## Provider matrix

| Provider ID | Required env var(s) | Optional env var(s) / config keys | Validation command |
|---|---|---|---|
| `exa` | `EXA_API_KEY` | none | `curl -s "https://api.exa.ai/search" -H "x-api-key: $EXA_API_KEY" -d '{"query":"test","numResults":1}'` |
| `brave` | `BRAVE_API_KEY` | none | `curl -s "https://api.search.brave.com/res/v1/web/search?q=test&count=1" -H "X-Subscription-Token: $BRAVE_API_KEY"` |
| `tavily` | `TAVILY_API_KEY` | none | `curl -s "https://api.tavily.com/search" -H "content-type: application/json" -d '{"api_key":"'$TAVILY_API_KEY'","query":"test","max_results":1}'` |
| `perplexity` | `PERPLEXITY_API_KEY` (API-key mode) | `PERPLEXITY_COOKIES` (cookie-auth mode) | `curl -s "https://api.perplexity.ai/chat/completions" -H "Authorization: Bearer $PERPLEXITY_API_KEY" -H "Content-Type: application/json" -d '{"model":"sonar","messages":[{"role":"user","content":"hello"}]}'` |
| `searxng` | `SEARXNG_ENDPOINT` (`SEARXNG_TOKEN` optional) | `SEARXNG_BASIC_USERNAME`, `SEARXNG_BASIC_PASSWORD`; or `searxng.endpoint`, `searxng.token`, `searxng.basicUsername`, `searxng.basicPassword` in `config.yml` | `curl -s "$SEARXNG_ENDPOINT/search?q=test&format=json" ${SEARXNG_TOKEN:+-H "Authorization: Bearer $SEARXNG_TOKEN"}` |
| `zai` | `ZAI_API_KEY` | stored OAuth in `agent.db` also accepted | `curl -s "https://api.z.ai/v1/chat/completions" -H "Authorization: Bearer $ZAI_API_KEY" -H "Content-Type: application/json" -d '{"model":"glm-4-flash","messages":[{"role":"user","content":"hello"}]}'` |
| `kagi` | `KAGI_API_KEY` | none | `curl -s "https://kagi.com/api/v0/search?q=test" -H "Authorization: $KAGI_API_KEY"` |
| `jina` | `JINA_API_KEY` | none | `curl -s "https://r.jina.ai/http://example.com" -H "Authorization: Bearer $JINA_API_KEY"` |
| `parallel` | `PARALLEL_API_KEY` | none | `curl -s "https://api.parallel.ai/v1/search" -H "Authorization: Bearer $PARALLEL_API_KEY" -d '{"query":"test"}'` |
| `anthropic-search` | `ANTHROPIC_SEARCH_API_KEY` (optional; falls back to Anthropic auth) | `ANTHROPIC_SEARCH_BASE_URL`, `ANTHROPIC_SEARCH_MODEL` | `curl -s "${ANTHROPIC_SEARCH_BASE_URL:-https://api.anthropic.com}/v1/messages" -H "x-api-key: ${ANTHROPIC_SEARCH_API_KEY:-$ANTHROPIC_API_KEY}" -H "anthropic-version: 2023-06-01" -d '{"model":"'${ANTHROPIC_SEARCH_MODEL:-claude-haiku-4-5}'","max_tokens":1024,"messages":[{"role":"user","content":"hello"}]}'` |
| `codex-search` | `OPENAI_API_KEY` or stored Codex OAuth in `agent.db` | `PI_CODEX_WEB_SEARCH_MODEL` | `curl -s "https://api.openai.com/v1/responses" -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" -d '{"model":"'${PI_CODEX_WEB_SEARCH_MODEL:-gpt-5.3-codex}'","input":"hello"}'` |
| `kimi/moonshot-search` | `MOONSHOT_SEARCH_API_KEY` or `KIMI_SEARCH_API_KEY` | `MOONSHOT_SEARCH_BASE_URL`, `KIMI_SEARCH_BASE_URL` | `curl -s "${MOONSHOT_SEARCH_BASE_URL:-https://api.moonshot.cn/v1}/chat/completions" -H "Authorization: Bearer ${MOONSHOT_SEARCH_API_KEY:-$KIMI_SEARCH_API_KEY}" -H "Content-Type: application/json" -d '{"model":"moonshot-v1-8k","messages":[{"role":"user","content":"hello"}]}'` |

## Notes

- Validation command endpoints and model names are examples. Confirm the exact
  endpoint against the provider's current API documentation before relying on
  them in automation.
- SearXNG reads both environment variables and equivalent `config.yml` settings under the `searxng` key. Environment variables are fallbacks.
- Perplexity supports API-key mode and cookie-auth mode. Cookie mode is used by the interactive `/login perplexity` flow.
- `z.ai` search also checks stored OAuth credentials in `agent.db`.
- Codex search requires either `OPENAI_API_KEY` or a stored Codex OAuth credential.
- Anthropic search has a dedicated key/base URL pair so search traffic can be routed independently from chat completions.

## Minimal `.env` examples

```dotenv
# Brave
BRAVE_API_KEY=bsk-...
```

```dotenv
# Exa
EXA_API_KEY=...
```

```dotenv
# SearXNG self-hosted
SEARXNG_ENDPOINT=https://search.example.com
SEARXNG_TOKEN=optional-bearer-token
```

```dotenv
# Perplexity API-key mode
PERPLEXITY_API_KEY=pplx-...
```

## Configuring in `config.yml`

Only SearXNG exposes structured config keys:

```yaml
searxng:
  endpoint: https://search.example.com
  token: optional-bearer-token
  basicUsername: user
  basicPassword: pass
```

All other search providers are enabled purely by environment variables or stored auth.

## Validation safety

All validation `curl` commands above use a test query. When running them, ensure:

- The command is not captured in shell history containing the real key.
- The output does not include the key or full response payloads in tool results.
- Errors are inspected for auth/permission issues, not just connectivity.
