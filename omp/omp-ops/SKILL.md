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
2. Answer using references/official/ for authoritative OMP behavior,
          references/providers/ for quick provider matrices, and
          `references/providers/tips.md` for hidden/undocumented runtime switches
   |
   v
3. Check local OMP version only when the answer depends on installed runtime behavior
```

## When to use this skill

Use this skill when the user asks about any of the following:

- Model provider setup and API behavior: Anthropic, OpenAI, Google, Groq,
  OpenRouter, Novita, local engines (Ollama, llama.cpp, LM Studio), custom
  providers in `models.yml`, and `providers.anthropic.serverSideFallback`.
- API key handling: env vars, `.env`, `agent.db`, `/login`, auth broker.
- Search providers and caveats: Exa, Brave, Tavily, DuckDuckGo
  datacenter/shared-egress limitations, SearXNG, Perplexity, z.ai, Kagi, Jina,
  Parallel, Anthropic search, Codex search, Kimi/Moonshot search.
- `modelRoles`, `cycleOrder`, `modelProviderOrder`, `enabledModels`,
  `disabledProviders`, `task.softRequestBudgetNotice`, `task.maxConcurrency`,
  and `task.maxRecursionDepth`.
- Hidden/undocumented runtime switches shown in OMP `tips.txt`, such as
  `PI_DIALECT`, `/btw`, `/tan`, `/force`, `/shake`, magic keywords
  (`ultrathink`, `orchestrate`, `workflowz`), or `omp stats`.

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
`title`, `task`, `advisor`. Values may append `:minimal`, `:low`, `:medium`,
`:high`, `:xhigh`, `:max`.

Built-in subagent names changed separately from model roles: `quick_task` was
renamed to `sonic` in 16.2.9, built-in `oracle` was removed in 16.2.9, and
`Tester` was added in 16.2.9.

### Local engines

`ollama`, `llama.cpp`, `lm-studio` are discovered keyless by default unless
explicitly configured or listed in `disabledProviders`.
For OMP 16.3.11+, `llama.cpp` discovery also respects advertised
`architecture.input_modalities`, so a router preset that reports image input
should not be treated as text-only.

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

### Recent OMP 16.2.9–16.5.1 operator notes

- 16.5.0 replaces the `--reasoning-slide-*` flag family with `--prewalk`,
  `--prewalk-into <model>`, and `--no-prewalk`; use the new flags in current
  operator guidance.
- 16.5.0 model configuration supports `~/.omp/agent/models.yaml` as a fallback
  beside `models.yml`; role aliases use `@role`, with `*` selecting `@default`.
  Quote `@` aliases in YAML values.
- 16.5.1 Anthropic OAuth accounts are organization-scoped: separate Team and
  personal subscriptions under one email may be selected and rotated as
  distinct accounts.

- 16.4.8 search: Perplexity now forces retrieval for all queries, improving
  reliability on search-heavy workflows.
- 16.4.8 JS eval cells keep top-level `function` and `var` declarations across
  cells even when the defining cell contains top-level `await`.

- 16.3.14 tightened TUI rendering: raw thinking blocks now strip HTML comment
  noise, and unfinalized tool blocks no longer pin the live-region scroll seam.
- 16.3.11 title generation is more reliable: the runtime now uses
  marker-based parsing for all models, and JSON-shaped title replies are
  unwrapped to the bare title instead of being displayed verbatim.
- 16.3.11 llama.cpp discovery honors per-model `architecture.input_modalities`
  from `/v1/models`, which prevents image-capable router presets from being
  misclassified as text-only.

- 16.3.0 config additions: `providers.anthropic.serverSideFallback` opt-in
  Anthropic server-side fallback beta; `task.softRequestBudgetNotice` enables
  subagent soft-budget wrap-up notices while keeping graceful abort guard
  active.
- 16.3.0 reliability: signed thinking/reasoning payload persistence fixed for
  Anthropic/OpenAI/Google; session shutdown saves editor drafts and cleans
  background jobs; git clone/fetch gets a separate 30-minute network-transfer
  deadline; `task.maxConcurrency` and `task.maxRecursionDepth` bypasses fixed.
- 16.3.0 tools/search: `apply_patch`/edit dirty-buffer and overwrite handling
  fixed; grep/ast_grep URL-scope parsing fixed for `www.` and collapsed-scheme
  spellings; Tavily retries without recency filters when content is empty;
  DuckDuckGo error clarity documents datacenter/shared-egress limitations.
- 16.3.2 search tools: `grep`, `glob`, and `ast_grep` now take a single
  optional `path` string instead of a `paths` array; semicolon-delimited
  multi-path input is supported, and omitted `path` searches the workspace
  root.
- 16.4.2 adds `novita` provider auth via `NOVITA_API_KEY` and extends
  thinking suffix support with `:max`.
- 16.2.12 breaking model behavior: canonical-alias grouping removed;
  `equivalence` in `models.yml`/`models.json` is inert; `omp models canonical`
  and the interactive `CANONICAL` tab were removed; model selectors now resolve
  by exact/flat ID plus provider preference.
- 16.2.9 subagents: `quick_task` renamed to `sonic`; built-in `oracle`
  removed; built-in `Tester` added.
- 16.2.7 provider behavior: Google Gemini/Vertex service-tier support and
  Vertex bearer access-token/API-key precedence changes; Google Vertex AI
  supported.

## Verification Checklist

Before answering, confirm:

- [ ] No real API key, token, or password appears in the final response.
- [ ] `references/official/` was consulted for behavior that may have changed.
- [ ] `references/providers/` was consulted for provider-specific env vars.
- [ ] `modelRoles` examples use exact flat IDs or provider/model selectors; do not document canonical alias coalescing as active behavior.
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
- `references/providers/models.md` — model provider keys, `modelRoles` setup,
  and owned in-band tool-call dialects (`PI_DIALECT`).
- `references/providers/tips.md` — verified catalog of OMP `tips.txt` tricks,
  hidden env vars, and common wording caveats.
- `references/official/` — authoritative copies of OMP docs after sync.
