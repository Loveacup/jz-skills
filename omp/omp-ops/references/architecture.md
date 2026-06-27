# OMP Configuration Architecture

Source: `docs/config-usage.md`, `docs/settings.md`, `docs/providers.md`, `docs/models.md`, `docs/secrets.md`.

## Config directory layout

OMP uses two scopes. Higher-precedence layers override lower ones.

| Scope | Base path | Notes |
|---|---|---|
| User (global) | `~/.omp/agent/` | Persistent settings, auth store, skills, custom tools, etc. |
| Project | `<cwd>/.omp/` | Read-only project overrides; not written by `omp config set`. |

`PI_CODING_AGENT_DIR` relocates the user agent directory entirely.
`OMP_PROFILE` / `--profile` moves the user base to `~/.omp/profiles/<name>/agent/`.

### Important files and directories

```text
~/.omp/agent/
├── config.yml              # global persistent settings
├── settings.json           # legacy; migrated to config.yml once
├── models.yml              # custom providers / overrides / equivalence
├── secrets.yml             # custom secret obfuscation rules
├── .env                    # agent-scope env vars (third .env precedence)
├── agent.db                # SQLite auth store (API keys + OAuth credentials)
├── sessions/               # session trees, exports, resumes
├── blobs/                  # artifact storage
├── skills/*/SKILL.md       # user skills
├── tools/                  # custom tools
├── hooks/                  # pre/post hooks
├── commands/               # slash commands
├── rules/                  # rule files
├── prompts/                # prompt files
├── extensions/             # extension modules
└── managed-skills/         # auto-learned skills

~/.omp/
├── .env                    # config-root env vars (fourth .env precedence)
└── cache/                  # caches, broker snapshots

<project>/.omp/
├── config.yml              # project settings override
├── settings.json           # legacy project settings
├── secrets.yml             # project-specific secrets
├── .env                    # first .env precedence for this cwd
├── SYSTEM.md               # system prompt override
├── APPEND_SYSTEM.md        # append to system prompt
├── AGENTS.md               # context-file capability
└── skills/*/SKILL.md       # project skills
```

## `config.yml`

Global path: `~/.omp/agent/config.yml`.
Project path: `<cwd>/.omp/config.yml`.

Precedence (low → high):

```text
built-in defaults  <-  global config  <-  project config  <-  CLI overlays  <-  runtime overrides
```

Example:

```yaml
# ~/.omp/agent/config.yml
modelRoles:
  default: anthropic/claude-sonnet-4-5
  smol: openai/gpt-4.1-mini
  slow: anthropic/claude-opus-4-5:high
  vision: gemini/gemini-3-pro-preview
  plan: anthropic/claude-opus-4-5
  designer: anthropic/claude-sonnet-4-5
  commit: openai/gpt-4.1-mini
  title: openai/gpt-4.1-mini
  task: anthropic/claude-sonnet-4-5
  advisor: anthropic/claude-sonnet-4-5:medium

disabledProviders:
  - ollama

enabledModels: []

modelProviderOrder:
  - anthropic
  - openai

tools:
  approvalMode: write
  approval:
    bash: prompt
    edit: prompt
    read: allow

compaction:
  strategy: snapcompact
  thresholdPercent: 80

secrets:
  enabled: true
```

### Key model-related settings

| Key | Type | Purpose |
|---|---|---|
| `modelRoles` | record | Map role → `provider/model-id` or canonical id. |
| `modelTags` | record | Custom role/tag metadata. |
| `cycleOrder` | array | Roles cycled by `/model` switcher. |
| `modelProviderOrder` | array | Provider precedence for ambiguous canonical ids. |
| `enabledModels` | array | Allow-list of concrete/canonical models. |
| `disabledProviders` | array | Block model/discovery providers by id. |

Supported roles: `default`, `smol`, `slow`, `vision`, `plan`, `designer`, `commit`, `title`, `task`, `advisor`.
Role values may append a thinking suffix: `:minimal`, `:low`, `:medium`, `:high`, `:xhigh`.

## `agent.db` and `auth_credentials`

`~/.omp/agent/agent.db` is the local SQLite credential store.

It holds:

- stored API-key credentials (`AuthStorage.setApiKey`)
- stored OAuth credentials (access + refresh tokens, auto-refreshed)
- login state per provider

Credential resolution order for a provider request:

1. Runtime override (e.g. CLI `--api-key`).
2. `models.yml` `apiKey` on a custom provider (env-name-or-literal).
3. Stored API key in `agent.db`.
4. Stored OAuth credential in `agent.db` (with refresh).
5. Provider environment variable (e.g. `OPENAI_API_KEY`).
6. `models.yml` fallback resolver.

In broker mode (`OMP_AUTH_BROKER_URL`), the local SQLite store is bypassed and layers 2–3 are served from a broker snapshot.

## `.env` precedence

OMP eagerly loads `.env` files before provider lookup. For each variable, the **first** source wins:

1. Existing process environment.
2. `<cwd>/.env`
3. `~/.omp/agent/.env`
4. `~/.omp/.env`
5. `~/.env`

Rules:

- A variable already in the process environment is never overwritten.
- Inside each parsed `.env`, `OMP_*` keys are mirrored to matching `PI_*` names.
- Keys must match `[A-Za-z_][A-Za-z0-9_]*`.
- Values may be single- or double-quoted; quotes are stripped.

### Project-local `.env` example

```dotenv
# <project>/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

## `modelRoles`

`modelRoles` maps a role alias to a concrete or canonical model selector.
Official 16.2.2 adds a `tiny` role for lightweight background tasks such as
session titles, memory, auto-thinking difficulty classification, and
unexpected-stop detection. When it is unset, those flows fall back to
`pi/smol`.

```yaml
modelRoles:
  default: anthropic/claude-sonnet-4-5
  smol: openai/gpt-4.1-mini
  slow: anthropic/claude-opus-4-5:high
  tiny: openai/gpt-4.1-mini
  advisor: anthropic/claude-sonnet-4-5:medium
```

- Use `provider/model-id` to pin a concrete variant.
- Use a canonical id (e.g. `gpt-5.3-codex`) to allow provider coalescing.
- A thinking suffix overrides the default thinking level for that role.
- Env overrides: `PI_SMOL_MODEL`, `PI_SLOW_MODEL`, `PI_PLAN_MODEL` (process-local only).
- CLI flags: `--model`, `--smol`, `--slow`, `--plan`, `--advisor`.

## Scopes and merge rules

- Objects are deep-merged across layers.
- Arrays and scalars are **replaced wholesale** by the higher-precedence layer.
- Project `config.yml` arrays do not extend global arrays; they become the entire effective list inside that project.
- `disabledProviders` and `enabledModels` support path-scoped entries.

### Path-scoped `disabledProviders`

```yaml
disabledProviders:
  - ollama
  - path: ~/projects/sensitive
    providers:
      - anthropic
      - openai
```

Applies when the current working directory is the configured path or under it.
