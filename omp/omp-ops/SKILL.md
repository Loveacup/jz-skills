---
name: omp-ops
description: |
  Operations skill for Oh My Pi (OMP). Trigger when the user asks about OMP
  configuration, model providers, API keys, search providers, `config.yml`,
  `models.yml`, `agent.db`, `.env` precedence, or `modelRoles`.
---

# omp-ops

> [!note]
> 同步与更新已改为手动触发。需要时运行 `scripts/orchestrate.sh`（Windows 用 `scripts/orchestrate.ps1`），它会检查本地、GitHub 与上游 OMP 三方的版本关系并给出建议动作；没有待处理动作时直接返回 `synced`。
>
> 对齐规则：
> 1. 若 GitHub 领先本地 → 从 GitHub 拉取。
> 2. 若本地领先 GitHub → 推送到 GitHub。
> 3. 若上游 OMP 领先且两端都旧 → 先按上游 OMP 更新官方文档，再推送到 GitHub。

This skill teaches agents how to operate, configure, and troubleshoot
[Oh My Pi](https://github.com/can1357/oh-my-pi) (OMP).

## Red Flags

| Do not... | Why |
|---|---|
| Hard-code API keys or tokens in any file. | `agent.db`, `.env`, and `/login` exist precisely to avoid that. |
| Assume the local OMP version matches this skill's reference version. | Check `omp --version` when local/runtime compatibility matters. |
| Edit `references/official/*` manually. | They are overwritten by the sync action. |
| Disable `secrets.enabled` to simplify output. | It leaks keys into provider requests. |

## Decision tree (core workflow)

```text
1. User triggers omp-ops (config, providers, keys, search, modelRoles, etc.)
   |
   v
2. Answer using references/official/ for authoritative OMP behavior
          and references/providers/ for quick provider matrices
   |
   v
3. Check local OMP version only when the answer depends on installed runtime behavior
```

## When to use this skill

Use this skill when the user asks about any of the following:

- Model provider setup: Anthropic, OpenAI, Google, Groq, OpenRouter, local
  engines (Ollama, llama.cpp, LM Studio), custom providers in `models.yml`.
- API key handling: env vars, `.env`, `agent.db`, `/login`, auth broker.
- Search providers: Exa, Brave, Tavily, SearXNG, Perplexity, z.ai, Kagi,
  Jina, Parallel, Anthropic search, Codex search, Kimi/Moonshot search.
- `modelRoles`, `cycleOrder`, `modelProviderOrder`, `enabledModels`,
  `disabledProviders`.
- `.env` precedence, `PI_CODING_AGENT_DIR`, profiles.

## Reference file rules

| Directory | Purpose | May you edit? |
|---|---|---|
| `references/official/` | Auto-synced copies of official OMP docs (`docs/*.md`). | **No.** These are overwritten by `sync-from-official`. |
| `references/providers/` | Skill-authored provider matrices and quick-start guides. | Only when official docs change or a provider is missing. |
| `references/architecture.md` | OMP config layout, `config.yml`, `agent.db`, `.env`, `modelRoles`. | Only when official docs change. |
| `references/security.md` | API key rules, forbidden actions, redaction. | Only when official docs change. |
| `references/VERSION` | Current skill version `<omp-version>-<revision>`. | Updated by sync/push scripts only. |
| `references/sync-state.json` | Last official version and sync timestamp. | Updated by sync script only. |

Always prefer `references/official/` for authoritative behavior and
`references/providers/` for concise lookup tables.

## Key facts

### Config precedence

```text
built-in defaults
  <- global ~/.omp/agent/config.yml
  <- project <cwd>/.omp/config.yml
  <- CLI --config overlays
  <- runtime overrides (--model, --smol, etc.)
```

Objects deep-merge; arrays and scalars are **replaced wholesale** by the
higher layer.

### `.env` precedence

```text
process env
  <- <cwd>/.env
  <- ~/.omp/agent/.env
  <- ~/.omp/.env
  <- ~/.env
```

`OMP_*` keys are mirrored to `PI_*` in each parsed `.env`.

### Credential resolution order

```text
runtime override (e.g. --api-key)
  <- models.yml apiKey on custom provider
  <- stored API key in agent.db
  <- stored OAuth in agent.db
  <- provider env var / .env
  <- models.yml fallback resolver
```

### Built-in model roles

`default`, `smol`, `slow`, `vision`, `plan`, `designer`, `commit`, `tiny`,
`title`, `task`, `advisor`. Values may append `:minimal`, `:low`, `:medium`, `:high`,
  `:xhigh`.

### Local engines

`ollama`, `llama.cpp`, `lm-studio` are discovered keyless by default unless
explicitly configured or listed in `disabledProviders`.

### Search provider auth

| Provider | Primary env var |
|---|---|
| Exa | `EXA_API_KEY` |
| Brave | `BRAVE_API_KEY` |
| Tavily | `TAVILY_API_KEY` |
| SearXNG | `SEARXNG_ENDPOINT` (+ optional `SEARXNG_TOKEN`) |
| Perplexity | `PERPLEXITY_API_KEY` or `PERPLEXITY_COOKIES` |
| z.ai | `ZAI_API_KEY` |
| Anthropic search | `ANTHROPIC_SEARCH_API_KEY` |
| Codex search | `OPENAI_API_KEY` or stored Codex OAuth |

## Verification Checklist

Before answering, confirm:

- [ ] No real API key, token, or password appears in the final response.
- [ ] `references/official/` was consulted for behavior that may have changed.
- [ ] `references/providers/` was consulted for provider-specific env vars.
- [ ] `modelRoles` examples use canonical or concrete selectors correctly.
- [ ] Project/global scope and array-replacement behavior were mentioned when
      relevant.
- [ ] The user was directed to `/login` or env vars instead of being told to
      paste a key into a committed file.

## When this skill doesn't have the answer

If the user's question is not covered by `references/official/` or `references/providers/`, guide them to search existing issues on the upstream OMP repository before guessing:

- Use GitHub issue search: `https://github.com/can1357/oh-my-pi/issues?q=is%3Aissue+<keywords>`
- Common filters:
  - `is:issue is:open <error message>`
  - `is:issue <provider name> <config key>`
  - `is:issue modelRoles`
  - `is:issue search provider`
- If no matching issue exists and the problem is reproducible, suggest opening a new issue with:
  - `omp --version`
  - Minimal config / `.omp/config.yml` snippet (redact keys)
  - Exact error message or unexpected behavior

Do not invent workarounds that are not documented or verified by an existing issue/PR.

## See also

- `references/architecture.md` — config layout, `config.yml`, `agent.db`, `.env`, `modelRoles`.
- `references/security.md` — API key rules and redaction.
- `references/providers/search.md` — search provider matrix.
- `references/providers/models.md` — model provider keys and `modelRoles` setup.
- `references/official/` — authoritative copies of OMP docs after sync.
