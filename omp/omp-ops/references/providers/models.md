# OMP Model Provider Key Configuration and `modelRoles`

Source: `docs/providers.md`, `docs/models.md`, `docs/settings.md`, `docs/environment-variables.md`.

The default custom-model config prefers `~/.omp/agent/models.yml` and falls
back to `~/.omp/agent/models.yaml` when the first file is absent. `models.json`
migration only applies when both YAML files are missing. Role values may use
`@role` aliases; `*` selects `@default`, and YAML values containing `@` should
be quoted.

## Common provider API keys

The table below lists the environment variable used by each core model provider when no stored credential exists. Set one of these in your shell or in an untracked `.env` file.

| Provider ID | Primary env var | Fallback env var(s) |
|---|---|---|
| `anthropic` | `ANTHROPIC_OAUTH_TOKEN` | `ANTHROPIC_API_KEY` |
| `openai` | `OPENAI_API_KEY` | — |
| `openai-codex` | `OPENAI_CODEX_OAUTH_TOKEN` | — |
| `google` | `GEMINI_API_KEY` | — |
| `google-vertex` | `GOOGLE_CLOUD_API_KEY` | ADC: `GOOGLE_APPLICATION_CREDENTIALS` + `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` |
| `groq` | `GROQ_API_KEY` | — |
| `openrouter` | `OPENROUTER_API_KEY` | — |
| `mistral` | `MISTRAL_API_KEY` | — |
| `xai` | `XAI_API_KEY` | — |
| `xai-oauth` | `XAI_OAUTH_TOKEN` | `XAI_API_KEY` |
| `github-copilot` | `COPILOT_GITHUB_TOKEN` | — |
| `cursor` | `CURSOR_ACCESS_TOKEN` | — |
| `azure` | `AZURE_OPENAI_API_KEY` | — |
| `amazon-bedrock` | `AWS_PROFILE` | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`, or ECS/IRSA chain |
| `deepseek` | `DEEPSEEK_API_KEY` | — |
| `fireworks` | `FIREWORKS_API_KEY` | — |
| `together` | `TOGETHER_API_KEY` | — |
| `nvidia` | `NVIDIA_API_KEY` | — |
| `novita` | `NOVITA_API_KEY` | — |
| `huggingface` | `HUGGINGFACE_HUB_TOKEN` | `HF_TOKEN` |
| `cerebras` | `CEREBRAS_API_KEY` | — |
| `moonshot` | `MOONSHOT_API_KEY` | — |
| `siliconflow` | `SILICONFLOW_API_KEY` | — |
| `siliconflow-cn` | `SILICONFLOW_CN_API_KEY` | — |
| `deepinfra` | `DEEPINFRA_API_KEY` | — |
| `yolo-auto` | `YOLO_AUTO_API_KEY` | — |
| `ollama` | `OLLAMA_API_KEY` (optional) | keyless by default |
| `lm-studio` | `LM_STUDIO_API_KEY` (optional) | keyless by default |
| `llama.cpp` | `LLAMA_CPP_API_KEY` (only when server requires auth) | keyless by default |

DeepInfra also provides the `image_gen` and `tts` backends. Select it in
`providers.imageOrder`, choose `provider: deepinfra` for an image-generation
request, or set `providers.tts: deepinfra`; TTS output supports MP3 and WAV.

Yolo-Auto is an API-key-backed provider for its flat-rate Qwen models. Set
`YOLO_AUTO_API_KEY` and verify the provider's current model catalog before
pinning a model id.

For custom models, `thinking.requiresEffort` defaults to auto-detection. Set it
to `false` only after verifying that the backend accepts an explicit reasoning-
off request; this preserves the `:off` selector instead of clamping it to the
lowest effort.

### xAI paid-model routing

On OMP 17.3.6, paid xAI models selected through `XAI_API_KEY` and the
`xai-oauth` provider use the Responses API path. Both provider defaults are
`grok-4.6`; when only `XAI_API_KEY` is available, automatic selection prefers
`xai/grok-4.6`, while `xai-oauth/grok-4.6` remains an explicit choice. Do not
configure presence/frequency penalties or stop sequences for xAI reasoning
models such as `grok-4.6` because the endpoint rejects them.

16.2.7 changed Google Vertex precedence so explicit env credentials override
stored auth before broker migration; verify exact env names against official
docs before advising a user to set them.

## Built-in local engines

Local engines are discovered automatically if not explicitly configured in `models.yml` and not disabled.

| Provider ID | Base URL env override | Default base URL | Auth |
|---|---|---|---|
| `ollama` | `OLLAMA_BASE_URL`, then `OLLAMA_HOST` | `http://127.0.0.1:11434` | keyless |
| `llama.cpp` | `LLAMA_CPP_BASE_URL` | `http://127.0.0.1:8080` | keyless |
| `lm-studio` | `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | keyless |
| `litellm` | `LITELLM_BASE_URL` | `http://127.0.0.1:4000/v1` | `LITELLM_API_KEY` (when proxy requires key) |

`litellm` discovery probes LiteLLM management metadata first (`GET /model_group/info`, then `GET /v2/model/info`), then falls back to the OpenAI-compatible `GET /models` list. Rich metadata maps `max_input_tokens`, `max_output_tokens`, `supports_vision`, `supports_reasoning`, and upstream-provider identity; bare fallback ids are enriched against bundled reference metadata when available. OpenAI-backed discovered models use the Responses route so reasoning summaries remain available, while mixed-provider groups stay on Chat Completions.

Release caveats:

- 16.3.0 fixed llama.cpp router/preset status-bar context reporting; do not
  tell users every preset is 128k just because status previously showed that.
- 16.2.12 fixed OpenAI-compatible discovery for LM Studio/proxies by enriching
  flat IDs from bundled model metadata when context length is omitted.
- 16.2.11 fixed timeout cleanup for Ollama, Llama.cpp, LM Studio, OpenAI,
  LiteLLM, and vLLM discovery.

## Quick `models.yml` examples

### Override a built-in provider

```yaml
providers:
  openrouter:
    baseUrl: https://openrouter.ai/api/v1
    apiKey: OPENROUTER_API_KEY
    headers:
      X-Title: my-app
```

### Add a custom OpenAI-compatible gateway

```yaml
providers:
  my-gateway:
    baseUrl: https://gateway.example.com/v1
    api: openai-completions
    apiKey: MY_GATEWAY_API_KEY
    authHeader: true
    models:
      - id: claude-sonnet
        name: Claude Sonnet via Gateway
        input: [text]
        contextWindow: 200000
        maxTokens: 8192
```

### Local keyless endpoint

```yaml
providers:
  local-openai:
    baseUrl: http://127.0.0.1:8000/v1
    api: openai-completions
    auth: none
    models:
      - id: qwen2.5-coder-32b
        name: Qwen 2.5 Coder 32B (local)
        input: [text]
        contextWindow: 128000
        maxTokens: 8192
```

### Custom LiteLLM gateway

```yaml
providers:
  litellm-gateway:
    baseUrl: http://gateway.example:4000/v1
    apiKey: LITELLM_API_KEY
    api: openai-completions
    discovery:
      type: litellm
```

LiteLLM metadata endpoints use the configured base URL with a trailing `/v1` stripped for discovery only, preserving any preceding proxy path. Runtime model calls keep the configured OpenAI-compatible `/v1` base URL.

## Allowed `api` values

- `openai-completions`
- `openai-responses`
- `openai-codex-responses`
- `azure-openai-responses`
- `anthropic-messages`
- `google-generative-ai`
- `google-gemini-cli`
- `google-vertex`

## `modelRoles` setup

`modelRoles` lives in `~/.omp/agent/config.yml` or `<project>/.omp/config.yml`.

Built-in roles:

| Role | Typical use |
|---|---|
| `default` | Main model for normal turns. |
| `smol` | Fast/cheap model for lightweight tasks. |
| `slow` | Strong reasoning model for hard problems. |
| `vision` | Image-capable model. |
| `plan` | Model used for planning phases. |
| `designer` | UI/UX or architecture work. |
| `commit` | Commit-message generation. |
| `tiny` | Lightweight background tasks such as titles, memory, and auto-classification. |
| `title` | Session-title generation. |
| `task` | Task-tool subagent model. |
| `advisor` | Advisor/WATCHDOG reviewer model (16.2.3+: full tool access, multi-advisor via WATCHDOG.yml). |

For custom vision models whose serving backend cannot accept WebP, set
`imageInputDecoder: stb` on the model or its `modelOverrides` entry. OMP then
normalizes attached and historical WebP image blocks before provider dispatch.

For proxy models whose id is ambiguous or noncanonical, `tokenizer` may select
an embedded local tokenizer (`claude-v3`, `claude-v47`, `claude-v5`,
`claude-v5-sonnet`, `qwen3`, `deepseek-v3`, `kimi-k2`, or `glm5`). Prefer the
catalog identity policy when it is correct; unknown models otherwise retain the
fast local estimate.

`Tester` and `sonic` are built-in subagents, not `modelRoles`; `oracle` is no
longer built in as of 16.2.9.

### Example configuration

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
  tiny: openai/gpt-4.1-mini
  title: openai/gpt-4.1-mini
  task: anthropic/claude-sonnet-4-5
  advisor: anthropic/claude-sonnet-4-5:medium

cycleOrder:
  - smol
  - default
  - slow

modelProviderOrder:
  - anthropic
  - openai
  - google
```

### Thinking suffixes

Append `:minimal`, `:low`, `:medium`, `:high`, `:xhigh`, or `:max` to a role value to set its thinking level:

```yaml
modelRoles:
  slow: anthropic/claude-opus-4-5:high
  tiny: openai/gpt-4.1-mini
  advisor: anthropic/claude-sonnet-4-5:medium
```

For local Qwen 3.8+ models using the `qwen-chat-template` dialect, OMP can
route the selected effort through `chat_template_kwargs.reasoning_effort`.
Set the model compatibility field `qwenTemplateReasoningEffort: false` when a
strict local server rejects unknown `chat_template_kwargs`; effort selections
are then omitted for the Qwen dialects and the template uses its own default.

### Exact flat IDs and provider preference

16.2.12 removed canonical alias coalescing.

`equivalence` keys in `models.yml`/`models.json` are inert.

Use `provider/model-id` for a concrete provider.

Use a bare exact flat id only when OMP can match that same id through provider preference.

`modelProviderOrder` chooses among provider candidates; it no longer feeds a catalog-wide canonical alias resolver.

### Recent provider notes (16.2.9–17.3.8)

- 17.4.1 adds `qwenTemplateReasoningEffort` to model compatibility settings for
  Qwen 3.8+ local backends. Keep it disabled only for strict servers that
  reject the generated chat-template reasoning argument.

- 17.2.5 supports positive `providers.<id>.discovery.timeoutMs` values for
  slow or remote model-discovery probes.

- 17.2.0 adds `providers.autoThinkingMaxEffort`; set it to `max` only when
  `auto` thinking classification should reach `max` on models that support it.
  The default remains `xhigh`, and the on-device three-bucket classifier stays
  capped at `xhigh`.

- 17.2.1 changes credential precedence after the runtime override and
  `models.yml` provider key: stored OAuth, a key saved by `/login`, provider
  environment variables, other stored API keys, then the custom-provider
  fallback resolver. Do not assume a legacy stored API key beats an explicit
  environment variable.

- 17.1.6 makes the per-spawn `task.effort` hint opt-in through
  `task.enableEffort` (default false), and adds `task.maxEffort` to cap the
  resolved effort, including after retry-fallback model swaps.

- 17.1.4 removes explicit per-spawn model selectors from `task` and
  `agent()`; spawned work uses the configured agent model. The `task.effort`
  selector remains available for `lo`, `med`, or `hi` thinking effort.

- 17.1.2 adds a `task` tool `effort` selector (`lo`, `med`, or `hi`) for each
  spawned task. It maps to the resolved model's supported thinking range and
  overrides the agent default for that call; omission preserves automatic
  per-prompt classification.

- 17.0.9 previously introduced per-call model/fallback selection; this was
  removed in 17.1.4, so do not rely on that older behavior.

- 17.0.7 preserves Portkey/gateway model ids that begin with `@` (for example,
  `@modal/GLM-5-2-FP8`) instead of rewriting them to a bundled wire id. Keep
  such ids exact in custom-provider model definitions.

- 17.0.6 adds Codex-subscription image generation through the `openai-codex`
  OAuth provider and supports a per-request image-provider override. This is
  independent of the active chat model; do not assume an `OPENAI_API_KEY` is
  required when a connected Codex subscription is selected.

- 17.0.4 adds `PI_CONFIG_FILES`, a platform-delimited settings-overlay path
  list loaded before explicit `--config` overlays. Treat wrapper-provided files
  as another configuration layer and keep secrets out of those files.

- 17.0.3 expands LiteLLM discovery to try `/model_group/info`, `/v2/model/info`,
  `/model/info`, and `/v1/model/info` before falling back to `GET /models`.
  Management-route access may require LiteLLM `allowed_routes` permission or a
  master/admin key; fallback-only models can have unknown context and pricing.

- 17.0.1 fixes xAI web-search routing through configured `xai` / `xai-oauth`
  proxy endpoints and headers, while preventing official OAuth tokens from
  being sent to custom endpoints. This is a provider-routing and credential
  boundary fix; keep custom endpoints explicitly trusted.

- 17.0.0 changes tool discovery and dispatch rather than provider credentials:
  custom, extension, MCP, image-generation, and TTS tools are discoverable
  through `xd://` devices, while BM25 tool discovery and per-tool MCP
  selection are removed. Keep provider/model selection separate from this
  runtime tool-transport change.

- 16.5.1 treats each Anthropic organization/subscription as a separate OAuth
  account for login, usage, logout, and credential rotation, including when one
  email owns both a Team seat and a personal plan.
- 16.5.0 replaced the reasoning-slide flag family with the `--prewalk`,
  `--prewalk-into`, and `--no-prewalk` execution controls.

- 16.3.11 session-title generation now uses marker-based parsing for all
  models. Treat bare JSON-shaped title output as a defect; the runtime strips
  wrappers and keeps the title field bare.
- 16.3.11 llama.cpp discovery now honors per-model
  `architecture.input_modalities` from `/v1/models`, so a router preset that
  advertises image input should be treated as vision-capable instead of
  text-only.

- `providers.anthropic.serverSideFallback` opt-in for Anthropic server-side
  fallback beta.
- Anthropic/OpenAI/Google signed thinking and reasoning payload persistence
  fixes prevent replay HTTP 400s.
- `NODE_EXTRA_CA_CERTS` is honored by model discovery/provider fetches for
  private CA gateways.
- LiteLLM stale reseller display-name suffixes are invalidated on upgrade.
- OpenAI Responses replay errors from missing reasoning items were fixed.
- Xiaomi MiMo default/validation uses supported `mimo-v2.5`.
- ZenMux Anthropic route classification was fixed for Claude Sonnet 5 signature
  enforcement.

### Recent provider notes (16.4.2)

- 16.4.2 adds `novita` provider auth via `NOVITA_API_KEY`.
- 16.4.2 extends thinking suffix support with `:max` in addition to the
  existing `:minimal`, `:low`, `:medium`, `:high`, and `:xhigh` values.

### Recent provider notes (17.3.6)

- Paid xAI models use the Responses API, default to `grok-4.6`, and reject
  presence/frequency penalties and stop sequences when reasoning is enabled.

### Recent provider notes (17.4.0)

- LiteLLM discovery now selects `openai-responses` for OpenAI-backed models
  and preserves Chat Completions for mixed-provider groups; this keeps
  reasoning summaries available without changing custom gateway definitions.

---

## Owned in-band tool-call dialects (`PI_DIALECT`)

When a model or gateway cannot reliably parse native provider tool calls, OMP can fall back to **owned in-band tool calling**: tools are described in the prompt using a syntax-specific grammar, the model emits tool calls as plain text, and OMP parses them locally.

### Selecting a dialect

The undocumented env var `PI_DIALECT` forces a specific dialect:

```bash
PI_DIALECT=kimi omp
PI_DIALECT=glm omp --model zhipu/glm-5.1
```

Known dialect values in v16.2.3 (from source/release notes; not exhaustive):

| Dialect | Typical model family |
|---|---|
| `glm` | Zhipu GLM |
| `hermes` | Hermes / Qwen-style |
| `kimi` | Moonshot Kimi |
| `xml` | Generic XML fallback |
| `anthropic` | Anthropic-style |
| `deepseek` | DeepSeek |
| `harmony` | OpenAI / gpt-oss |
| `qwen3` | Qwen3 |
| `minimax` | MiniMax M2/M3 (added v16.0.5) |
| `pi` / `pi-native` | **Removed in v16.2.2** |

### Discoverable alternatives

Because `PI_DIALECT` is not documented in `docs/environment-variables.md`, prefer these config-level controls when possible:

- **`tools.format`** in `config.yml` — set to `native` or an owned syntax (`glm`, `kimi`, `anthropic`, `deepseek`, `harmony`, `xml`, `qwen3`, `minimax`).
- **`PI_OWNED_TOOLS=1`** — enables owned mode with GLM as default.
- **`PI_OWNED_TOOLS=<syntax>`** — enables owned mode with a specific syntax.

### When to use it

- Model repeatedly fails to invoke tools or emits malformed tool-call JSON.
- Using a custom gateway/proxy that advertises OpenAI compatibility but mishandles `tools`/`tool_choice`.
- Model family has a known preferred in-band syntax (e.g., MiniMax M3 with `<minimax:tool_call>` wrappers).

### Caveats

- `PI_DIALECT` is a hidden env var; values and availability can change between releases.
- v16.2.2 removed the `pi` / `pi-native` dialect; tips.txt still mentions the general feature but `PI_DIALECT=pi` will not work.
- For stable configuration, set `tools.format` in `config.yml` instead.
