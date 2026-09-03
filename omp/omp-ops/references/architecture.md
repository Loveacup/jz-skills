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
├── models.yml              # custom providers / overrides; preferred YAML config
├── models.yaml             # fallback YAML config (16.5.0+)
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
├── WATCHDOG.yml            # multi-advisor roster (16.2.3+)
├── WATCHDOG.yaml           # alternative YAML extension
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
  - google

tier:
  openai: auto      # per-family service tiers replace global serviceTier (16.2.7+)
  anthropic: auto
  google: auto

providers:
  anthropic:
    serverSideFallback: false  # opt-in Anthropic beta fallback chain (16.3.0+)
  autoThinkingMaxEffort: xhigh  # use `max` only when explicitly enabled (17.2.0+)

security:
  enabled: false  # opt-in native security workflow (17.2.1+)

task:
  softRequestBudgetNotice: false  # opt-in subagent soft-budget wrap-up steering notices (16.3.0+)
tools:
  approvalMode: write
  approval:
    bash: prompt
    edit: prompt
    read: allow

compaction:
  methodOrder: [remote, snap]  # ordered preference; replaces strategy/remoteEnabled (17.4.0+)
  asyncEnabled: true            # speculate compaction in the background (17.4.0+)
  thresholdPercent: 80
  remoteStreamingV2Enabled: true  # forward full history to provider (16.2.3+)
  v2RetainedMessageBudget: 50     # max retained turns for V2 streaming

statusLine:
  compactThinkingLevel: true   # render thinking level as single leading glyph
  contextLine: annotated        # context gauge: percentage, annotated, or embedded (17.4.0+)

edit:
  citationTags: true           # emit hashline headers as OpenAI citation markers

secrets:
  enabled: true

extendedContext: true  # allow premium long-context tiers before compaction (17.4.0+)
```

### Key model-related settings

| Key | Type | Purpose |
|---|---|---|
| `modelRoles` | record | Map role → provider/model-id or exact flat model id. |
| `modelTags` | record | Custom role/tag metadata. |
| `cycleOrder` | array | Roles cycled by `/model` switcher. |
| `modelProviderOrder` | array | Provider precedence when an exact flat model id is available from multiple providers. |
| `enabledModels` | array | Allow-list of provider/model ids or exact flat model ids. |
| `disabledProviders` | array | Block model/discovery providers by id. |

Supported roles: `default`, `smol`, `slow`, `vision`, `plan`, `commit`, `tiny`, `title`, `task`, `advisor`.
Subagent names and model roles are separate; do not add `sonic` or `Tester` as `modelRoles`.
Role values may append a thinking suffix: `:minimal`, `:low`, `:medium`, `:high`, `:xhigh`, `:max`.

### OMP 17.0.0 tool transport boundary

OMP 17.0.0 mounts discoverable custom, extension, MCP, image-generation, and
TTS tools as `xd://` devices. Read a device for its documentation and write to
the device to dispatch it. The former BM25 discovery settings and per-tool MCP
selection settings are removed; do not add `tools.discoveryMode`,
`mcp.discoveryMode`, or `mcp.discoveryDefaultServers` to new configuration.
The `hub` tool now covers IRC, jobs, and launch/process supervision.

### OMP 17.0.9–17.1.6 task and MCP settings

`task.isolation.apply` defaults to `true`: successful isolated `task` runs
apply their changes to the parent checkout. Set it to `false` when the caller
must retain patch/branch artifacts for later integration.

`mcp.renderMarkdownResults` defaults to `true`, so non-JSON MCP text results
render as Markdown in the terminal transcript. Set it to `false` when raw MCP
text is required for downstream parsing or comparison.

From OMP 18.1.3, MCP tool results also expose the protocol's
`structuredContent` channel to the model. When an MCP server returns a terse
acknowledgement in `content` and its actual payload in `structuredContent`,
inspect the structured payload rather than treating the result as data-less.

Each `task` tool spawn may set `effort` to `lo`, `med`, or `hi` only when
`task.enableEffort` is enabled. OMP maps the selector to the resolved model's
lowest, middle, or highest supported thinking level and applies it only to that
call; omitting it keeps automatic prompt classification. `task.maxEffort` can
cap the resolved effort, including after retry-fallback model swaps.

OMP 17.1.4 removes explicit per-call model selection from `task` and `agent()`;
those spawns use the configured agent model.

### OMP 18.1.7 local models and eval

On Apple silicon, `providers.tinyModelDevice: mlx` or
`PI_TINY_DEVICE=mlx|metal` routes local tiny-model work through MLX; ONNX CPU
remains the fallback when the MLX runtime is unavailable. Ruby and Julia eval
backends are removed. Eval `agent()` and `completion()` return asynchronous
handles, so integrations should use `await`/`wait`; the former `parallel()` and
`pipeline()` helpers are no longer available.

OMP 17.2.9 preserves `enabled: false` while importing MCP servers from Claude
Code, Codex, Gemini CLI, Cursor, Windsurf, and VS Code. For those translated
sources, a project entry is loaded before a same-named user entry, so a
project-level disable suppresses the user-level server. OpenCode retains its
user-first ordering; verify that source when diagnosing a translated MCP
server that remains mounted.

## Multi-Advisor (`WATCHDOG.yml`)

As of 16.2.3, advisors are configured via `WATCHDOG.yml` (or `WATCHDOG.yaml`)
in `~/.omp/agent/`. Each advisor can have its own model, tool subset, and
instructions. Advisors now have full access to all built-in agent tools
(including edit, write, and bash) — no longer read-only. In 17.3.0, the global
`advisor.subagents` setting was removed: configure advisors per agent through
the `advisor` frontmatter field or the `task.agentAdvisor` setting. Existing
`advisor.subagents: true` configurations migrate to
`task.agentAdvisor: { task: "on" }`.

Manage the roster with `/advisor configure`, a mouse-driven full-screen TUI.

```yaml
# ~/.omp/agent/WATCHDOG.yml
advisors:
  - slug: code-reviewer
    name: Code Reviewer
    model: anthropic/claude-sonnet-4-5
    tools: [read, grep, glob, edit, lsp]
    instruction: |
      Review code for correctness, security, and style.
  - slug: security-auditor
    name: Security Auditor
    model: anthropic/claude-opus-4-5:high
    tools: [read, grep, glob]
    instruction: |
      Audit for OWASP Top 10 vulnerabilities and secret leaks.
```

### New config keys (16.2.3)

| Key | Type | Purpose |
|---|---|---|
| `compaction.remoteStreamingV2Enabled` | boolean | Enable V2 streaming remote compaction (default: true for compatible models). |
| `compaction.v2RetainedMessageBudget` | integer | Max retained messages for V2 streaming compaction. |
| `statusLine.compactThinkingLevel` | boolean | Render thinking level as a single leading glyph instead of text suffix. |
| `edit.citationTags` | boolean | Emit hashline section headers as OpenAI citation markers. |
| `edit.recoverInlineEdits` | boolean | Recover stray XML-shaped sloppy-edit payloads emitted as plain text into edit calls (18.1.2+). |
| `compaction.methodOrder` | array | Ordered compaction method preference, replacing `compaction.strategy` and `compaction.remoteEnabled`. |
| `compaction.asyncEnabled` | boolean | Speculatively compact context in the background (enabled by default). |
| `statusLine.contextLine` | string | Show context usage as `percentage`, `annotated`, or `embedded`. |
| `extendedContext` | boolean | Allow premium long-context model tiers; disable to compact earlier at standard-pricing limits. |

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
4. Stored OAuth credential in `agent.db` (with refresh). For Anthropic and
   ChatGPT/Codex, each organization or workspace is treated as a separate
   account during login, usage, and rotation; select the intended workspace
   in the consent flow.
5. Provider environment variable (e.g. `OPENAI_API_KEY`).
6. `models.yml` fallback resolver.

In broker mode (`OMP_AUTH_BROKER_URL`), the local SQLite store is bypassed and layers 2–3 are served from a broker snapshot.

## `.env` precedence

OMP eagerly loads `.env` files before provider lookup. For each variable, the **first non-empty** source wins:

1. Existing process environment.
2. `<cwd>/.env`
3. `~/.omp/agent/.env`
4. `~/.omp/.env`
5. `~/.env`

Rules:

- Empty process values may be filled by a later `.env`; non-empty values are never overwritten.
- Inside each parsed `.env`, `OMP_*` keys mirror matching `PI_*` names and override a same-file `PI_*` value.
- Keys must match `[A-Za-z_][A-Za-z0-9_]*`.
- Values are parsed literally (single/double quotes are stripped); unsafe names/values are discarded.

`PI_CONFIG_FILES` may provide a platform-delimited path list of settings
overlays (`:` on Unix, `;` on Windows). These files load in listed order
before explicit `--config` overlays, which is useful for wrapper scripts that
need to inject settings without changing argv.

### Project-local `.env` example

```dotenv
# <project>/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

## `modelRoles`

`modelRoles` maps a role alias to a provider/model-id or exact flat model id.
Official 16.2.2 adds a `tiny` role for lightweight background tasks such as
session titles, memory, auto-thinking difficulty classification, and
unexpected-stop detection. When it is unset, those flows fall back to `pi/smol`.
Subagent names and model roles are separate.

```yaml
modelRoles:
  default: anthropic/claude-sonnet-4-5
  smol: openai/gpt-4.1-mini
  slow: anthropic/claude-opus-4-5:high
  tiny: openai/gpt-4.1-mini
  advisor: anthropic/claude-sonnet-4-5:medium
```

- Use `provider/model-id` to pin a concrete variant.
- Use an exact flat model id only when the same id exists across providers and `modelProviderOrder` should choose the provider.
- Canonical alias coalescing was removed in 16.2.12; `equivalence` in `models.yml`/`models.json` is inert.
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
