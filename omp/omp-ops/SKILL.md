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
  OpenRouter, Novita, SiliconFlow, local engines (Ollama, llama.cpp, LM Studio), custom
  providers in `models.yml`, and `providers.anthropic.serverSideFallback`.
- API key handling: env vars, `.env`, `agent.db`, `/login`, auth broker.
- Search providers and caveats: Exa, Brave, Tavily, DuckDuckGo
  datacenter/shared-egress limitations, SearXNG, Perplexity, z.ai, Kagi, Jina,
  Parallel, Firecrawl, Anthropic search, Codex search, Kimi/Moonshot search.
- `modelRoles`, `cycleOrder`, `modelProviderOrder`, `enabledModels`,
  `disabledProviders`, `task.softRequestBudgetNotice`, `task.maxConcurrency`,
  `task.maxRecursionDepth`, and per-call `task.effort` selection.
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
  <- stored OAuth in agent.db
  <- API key saved by /login
  <- provider env var / .env
  <- other stored API key
  <- models.yml fallback resolver
```

### Built-in model roles

`default`, `smol`, `slow`, `vision`, `plan`, `commit`, `tiny`,
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
### Recent OMP 16.2.9–18.1.10 operator notes
- 18.1.8–18.1.10: background task structured results use `agent://<id>` when inline JSON is unsuitable; eval `agent()`/`completion()` use async handles (`await`/`wait`); browser/computer APIs use JS/Python eval preludes; image questions use `read <image>?q=` and `images.questionTimeoutMs`; `yield` accepts direct `data`/`error`. Review integrations before upgrading.
- Unreleased `retry.waitForUsageReset` may wait through provider-reported quota resets beyond `retry.maxDelayMs`; treat it as pending until the official settings schema is documented.
- 17.2.6 adds `/reset`, which clears live context while retaining the session id and on-disk transcript.
- 17.2.5 changes computer to persistent JavaScript runs and edit replace mode to one `{path, old_string, new_string, replace_all?}` operation; review old batch configs before upgrading.
- 17.2.3 preserves backend codes and messages from Codex Web Search SSE errors; use that detail when separating provider failures from credential or endpoint configuration problems.
- 17.2.2 reserves `Ctrl+L` for `app.live.toggle` (live voice mode) and moves
  `app.display.reset` to `Alt+L`. Hashline editing and plan guidance now use
  the unified `PUT`/`CUT` grammar with `.=` ranges and named registers.
  For Kitty images inside tmux, `PI_KITTY_PLACEHOLDERS=1` opts into Unicode
  placeholders; `PI_NO_KITTY_PLACEHOLDERS=1` takes precedence and disables them.
- 17.2.1 adds default-off `security.enabled`; canonical findings and SARIF-compatible results use read-only `security://`; imported bundles remain distinct from native attribution.
- 17.2.0 adds `providers.autoThinkingMaxEffort: max` for supported models (default `xhigh`) and `/login exa` as an alternative to `EXA_API_KEY`.
- 17.1.8 adds `omp cleanse`, conversational `/guided-goal`, and temp-directory screenshot saving.
- 18.1.9 replaces the `inspect_image` tool and `/vision` controls with `read <image>?q=<question>`; `inspect_image.timeoutMs` migrates to `images.questionTimeoutMs`. Browser/computer automation now uses JS/Python eval preludes with reusable handles. In 18.1.10, subagent `yield` takes `data`/`error` directly instead of a nested `result` wrapper.
- 17.1.6 makes the per-spawn `task.effort` hint opt-in: set `task.enableEffort` before relying on `lo`, `med`, or `hi`; use `task.maxEffort` to cap resolved effort for spawned tasks and retries.
- 17.1.4 removes the per-call `model` selector from `task` and `agent()`; spawned work uses the agent's configured model. Keep using `task.effort` (`lo`, `med`, or `hi`) when only the thinking level needs to vary.
- 18.1.5 removes the bundled `designer` subagent and model role; remove `designer` / `@designer` from model-role configurations.
- 18.1.7 adds the Apple Silicon MLX backend for local tiny models (`PI_TINY_DEVICE=mlx` or `metal`) and removes Ruby/Julia eval backends. Eval `agent()`/`completion()` calls now return asynchronous handles; synchronize them with `await`/`wait` rather than the removed `parallel()`/`pipeline()` helpers.
- 17.0.9 adds keyless Firecrawl search when `firecrawl` is explicitly selected; automatic fallback still requires credentials, while the 18.1.6 `providers.fetch` URL reader requires `FIRECRAWL_API_KEY`. It also defaults
  `task.isolation.apply` and `mcp.renderMarkdownResults` to `true`, respectively
  applying successful isolated task changes to the parent checkout and rendering
  non-JSON MCP text as Markdown. Set either key to `false` when retaining
  artifacts or raw MCP text is required.
- 17.0.7 preserves custom-provider model ids beginning with `@` (such as Portkey ids); keep those ids exact rather than normalizing them to a bundled model id.
- 17.0.6 adds Codex-subscription image generation through `openai-codex`,
  independent of the active chat model, and makes Codex web search honor
  custom endpoints without forwarding official OAuth credentials there.
  Treat custom endpoint routing as a credential boundary and fail closed when
  the explicitly selected provider has no usable credentials.
- Anthropic and ChatGPT/Codex OAuth accounts are organization/workspace scoped;
  select the intended workspace during login when one email has multiple seats
  or subscriptions.
- 17.0.4 adds `PI_CONFIG_FILES`, a platform-delimited (`:` on Unix, `;` on
  Windows) list of settings overlays loaded before explicit `--config`
  overlays. Use it for wrapper-injected settings and keep credentials out of
  the referenced files.

- 17.0.3 removes the unreliable Bing and Yahoo HTML-scraping web-search
  providers. Do not treat either provider as an available fallback.
- 17.0.3 clarifies `PI_TUI_RESIZE_IN_PLACE`: truthy values force in-place
  resize without borrowing the alternate screen; false values force the
  alternate-screen fast path. Warp defaults to the in-place path.

- 17.0.1 fixes `omp grep` paths with a stray leading colon, makes xAI web
  search honor configured proxy endpoints and headers without forwarding
  official OAuth tokens to custom endpoints, and improves Windows broken-pipe
  handling. These are runtime fixes; they do not change provider credentials
  or search-provider setup.

- 17.0.0 consolidates `irc`, `job`, and `launch` into the `hub` tool and
  exposes discoverable custom, extension, MCP, image, and TTS tools through
  `xd://` devices. Use `read xd://<tool>` for documentation and
  `write xd://<tool>` for execution; do not rely on the removed hidden
  `resolve` or `search_tool_bm25` paths.
- 17.0.0 removes the SSH agent tool and the legacy `report_finding` tool.
  SSH host management remains available, but remote command execution is no
  longer an OMP agent-tool workflow.
- 17.0.0 adds opt-in `edit.enforceSeenLines` and optional generic-task
  prewalk via `prewalk` / `task.agentPrewalk` / `task.prewalk`. The default
  prewalk behavior remains off.
- 18.1.2 uses XML-shaped sloppy edits (`<SM:EDIT>`, `<SM:FIND>`, `<SM:PUT>`) and can recover stray inline payloads; preserve copy-ready error payloads and check `edit.recoverInlineEdits` before blaming the model or file contents.
- 16.5.0 replaces the `--reasoning-slide-*` flag family with `--prewalk`,
  `--prewalk-into <model>`, and `--no-prewalk`; use the new flags in current
  operator guidance.
- 16.5.0 model configuration supports `~/.omp/agent/models.yaml` as a fallback
  beside `models.yml`; role aliases use `@role`, with `*` selecting `@default`.
  Quote `@` aliases in YAML values.
- 16.5.1 Anthropic OAuth accounts are organization-scoped: separate Team and
  personal subscriptions under one email may be selected and rotated as
  distinct accounts.

- 16.4.8 search: Perplexity forces retrieval for search-heavy workflows; JS eval
  cells keep top-level `function` and `var` declarations across cells.

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
- [ ] For search questions, `searxng.engines` and supported query directives
      are checked against the official mirror before giving configuration advice.
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
