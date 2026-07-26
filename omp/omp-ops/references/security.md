# OMP Security Rules for `omp-ops`

Source: `docs/providers.md`, `docs/secrets.md`, `docs/environment-variables.md`.

## API key handling rules

1. **Never commit keys.** API keys, OAuth tokens, bearer tokens, and passwords must not be written into committed config files, SKILL.md files, or tool outputs.
2. **Prefer stored auth.** Use `/login` or `omp auth-broker login <provider>` to persist credentials in `~/.omp/agent/agent.db` (local SQLite) or a remote auth broker.
3. **Use environment variables.** Set provider env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) in an untracked `.env` or in your shell environment.
4. **Project `.env` is allowed** for project-specific endpoints, but ensure it is ignored by version control.
5. **`models.yml` `apiKey` is env-name-or-literal.** If the value names an existing env var, that var is used; otherwise the literal string becomes the key. Prefer env-var names over literals.
6. **Command-resolved secrets.** Prefix a provider/header value with `!` to run a shell command (10 s timeout) and use trimmed stdout. This is acceptable for local password managers.
7. **Custom endpoint isolation.** When routing Codex/OpenAI-compatible traffic
   to a custom endpoint, use its explicit API key and headers; do not allow
   official OAuth credentials to cross that endpoint boundary. Prefer an
   explicit provider selection that fails closed when its credentials are
   unavailable.
8. **Credential display is redacted.** `omp config list` masks configured
   credential values and omits them from JSON output; `omp config get <path>`
   remains an explicit value request and should be handled as sensitive output.
9. **Watch OAuth grant age.** `omp usage` warns when an Anthropic OAuth grant
   is within roughly a week of its 30-day server-side lifetime; re-login before
   the deadline instead of relying on refresh rotation alone.

```yaml
# acceptable in models.yml
providers:
  my-gateway:
    baseUrl: https://gateway.example.com/v1
    apiKey: MY_GATEWAY_API_KEY
```

```yaml
# also acceptable
providers:
  openai:
    apiKey: "!op read op://dev/openai/api-key"
```

## Forbidden actions

- Do not write real API key values into `config.yml`, `models.yml`, `secrets.yml`, `.env`, or any skill/reference file.
- Do not print keys, tokens, or bearer credentials to tool result output unless explicitly redacted.
- Do not snapshot `agent.db` into a public location; it contains encrypted credential material.
- Do not persist broker tokens (`OMP_AUTH_BROKER_TOKEN`, `auth.broker.token`) in committed files.
- Do not use `curl` or `bash` to echo env vars that contain secrets during skill execution.
- Do not disable `secrets.enabled` solely to make output easier to read.
- Do not store mTLS private keys (`CLAUDE_CODE_CLIENT_KEY`) alongside source code.

## Redaction requirements

OMP has built-in secret obfuscation (`secrets.enabled` in `config.yml`).

### How it works

1. On session startup, OMP collects secrets from:
   - environment variables matching `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PASS`, `AUTH`, `CREDENTIAL`, `PRIVATE`, `OAUTH` with values ≥ 8 characters
   - `~/.omp/agent/secrets.yml` and `<cwd>/.omp/secrets.yml`
2. Outbound text to LLMs is scanned and secret values replaced with deterministic placeholders like `#AB12#`.
3. Placeholders are restored when building display/resume context (`obfuscate` mode).

### Modes

| Mode | Placeholder | Reversible |
|---|---|---|
| `obfuscate` (default) | `#[A-Z0-9]{4}#` | Yes |
| `replace` | same-length deterministic string | No |

### `secrets.yml` example

```yaml
- type: plain
  content: sk-proj-abc123def456

- type: regex
  content: "AKIA[0-9A-Z]{16}"

- type: regex
  content: "postgres://[^\\s]+"
  mode: replace
  replacement: "postgres://***"
```

### Agent skill output

Any script or tool run by this skill that prints status must:

- Strip `*_API_KEY`, `*_TOKEN`, `*_SECRET`, `*_PASSWORD` values before printing.
- Use placeholder strings like `<REDACTED>` for key identifiers.
- Validate that JSON status output does not contain real credential material.

## Credential precedence summary

```text
runtime override (e.g. --api-key)
  -> models.yml apiKey on custom provider
  -> stored API key in agent.db
  -> stored OAuth in agent.db
  -> provider env var / .env
  -> models.yml fallback resolver
```

## Reporting leaks

If a key is accidentally written to any file in this skill repository, rotate the credential immediately and overwrite the file with a redacted version.
