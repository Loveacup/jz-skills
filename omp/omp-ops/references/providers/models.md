# OMP Model Provider Key Configuration and `modelRoles`

Source: `docs/providers.md`, `docs/models.md`, `docs/settings.md`, `docs/environment-variables.md`.

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
| `huggingface` | `HUGGINGFACE_HUB_TOKEN` | `HF_TOKEN` |
| `cerebras` | `CEREBRAS_API_KEY` | — |
| `moonshot` | `MOONSHOT_API_KEY` | — |
| `ollama` | `OLLAMA_API_KEY` (optional) | keyless by default |
| `lm-studio` | `LM_STUDIO_API_KEY` (optional) | keyless by default |
| `llama.cpp` | `LLAMA_CPP_API_KEY` (only when server requires auth) | keyless by default |

## Built-in local engines

Local engines are discovered automatically if not explicitly configured in `models.yml` and not disabled.

| Provider ID | Base URL env override | Default base URL | Auth |
|---|---|---|---|
| `ollama` | `OLLAMA_BASE_URL`, then `OLLAMA_HOST` | `http://127.0.0.1:11434` | keyless |
| `llama.cpp` | `LLAMA_CPP_BASE_URL` | `http://127.0.0.1:8080` | keyless |
| `lm-studio` | `LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | keyless |
| `litellm` | `LITELLM_BASE_URL` | `http://127.0.0.1:4000/v1` | `LITELLM_API_KEY` (when proxy requires key) |

`litellm` discovery probes LiteLLM management metadata first (`GET /model_group/info`, then `GET /v2/model/info`), then falls back to the OpenAI-compatible `GET /models` list. Rich metadata maps `max_input_tokens`, `max_output_tokens`, `supports_vision`, and `supports_reasoning`; bare fallback ids are enriched against bundled reference metadata when available.

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
| `advisor` | Advisor/WATCHDOG reviewer model. |

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

Append `:minimal`, `:low`, `:medium`, `:high`, or `:xhigh` to a role value to set its thinking level:

```yaml
modelRoles:
  slow: anthropic/claude-opus-4-5:high
  tiny: openai/gpt-4.1-mini
  advisor: anthropic/claude-sonnet-4-5:medium
```

### Canonical ids

Use a canonical upstream id to let OMP pick an available concrete provider variant:

```yaml
modelRoles:
  default: gpt-5.3-codex
```

`modelProviderOrder` then controls which concrete provider wins.
