# OMP Search Providers

Source: `docs/environment-variables.md` section 3 (Web search subsystem).

OMP supports multiple web-search backends. Each provider is selected by setting its auth variable and/or config key. Use the ordered `providers.webSearchOrder` list for fallback priority and `providers.webSearchExclude` to suppress providers; legacy `providers.webSearch` values migrate automatically. Image search has the analogous `providers.imageOrder` list. Do not assume the first credentialed provider is the intended route when an explicit order is configured.

As of OMP 17.0.3, the unreliable Bing and Yahoo HTML-scraping providers are
removed; they are intentionally absent from the provider matrix below.

## Provider matrix

| Provider ID | Required env var(s) | Optional env var(s) / config keys | Validation command |
|---|---|---|---|
| `exa` | `EXA_API_KEY` or stored key from `/login exa` | `exa.enabled` controls Exa web-search enablement; legacy `exa.enableSearch` migrates automatically | `omp search --provider exa "test"` |
| `brave` | `BRAVE_API_KEY` | none | `curl -s "https://api.search.brave.com/res/v1/web/search?q=test&count=1" -H "X-Subscription-Token: $BRAVE_API_KEY"` |
| `tavily` | `TAVILY_API_KEY` | none | `curl -s "https://api.tavily.com/search" -H "content-type: application/json" -d '{"api_key":"'$TAVILY_API_KEY'","query":"test","max_results":1}'` |
| `duckduckgo` | none | built-in fallback; 16.3.0 improves error clarity and documents datacenter/shared-egress limitations | `omp search --provider duckduckgo "test"` |
| `perplexity` | `PERPLEXITY_API_KEY` (API-key mode) | `PERPLEXITY_COOKIES` (cookie-auth mode); `PI_PERPLEXITY_MODEL` (consumer subscription model, default `experimental`); `PI_PERPLEXITY_API_MODEL` (direct API model, default `sonar-pro`) | `curl -s "https://api.perplexity.ai/chat/completions" -H "Authorization: Bearer $PERPLEXITY_API_KEY" -H "Content-Type: application/json" -d '{"model":"sonar","messages":[{"role":"user","content":"hello"}]}'` |
| `searxng` | `SEARXNG_ENDPOINT` (`SEARXNG_TOKEN` optional) | `SEARXNG_BASIC_USERNAME`, `SEARXNG_BASIC_PASSWORD`; or `searxng.endpoint`, `searxng.token`, `searxng.basicUsername`, `searxng.basicPassword`, `searxng.engines` in `config.yml` | `curl -s "$SEARXNG_ENDPOINT/search?q=test&format=json" ${SEARXNG_TOKEN:+-H "Authorization: Bearer $SEARXNG_TOKEN"}` |
| `zai` | `ZAI_API_KEY` | stored OAuth in `agent.db` also accepted | `curl -s "https://api.z.ai/v1/chat/completions" -H "Authorization: Bearer $ZAI_API_KEY" -H "Content-Type: application/json" -d '{"model":"glm-4-flash","messages":[{"role":"user","content":"hello"}]}'` |
| `kagi` | `KAGI_API_KEY` | none | `curl -s "https://kagi.com/api/v0/search?q=test" -H "Authorization: $KAGI_API_KEY"` |
| `jina` | `JINA_API_KEY` | none | `curl -s "https://r.jina.ai/http://example.com" -H "Authorization: Bearer $JINA_API_KEY"` |
| `parallel` | `PARALLEL_API_KEY` | none | `curl -s "https://api.parallel.ai/v1/search" -H "Authorization: Bearer $PARALLEL_API_KEY" -d '{"query":"test"}'` |
| `firecrawl` | none when explicitly selected; `FIRECRAWL_API_KEY` for automatic provider-chain eligibility | `FIRECRAWL_BASE_URL` overrides the search endpoint (`FIRECRAWL_API_URL` is a fallback alias); Firecrawl REST API key is omitted only in explicit keyless mode; the automatic chain remains credential-gated | `omp search --provider firecrawl "test"` |
| `anthropic-search` | `ANTHROPIC_SEARCH_API_KEY` (optional; falls back to Anthropic auth) | `ANTHROPIC_SEARCH_BASE_URL`, `ANTHROPIC_SEARCH_MODEL` | `curl -s "${ANTHROPIC_SEARCH_BASE_URL:-https://api.anthropic.com}/v1/messages" -H "x-api-key: ${ANTHROPIC_SEARCH_API_KEY:-$ANTHROPIC_API_KEY}" -H "anthropic-version: 2023-06-01" -d '{"model":"'${ANTHROPIC_SEARCH_MODEL:-claude-haiku-4-5}'","max_tokens":1024,"messages":[{"role":"user","content":"hello"}]}'` |
| `codex-search` | `OPENAI_API_KEY` or stored Codex OAuth in `agent.db` | `PI_CODEX_WEB_SEARCH_MODEL` | `curl -s "https://api.openai.com/v1/responses" -H "Authorization: Bearer $OPENAI_API_KEY" -H "Content-Type: application/json" -d '{"model":"'${PI_CODEX_WEB_SEARCH_MODEL:-gpt-5.3-codex}'","input":"hello"}'` |
| `kimi/moonshot-search` | `MOONSHOT_SEARCH_API_KEY` or `KIMI_SEARCH_API_KEY` | `MOONSHOT_SEARCH_BASE_URL`, `KIMI_SEARCH_BASE_URL` | `curl -s "${MOONSHOT_SEARCH_BASE_URL:-https://api.moonshot.cn/v1}/chat/completions" -H "Authorization: Bearer ${MOONSHOT_SEARCH_API_KEY:-$KIMI_SEARCH_API_KEY}" -H "Content-Type: application/json" -d '{"model":"moonshot-v1-8k","messages":[{"role":"user","content":"hello"}]}'` |

## Notes

- Validation command endpoints and model names are examples. Confirm the exact
  endpoint against the provider's current API documentation before relying on
  them in automation.
- SearXNG reads both environment variables and equivalent `config.yml` settings under the `searxng` key. Environment variables are fallbacks.
- Tavily retries without recency filters if the first response returns no
  content; 16.2.2/16.3.0 release notes document this as current behavior.
- Perplexity supports API-key mode and cookie-auth mode. Cookie mode is used by the interactive `/login perplexity` flow.
- 16.4.8 tightened Perplexity search reliability by forcing retrieval for all queries.
- `z.ai` search also checks stored OAuth credentials in `agent.db`.
- Codex search requires either `OPENAI_API_KEY` or a stored Codex OAuth credential.
- 17.0.6 makes Codex web search honor a configured `openai-codex` base URL,
  API key, and headers without forwarding official OAuth credentials to a
  custom endpoint. Explicitly selected providers fail closed when their
  credentials do not resolve; verify custom endpoints before enabling them.
- Anthropic search has a dedicated key/base URL pair so search traffic can be routed independently from chat completions.
- 17.0.1 fixes xAI web search so configured `xai` / `xai-oauth` proxy endpoints
  and headers are honored; official OAuth tokens are not sent to custom
  endpoints. Treat custom endpoint routing as a security boundary and verify
  the endpoint before enabling it.
- 17.0.9 adds explicit keyless Firecrawl search. Keep it explicitly selected
  when intentionally using the keyless REST path; automatic provider ordering
  still requires Firecrawl credentials.
- 17.1.2 adds `searxng.engines`, a comma-separated engine/shortcut list sent to
  SearXNG. Search queries also support shared operators such as `site:`, date
  bounds, `filetype:`, quoted phrases, exclusions, and `OR`; unsupported
  constraints are post-filtered when possible and relaxed with a notice if
  they would remove every result.
- 17.2.0 adds interactive Exa key onboarding through `/login exa`; keep
  `EXA_API_KEY` when environment-based configuration is preferred. Explicit
  Exa selection still has a keyless public MCP fallback boundary as documented
  by the official mirror.
- 17.2.3 preserves the backend code and message when Codex Web Search returns
  an SSE error. When diagnosing `codex-search`, inspect the reported provider
  error rather than treating the old generic `Codex error (): Unknown error`
  text as a credential or endpoint diagnosis.
- 17.2.5 adds `providers.webSearchTimeoutSeconds` for a configurable per-request
  web-search timeout. Increase it only for providers that are known to need
  more time; keep the default when diagnosing ordinary credential or endpoint
  failures.
- 18.0.0 adds endpoint/model overrides for search integrations: use
  `PI_PERPLEXITY_MODEL` for consumer-cookie mode and `PI_PERPLEXITY_API_MODEL`
  for direct API mode; `FIRECRAWL_BASE_URL` and `GOOGLE_GEMINI_BASE_URL` route
  those search backends to explicit HTTP(S) endpoints. Treat custom endpoints
  as a security boundary and verify them before enabling.
- The current official migration consolidates Exa enablement on `exa.enabled`;
  legacy `exa.enableSearch` is migrated automatically. The obsolete Researcher
  and Websets settings are removed, so do not add them to new configuration.

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
  engines: ddg, br, startpage
```

All other search providers are enabled purely by environment variables or stored auth.

## Validation safety

All validation `curl` commands above use a test query. When running them, ensure:

- The command is not captured in shell history containing the real key.
- The output does not include the key or full response payloads in tool results.
- Errors are inspected for auth/permission issues, not just connectivity.
- These commands are human verification examples and should not be run by
  `omp-ops` maintenance automation.
