# Changelog

## [Unreleased]

### Added

- `omp usage` now surfaces auto-disabled credentials as red `✗` tombstone rows (identity, how long ago, the shortened upstream cause — e.g. `Refresh token expired` — and a re-login hint), including a provider section when no active credential remains. User-driven tombstones (`replaced by newer credential`, `deleted by user`) and API-key rows stay hidden. Requires a broker with `GET /v1/credentials/disabled`; older brokers degrade to no tombstone rows.
- `omp usage` warns about Anthropic's ~30-day OAuth grant lifetime: accounts whose interactive login (`authorizedAt`) is within a week of the deadline get a yellow `⚠ re-login within <time>` line, and past-deadline accounts a red one. Grants die server-side exactly ~30 days after login regardless of refresh rotation, so this is the only warning before the broker auto-disables the row.

### Fixed

- Fixed the Docker `natives-builder` stage failing to build releases ≥ 17.1.1: the native audio stack added bindgen (miniaudio needs libclang) and a bundled-opus CMake build (needs cmake + make), none of which were installed in the slim builder image.
- Fixed `omp usage` duplicating org-less legacy accounts as "no usage data" rows whenever any sibling report carried an organization (mixed pools of pre-org-capture rows and fresh org-scoped logins): an org-less account is now covered by its own org-less report, while org-attributed sibling reports still never count as its coverage.
- `omp usage` revalidates the broker credential snapshot before rendering: live usage reports were previously paired with a disk-cached account list up to an hour old, so a just-completed re-login (org-less row upserted to org-scoped) rendered as a phantom duplicate until the cache expired.

## [17.1.3] - 2026-07-24

### Fixed

- Fixed the in-process `find` builtin's `-exec`/`-execdir` children inheriting the omp process's real stdout/stderr, so commands like `find … -exec ls -ld {} \;` spammed their output straight into the terminal (corrupting the TUI) instead of the tool's captured output, and bypassed shell redirects. Exec children now stream stdout/stderr back through the shell's scope streams (matching `xargs`/`ifne`) and run with the shell's exported environment (`env_clear` + scope snapshot) instead of the host process environment.
- Fixed `ast_edit` erroring with "`lang` is required" — an argument that no longer exists in the tool schema — when `paths` resolved to files of multiple languages (e.g. a crate directory with `.rs` + `.toml`). Mixed-language paths now rewrite per file: each file is parsed in its own inferred language, patterns are compiled per language, and a pattern that doesn't parse in some matched language simply skips those files.
- Fixed the `retain` tool's TUI renderer crashing when streaming arguments temporarily expose a non-array `items` value ([#6528](https://github.com/can1357/oh-my-pi/issues/6528)).
- Fixed Edit and Write tools failing with `Settings not initialized` in isolated sessions by using each tool session's settings for generated-file guards, with safe schema defaults for standalone guards and inline-image rendering ([#6549](https://github.com/can1357/oh-my-pi/issues/6549)).

## [17.1.2] - 2026-07-24

### Added

- Added in-process moreutils-style shell builtins to the bash tool's embedded shell: `ts` (timestamp lines; `-i`/`-s` elapsed modes, `-m` monotonic clock, `-r` relative rewriting of RFC3339/syslog timestamps, `%.S`/`%.s`/`%.T` subsecond extensions), `sponge` (soak stdin fully before atomically writing the target, so `foo file | ... | sponge file` works; `-a` appends), `ifne` (run a command only when stdin is non-empty; `-n` inverts and passes non-empty stdin through), `isutf8` (streaming UTF-8 validation with line/char/byte diagnostics; `-q`, `-l`, `-i`), `combine` (boolean `and`/`not`/`or`/`xor` on the lines of two files, `-` for stdin), and `errno` (errno name/number/description lookup with `-l` list and `-s` search; unix only). Like the uutils-backed builtins, they run in-process against the command's own stdio, resolve paths against the shell working directory, honor cancellation, and are disabled by `PI_DISABLE_UUTILS_BUILTINS`.
- The bash tool prompt now lists the available shell builtins (`mkdir` through `jq`, `rm`/`mv`/`ln`, and the moreutils set) so the model relies on them without existence checks; the line is dropped when `PI_DISABLE_UUTILS_BUILTINS` disables the builtins and omits unix-only `errno` on Windows.
- Sessions using a broker-backed auth store now report each completed request's token usage and cost to the auth broker (batched, 10s cadence) so the broker can track actual token burn per client install
- Added a per-spawn `effort` parameter to the `task` tool (`"lo"` | `"med"` | `"hi"`): each selector maps onto the resolved model's supported thinking range (lowest, middle, and highest level — whatever the model tops out at, e.g. `high`, `xhigh`, or `max`) and overrides the agent's default selector, including `auto`. Omitting `effort` keeps the existing automatic per-prompt thinking classification.
- Added `searxng.engines` setting for the SearXNG web search provider: a comma-separated list of engine names or bang shortcuts (e.g. `ddg, br, startpage`) sent as the API's `engines=` parameter. Shortcuts are resolved to canonical engine names via the instance's `/config` endpoint (cached per endpoint; entries pass through verbatim if `/config` is unreachable). Bang syntax in queries (`!ddg foo`) continues to pass through to the instance, and external bangs (`!!g`) are now stripped client-side since SearXNG answers them with an HTTP redirect even for JSON requests.
- Web search queries now understand Google-style directives on every provider: `site:`/`-site:` (plus `domain:`/`host:` aliases), `after:`/`before:`/`since:`/`until:` date bounds, `inurl:`/`intitle:`/`intext:`/`allin*:`, `filetype:`/`ext:`, `lang:`, quoted phrases (including smart quotes), `+term`, `-`/`NOT` exclusions, and `OR`/`|` groups. A shared parser (`web/search/query.ts`) structures the query once per request; each provider maps constraints onto native API filters where the upstream supports them (Perplexity domain/date/language filters on both the API-key and ask paths, Tavily `include_domains`/`exclude_domains` + `start_date`/`end_date`, Exa domain lists + published-date bounds on API and MCP paths, Anthropic `allowed_domains`/`blocked_domains`, xAI `filters.allowed_domains`/`excluded_domains`, Parallel `source_policy`, Brave absolute `freshness` ranges, Firecrawl `tbs=cdr` date ranges, Jina `X-Site`, SearXNG `language`) and otherwise re-emits only the operator syntax its engine parses (full Google syntax for Gemini grounding, OpenAI, Kagi, and the credential-free scrapers — with scraper-hostile path-`site:`/`inurl:` operators demoted to plain keywords; conservative subsets for DuckDuckGo, Mojeek, Kimi, Z.AI, TinyFish, and Synthetic). The pipeline then applies a lenient post-filter to every response: constraints the engine ignored are enforced on the returned sources, and any constraint dimension that would eliminate every result is relaxed and reported to the model (`Note: no results matched \`site:...\`; the constraint was relaxed`) instead of returning nothing. Directive-free queries are passed through byte-identical everywhere.
- Eval and browser `run` code previews are now prettified for display: minified/compact agent-written cells are expanded by conservative streaming formatters (Python, JavaScript, Ruby, Julia) that indent block structure, split statements, normalize operator spacing (JS), and expand object literals wider than 100 columns onto one property per line — purely for rendering, the executed source is untouched. The formatters handle in-flight prefixes (unterminated strings/comments/blocks) without inventing closers, and layout decisions are prefix-stable so already-rendered lines never reflow while a call streams.

### Changed

- Large pastes saved via the large-paste menu now insert `local://paste-N.md` references (previously `local://attachment-N`), so the saved paste carries a markdown extension and a clearer name.
- Raw SSE debug capture now trims over-budget events smartly instead of chopping off the tail: tool definitions inside `data:` payloads are compacted first (name kept, schema/description elided — often enough to keep the whole payload as valid JSON), and anything still over the 64k cap keeps its head and tail with a `: omp-debug-elided chars=N` comment marking the removed middle, so trailing fields like `usage` stay visible.
- The `web_search` tool prompt now tells the model to never search for content that is programmatically accessible or has a known URL (GitHub, known arXiv papers, Wikipedia pages, official docs) and to `read` the URL directly instead.

### Fixed

- Fixed `todo` calls that omit `op` hard-failing validation ("op must be operation to apply (was missing)"): the tool now validates leniently and infers the op for unambiguous payloads (`list` → `init`, `phase`+`items` → `append`, bare `items` on an empty list → `init`); `op` stays required in the schema, and ambiguous op-less calls surface the schema error as a retryable tool error.
- Fixed credential-free web search engines (SearXNG, DuckDuckGo, Google, Startpage, Ecosia, Mojeek, and the Public Web fan-out) returning zero results for queries with `site:` paths (e.g. `site:github.com/owner/repo`) or `inurl:` operators: scraper engines only match `site:` against a bare domain and DuckDuckGo ignores `inurl:` entirely, so such queries silently emptied the result set and fell through to the next provider in the chain. A shared `formatScraperQuery` formatter now structurally demotes path-carrying `site:` and all `inurl:` values to plain search terms (covering OR-grouped and quoted directives) while preserving bare-domain `site:` filters, negated operators, and each engine's supported syntax; the pipeline post-filter still enforces the demoted constraints on returned sources.
- Fixed `ast_edit` previews reading like applied edits to the model: the `⟨proposed⟩` badge was TUI-only, so the model-visible result (hashline header + `-`/`+` rows, identical to applied edit output) carried no staged-proposal signal. The preview result now leads with a "Staged as a proposal — files NOT modified yet" notice naming `xd://resolve`/`xd://reject`, the injected resolve reminder names the source tool, and the `ast_edit` tool prompt documents the two-phase flow.
- Fixed the `hub` launch `ps`/`list` response burying the active process behind every exited one and growing without bound in long-lived projects: the broker now lists non-terminal daemons first (oldest to newest) and caps exited/failed history at the 10 most recently exited, so the active launch is immediately visible and the response stays bounded. Broker recovery also preserves each already-terminal daemon's real exit time instead of overwriting it with the restart timestamp, so the history cap keeps the genuinely most-recently-exited processes after an idle-broker restart ([#6517](https://github.com/can1357/oh-my-pi/issues/6517)).
- Fixed a tool call rendering twice in the transcript. A mid-stream `rebuildChatFromMessages` (from `/shake`, auto-compaction, or a settings toggle) preserves the live `pendingTools` components across the clear+replay, but that preservation assumed every pending-tool component was still dangling. When a tool's result had already landed in the session entries while its component still lingered in `pendingTools`, the replay reconstructed the completed block *and* the preserved live component was re-appended, so the same block appeared twice; resolved components are now dropped from preservation and owned by the replay ([#6516](https://github.com/can1357/oh-my-pi/issues/6516)).
- Fixed `--model default` (and other bare role names) resolving to the bundled `cursor/default` catalog model instead of the configured `modelRoles.default` role. `resolveCliModel`'s exact-match phase ran its unauthenticated catalog fallback before role resolution, so a bundled id colliding with a reserved role name shadowed a configured, runnable role — failing with `No API key found for cursor` on machines without Cursor credentials. The catalog fallback is now deferred so an authenticated exact model still wins, a configured role beats an unauthenticated catalog-only id, and the catalog id is still recovered when no role matches ([#6508](https://github.com/can1357/oh-my-pi/issues/6508)).

### Removed

- Removed the `model` parameter from `task` and `agent()`: explicit per-spawn model selectors and fallback chains are no longer supported; spawns always use the agent's configured model

## [17.1.1] - 2026-07-24

### Added

- Added the `/session pin` subcommand and account picker to pin provider OAuth accounts for the current session
- Added the disabled-by-default `computer` essential tool with configurable enablement, backend, display, and maximum width/height settings. Native desktop execution runs through a `DesktopSession` worker; observation uses read approval, input uses exec approval, and provider checks always prompt and fail closed.
- Added the `/computer` slash command (`on`/`off`/`status`/toggle) to enable or disable the computer tool for the current session without persisting settings.
- Exposed `computer` to models without native OpenAI computer-use support as a regular function tool with a typed GA action schema; the same native desktop backend and approval policy apply on both paths.
- Hardened computer action ingress: action-specific fields, modifier/key arrays, coordinates, drag points, and scroll deltas fail closed before native input; numeric fields must be signed 32-bit integers and coordinates must be non-negative.

### Changed

- Replaced Chromium-backed `/live` media and external speech recorder/player subprocesses with the cross-platform native microphone, speaker, Opus, and WebRTC stack from `@oh-my-pi/pi-natives`.

### Fixed

- Fixed live-call attestation depending on the ChatGPT desktop app being installed: `generateLiveAttestation` now mints DeviceCheck tokens in-process through the `@oh-my-pi/pi-natives` `deviceCheckGenerateToken` binding instead of probing `/Applications` for the app's `devicecheck.node` addon, so the `x-oai-attestation` header works on hosts without the desktop app and drops the `createRequire` addon probing; the attestation provider is now wired up to `@oh-my-pi/pi-ai` for ChatGPT-OAuth Codex requests.
- Fixed `xd://` device execution failures rendering as `write` errors instead of using the mounted tool's own error renderer.
- Fixed custom tools without bespoke renderers losing the default state-tinted card when mounted under `xd://`; dispatched calls now keep their label, arguments, status, output preview, and expansion affordance instead of dumping a bare result line into the transcript.
- Fixed the clipboard image-paste keybind mangling copied URL text into a bogus path error on macOS (e.g. `Image not found at /https/::i.can.ac:CE4Ek3.png` for a copied `https://i.can.ac/CE4Ek3.png`). AppleScript's `the clipboard as «class furl»` coerces plain *text* into a file URL by treating the string as an HFS path (`:`↔`/` swap), so `readMacFileUrlsFromClipboard` returned a garbage path that dead-ended in `handleImagePathPaste` instead of falling through to the text paste. The script now bails early via `clipboard info for «class furl»` unless the pasteboard actually carries a `public.file-url` representation, so URL/text clipboards paste as text.
- Fixed spilled tool-output artifact descriptors leaking on error/abort paths. `OutputSink.dump()` was the only path that closed the spill `Bun.FileSink`, but the bash and Python executors re-throw on failure and their `finally` blocks never closed the sink, so a large-output command that errored leaked the artifact descriptor until an unrelated read (e.g. a `SKILL.md` load) hit `EMFILE`. `OutputSink` now exposes an idempotent `dispose()` that closes the sink exactly once, wired into every executor's `finally` ([#6463](https://github.com/can1357/oh-my-pi/issues/6463)).
- Fixed the first submitted prompt stalling while the local tiny-title worker started: the interactive submit handler now paints the pending user row before starting title generation, and startup prewarms an idle, unref'd worker so the first submit reuses a live subprocess instead of paying spawn latency ahead of the first frame ([#6462](https://github.com/can1357/oh-my-pi/issues/6462)).
- Fixed legacy Pi extensions failing validation when importing the upstream `keyText` keybinding helper ([#6470](https://github.com/can1357/oh-my-pi/issues/6470)).

## [17.1.0] - 2026-07-24

### Breaking Changes

- Replaced the `providers.webSearch` and `providers.image` single-preference configuration options with `providers.webSearchOrder` and `providers.imageOrder` priority lists. Existing configurations migrate automatically on startup.

### Added

- Added dynamic multi-root workspace context support, allowing users to manage multiple workspace directories mid-session via `/add-dir`, `/remove-dir`, and `/dirs` slash commands, or seed them at launch using the `--add-dir` CLI flag.
- Added `/live`, a Codex-authenticated real-time voice interface that streams microphone audio over WebRTC and routes coding tasks through the active agent session.
- Added opt-in usage-aware model fallback for rationed coding plans, including a `/usage` command to view live quantitative usage data and automatic fallback chain traversal.
- Added `error.notify` configuration to allow failed model turns to trigger distinct terminal or desktop notifications.
- Added auto-following light and dark themes to HTML session exports, with a `/export --themes` option to bundle selected TUI themes.
- Added owner-routed asynchronous job delivery, ensuring background bash and task results are injected directly into the owning subagent or agent session rather than the top-level session.
- Added background-on-steer capability for auto-backgrounded bash commands, allowing incoming user or peer messages to immediately background running commands.
- Added `friendlyName` support for hidden secrets, allowing model-visible placeholders to carry sanitized semantic labels, hashes, and case hints.
- Added support for Jujutsu (`jj`) repositories in the statusline `git` segment, displaying the nearest bookmark or change ID and retrieving working-copy change counts.
- Added `block` and `unblock` operations for tasks, introducing a `blocked` status for tasks waiting on external input to exclude them from incomplete-todo reminders.
- Added a toggle-list editor in `/settings` for managing array-of-enum settings like search and image provider orders.
- Added `models.yml` Bedrock Converse prompt-cache capability overrides for bundled and opaque inference profiles.
- Added `getServiceTiers()` and `setServiceTier()` extension APIs to read and modify the live per-family service tier for session requests.
- Added opt-in `omp bench --cache` for independent cold/warm prompt-cache benchmarking with stable-prefix controls.
- Added `tools.xdevDocs` prompt-doc modes and the `tools.xdevInlineDevices` glob allowlist to control which mounted device documentation is inlined into the system prompt.
- Added the opt-in `read.renderMarkdown` setting for formatted Markdown read previews.

### Changed

- Updated subagent behavior to inherit `async.enabled` and `bash.autoBackground.enabled` from parent sessions, and refined subagent run completion to wait for background jobs to settle.
- Added ordered `bash.patterns` command approval rules to allow, prompt, or deny bash commands by pattern.
- Updated Markdown file handling so all Markdown flavors (`.markdown`, `.mdx`, `.mdc`, etc.) respect the `read.summarize.prose` setting.
- Upgraded xAI web search to use `grok-4.5` at low reasoning effort instead of `grok-4.3`.
- Improved search provider resilience by cascading and falling back through other configured search providers when the preferred provider fails.
- Extended the bash tool's `direnv` and `devenv` auto-loading to all backends (including the ACP client terminal and interactive PTY) while honoring `direnv`'s local allow list.

### Fixed

- Fixed a path traversal vulnerability in blob reference resolution by rejecting non-canonical hashes in `parseBlobRef`.
- Fixed multiple edge cases in the secret obfuscation and redaction engine, including handling of context-sensitive regexes, placeholder key requirements in unwritable directories, friendly-name forgery vulnerabilities, and regex match boundaries straddling existing placeholders.
- Fixed a first-use race condition in `ArtifactManager` where concurrent callers could allocate duplicate artifact IDs.
- Fixed Vibe-mode session stability, resolving issues with workers disappearing across restarts, hanging during teardown, clobbering target tools during session switches, and resolving against incorrect models.
- Fixed concurrent MCP configuration mutations losing updates by serializing read-modify-write operations under a per-file lock with atomic writes.
- Fixed legacy extensions failing to load on npm/source-link installs due to transitive CommonJS dependency graph clobbering.
- Fixed `omp auth-gateway` commands bypassing the process-scoped OAuth account pool configured via environment variables.
- Fixed terminal transcript rendering issues where displaceable snapshots (like waiting polls and todo lists) spammed native scrollback.
- Fixed the terminal title to reflect the active agent run state (working, waiting, or blocked) when `tui.titleState` is enabled.
- Fixed the `browser` tool's `open` action ignoring timeouts during browser acquisition and leaking orphaned browser instances.
- Fixed the `write` tool silently creating empty files when a read-tool selector was mis-dispatched as a write.
- Fixed snapcompact archiving reproducing assistant reasoning (`¶think:` sections) into replayed frames for Anthropic-dialect models.
- Fixed Linux socket-mode DAP launches hanging indefinitely on connection failures.
- Fixed Plan Review annotations being discarded on dismissal and limited to headings.
- Fixed Assistant-mode TTS playback aborting prematurely when an agent continued after a tool call.
- Fixed absolute usage amounts rendering inconsistently across CLI, TUI, and ACP output surfaces.
- Fixed MCP sessions dropping tools from servers that finished connecting after the initial startup window.

## [17.0.9] - 2026-07-23

### Added

- Added per-call `model` selection to the `task` tool, including per-item batch selectors, fallback chains, and explicit reasoning suffixes.
- Added Firecrawl keyless mode: explicitly selecting `firecrawl` as the web-search provider now works without `FIRECRAWL_API_KEY` by calling the Firecrawl REST API without an `Authorization` header; the automatic provider chain remains credential-gated (#4332).
- Added `mcp.renderMarkdownResults` (enabled by default): non-JSON MCP text results render as Markdown in the terminal transcript; set it to `false` to keep raw text.

### Changed

- Adjusted retry fallback handling to recognize discovery-only and runtime extension providers, preventing spurious unknown-provider warnings.
- Restored Auto QA's ask-the-user default: `dev.autoqa` defaults to `true` again, so the first `xd://report_issue` write pops the consent dialog instead of the feature being silently off. Denying consent (or `dev.autoqa: false` / `PI_AUTO_QA=0`) fully disables prompt injection; an explicitly configured `dev.autoqa: true` overrides a past denial. Also restored the #1224 guarantee lost in the xd:// device consolidation: the grievance row is inserted only after consent resolves to granted (or `PI_AUTO_QA_PUSH=1`), so nothing touches the local database while consent is unset or denied.

### Fixed

- Fixed Auto QA grievance recording silently dropping every report since the xd:// device consolidation: `openAutoQaDb` treated the database file path (`~/.omp/autoqa.db`) as a directory and tried to open `autoqa.db/autoqa.db` inside it, which fails on legacy installs (the flat file blocks the directory) and fresh ones alike (SQLite does not create parent directories). Also restored the `busy_timeout` pragma dropped in the same refactor (#2421). Renamed `getAutoQaDbDir` to `getAutoQaDbPath` to match what it returns.
- Fixed the setup wizard hiding the selected row on short terminals (e.g. 24x80): the provider sign-in, theme, and web-search lists now fit their windows to the visible height, and decorative chrome (sign-in hint, theme mock preview) yields to the list when space is tight.
- Fixed restored sessions replaying terminal aborted or errored assistant turns, which could repeatedly fail continuation from an assistant role; `/retry` now consults the persisted transcript so the failed turn remains retryable without re-entering provider context.
- Fixed `get_available_models` and `set_model` RPCs racing background model discovery on cold start by awaiting the in-flight refresh before reading the registry. RPC/ACP clients that query the catalog or select a model immediately after session ready previously saw only statically-bundled models until discovery completed seconds later.
- Fixed deferred `--model <provider>/<pattern>` CLI resolution failing on cold start with "Model not found" when the selector pointed at a discovery-backed provider (proxy / ollama / lm-studio / llama.cpp / litellm). The deferred retry now runs a cache-aware discovery pass before resolving, mirroring the default-role fallback's cold-cache race fix (issues #6114, #6162).
- Fixed MCP tool calls that return a `WWW-Authenticate` challenge by preserving the structured metadata, completing the configured OAuth flow, and retrying the call once on the refreshed connection.
- Fixed the Hindsight API token setting being absent from the Memory tab, so authenticated servers can be configured entirely in the TUI.
- Fixed aborted-task follow-up hints pointing at `history://` transcripts that cannot resolve: the hint now reports the transcript as unavailable when the agent ref retains no session file, while still-resumable agents keep their `hub` resume hint.
- Fixed compiled binaries failing to load legacy Pi extensions with minified imports, `pi-ai/compat`, or transitive runtime dependencies. The compatibility loader now follows compact static imports, resolves transitive on-disk ESM imports and CommonJS requires with package conditions, and restores the legacy `copyToClipboard` and `decodeKittyPrintable` root exports used by `pi-vimmode` and `pi-web-access`.
- Fixed a budget-aborted keep-alive subagent becoming an unkillable registration with no `hub`-level stop. A subagent force-stopped for exceeding its soft request budget is kept resumable (status `idle`, adopted by the lifecycle) so its context can be salvaged, but its async job row settles and is reaped after ~5 min — after which `hub cancel <id>` could only report `Background job not found` because it consulted the job manager alone. `hub cancel` now falls through to the agent registration: for an id the caller spawned that has no live job, it aborts any in-flight turn, disposes the session, and drops the registration (the interactive Agent Hub `x` and collab `kill` already did this; the model-facing `hub` did not). Cross-agent kills stay impossible and Main/advisor refs are never targeted ([#6315](https://github.com/can1357/oh-my-pi/issues/6315)).
- Fixed Agent Hub fallback rows hiding routing provenance and the resolved provider/model ([#6316](https://github.com/can1357/oh-my-pi/issues/6316)).
- Reduced format-on-write latency by avoiding cold language-server startup when diagnostics are disabled.
- Rewrote the `/guided-goal` interviewer rubric around loop-engineering: deterministic success criteria, verification commands, attempt caps, scope boundaries, and stop conditions. Ready objectives must use the five-section structured markdown form.
- Added `task.isolation.apply` (default `true`) to choose whether successful isolated `task` runs automatically apply their changes to the parent checkout or retain patch/branch artifacts for later integration.
- Added opt-in RPC protocol v2 negotiation with bounded, lossless chunking for stdout objects up to 64 MiB, plus stable cursor-based message pages for histories that should not travel as one response. Legacy JSONL clients remain on protocol v1, while the bundled TypeScript and Python RPC clients negotiate, reassemble, and drain message pages automatically.
- Fixed protocol v2 chunked framing materializing the whole base64 transport in memory: near-limit logical frames (~63 MiB) peaked around 686 MB RSS and over-ceiling frames allocated the full payload buffer before rejection. Chunk lines are now produced lazily from a single serialization, the 64 MiB ceiling is checked before any full-payload allocation, and RPC stdout writes honor backpressure line by line.
- Fixed the bundled TypeScript and Python RPC clients throwing when a `get_messages_page` cursor went stale mid-walk (e.g. a background bash appending a message between pages): the high-level `getMessages()` drains now discard partial pages and fall back to the legacy snapshot on both `session_busy` and `stale_cursor`, driven by a new machine-readable `code` field on RPC error responses. Direct page calls remain strict.

## [17.0.8] - 2026-07-22

### Added

- Added a `/tree` re-answer option for past `ask` tool results, allowing users to re-open the picker with original questions and branch the new answer as a sibling while keeping the original branch reachable.
- Added configurable Hindsight client request deadlines via `hindsight.requestTimeoutMs`, `reflectTimeoutMs`, `recallTimeoutMs`, and `retainTimeoutMs` settings (and matching `HINDSIGHT_*_TIMEOUT_MS` environment variables).
- Added `omp-linux-musl-x64` and `omp-linux-musl-arm64` release binaries for Alpine and other musl-based Linux distributions, with automatic musl selection in the installer and self-updater.

### Changed

- Optimized edit-tool previews, diff components, and intra-line word highlighting to compute line and word diffs natively, reducing synchronous diff times by 2-10x on large inputs.
- Updated diff generation and rendering components to rely exclusively on native UTF-16 diff bindings, removing `isWellFormed()` guards and JS fallback code paths.

### Removed

- Removed npm `diff` dependency.
- Fixed an issue where `Ctrl+V` clipboard paste was ignored while API-key and other modal prompts had focus.
- Fixed `scripts/install.sh` incorrectly installing an x86_64 build on Apple Silicon when running under Rosetta.
- Fixed the model picker hiding Codex models available through secondary configured ChatGPT/Codex OAuth accounts by unioning catalogs across all stored accounts.
- Fixed GitHub Copilot 1M-context models disappearing from the model picker on restart with a "Could not restore model" warning.
- Fixed `--model <role>` startup selection skipping configured fallback chains when the primary model is unavailable.
- Fixed global model role updates clobbering concurrent or external edits to `config.yml` by merging only the changed role instead of persisting a stale in-memory snapshot.
- Fixed terminal provider errors on continuation turns after failed tool results silently ending runs without persisting the error diagnostics.
- Fixed repeated OpenRouter Gemini stream closures consuming the full retry budget by limiting recovery attempts before surfacing the error.
- Fixed Agent Hub performance freezes when opening large read-only Advisor transcripts by collapsing synthetic inputs into compact summary rows and rendering Markdown lazily on expansion.
- Fixed `/agents` incorrectly showing prewalk as disabled for the bundled `task` agent when enabled by its runtime default.
- Fixed `hub start` waiting for the full timeout when a launched process exited or became ready quickly.
- Fixed `tools.maxTimeout` failing to clamp default tool timeouts when no explicit timeout was provided by the agent.
- Fixed MCP argument-shaping parity between direct and subagent tool calls, ensuring strict servers do not reject proxied calls with unrecognized keys.
- Fixed a crash in extensions like `pi-mcp-adapter` caused by the TypeBox compatibility shim omitting `Type.Unsafe`.
- Fixed `omp models` hanging after output by properly clearing managed extension timers and shutting down sessions before returning.
- Fixed HTML session exports causing browser call stack overflows when rendering deeply nested conversation trees.
- Fixed task agents ending prematurely on connection errors instead of entering the auto-retry path.
- Fixed a startup race condition where the default model role was incorrectly overridden by an unrelated provider's default on a cold cache.
- Fixed unqualified `--model` startup selection preferring unauthenticated provider catalog entries over configured providers.
- Fixed provider stream failures being invisible in the main log by logging a warning with error details when a turn ends in a provider error.
- Fixed parallel `todo done` calls losing completions due to asynchronous session events overwriting newer tool states.
- Fixed `omp` crashing when `git` is not installed or missing from the system `PATH`.
- Fixed `/changelog` commands reporting no entries in standalone binaries by embedding the release history as a fallback.
- Fixed isolated branch merge-backs rejecting committed agent edits when the parent branch had unrelated uncommitted changes in the same file.
- Fixed the 30-second Hindsight client timeout aborting healthy `reflect` operations by applying dedicated, longer deadlines.
- Fixed Mnemopi consolidation redundantly re-storing cumulative session transcripts after incremental auto-retain.
- Fixed turn-ending Codex rate-limit errors being hidden behind the Plan Review overlay.
- Fixed prewalked subagents continuing to display their starting model after switching to the target model.
- Fixed the Escape key aborting an ongoing agent turn instead of stopping text-to-speech playback.
- Fixed project system prompts shortening working directories to `~`, which could cause models to generate incorrect absolute paths for tool calls.
- Fixed the TUI `/usage` matrix misaligning multi-account columns across quota windows.
- Fixed near-miss `xd://` write targets silently creating filesystem paths instead of throwing a corrective URI error.
- Fixed the `task` tool rejecting valid batch calls with misleading validation errors when batching is disabled.
- Fixed JS/TS `debug` launches timing out on WSL2 with mirrored networking by waiting for the adapter's listening banner and handling transport closures immediately.
- Fixed post-compaction transcript rebuilds blocking the main thread by reusing settled message components and layout caches.
- Fixed the fullscreen Plan Review overlay remaining interactive and appearing frozen during slow asynchronous operations by locking input and showing a submitting indicator.
- Fixed dynamic model discovery refreshes dropping provider-level compatibility overrides from `models.yml`.
- Fixed a startup crash that locked users out of the app when `prewalk.enabled` was set but the prewalk hand-off target had no configured API key.
- Fixed in-progress aborts awaiting `session_stop` extension handlers whose results would be discarded.
- Fixed `/retry` reporting "Nothing to retry" after a stream stalled or aborted mid-tool-call.
- Fixed locally consumed extension commands triggering automatic title generation and exposing their command text to the title model.

## [17.0.7] - 2026-07-21

### Fixed

- Fixed Portkey/gateway custom models whose ids start with `@` (e.g. `@modal/GLM-5-2-FP8`) being rewritten to unrelated bundled wire ids (e.g. `glm-5-2`), which caused `400` responses requiring `x-portkey-config` or `x-portkey-provider`.

## [17.0.6] - 2026-07-20

- Fixed failed plan-mode exits leaving the session on the restored execution model while plan mode remained active and silently changing ambient `xd://` tool presentation; rollback now restores the plan model, thinking level, and exact top-level-versus-mounted tool partition so exit can be retried safely ([#6013](https://github.com/can1357/oh-my-pi/pull/6013)).

### Added

- Added native Warp CLI-agent events for rich session status, tool approvals, and completion notifications ([#5592](https://github.com/can1357/oh-my-pi/pull/5592) by [@metaphorics](https://github.com/metaphorics)).
- Added Codex (ChatGPT subscription) support to `generate_image`. The tool now resolves a connected `openai-codex` OAuth credential and drives OpenAI's hosted `image_generation` tool through the ChatGPT backend (`chatgpt.com/backend-api/codex/responses`, `chatgpt-account-id` header) **independent of the active chat model** — so image generation works on a ChatGPT/Codex subscription with no metered `OPENAI_API_KEY`, even when the active model is Claude/Gemini/etc. A new `providers.image: "openai-codex"` option forces it; `auto` now auto-detects a connected subscription (priority: active GPT image tool > Codex subscription > Antigravity > xAI > OpenRouter > Gemini), and the `openai` preference falls back to it when no `OPENAI_API_KEY`/active GPT model is present.
- Added an optional `provider` parameter to `generate_image` (`auto` | `openai` | `openai-codex` | `antigravity` | `xai` | `gemini` | `openrouter`) that overrides the `providers.image` setting **for a single request** — so "generate this using gemini / codex / xai" routes per-call without changing the global setting. Absent → the `providers.image` setting applies, unchanged; the named provider uses the same resolution semantics (falls back to auto-detect if it has no credentials). File: `tools/image-gen.ts` (`imageProviderSchema`, `findImageApiKey` `preference` arg).
- Added OpenTelemetry log and metric export alongside the existing trace export. When `OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` (or the shared `OTEL_EXPORTER_OTLP_ENDPOINT`) is set, `omp` registers a `LoggerProvider` and forwards every centralized-logger event as an OTLP log record (severity + attributes + active span context for log↔trace correlation, min level via `OTEL_LOG_LEVEL`, plus a structured `agent run completed` summary event). When `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` (or the shared endpoint) is set, it registers a `MeterProvider` with a `PeriodicExportingMetricReader` and records GenAI-semconv `gen_ai.client.token.usage` plus `pi.omp.agent.*` counters/histograms (runs, steps, chat/tool calls by name+status+finish reason, latencies, estimated cost, errors) from the agent run summary and per-chat usage hooks. Each signal honors its own `OTEL_*_EXPORTER=none` kill switch, the global `OTEL_SDK_DISABLED`, and declines non-`http/protobuf` protocols independently ([#4604](https://github.com/can1357/oh-my-pi/issues/4604)).
- `retry.fallbackChains` wildcards now support id-prefixed targets and keys: a chain entry like `"openrouter/google/*"` re-prefixes the failing model's bare id (`google-antigravity/gemini-x` → `openrouter/google/gemini-x`), a plain `"provider/*"` entry falling back *from* an aggregator strips the vendor prefix when the target provider only knows the bare id (`openrouter/google/x` → `google-vertex/x`), and an id-prefixed key (`"openrouter/google/*"`) scopes a chain to that provider's ids under the prefix.
- The session tree selector (`/tree`, `/branch`) now supports Shift+Enter to summarize-and-switch in one step: it forks from the selected entry with a branch summary, with no extra prompt and regardless of `branchSummary.enabled`. Plain Enter keeps the current behavior (direct switch by default; the summary prompt only when `branchSummary.enabled` is on). ([#5152](https://github.com/can1357/oh-my-pi/issues/5152))
- Added the turn's local timestamp (`YYYY-MM-DD HH:mm:ss`, down to the second) to the per-turn token-usage row shown under assistant messages when `display.showTokenUsage` is enabled.

### Changed

- Reduced concurrent subagent update CPU by reconstructing recent output only at progress emission boundaries. ([#5936](https://github.com/can1357/oh-my-pi/issues/5936))
- Fixed `docs/advisor-watchdog.md` overstating advisor delivery for a normal yield: the severity table listed `concern` as unconditionally interrupting and the prose promised a self-ended run could always be steered/resumed. Documented the #4840 terminal-answer exception (`concern` becomes a passive card while `blocker` normally steers, #5628) plus the plan-mode and deferred-ACP constraints that preserve would-be steers until the user resumes ([#5913](https://github.com/can1357/oh-my-pi/issues/5913)).
- Fixed subagent (task) sessions triggering an unnecessary tiny-model session-title generation call on `todo init`. Subagent sessions in a non-interactive host (print/RPC/ACP/eval/SDK/CI) have no operator-visible title and now skip the replan title refresh; interactive hosts keep it, since a live subagent focused from the Agent Hub renders its session name in the status line ([#5910](https://github.com/can1357/oh-my-pi/issues/5910)).
- Fixed `tab.scroll()` timing out after a queued wheel event waits too long for a busy renderer's acknowledgement ([#5905](https://github.com/can1357/oh-my-pi/issues/5905)).
- Made the hashline seen-line guard opt-in and off by default (see `edit.enforceSeenLines`), and stopped excluding column-clipped (>512-char) lines from a snapshot's seen set: a displayed line now counts as seen even when its display was column-truncated, so single-line edits on long lines found via `read`/`grep` apply without a separate full-width re-read.
- Changed the default `astGrep.enabled` setting to `false`
- Batched todo operations with real tool calls to prevent solo todo turns and extra round trips
- Changed every bundled TTSR rule to warn without interrupting generation.
- Renamed the system prompt's project-context section wrapper from `<context>` to `<repo-rules>` to stop it colliding with the `task` tool's `context` parameter under in-band XML tool dialects: models were closing `<parameter name="context">` with a stray `</context>` (primed by the ambient section tag) and emitting sibling params as bare `<tasks>` elements, so `tasks` arrived missing.
- Rendered `read xd://` calls in the compact grouped read view instead of a full tool-execution card; other internal URLs (`skill://`, `agent://`, …) still render full so their resolved content stays visible.

### Fixed

- Fixed the interactive `!`/`!!` shell shortcut spawning fish as a login shell (`fish -l -c …`), which fired `status is-login` blocks in user config (agent/keychain setup, PATH mutation) on every command. fish is now started with `-i` instead — interactive shells source the same `config.fish`/`conf.d` files (so aliases and functions from #1816 keep working) without login-shell side effects. zsh behavior (`-l -i`) is unchanged.
- Fixed the status-line `tok/s` badge ignoring vibe worker sessions: in `/vibe` mode the director is often idle while workers stream, so the badge showed a stale/zero rate while parallel work was actively generating tokens. The rate now aggregates the main session's live tok/s with every live vibe worker's tok/s, and falls back to the main session's own cached rate when no workers are streaming.
- Fixed `plan.defaultOnStartup` being ignored by headless `omp -p` sessions, so the initial prompt now runs in plan mode and the persisted session remains in plan mode for later review ([#6017](https://github.com/can1357/oh-my-pi/issues/6017)).
- Fixed resuming an active plan session replacing its journal-restored model with the current `modelRoles.plan` setting ([#6015](https://github.com/can1357/oh-my-pi/issues/6015)).
- Fixed `--model <role>` resolving a bare configured `modelRoles` key.
- Browser tool selectors now accept bare snapshot refs (`tab.click("e501")`, `@e501`) everywhere `aria-ref=e501` works — previously the tab-worker backend fell through to a CSS tag selector that could never match, burning the 2s zero-match watchdog with a misleading "matches no elements" hint. `tab.select`, `tab.uploadFile`, `tab.press({ selector })`, `tab.screenshot({ selector })`, and `tab.drag` now resolve refs too. Unknown/stale refs fail immediately with the "refresh refs" error.
- `tab.select` no longer double-reports the previously selected option of a single `<select>`: the returned selection is read back after the full assignment pass instead of mid-loop.
- Fixed transcript blocks being visibly duplicated during streaming (whole tool boxes and assistant paragraphs recommitted below their first copy on the terminal tape) by removing transcript committed-prefix compaction entirely. Dropping committed rows from the transcript's local frame shifted the frame under the engine's committed-prefix ledger, so the audit re-anchored and recommitted rows the tape already held. The transcript now always keeps its full local frame; committed finalized blocks still skip `render()` via the segment reuse bypass. Reverts the compaction half of [#5930](https://github.com/can1357/oh-my-pi/issues/5930)'s fix (compose keeps the render bypass; the local frame is no longer truncated).
- Fixed tmux pane growth during a live response blanking finalized chat history re-exposed from native scrollback by rebasing the in-place repaint's commit seam to the resized viewport tail ([#6011](https://github.com/can1357/oh-my-pi/issues/6011)).
- Fixed classifier refusals (e.g. Anthropic `stop_reason: "refusal"`) ending the turn with no visible error. Two independent regressions: (1) session events reached subscribers out of order when a turn's provider events landed in one tick — extension emits only await for event types with registered handlers, so the assistant `message_end` overtook its own `message_start` and the TUI skipped the error render entirely (no pinned banner, no inline `Error:` line); subscriber fan-out is now serialized in emission order. (2) Refusal turns are pruned from active context at settle (#3591), which also erased them from `state.messages` before `prompt()` resolved — print mode printed nothing and exited 0, and the task executor's `getLastAssistantMessage()` saw the previous turn. The pruned refusal is now retained until the next run starts, `getLastAssistantMessage()` reports it, and print mode reads the settled assistant via that accessor (exit 1 + refusal message on stderr). Additionally, `#lastAssistantMessage` is now set synchronously on `message_end` to prevent `agent_end` maintenance from reading a stale assistant turn when tool results and stops land in the same tick.
- Fixed `before_provider_request` extension contexts exposing the primary session model for cross-provider Advisor requests instead of the request model ([#6006](https://github.com/can1357/oh-my-pi/issues/6006)).
- Fixed isolated `task` subagents mutating the parent checkout and stacking parallel task branches. Copy isolation backends (reflink/apfs/btrfs/zfs/block-clone/rcopy) materialise the worktree by duplicating its `.git` verbatim; when the parent is a linked git worktree its `.git` is a pointer file, so the isolation shared the parent's HEAD/index/ref namespace and a task's `git checkout`/`commit` moved the parent's branch (and the rcopy `git worktree add` path leaked task branches into the shared namespace so a second task committed on top of the first). `ensureIsolation` now runs a new `git.detachGitDir` after `isoStart`: each isolation becomes a standalone repo with a frozen HEAD/refs/index snapshot that borrows the source object database through `objects/info/alternates`, so isolated git operations stay private, every task branch is parented on the requested base, and patch/branch capture (`git fetch <merged>`) still resolves objects. ([#6003](https://github.com/can1357/oh-my-pi/issues/6003))
- Fixed `browser.run` leaving Puppeteer request handlers and interception state with divergent lifetimes by removing run-scoped handlers, disabling interception, and releasing held requests on every exit path ([#6004](https://github.com/can1357/oh-my-pi/issues/6004)).
- Fixed Codex web search to honor configured `openai-codex` base URLs, API keys, and headers without leaking official OAuth credentials to custom endpoints; explicitly selected providers now fail closed instead of silently falling back ([#6001](https://github.com/can1357/oh-my-pi/issues/6001)).
- Fixed `launch start` waiting for a finite PTY command to exit when the broker's PID-file handoff was unavailable; PTY startup now reports the spawned PID directly and returns an authoritative running or exited snapshot promptly ([#5996](https://github.com/can1357/oh-my-pi/issues/5996)).
- Fixed queued user steering aborting side-effecting `hub start` calls after the broker request may already have been written; only passive hub waits and followed logs are now interruptible ([#5995](https://github.com/can1357/oh-my-pi/issues/5995)).
- Fixed JavaScript/TypeScript debugging by launching vscode-js-debug over TCP, handling recursive `startDebugging` child sessions, synchronizing breakpoints across the session tree, and terminating every child connection ([#5984](https://github.com/can1357/oh-my-pi/issues/5984)).
- Fixed rich ask options showing preview content only for the highlighted choice; every option now renders its preview inline, with pageable long content and accurate configured paging and cancel hints ([#5988](https://github.com/can1357/oh-my-pi/pull/5988) by [@metaphorics](https://github.com/metaphorics)).
- Fixed legacy pi extensions failing extension validation when importing `getPackageDir` or `getProjectDir` from `@earendil-works/pi-coding-agent` (aliased to the legacy shim). The shim only re-exported `getAgentDir`; the two missing path helpers now resolve — `getProjectDir` from `@oh-my-pi/pi-utils`, and `getPackageDir` as a string-valued wrapper over omp's canonical package-root helper that falls back to the executable's directory inside `bun --compile` binaries (where the canonical helper returns `undefined`), matching pi's string contract. Extensions like `@gotgenes/pi-permission-system` install and load, and `path.join(getPackageDir(), …)` no longer crashes in the shipped binary ([#5968](https://github.com/can1357/oh-my-pi/issues/5968)).
- Fixed headless print mode disposing the session before a final advisor review completed, which could drop the advisor transcript and usage ([#5942](https://github.com/can1357/oh-my-pi/pull/5942)).
- Fixed capped zero-block assistant stops remaining in active/session history with the full failed-request usage, causing the next post-snapcompact `continue` to re-enter context maintenance at the same boundary; capped empty turns are now discarded and the failure names model switching or `/shake images` as recovery options ([#5959](https://github.com/can1357/oh-my-pi/issues/5959)).
- Long sessions no longer re-run `convertToLlm` over settled history every turn. Conversion is memoized per message identity (plus the assistant `interruptedNext` neighbor flag): an exact re-convert of the same array reuses the outer `Message[]`, append-only growth reuses the converted prefix via slice-on-growth, and the prune/shake/strip-images/prewalk-scrub rewrite seams invalidate the affected message before the next pass. On the `llm-assembly` bench (N=5000) steady/append convert and repeat estimate are all >10x faster with robust MAD-noise well under 20% ([#5934](https://github.com/can1357/oh-my-pi/issues/5934)).
- Fixed `/exit` hanging on post-prompt work and stacking independent subsystem teardown delays by bounding the aborted-work drain, disposing independent session resources concurrently, and keeping long shutdown waits visible ([#5932](https://github.com/can1357/oh-my-pi/issues/5932)).
- Fixed queued-message display updates being skipped by focused-editor keystroke frames by explicitly repainting the pending-message container ([#5928](https://github.com/can1357/oh-my-pi/issues/5928)).
- Fixed RPC and RPC-UI startup crashes when an in-process extension claimed Bun's singleton stdin stream before the protocol reader ([#5898](https://github.com/can1357/oh-my-pi/issues/5898)).
- Bash command timeouts now render with a warning (yellow) border instead of an error (red) border, reflecting that the timeout ran its course rather than the command failed. `isError` remains `true` on the result so the model still knows the command did not complete normally. The `timedOut` flag is now propagated from the bash executor to distinguish timeouts from user aborts.
- Fixed Cursor responses streams stalling after an exec-channel tool completed without automatically recovering. The session now continues from the already-buffered tool result instead of replaying the side-effecting request. ([#5790](https://github.com/can1357/oh-my-pi/issues/5790))
- Fixed linked legacy pi extensions failing to load when they import `DefaultPackageManager` or linkedom: the coding-agent compatibility shim now enumerates OMP extension paths with plugin metadata, and extension-graph CommonJS modules load through synchronous default-export bridges with linkedom's bundled canvas fallback. ([#5658](https://github.com/can1357/oh-my-pi/issues/5658))
- Fixed the advisor retrying terminal, non-retriable provider failures (e.g. blocked prompts) three times before giving up; such failures now drop the bounded batch after a single attempt while transient failures keep the 3-attempt retry path ([#5468](https://github.com/can1357/oh-my-pi/pull/5468)).
- Fixed reassigning the `plan` role model mid-planning not taking effect on the active planning turn; the change now applies at the next turn boundary instead of only the next plan-mode entry ([#5657](https://github.com/can1357/oh-my-pi/issues/5657)).
- Added managed `ctx.setInterval` / `ctx.setTimeout` / `ctx.clearTimer` helpers on the extension context. Callbacks scheduled through them run with the same isolation as handler dispatch — a throw or rejected promise is logged and reported through the extension error channel instead of escaping as a process-fatal `uncaughtException` — and every outstanding timer is `unref`'d and cleared automatically on `session_shutdown` ([#5664](https://github.com/can1357/oh-my-pi/issues/5664)).
- Fixed an extension's self-scheduled `setInterval`/`setTimeout` callback throwing being able to tear down the whole session. Such callbacks ran outside the handler-dispatch try/catch, surfaced as a process-level `uncaughtException`, and the global postmortem handler treated them as fatal; extension authors now have sanctioned managed timers (see Added), and the constraint is documented in `docs/extensions.md` / `docs/skills/authoring-extensions.md` ([#5664](https://github.com/can1357/oh-my-pi/issues/5664)).
- Fixed `/quit` and `/exit` leaving failed or stalled automatic title-generation requests alive during session teardown; disposal now aborts both online provider and local tiny-model title requests ([#5666](https://github.com/can1357/oh-my-pi/issues/5666)).
- Fixed `startup.quiet` still rendering the `xdev: xd://: mounted …` status line when MCP tools connect; quiet startup now suppresses only the user-visible mount notice while retaining the hidden model-facing device update ([#5670](https://github.com/can1357/oh-my-pi/issues/5670)).
- Fixed command error in `hub` tool with a non-POSIX shell ([#5682](https://github.com/can1357/oh-my-pi/pull/5682))
- Fixed xdev-routed checkpoint and rewind writes not tracking checkpoint state and leaving rewinding results in rebuilt provider and session context.
- Fixed the built-in advisor silently doing nothing when its model routes through the `cursor` provider: the advisor runs in its own `Agent` that was constructed without `cursorExecHandlers`, so on Cursor — where every tool executes server-side and is dispatched back through the client's exec handlers — each advisor tool call (including the MCP `advise` tool) came back `toolNotFound`/"tool not available" and no advice was ever routed. The advisor `Agent` now gets a Cursor exec bridge scoped to its own granted tool set, mirroring the primary agent. The bridge's native `delete` frame is gated so a read-only advisor cannot delete workspace files it was never granted a mutating tool for ([#5680](https://github.com/can1357/oh-my-pi/issues/5680)).
- Fixed the fullscreen plan-review overlay staying visible until the approved execution turn finished, so after picking "Approve and keep context" (or any approve option) work proceeded underneath while the operator was stuck on the plan-review screen. The overlay is now hidden once execution begins — after the async transcript rebuild, before the blocking synthetic prompt is dispatched — instead of only after the whole turn returns ([#5688](https://github.com/can1357/oh-my-pi/issues/5688)).
- Fixed MCP tools repeatedly unmounting and remounting mid-session when server names have overlapping sanitized prefixes (e.g. `atlassian` alongside an imported `atlassian:atlassian`), and stale tools remaining registered after disconnecting a server with special characters in its name.
- Fixed the `/usage show` `in use by this session:` marker showing only the login email, so two same-email Anthropic credentials in different orgs (a Team seat and a personal Max plan) were indistinguishable. The marker now suffixes the active organization (`email (OrgName)`) via a shared `formatActiveAccountLabel`, matching the account list and login-success surfaces ([#5691](https://github.com/can1357/oh-my-pi/issues/5691)).
- Fixed Windows stdio MCP servers launched through `.cmd`/`.bat` shims failing with `Transport closed`; the launch now builds a `cmd.exe /d /e:ON /v:OFF /c` command line escaped for `cmd.exe`'s parser and spawned with `windowsVerbatimArguments`, so the resolved command path and arguments (including `%VAR%`, quotes, and shell metacharacters) reach the server intact and cannot inject commands (BatBadBut / CVE-2024-24576) ([#5696](https://github.com/can1357/oh-my-pi/issues/5696)).
- Fixed the TUI usage panel truncating organization suffixes from same-email account labels even when the terminal has enough width ([#5701](https://github.com/can1357/oh-my-pi/issues/5701)).
- Fixed a startup crash on Windows when running from a drive root (e.g. `R:\`): `fs.realpath` throws `EISDIR` there, but `canonicalProjectDir` in `launch/presence.ts` and `launch/client.ts` only recovered `ENOENT`. It now also falls back to `path.resolve()` on `EISDIR` ([#5708](https://github.com/can1357/oh-my-pi/issues/5708) by [@ve3xone](https://github.com/ve3xone)).
- Fixed unknown `__omp_worker_*` CLI selectors exiting 0 with empty output instead of erroring; an unrecognized worker-host selector now writes `Error: unknown worker selector: …` to stderr and exits nonzero, so a stale or mistyped selector can no longer look healthy to a parent process or install smoke path ([#5712](https://github.com/can1357/oh-my-pi/issues/5712)).
- Fixed Plan Review capturing mouse drags as pointer events, preventing native terminal text selection ([#5711](https://github.com/can1357/oh-my-pi/issues/5711)).
- Fixed orphaned TUI processes with revoked terminal descriptors remaining alive after a fatal error and amplifying shared log-rotation races into runaway memory, file-descriptor, swap, and disk consumption ([#5716](https://github.com/can1357/oh-my-pi/issues/5716)).
- Fixed approved-plan execution looping through filesystem searches when a model rewrites the required `local://<slug>-plan.md` read as a same-basename working-directory path; a missing cwd-root alias now recovers the active session-local plan while preserving any real working-tree file ([#5704](https://github.com/can1357/oh-my-pi/issues/5704)).
- Fixed Ask dialogs immediately accepting their highlighted single-select answer when they appear while the user is typing a space in the prompt editor ([#5717](https://github.com/can1357/oh-my-pi/issues/5717)).
- Stopped post-compaction auto-continue from opening another primary turn after a terminal text answer with no queued work, and moved automatic auto-learn capture into an abortable private agent with only `manage_skill` and `learn` tools ([#5715](https://github.com/can1357/oh-my-pi/issues/5715)).
- Fixed the `write` approval gate misclassifying `xd://` device writes as `exec` when the mounted tool declared a function-valued (argument-dependent) `approval`: the gate discarded the function and never decoded the device JSON payload, so read/write device operations prompted in non-yolo modes their approval mode permits. It now parses valid object payloads and evaluates the mounted tool's normal approval decision, while malformed JSON, non-object payloads, and unknown devices still fall back to `exec` and prompt ([#5727](https://github.com/can1357/oh-my-pi/issues/5727)).
- Fixed custom LSP servers such as `roslyn-language-server` crashing after initialization when they request unconfigured `workspace/configuration` sections; missing settings now receive the spec-required `null` instead of `{}` ([#5745](https://github.com/can1357/oh-my-pi/issues/5745)).
- Fixed late user-initiated bash results and minimized-output artifacts being recorded in whichever session or branch was active when execution finished; bash now retains its originating transcript across `new_session`/`switch_session`/`branch`/tree navigation, and an intentionally dropped session stays deleted instead of being recreated by a straggling result ([#5743](https://github.com/can1357/oh-my-pi/issues/5743)).
- Fixed Claude Code marketplace plugins with `scope: "local"` leaking skills, hooks, tools, commands, and MCP servers into unrelated projects ([#5750](https://github.com/can1357/oh-my-pi/issues/5750)).
- Fixed headless `omp -p` waiting indefinitely after a completed turn when final mnemopi consolidation stalls; print mode now applies the same bounded consolidation shutdown budget as interactive exit and reaps the embed worker ([#5753](https://github.com/can1357/oh-my-pi/issues/5753)).
- Fixed explicit-tool sessions bypassing `xd://` presentation for ambient discoverable custom and MCP tools, which sent their schemas top-level and could exceed provider tool limits or trigger schema-compatibility errors.
- Fixed `providers.webSearch: kimi` sending a Moonshot Open Platform credential (`MOONSHOT_API_KEY` / stored `moonshot` auth) to the Kimi Code search endpoint (`api.kimi.com/coding/v1/search`), which rejects it with `401` and silently falls back to another provider. Kimi web search now resolves and advertises Kimi Code credentials only — a Kimi Code Console key via `KIMI_SEARCH_API_KEY` / `MOONSHOT_SEARCH_API_KEY` or `omp /login kimi-code` ([#5762](https://github.com/can1357/oh-my-pi/issues/5762)).
- Fixed extension/SDK/RPC `registerTool` demoting essential built-ins (`read`/`write`/`bash`/`edit`/`glob`/…) to `discoverable` when a re-registration omitted `loadMode`, which — with `tools.xdev` on — unmounted them from the top-level schema and broke the `xd://` transport (`read xd://`/`write xd://`), leaving the model with no callable coding essentials. Omitted `loadMode` now defaults to `"essential"` for known essential built-in names at every adapter boundary, and `read`/`write` (the transport itself) are never mounted under xdev regardless of `loadMode` ([#5764](https://github.com/can1357/oh-my-pi/issues/5764)).
- Fixed the advisor skipping the next real user instruction after auto-learn accepted and pruned a terminal empty assistant stop; advisor transcript cursors now detect rewritten prefixes and re-prime before slicing the next update ([#5731](https://github.com/can1357/oh-my-pi/issues/5731)).
- Fixed built-in advisors retrying a quota- or rate-limited provider until becoming unavailable instead of applying the matching `retry.fallbackChains` model chain; advisor fallbacks now emit the same applied and succeeded lifecycle events as primary-agent fallbacks ([#5740](https://github.com/can1357/oh-my-pi/issues/5740)).
- Made the model selector status messages use the role tag (`SMOL`, `SLOW`) instead of the display name (`Fast`, `Thinking`), matching the rest of the TUI and CLI/env role terminology ([#5585](https://github.com/can1357/oh-my-pi/issues/5585)).
- Fixed Cursor models receiving only top-level tools by forwarding mounted `xd://` devices, including user-configured MCP servers, through Cursor's request-context MCP catalog and execution bridge ([#5650](https://github.com/can1357/oh-my-pi/issues/5650)).
- Fixed Windows bash crashes when a piped command times out while flushing output; explicit-timeout watchdogs now wait for bounded native teardown instead of returning mid-drain. ([#5316](https://github.com/can1357/oh-my-pi/issues/5316))
- Fixed a race where hub/IRC `send` and `ensureLive` could hand out or inject into a subagent session mid-`park` dispose: park now detaches and flips status to `parked` before `session.dispose()`, concurrent `ensureLive` cancels a pre-detach park or waits then revives, and IRC delivery always gates through `ensureLive` so receipts/unread counts stay truthful ([#5633](https://github.com/can1357/oh-my-pi/issues/5633)).
- Migrated legacy `dev.autoqa.consent` → `dev.autoqaConsent` and `todo.reminders.max` → `todo.remindersMax` on settings load so pre-v17 nested or quoted-dotted config no longer leaves the parent path as an object (which made `dev.autoqa` truthy and enabled Auto QA, and discarded the reminder limit). Explicit new keys win, a separately configured parent boolean is preserved, an irrecoverable object parent falls back to the schema default, and only the new keys persist on save ([#5632](https://github.com/can1357/oh-my-pi/issues/5632)).
- Fixed all keyboard input dying after the first keypress when a `~/.claude/tools` (or `.omp/tools`) module attaches a stdin consumer at import time — e.g. an MCP `StdioServerTransport` constructed at module top level, or a bare `process.stdin.resume()`. The custom-tool/extension/hook/plugin loader guard now snapshots and restores `process.stdin` (listeners, paused state, raw mode) around third-party module evaluation, so a hijacked stdin reader can no longer starve the TUI's own listener ([#5618](https://github.com/can1357/oh-my-pi/issues/5618)).
- Fixed the ask tool's "Other" custom-input dialog rendering the title, options, and hint one column to the right of the `> ` input gutter; the prompt-style editor chrome now aligns to column 0 ([#5313](https://github.com/can1357/oh-my-pi/issues/5313))
- Fixed advisor context maintenance undercounting the provider context: the compaction decision now anchors on the advisor's provider-reported context usage (cached input + generated output) floored by a full local estimate that includes the advisor system prompt and tool schemas, rejects stale provider usage retained across advisor compaction, and recovers a provider overflow by clearing only the advisor's own context at the current primary cursor — retrying the bounded failing batch once against a fresh context without replaying old primary history and keeping later updates eligible ([#5282](https://github.com/can1357/oh-my-pi/issues/5282))
- Fixed RPC mode (`--mode rpc`) crashing the whole process with an uncaught `SyntaxError: Failed to parse JSONL` on any non-JSON stdin line. Malformed lines are now reported via a `Failed to parse command` error frame and the frame loop keeps running. ([#5194](https://github.com/can1357/oh-my-pi/issues/5194))
- Fixed the status line loop indicator to distinguish waiting, running, and paused states and show the remaining loop budget ([#5832](https://github.com/can1357/oh-my-pi/pull/5832) by [@wolfiesch](https://github.com/wolfiesch)).
- Fixed single-model task agents ignoring an explicitly configured default retry fallback chain, which left subagents failed after their selected provider became unreachable instead of advancing to the configured fallback model.
- Fixed the `/extensions` dashboard tab labeled "Agents (standard)" being confused with the `/agents` subagents feature — the `.agent`/`.agents` config-standard provider now presents as "Agent Dirs (.agent/.agents)" since it lists skills, rules, prompts, commands, and context/system files, never subagents ([#5821](https://github.com/can1357/oh-my-pi/issues/5821)).
- Fixed non-raw `read` line selectors returning context outside the requested inclusive range ([#5802](https://github.com/can1357/oh-my-pi/issues/5802)).
- Fixed LSP requests silently clamping explicit timeouts above 60 seconds by supporting documented budgets up to 300 seconds ([#5804](https://github.com/can1357/oh-my-pi/issues/5804)).
- Clarified async task and hub guidance: inspecting a settled job consumes its automatic delivery, job IDs expire from process memory after roughly five minutes, and completion does not verify claimed artifacts ([#5869](https://github.com/can1357/oh-my-pi/issues/5869)).
- Fixed `vibe_wait` TV-wall panels stacking duplicate frozen frames in native scrollback while two or more workers were live ([#5777](https://github.com/can1357/oh-my-pi/issues/5777)).
- Fixed async task job rows omitting resolved subagent model and reasoning badges when `task.showResolvedModelBadge` is enabled. ([#5060](https://github.com/can1357/oh-my-pi/issues/5060))
- Fixed raw Puppeteer `page`/`browser` promises from crashing inline browser workers or killing dedicated workers when a target closed before the caller awaited the promise.
- Fixed auto-compaction dead-ending in a warning loop ("Compaction freed too little context to make progress") when the single most-recent turn is itself over budget so `prepareCompaction` has nothing to summarize (`findCutPoint` never cuts inside a tool result). This `!preparation` short-circuit never ran the artifact-backed `shake` elide rescue that #3786 added to the post-maintenance guard, so snapcompact/context-full maintenance paused with no attempt to shrink the oversized tail. The dead-end now runs the same elide pass, re-prepares on the shrunken branch, and falls through to a normal compaction when the tail became summarizable — only pausing (single warning) when nothing is elide-eligible. ([#4786](https://github.com/can1357/oh-my-pi/issues/4786))
- Fixed GitHub-hosted repository file reads falling back to `curl` by adding a dedicated `github` file-read operation and explicit tool-routing guidance ([#4805](https://github.com/can1357/oh-my-pi/issues/4805)).
- Bounded RPC JSONL frames to 1 MiB, compacted oversized `agent_end` frames without losing complete Python prompt results, and guaranteed worker reaping plus pending-request rejection after output-reader failures or explicit stops ([#5405](https://github.com/can1357/oh-my-pi/issues/5405)).
- Fixed `web_search` being unreachable under default config: with `tools.xdev: true`, the discoverable `web_search` tool was mounted under `xd://` and dropped from the top-level toolset, so models calling it directly got "Tool web_search not found". It is now pinned top-level via `XDEV_KEEP_TOP_LEVEL` while other discoverable tools keep mounting under `xd://` ([#5973](https://github.com/can1357/oh-my-pi/issues/5973)).
- Fixed onboarding omitting model selection by adding a persisted default-model step (fresh installs only — the setup version is not bumped, so existing installs are not re-prompted), and documented custom `models.yml` provider configuration and default-role selection ([#5979](https://github.com/can1357/oh-my-pi/issues/5979)).
- Fixed `autoResume` crossing an explicit `/new` boundary: after `/new` a new session's JSONL is created lazily (only once assistant output exists), so exiting before any assistant message left the per-terminal breadcrumb pointing at a not-yet-materialized file. `readTerminalBreadcrumbEntry` rejected the missing target and `continueRecent()` fell back to the most-recent session — the pre-`/new` transcript — processing the next prompt with stale context. `/new` now records a durable `fresh` breadcrumb boundary that `continueRecent()` honors (starting fresh) even when the target is absent, while a genuinely stale/deleted breadcrumb still falls back to the most-recent session ([#5730](https://github.com/can1357/oh-my-pi/issues/5730)).
- Fixed subagents that repeatedly submit malformed `yield` results from leaving the parent waiting forever; malformed submissions now repeat the required response format, and repeated invalid submissions fail the child with a clear error. ([#4957](https://github.com/can1357/oh-my-pi/issues/4957))
- Fixed configured or `-e` extensions in compiled binaries failing to resolve bundled `@oh-my-pi/*` value imports through the `omp-legacy-pi-bundled:` registry, and surfaced extension load failures during interactive and `-p` session startup. ([#4954](https://github.com/can1357/oh-my-pi/issues/4954))

### Removed

- Fixed the Cursor-backed advisor losing entire turns when it selected server-native tools (`bash`, `grep`, etc.) outside its grant: exec-resolved native blocks are already rejected in-band by the advisor-scoped bridge, so they no longer trip the unavailable-tool quarantine and discard the `advise` emitted in the same turn ([#5900](https://github.com/can1357/oh-my-pi/issues/5900)).
- Fixed custom `anthropic-messages` OAuth providers being unable to opt into configured Claude Code fingerprint header overrides. ([#5888](https://github.com/can1357/oh-my-pi/issues/5888))
- Fixed authoritative providers (e.g. `openai-codex`) keeping unsupported bundled models selectable when a fresh model cache and an expired OAuth token coincided: built-in discovery now forces the OAuth refresh so the provider's model manager is constructed and prunes stale bundled entries (e.g. `gpt-5.4-nano`) instead of waiting out the cache TTL. ([#5364](https://github.com/can1357/oh-my-pi/issues/5364))

## [17.0.5] - 2026-07-18

### Added

- Added support for Codex (ChatGPT subscription) in `generate_image` via the `providers.image: "openai-codex"` option, including automatic subscription detection and fallback logic.
- Added an optional `provider` parameter to `generate_image` to override the global image provider setting for a single request.
- Added OpenTelemetry log and metric export capabilities alongside existing trace exports, supporting standard OTLP environment variables.
- Added support for id-prefixed targets and keys in `retry.fallbackChains` wildcards (e.g., `"openrouter/google/*"`).
- Added support for `Shift+Enter` in the session tree selector (`/tree`, `/branch`) to summarize and switch branches in a single step.
- Added the `PI_CONFIG_FILES` environment variable to load settings overlays before `--config` overlays.

### Changed

- Changed bundled TTSR rules to warn instead of interrupting generation.
- Renamed the system prompt's project-context section wrapper from `<context>` to `<repo-rules>` to prevent XML tag collisions with in-band tool dialects.
- Renamed the `/extensions` dashboard tab "Agents (standard)" to "Agent Dirs (.agent/.agents)" to clarify its purpose.
- Optimized performance by reducing concurrent subagent update CPU usage, skipping unnecessary title generation in non-interactive hosts, and memoizing `convertToLlm` conversions over settled history.
- Improved the display of `read xd://` calls by rendering them in a compact grouped view instead of full tool-execution cards.
- Made the hashline seen-line guard opt-in and off by default via `edit.enforceSeenLines`.

### Fixed

- Fixed isolated `task` subagents mutating the parent git checkout and stacking parallel task branches by detaching the git directory.
- Fixed Windows compatibility issues, including `launch start` daemons opening visible console windows, startup crashes when running from a drive root, and command errors in the `hub` tool with non-POSIX shells.
- Fixed Windows stdio MCP servers launched through `.cmd`/`.bat` shims failing with `Transport closed` by escaping arguments properly.
- Fixed browser tool selectors (`tab.click`, `tab.select`, etc.) to accept bare snapshot refs (e.g., `tab.click("e501")`, `@e501`) and resolved crashes when handed `ElementHandle` objects.
- Fixed classifier refusals (e.g., Anthropic `stop_reason: "refusal"`) ending turns with no visible error or exiting 0 in print mode.
- Fixed transcript blocks being duplicated during streaming and tmux pane growth blanking finalized chat history.
- Fixed JS/TS debugging by launching vscode-js-debug over TCP and synchronizing breakpoints across the session tree.
- Fixed legacy pi extensions failing validation or loading when importing path helpers or package managers.
- Fixed `/login` and `/logout` failing to refresh model discovery with fresh credentials due to stale cached data.
- Fixed Cursor models and advisors failing to receive or execute mounted `xd://` devices and MCP tools.
- Fixed MCP tools repeatedly unmounting/remounting with overlapping sanitized prefixes, and stale tools remaining after disconnecting.
- Fixed custom LSP servers crashing when requesting unconfigured `workspace/configuration` sections.
- Fixed keyboard input dying after the first keypress when custom tools or modules hijack stdin at import time.
- Fixed auto-compaction dead-ending in a warning loop when the most recent turn is over budget.
- Fixed GitHub-hosted repository file reads falling back to `curl` by adding a dedicated `github` file-read operation.
- Fixed active session markers and TUI usage panels truncating organization suffixes from same-email account labels.
- Fixed `write` approval gates misclassifying `xd://` device writes as `exec`.
- Fixed bash command timeouts rendering with an incorrect error border, and resolved Windows bash crashes when piped commands time out.
- Migrated legacy nested/quoted-dotted config keys (e.g., `dev.autoqa.consent` -> `dev.autoqaConsent`) on settings load.
- Added managed `ctx.setInterval` / `ctx.setTimeout` / `ctx.clearTimer` helpers on extension contexts to prevent uncaught exceptions from crashing sessions.

## [17.0.4] - 2026-07-18

### Fixed

- Fixed bundled Linux ffmpeg recording by selecting its available ALSA input when PulseAudio support is absent, and surfaced recorder stderr when capture fails ([#5907](https://github.com/can1357/oh-my-pi/issues/5907)).
- Session load now skips the recursive async blob-ref resolver for entries with no `blob:sha256:` references. A cheap synchronous precheck gates the walk per entry (preserving the previous per-entry initiation order under synchronous store mutation), so text-heavy histories no longer pay the `Promise.all` tree descent for every non-session entry ([#5922](https://github.com/can1357/oh-my-pi/issues/5922)).
- Fixed `task` tool schemas emitting boolean subschemas that llama.cpp grammar generation cannot parse ([#5957](https://github.com/can1357/oh-my-pi/issues/5957)).
- Fixed the transcript keeping finalized assistant blocks in the live compose walk after their rows entered native terminal scrollback, making each stream tick's `TranscriptContainer.render` depth-linear in session length. Fully committed finalized blocks are now compacted out of the local frame regardless of post-finalize version tracking; a later mutation no longer recommits on ordinary frames (no duplication) and rehydrates on the next destructive full replay (no loss). Compose cost for a live tail tick is now flat as depth grows (`bench/transcript-compose.bench.ts`: ratio(N5000/N500) 2.30 → 0.90) ([#5930](https://github.com/can1357/oh-my-pi/issues/5930)).
- Fixed `/quit` and `/exit` hanging during interactive shutdown by making the mnemopi dispose path retain the current session and flush in-flight extractions without sleeping the bank; the `/memory enqueue` path and end-of-session backend enqueue still perform full cross-session consolidation. ([#3641](https://github.com/can1357/oh-my-pi/issues/3641))
- Fixed interactive bash shortcut `cd` commands leaving the OMP session and status-line working directory unchanged.

## [17.0.3] - 2026-07-17

### Changed

- `omp usage` and the in-session `/usage` view now show the Anthropic organization next to the account for org-scoped credentials (with `--redact` masking applied per part in the CLI, falling back to the org id when no display name is available), attribute "no usage data" rows per organization, and match the "in use by this session" marker by organization so only the active subscription is flagged. The OAuth login success message names the account and organization that was stored — a login landing on an unintended subscription is visible immediately.
- `/logout` labels Anthropic accounts with their organization and marks only the credential of the active organization as active; `omp token --list` shows the organization next to each account. Two subscriptions sharing one email are distinguishable when selecting which to remove or mint a token for.
- `omp auth-broker migrate --from-local` dedupes Anthropic OAuth identities per organization, so a Team seat already on the broker no longer blocks uploading the personal plan under the same email.
- The status line invalidates its cached usage when the session rotates to a different Anthropic organization (previously the old subscription's quota could linger for the cache TTL), and `omp auth-gateway check` labels each credential with its organization so a failing row says which subscription needs re-login.
- `omp usage` "no usage data" attribution is org-decisive whenever either the stored account or a report carries an organization: an org-less legacy credential whose own fetch failed is no longer hidden by an org-attributed sibling report sharing the same email.
- Active-account matching for `/usage`, `/logout`, and `omp token --list` now treats a shared organization as a qualifier rather than a match: two Anthropic Team seats in one org (same org id, per-user pools) no longer flag each other's rows or reports as "in use by this session" — the base identity (account/email/project) is still required, with org-only sessions matching on the org alone.
- `omp usage` "no usage data" coverage now requires the member's own identity within a shared organization: a sibling Team member's same-org report no longer counts as coverage for an account whose own report is missing, while an org-only account remains covered by any same-org report.
- `omp auth-broker migrate --from-local` reruns now recognize an already-migrated org-only Anthropic row (login recovered neither email nor account) by its organization id instead of re-uploading it, which could overwrite the broker's newer refresh token with the stale local one.
- Updated tangential agent forks to ignore parent session history and focus exclusively on the new request
- Hardened `/tan` fork isolation: the clone's inherited todo list is cleared at fork (parent todo reminders no longer drag the tan back onto the parent's task), the fork notice warns that the parent is concurrently editing the same working directory, and the notice is re-injected after each compaction so the fork boundary survives summarization
- Added visual markers in the transcript for elided tool calls that have no corresponding result
- Updated status event log to prioritize the most recent entries in the display window
- Updated the snapcompact shape preview transcript to use the compact scope format shown to models during compaction.

### Fixed

- Fixed `xd://` mount notices triggering unsolicited model turns by deferring hidden notices until the next user prompt.
- Fixed `xd://` device tools appearing in the direct tool inventory and prompting invalid function calls ([#5797](https://github.com/can1357/oh-my-pi/issues/5797)).
- Fixed `history://` read selectors being treated as part of the agent id instead of paging the transcript ([#5806](https://github.com/can1357/oh-my-pi/issues/5806)).
- Narrowed the `history://` contract in the system prompt to match the implementation: it serves registered agents process-wide plus persisted subagents discoverable from their artifact trees, but does not discover unregistered top-level sessions solely from persisted session files ([#5839](https://github.com/can1357/oh-my-pi/issues/5839)).
- Fixed expanded `!` bash and `eval` output keeping a stale `… N more lines (ctrl+o to expand)` footer after Ctrl+O revealed every line ([#5842](https://github.com/can1357/oh-my-pi/issues/5842)).
- Fixed MCP reauthentication continuing to an authorization URL without `client_id` after dynamic client registration fails; the registration error now blocks the flow with the provider response details ([#5852](https://github.com/can1357/oh-my-pi/issues/5852)).
- Fixed collapsed todo views hiding the in-progress task in large phases. Both the transient `Todo` tool result and the sticky `Todos` HUD now share one walking-viewport policy: completed/abandoned tasks are omitted, every active task (the in-progress one, or a pending task a live subagent is executing) is pulled to the head in todo order, remaining rows fill with the following pending tasks, and an explicit `… N more active todos` summary is shown when active work alone exceeds the preview cap ([#5873](https://github.com/can1357/oh-my-pi/issues/5873)).
- Fixed legacy provider extensions failing to load when they use the historical synchronous auth-storage surface ([#5879](https://github.com/can1357/oh-my-pi/issues/5879)).
- Fixed orphaned detached MCP stdio server process trees surviving session dispose by escalating stdin-EOF → group SIGTERM → group SIGKILL on close() (#5578)
- Fixed `/new` starting an unsolicited old-context provider turn when a hidden steer (e.g. an `xd://` mount notice) was queued: the session transition is now an atomic boundary, so a queued steer/follow-up can no longer auto-resume against the pre-`/new` context while the session is disconnected mid-transition. `/compact` still resumes a steer/follow-up that arrives while it runs, draining the queue once it reconnects ([#5800](https://github.com/can1357/oh-my-pi/issues/5800)).
- Fixed signed thinking-only Claude stops being discarded and retried as empty responses ([#5881](https://github.com/can1357/oh-my-pi/issues/5881)).
- Fixed repeated URL reads and URL-backed searches returning stale same-session responses instead of refetching the resource ([#5803](https://github.com/can1357/oh-my-pi/issues/5803)).
- Fixed `read`/`write` not recognizing ZIP-based `.jar`/`.war`/`.ear`/`.apk` files as archives, so `read lib.jar:META-INF/MANIFEST.MF` failed with path-not-found ([#5808](https://github.com/can1357/oh-my-pi/issues/5808)).
- Fixed legacy binary `.doc`/`.ppt`/`.xls`/`.rtf` being advertised as convertible in `read`, `fetch`, and CLI `@file` handling despite having no markit converter, which surfaced an `Unsupported format` error instead of falling through to normal file handling ([#5808](https://github.com/can1357/oh-my-pi/issues/5808)).
- Fixed Kimi Code transport selection to follow live per-model protocol metadata by default while preserving explicit OpenAI and Anthropic overrides ([#5893](https://github.com/can1357/oh-my-pi/issues/5893)).
- Fixed repeated edit-tool rejections from local models by recovering comma-separated ranges and malformed trailers, while clarifying canonical string input and `.=` syntax ([#5805](https://github.com/can1357/oh-my-pi/issues/5805)).
- Fixed LSP diagnostics and edit-time diagnostics writethrough for pull-only servers that advertise `textDocument/diagnostic` statically or through dynamic registration ([#5825](https://github.com/can1357/oh-my-pi/issues/5825)).
- Fixed local `!` command output concatenating carriage-return progress updates by preserving them as readable line boundaries ([#5845](https://github.com/can1357/oh-my-pi/issues/5845)).
- Fixed `hub`/`irc` peer discovery after process-crash resume by restoring persisted subagents as parked peers before listing the roster ([#5864](https://github.com/can1357/oh-my-pi/issues/5864)).

### Removed

- Removed the unreliable Bing and Yahoo HTML-scraping web search providers

## [17.0.2] - 2026-07-17

### Added

- Added native Warp CLI-agent events for rich session status, tool approvals, and completion notifications.
- Added support for ChatGPT/Codex subscriptions in the `generate_image` tool, allowing image generation without a metered `OPENAI_API_KEY` even when using other active models.
- Added an optional `provider` parameter to `generate_image` to override the global `providers.image` setting for a single request.
- Added OpenTelemetry log and metric export support alongside existing trace exports, enabling forwarding of centralized-logger events and GenAI-semconv metrics when configured.
- Enhanced `retry.fallbackChains` wildcards to support id-prefixed targets and keys, allowing more flexible model fallback routing across different providers.
- Added an opt-in per-project model role storage mode with global fallback from the model selector.
- Added per-advisor on/off toggle (`enabled: false` in `WATCHDOG.yml`): advisors stay in the roster but their runtime is never built — they show `○` in `/advisor status` rather than disappearing. Existing configs are backward-compatible (defaults to `true` when absent).
- Colored the status line's advisor `++` badge by roster health (green all running, yellow quota-exhausted, red failed, dim paused); per-advisor glyphs (`●`/`○`/`✕`) show in `/advisor status`.
- Added real provider quota display (usage percent, window, reset timer) to `/advisor status` and the `/advisor configure` preview.

### Changed

- Changed Bash command timeouts to render with a warning (yellow) border instead of an error (red) border, while still indicating to the model that the command did not complete normally.
- Made the hashline seen-line guard opt-in and off by default via `edit.enforceSeenLines`, and improved handling of column-clipped lines so single-line edits on long lines apply without a full-width re-read.
- Changed bundled TTSR rules to warn without interrupting generation.
- Renamed the system prompt's project-context section wrapper from `<context>` to `<repo-rules>` to prevent collisions with the `task` tool's `context` parameter.
- Enriched `/advisor status` to show per-advisor status glyphs, model, spend breakdown, and quota window for every configured advisor (including disabled ones), replacing the previous single-advisor-only summary.

### Fixed

- Fixed loading issues for linked legacy extensions importing `DefaultPackageManager` or `linkedom`.
- Fixed the advisor retrying terminal, non-retriable provider failures (e.g., blocked prompts), ensuring they fail immediately while transient failures still retry.
- Fixed an issue where reassigning the `plan` role model mid-planning did not take effect until the next plan-mode entry; it now applies at the next turn boundary.
- Added managed timer helpers (`ctx.setInterval`, `ctx.setTimeout`, `ctx.clearTimer`) to the extension context to prevent self-scheduled callbacks from throwing uncaught exceptions and crashing the session.
- Fixed `/quit` and `/exit` leaving stalled automatic title-generation requests alive during session teardown.
- Fixed `startup.quiet` still rendering the `xdev: xd://: mounted` status line when MCP tools connect.
- Fixed command errors in the `hub` tool when using a non-POSIX shell.
- Fixed xdev-routed checkpoint and rewind writes not tracking checkpoint state.
- Fixed the built-in advisor silently failing when its model routes through the Cursor provider by adding a Cursor execution bridge scoped to its granted tool set.
- Fixed the fullscreen plan-review overlay staying visible until the approved execution turn finished; it is now hidden as soon as execution begins.
- Fixed MCP tools repeatedly unmounting and remounting mid-session due to overlapping sanitized prefixes, and resolved stale tools remaining registered after disconnecting a server with special characters.
- Fixed the `/usage show` marker and TUI usage panel to display and preserve the active organization suffix (`email (OrgName)`) to distinguish between multiple credentials with the same email.
- Fixed Windows stdio MCP servers launched through `.cmd` or `.bat` shims failing with `Transport closed` by properly escaping arguments and spawning with `windowsVerbatimArguments`.
- Fixed a startup crash on Windows when running from a drive root (e.g., `R:\`).
- Fixed unknown `__omp_worker_*` CLI selectors exiting with code 0 instead of throwing an error.
- Fixed Plan Review capturing mouse drags as pointer events, which prevented native terminal text selection.
- Fixed orphaned TUI processes remaining alive after a fatal error and causing high resource consumption.
- Fixed approved-plan execution looping through filesystem searches when a model rewrites the required plan read path.
- Fixed Ask dialogs immediately accepting highlighted answers when they appear while the user is typing a space.
- Stopped post-compaction auto-continue from opening another primary turn after a terminal text answer with no queued work.
- Fixed the `write` approval gate misclassifying `xd://` device writes as `exec` when the mounted tool declared a function-valued approval.
- Fixed custom LSP servers (such as `roslyn-language-server`) crashing when requesting unconfigured workspace configuration sections.
- Fixed late user-initiated bash results being recorded in whichever session or branch was active when execution finished; they now retain their originating transcript.
- Fixed Claude Code marketplace plugins with `scope: "local"` leaking skills, hooks, tools, commands, and MCP servers into unrelated projects.
- Fixed headless `omp -p` waiting indefinitely after a completed turn when final consolidation stalls.
- Fixed explicit-tool sessions bypassing `xd://` presentation for ambient discoverable custom and MCP tools.
- Fixed `providers.webSearch: kimi` incorrectly sending Moonshot credentials instead of Kimi Code credentials.
