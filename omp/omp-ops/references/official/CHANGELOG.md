# Changelog

## [Unreleased]

## [16.4.5] - 2026-07-11

### Breaking Changes

- Reworked the task tool wire schema: moved the top-level agent field into individual task items, renamed assignment to task and id to name, and removed the role and description fields. UI labels are now automatically generated from the task text.

### Added

- Introduced a fullscreen, mouse-supported Model Hub (via /model) featuring a sidebar of scopes, metadata-aligned model tables, inline role/thinking assignment strips, custom role creation, quick-switch cycle editing, and manual provider refreshing.
- Added a /pause command to freeze all active agents (main, subagents, and advisor) at their next safe step, allowing manual repository edits mid-run before resuming.
- Added support for per-ID bulk conflict directives via write({ path: "conflict://*", content: "..." }) to resolve multiple conflicts in a single call.
- Added auto as a valid thinking-level in agent frontmatter, which is now the default for the bundled task subagent.
- Added rich, interactive, fixed-height ask dialogs featuring question tabs, option previews, notes, and multi-select toggles.

### Changed

- Redesigned OAuth logins to run inside a cancellable dialog (aborted via Esc) rather than an inescapable pairing prompt.
- Reworked the subagent soft request budget to gracefully steer child agents to wrap up and yield partial findings instead of silently terminating them, and raised the default budget to 200 requests.
- Updated task rendering to retain the agent type badge on live progress and finished result rows.

### Fixed

- Fixed issues where in-flight tool calls or task blocks would disappear from the chat during mid-turn transcript rebuilds or when background jobs settled.
- Fixed mixed blocking and non-blocking task batches degrading all spawns to synchronous execution; execution mode is now correctly handled per item.
- Fixed budget-stopped subagents becoming unreachable, allowing them to remain adopted and resumable via irc with full context.
- Fixed code duplication in write conflict://<N> when models pasted lines adjacent to the marker block.
- Fixed visible per-keystroke lag when searching in the /resume session picker by caching search targets and debouncing SQLite lookups.
- Fixed compiled Linux binary extension loading failures related to bundled web-search header generation data paths.
- Fixed job list and empty-poll snapshots returning empty output, ensuring running subagents without backing jobs are properly listed.
- Fixed agents getting stuck waiting for messages from peers that have already stopped running.
- Fixed compiled Linux binary extension loading when bundled web-search header generation cannot read `header-generator` data files from the build-time path. ([#5178](https://github.com/can1357/oh-my-pi/issues/5178))
- Fixed plugin custom tool loading to skip and report invalid feature entries instead of crashing startup when a plugin dependency tree leaves one feature unresolved. ([#5189](https://github.com/can1357/oh-my-pi/issues/5189))

## [16.4.4] - 2026-07-11

### Changed

- Optimized session title generation and auto-thinking classification for sub-billion-parameter tiny models (such as LFM2) by rewriting system prompts, improving input truncation to preserve message context, and unifying preprocessing to filter out noise like ANSI codes, XML tags, and long commit hashes.

### Fixed

- Fixed an issue where the Windows binary exited silently without running the CLI, which also caused `omp update` to roll back.
- Fixed native Windows binary compatibility on older Windows 10 CPUs by building the `omp-windows-x64.exe` release asset with a baseline x64 runtime instead of AVX2. (#5172)
- Fixed `GenerateImage` rejecting OpenAI Codex-compatible proxy bearer keys when the token does not expose a `chatgpt-account-id`. (#5174)
- Fixed context promotion documentation to accurately reflect the `contextPromotionTarget` runtime behavior and `contextPromotion.enabled` default. (#5163)

## [16.4.3] - 2026-07-11

### Added

- Added /vibe mode, allowing the model to act as a director driving persistent background worker sessions (fast and good tiers) with dedicated session tools (vibe_spawn, vibe_send, vibe_wait, vibe_kill, vibe_list) and a live TUI "TV wall" showing active worker activity, tool traces, and streamed output.
- Added multiple credential-free web search providers (Google, Bing, Yahoo, Startpage, Ecosia, Mojeek) with stealth-browser escalation, bot challenge detection, and recency filters, alongside a parallel public ("Public Web") provider that aggregates and deduplicates results across all engines.
- Added PCRE2 fallback support for grep lookaround and backreferences when the default Rust regex engine rejects a pattern.
- Added a helpful stderr hint when launching omp acp from an interactive terminal to clarify that the command communicates via JSON-RPC over stdout.

### Changed

- Reduced browser action timeout from 15s to 8s to improve agent iteration speed.
- Refined agent delegation logic to prioritize top-level planning by the primary agent, discourage single-agent delegation, and handle prerequisite work inline.
- Optimized credential-free web search engine ordering and routing, prioritizing Startpage and Ecosia, and using randomized desktop Chrome profiles with stealth-browser escalation for blocked requests.

### Fixed

- Fixed advisor config preserving an explicit empty tool list so `/advisor config` can disable all advisor tools. ([#5155](https://github.com/can1357/oh-my-pi/issues/5155))
- Fixed npm bundle generation failing on Linux with E2BIG by building dist/cli.js in-process via Bun.build instead of passing the embedded docs payload as a CLI --define argument.
- Fixed compiled-binary extensions failing to load native .node FFI dependencies by resolving platform-specific packages against the extension's own node_modules.
- Fixed a hang in omp search and omp q CLI commands by ensuring the AuthStorage connection is properly closed upon completion.
- Fixed write blocking for the full LSP diagnostics poll by deferring slow diagnostics to a late-diagnostics channel.
- Fixed multiple browser and puppeteer tool issues, including locator action timeouts, missing console/print output buffering, missing fill() method on element handles, and incorrect viewport screenshots on multi-tab setups.
- Improved browser selector error diagnostics to report match counts and abort early on empty matches instead of waiting for the full timeout.
- Fixed silent failures, duplicate error messages, and unhandled provider errors in ACP mode when errors occurred before streaming assistant text.
- Fixed glob reporting contradictory "no files found" messages on timeout by explicitly stating the scan was incomplete.
- Fixed read adding unwanted context padding to raw range selectors (e.g., raw:31-31).
- Fixed first-run interactive startup rendering the entire changelog when the last-seen marker is missing or unreadable (#5135).
- Fixed empty local-model stop responses exhausting retries without displaying a user-visible error (#5128).
- Fixed serialization of BigInt values in tool arguments during session compaction.
- Fixed GPT-5.6 over-delegating work by centralizing task fan-out and concurrency policy in the system prompt.
- Fixed session title generation including leaked thinking markup from OpenAI-compatible endpoints (#5122).
- Fixed bare skill://<name> path-only resolution for bash, grep, and glob to resolve to the skill directory instead of SKILL.md (#5087).
- Fixed macOS stdio MCP servers missing Apple Events TCC prompts by spawning MCP children via the correct Bun.spawn overload (#5085).
- Fixed the /move directory picker drawing a narrow 68-column frame inside wider overlays (#5067).
- Fixed snapcompact inline imaging for GitHub Copilot Business and Enterprise models (#4779).
- Fixed omp commit agent sessions to ensure valid proposals are committed before teardown, handle missing host outputs with non-zero exits, and prevent forcing GPG_TTY on signing-enabled repositories (#4794).

### Removed

- Removed the bundled plan subagent from available task agents.

## [16.4.2] - 2026-07-10

### Fixed

- Fixed an issue where BigInt values in tool arguments failed to serialize during session compaction.
- Resolved an issue where GPT-5.6 over-delegated tasks by refining task fan-out and concurrency policies in the system prompt.
- Fixed a race condition in concurrent MCP OAuth token refreshes across processes, ensuring rotating refresh tokens are only refreshed once and preventing stale token errors from clearing valid credentials.

## [16.4.1] - 2026-07-10

### Changed

- Reduced agent bias against large diffs and refactors in advisor prompts
- Updated advisor blocker criteria to prioritize explicit user instructions over plan size

### Fixed

- Fixed MCP OAuth dynamic client registration omitting discovered scopes on the RFC 7591 registration body. Providers such as Clerk bind DCR-created clients to only the scopes declared at registration, then reject the subsequent authorize request when it asks for `openid` (from `scopes_supported`). Registration now includes `config.scopes` when present, matching Claude Code and the scopes already sent on authorize.

## [16.4.0] - 2026-07-10

### Breaking Changes

- Renamed the bundled agent explore to scout, including its configuration keys, prompt files, and task definitions. Any configurations, allowlists, or invocations referencing explore must now use scout.
- Changed the public `selectLaunchAdapter()` result from `DapResolvedAdapter | null` to `LaunchAdapterSelection`; callers must handle `adapter`, `unavailable`, and `none` outcomes.

### Added

- Added a native, first-class max thinking tier for supported models, including a new thinkingBudgets.max configuration setting, support in CLI flags (--thinking, :max model suffixes), and terminal theme customization (thinkingMax border color and icons).

### Fixed

- Fixed Go debug launches falling back to native debuggers when Delve is unavailable; nested modules and `go.work` workspaces now resolve local Delve adapters before PATH, newly installed adapters are detected without restart, and missing adapter errors include install or configuration guidance. ([#5037](https://github.com/can1357/oh-my-pi/issues/5037))
- Fixed a memory leak (large retained JavaScriptCore heaps) in the TUI during session transcript rebuilds and refreshes by properly handling snapcompact archive image frames.
- Fixed a crash in interactive TUI sessions (Cannot set cwd while another same-realm JS runtime is running) when the JS evaluation worker falls back to the in-process inline path.
- Fixed compaction aborting when Amazon Bedrock credential resolution fails, ensuring it now falls back to trying an authenticated model.
- Improved OpenAI prompt cache hit rates for full-context forks by persisting inherited provider prompt-cache keys separately from session IDs, and added a --prompt-cache-key flag for explicit cache affinity.
- Fixed Codex advisor requests incorrectly using local session labels as provider session IDs, switching to stable UUIDv7 provider identities.
- Fixed macOS stdio MCP servers launching in detached sessions, allowing tools like xcrun mcpbridge to successfully trigger TCC Apple Events permission prompts.
- Fixed the ask tool timeout behavior to automatically select the recommended option if the UI selector does not settle.
- Fixed LSP workspace diagnostics for Go workspaces to correctly recognize go.work roots and include all specified modules in go build package patterns.
- Fixed interactive OAuth login (/login xai-oauth) delaying success messages; credentials are now reported immediately while model metadata refreshes in the background.
- Fixed a crash in the Windows bash tool when a timeout occurs while a piped command is streaming output.
- Fixed subagent yield tool calls being discarded when a soft request budget aborts the assistant turn before the yield event completes.
- Fixed --tools filtering in interactive sessions incorrectly disabling deferred MCP tools from configured servers.
- Fixed kept-alive task subagents entering infinite provider-call loops after an IRC wake and terminal yield.

## [16.3.15] - 2026-07-09

### Changed

- Integrated testing guidance directly into the main system prompt for improved workflow cohesion
- Moved testing guidance into the main system prompt and removed the bundled Tester subagent.

## [16.3.14] - 2026-07-09

### Fixed

- Fixed issue where unfinalized tool blocks could incorrectly pin the live-region scroll seam
- Improved rendering of raw thinking blocks by stripping empty HTML comment noise
- Fixed display of thinking blocks consisting entirely of hidden comment noise
- Fixed gpt-5.6 reasoning summaries rendering literal `<!-- -->` sentinel lines in thinking blocks; empty HTML comments (and the unterminated `<!--` tail while streaming) are now dropped from the thinking display, and blocks reduced to pure comment noise are hidden entirely.

## [16.3.13] - 2026-07-09

### Fixed

- Fixed `read` and `grep` treating empty optional `selector` fields emitted by models as invalid selectors instead of behaving like omitted selectors. ([#4879](https://github.com/can1357/oh-my-pi/issues/4879))
- Fixed `grep` explicit line selectors on directory searches so they filter each matched file by line number instead of aborting with a single-file-only error ([#4898](https://github.com/can1357/oh-my-pi/issues/4898)).
- Fixed Read tool previews dropping explicit `selector` arguments, so line ranges and `raw` modifiers render in terminal read call titles again ([#4899](https://github.com/can1357/oh-my-pi/issues/4899)).
- Fixed named profiles dropping default user keybindings from `~/.omp/agent/keybindings.*`; profile keybindings now inherit those defaults and override only the keys they define ([#4867](https://github.com/can1357/oh-my-pi/issues/4867)).
- Fixed pi extensions calling `ctx.ui.addAutocompleteProvider(...)` crashing at load with `TypeError: ... is not a function` — a failure that, for extensions guarding init in one `try/catch` (e.g. `@ff-labs/pi-fff`), aborted the extension's entire initialization. `ExtensionUIContext` now implements pi's autocomplete-provider API: interactive mode stacks each registered factory on top of the built-in editor provider (re-applied on every slash-command refresh, with throwing or malformed factories skipped), while RPC/ACP/headless contexts accept the factory as a no-op. ([#4919](https://github.com/can1357/oh-my-pi/issues/4919))
- Fixed bundled reviewer and plan subagents to inherit their model roles' explicit thinking effort suffixes instead of pinning `high` ([#4761](https://github.com/can1357/oh-my-pi/issues/4761)).
- Built-in provider model discovery now refreshes an expired stored OAuth credential before an online refresh needs it, instead of silently skipping the provider. The refresh is scoped to the providers actually being discovered (`refreshProvider` cannot rotate unrelated credentials), fires under `online-if-uncached` only when the model manager will actually fetch, and offline discovery stays peek-only ([#4893](https://github.com/can1357/oh-my-pi/issues/4893)).
- Fixed Escape during an active TUI prompt requiring a second press before canceling; the first Escape now aborts the streaming turn immediately. ([#4921](https://github.com/can1357/oh-my-pi/issues/4921))
- Fixed the streamed `write` tool's collapsed pending tail preview leaving stale rows above the first partial-result frame in the TUI; the first result now replays the viewport like the SSH placeholder seam already did ([#4477](https://github.com/can1357/oh-my-pi/issues/4477))
- Fixed first-run setup ignoring a pre-seeded `config.yaml`: the settings loader now treats `config.yml` and `config.yaml` as equivalent existing main config files, writes back to the existing extension, and only creates canonical `config.yml` for fresh installs. ([#4914](https://github.com/can1357/oh-my-pi/issues/4914))
- Fixed extension `sendUserMessage()` without `deliverAs` surfacing `AgentBusyError` during active streams; omitted `deliverAs` now queues a steer through the normal prompt flow, and ACP/RPC skill-command prompts queue while streaming (RPC honors the prompt command's `streamingBehavior`, defaulting to steer) ([#4923](https://github.com/can1357/oh-my-pi/issues/4923)).

## [16.3.12] - 2026-07-08

### Added

- Typing `#<number>` (e.g. `#3164`) in the prompt now offers PR and Issue autocomplete candidates that rewrite to the `pr://`/`issue://` internal URL, resolved from the current repo's git remote via the existing `read` tool → InternalUrlRouter → `gh` pipeline. Naming the type (`pr #3164` / `issue #3164`) constrains the candidates to that kind, and embedded hashes like `owner/repo#N`, `foo#N`, or URL fragments are left untouched ([#3218](https://github.com/can1357/oh-my-pi/issues/3218))

### Changed

- Memoized non-message token totals (system prompt, tool schemas, skills) so the per-turn compaction and context-threshold paths recompute them at most once per input change instead of on every call. `getContextBreakdown` and `#estimateStoredContextTokens` previously re-tokenized the system prompt and every tool's wire schema (per-tool `JSON.stringify`) several times per turn over inputs that change at most once per turn.

### Fixed

- Improved handling of unawaited promises in JS eval cells to prevent process crashes
- Added warning logs for unhandled rejections originating from finished eval cells
- Improved advisor robustness by blocking exhausted accounts during consecutive turn failures
- Fixed advisor turns hammering the same usage-limited account: a failed advisor turn now marks the exhausted credential blocked (with the provider's retry hint and usage-report reset time), so the next retry rotates to a sibling instead of re-picking the blocked account every few seconds. Previously the in-stream auth retry rotated within a request but never blocked the last failing credential, and the advisor loop — unlike the primary retry pipeline — never called `markUsageLimitReached`.
- Added the account key to the `codex-auto-reset: skipped` debug log so skip reasons (e.g. `weekly-not-exhausted`) can be attributed to the evaluated account.
- Fixed unawaited promise rejections in JS eval cells crashing the session: a floating rejection now fails the owning cell run (`Unhandled rejection (missing await?): …`) instead of escaping to the global `unhandledRejection` handler, which printed `[Unhandled Rejection]` and killed the process (inline fallback) or tore down the eval worker (dedicated worker). Rejections surfacing after a cell settled are downgraded to a warn log attributed to the finished cell.
- Fixed project `.omp/RULES.md` sticky rules being shadowed by user `~/.omp/agent/RULES.md` rules with the same synthesized `RULES` name, so both user and project sticky rules now inject ([#4739](https://github.com/can1357/oh-my-pi/issues/4739)).
- Fixed bash internal-URL expansion so unresolved literal `memory://` / `skill://` text stays verbatim instead of aborting command execution ([#4737](https://github.com/can1357/oh-my-pi/issues/4737)).
- Fixed `agent://<id>` (and the `output()` eval helper) failing with `Not found` for a subagent spawned by another subagent (any spawn chain 2+ levels deep). `artifactsDirsFromRegistry` scanned only each ref's adopted (root-wide) `ArtifactManager` dir, but a subagent's own children are written one level deeper under its `sessionFile`-derived dir — so a live, addressable nested peer's output was unresolvable. The resolver now collects both candidate dirs per registered agent. ([#4650](https://github.com/can1357/oh-my-pi/issues/4650))
- Fixed plan mode to document `local://` artifacts as writable session-local planning files and to carry every pre-approval `local://` artifact into the fresh session created by Approve and Execute.
- Fixed the browser tool failing to launch Microsoft Edge-only Windows installs with Puppeteer's empty `Code: 0` launch error by keeping Edge's required `--enable-automation` default while preserving Chrome/Chromium stealth launch defaults.
- Fixed bash/tool command environments inheriting Bun-autoloaded launch `.env.local` values, so nested apps can load their own dotenv values without parent deployment variables taking precedence. ([#4723](https://github.com/can1357/oh-my-pi/issues/4723))
- Fixed legacy plugin validation for extension graphs that import JSON with `with { type: "json" }`, leaving JSON files on Bun's native loader instead of parsing them as JavaScript ([#4687](https://github.com/can1357/oh-my-pi/issues/4687)).
- Fixed pasted terminal transcripts beginning with a shell prompt (`$ ...`) being mistaken for local Python shortcuts instead of being submitted as normal prompts ([#4678](https://github.com/can1357/oh-my-pi/issues/4678)).
- Fixed wrapped OAuth copy-URL rows corrupting on paste: continuation chunks no longer carry a leading indent, so a multi-row terminal selection reassembles to the exact authorize URL (browsers strip newlines on paste but preserve or percent-encode embedded spaces, which previously corrupted the URL at every chunk boundary).
- Fixed Windows browser-launch failures being unobservable: the opener now uses `%SystemRoot%`-resolved PowerShell `Start-Process` (via `-EncodedCommand`) instead of `rundll32`, which exits 0 unconditionally. Failures ShellExecute itself reports — missing target, no handler executable, access denied — now surface as non-zero exits and are logged; the encoded payload also keeps OAuth query strings (`&`-bearing) opaque to shell metacharacter parsing.
- Fixed system prompt date rendering to use the host local calendar date instead of UTC.
- Fixed `bash` tool `timeout: 0` so it disables the command deadline instead of falling back to the minimum timeout.
- Fixed `read` and `grep` refusing to access filesystem paths whose names end in a selector-shaped suffix (e.g. `test:1-2`, `log:raw`) by preferring a literal match over the trailing `:<selector>` peel when the raw path exists on disk ([#4618](https://github.com/can1357/oh-my-pi/issues/4618)).
- Fixed wrapped Edit-diff rows leaking inverse video into the result card's right-edge padding: a row that broke inside an intra-line highlight left inverse active at the row end, so the frame padding after it rendered as a default-foreground block ([#4616](https://github.com/can1357/oh-my-pi/pull/4616) by [@chan1103](https://github.com/chan1103))
- Fixed Edit-diff continuation rows escaping into the line-number column when the row's gutter was left-padded (line number narrower than the widest in the diff) or blanked by the gutter dedup (the bare `+` row of a single-line replacement); such rows now wrap behind a continuation gutter, while body lines that merely start with `|` keep wrapping generically ([#4616](https://github.com/can1357/oh-my-pi/pull/4616) by [@chan1103](https://github.com/chan1103))
- Fixed live advisors continuing to use a stale `modelRoles.advisor` selection after `/model` changed the advisor model. ([#4612](https://github.com/can1357/oh-my-pi/issues/4612))
- Fixed Claude plugin slash commands and skills silently vanishing when the plugin manifest declares `commands`/`slash-commands`/`skills` as a JSON array — the shape the Claude plugins reference documents and real plugins like `addyosmani/agent-skills` ship. `resolvePluginDir` in `packages/coding-agent/src/discovery/claude-plugins.ts` typed those fields as `string` and dropped array values on the floor; it now normalizes both shapes, loads every in-root entry, and reports one out-of-plugin-root warning per bad entry. The resolver also now honours Claude's per-field merge semantic — `skills` adds to the default `skills/` scan; `commands`/`slash-commands` replace the default `commands/` — so plugins like `{"skills":["./extra-skills"]}` no longer lose their default `skills/` folder while `{"commands":["./admin"]}` still replaces `commands/` as documented. ([#4609](https://github.com/can1357/oh-my-pi/issues/4609))
- Fixed macOS Backspace on empty search not deleting sessions in the `/resume` picker; Fn+Backspace terminals that deliver `\x7f` instead of `\e[3~` now reach the delete confirmation dialog. ([#4580](https://github.com/can1357/oh-my-pi/pull/4580) by [@JagravNaik](https://github.com/JagravNaik))
- Fixed `/rename` title arguments treating `#` prompt-action tokens as autocomplete triggers instead of literal session title text. ([#4600](https://github.com/can1357/oh-my-pi/issues/4600))
- Fixed empty session `.jsonl` files accumulating in `~/.omp/agent/sessions/<cwd>/` after a draft-then-clear exit cycle. `SessionManager.saveDraft(text)` materializes the session file so the draft sidecar has a parent; a subsequent `saveDraft("")` unlinked the sidecar but left the metadata-only JSONL behind (title slot + session header + startup selector entries, ~500–750 B), and `#shouldHaveSessionFile()` could no longer prune it once `#fileIsCurrent`/`#forceFileCreation` were latched. `SessionManager.close()` now drops only draft-owned metadata-only sessions with no saved draft sidecar to reattach to, while keeping real conversations, meaningful non-message entries such as handoff custom messages, explicit `ensureOnDisk()` sessions, drafts still pending for `--resume`, and never-materialized sessions untouched ([#4571](https://github.com/can1357/oh-my-pi/issues/4571)).
- Fixed the advisor being disabled for the entire session when the advisor role resolves to a reasoning model that exposes no controllable effort surface (Devin `devin/glm-5-2*`: `reasoning: true`, `thinking: undefined` — Cascade routes by sibling model id rather than a wire param). `#resolveAdvisorRuntimeDescriptors` in `packages/coding-agent/src/session/agent-session.ts` used to hardcode `ThinkingLevel.Medium`, which tripped `requireSupportedEffort` on the first advisor prompt with `Thinking effort medium is not supported by devin/glm-5-2. Supported efforts:` (empty list). The advisor descriptor now clamps the requested effort against the resolved model via `resolveThinkingLevelForModel` and forwards no explicit effort when the model has no controllable efforts — matching the `auto`-path fix (`clampAutoThinkingEffort`) and the Autonomous Memory stage fix (`clampThinkingLevelForModel`). Explicit `:off` still disables reasoning, and models that support `medium` (e.g. Anthropic) keep receiving it ([#4579](https://github.com/can1357/oh-my-pi/issues/4579)).
- Fixed legacy extension plugin validation failing with `Export named 'calculateCost' not found in module '.../legacy-pi-ai-shim.ts'` when the extension imports `calculateCost` (or `modelsAreEqual` / `getBundledProviders`) from `@oh-my-pi/pi-ai`. Those symbols were relocated to `@oh-my-pi/pi-catalog/models` during the catalog split but were never bridged back through the legacy `pi-ai` root shim; the shim now re-exports them alongside the existing `getModel` / `getModels` aliases so plugins written against pre-split pi-ai load again ([#4584](https://github.com/can1357/oh-my-pi/issues/4584)).
- Fixed legacy extension plugin validation failing with `Export named 'calculateCost' not found in module '.../legacy-pi-ai-shim.ts'` when the extension imports relocated catalog symbols such as `calculateCost`, `modelsAreEqual`, `getBundledProviders`, `getBundledModel`, or `getBundledModels` from `@oh-my-pi/pi-ai`. Those symbols were relocated to `@oh-my-pi/pi-catalog/models` during the catalog split but were never bridged back through the legacy `pi-ai` root shim; the shim now re-exports them alongside the existing `getModel` / `getModels` aliases so plugins written against pre-split pi-ai load again ([#4584](https://github.com/can1357/oh-my-pi/issues/4584)).
- Fixed legacy pi extension imports of `DefaultResourceLoader` from `@mariozechner/pi-coding-agent` / `@earendil-works/pi-coding-agent` by adding a compatibility loader shim that translates `resourceLoader` into OMP's native session discovery options. ([#4567](https://github.com/can1357/oh-my-pi/issues/4567))
- Fixed legacy Pi extension reloads on POSIX so `loadLegacyPiModule` imports the entry through a cache-busting filesystem path, refreshes load-time graph hooks when reloads add new modules, and threads the current load's `?mtime` tag through the extension source graph — relative `./helper.ts` siblings, `#alias/*` package-imports, extension-local bare dependency entries, and their relative children all rekey per reload, so same-process re-imports pick up edits across the whole graph. ([#4565](https://github.com/can1357/oh-my-pi/issues/4565))
- Fixed bash tool pipeline execution preserving stale upstream output when the final stage was a stripped `head`/`tail` limiter; the tool now runs the command as written so `seq 1 5 | head -n2` returns only `1` and `2`. ([#4562](https://github.com/can1357/oh-my-pi/issues/4562))
- Fixed the status-line token-rate segment rendering as `<number>/s`, which Ghostty auto-detected as a hyperlink on Ctrl+hover. ([#4541](https://github.com/can1357/oh-my-pi/issues/4541))
- Fixed retry fallback model recovery by exposing `retry.fallbackChains` in `/settings`, adding a `/model` action to assign the selected default fallback model, and clearing a selected model's retry cooldown marker on manual model switches. ([#4533](https://github.com/can1357/oh-my-pi/issues/4533))
- Fixed `/handoff` and auto-handoff skipping extension lifecycle hooks by emitting cancellable `session_before_switch` hooks and a `session_switch` with `reason: "handoff"` after the replacement session is ready ([#4434](https://github.com/can1357/oh-my-pi/issues/4434)).
- Fixed TTSR stream interrupts so only the tool call whose stream matched a rule receives the rule-named abort result; sibling tool-call placeholders now use a neutral abort reason ([#2783](https://github.com/can1357/oh-my-pi/issues/2783)).

## [16.3.11] - 2026-07-06

### Changed

- Improved session title generation reliability by moving to marker-based parsing for all models

### Fixed

- Fixed session titles occasionally showing raw `{"title": "..."}` JSON. Online title generation now always uses the `<title>...</title>` marker prompt instead of a forced `set_title` tool call — hosts that ignored or rejected forced `tool_choice` echoed the prompt's JSON example verbatim as the title — and JSON-shaped responses (bare, code-fenced, marker-wrapped, or truncated) are unwrapped to the bare title.
- Fixed Linux startup prompt construction to read the CPU model from `/proc/cpuinfo` instead of `os.cpus()`, avoiding per-core sysfs frequency probes on many-core hosts ([#4712](https://github.com/can1357/oh-my-pi/issues/4712)).
- Fixed llama.cpp model discovery to honor per-model `architecture.input_modalities` from `/v1/models`, so router presets that advertise image input are no longer treated as text-only ([#4719](https://github.com/can1357/oh-my-pi/issues/4719)).

## [16.3.10] - 2026-07-06

### Changed

- Limited subagent HUD display to 8 items with a summary for additional running subagents
- Improved TUI performance by coalescing agent registry and observer UI updates

### Fixed

- Fixed high-subagent sessions overwhelming the TUI by bounding the running-subagent HUD and coalescing subagent progress repaint bursts.
- Fixed browser run cleanup crashing or wedging the whole omp session: run-end and tab-close aborts could reject fire-and-forget `wait()`/facade/tab promises with no consumer, and the global unhandled-rejection handler then exited the process, killing every subagent sharing it. Run-scoped promises are now observed at creation and routine browser teardown aborts are downgraded to log lines ([#4499](https://github.com/can1357/oh-my-pi/issues/4499), [#4672](https://github.com/can1357/oh-my-pi/issues/4672)).
- Reduced CPU use while many task subagents stream progress by disabling the obsolete task partial-result spinner repaint loop ([#4424](https://github.com/can1357/oh-my-pi/issues/4424)).
- Capped collapsed nested subagent trees at the same per-level agent limit as top-level task rendering (failures prioritized, elided rows summarized), so deep many-subagent sessions no longer render unbounded progress trees on every repaint.
- Fixed skill card headers to render a single space between the `skill` tag and skill name ([#4662](https://github.com/can1357/oh-my-pi/issues/4662)).
- Fixed `get_session_stats` RPC responses to include context-window usage so RPC clients can render context meters.
- Fixed startup of cached llama.cpp vision models so the initial default/restored model refreshes `/props` metadata before the session exposes it as text-only.
- Fixed IRC-woken yielded subagents skipping empty-stop retry because stale yield-termination state carried into the wake turn ([#4658](https://github.com/can1357/oh-my-pi/issues/4658)).
- Fixed `irc wait` skipping replies that arrived between wait calls by draining pending IRC asides before honoring queued-interrupt aborts ([#4657](https://github.com/can1357/oh-my-pi/issues/4657)).

## [16.3.9] - 2026-07-06

### Added

- Added a `--file` flag to the `say` command to read input text directly from files.
- Enabled streaming text synthesis in the `say` command for gapless, long-form audio generation.
- Added voice selection validation to the `say` command.

### Changed

- Improved the `say` command to display the segment count and total duration upon completion.

### Fixed

- Fixed an issue where local llama.cpp vision models remained text-only after a model refresh, ensuring they are correctly recognized as image-capable when configured as the default or vision role.
- Fixed `omp commit` split plans aborting when lock files (such as `bun.lockb`) were staged alongside their manifests by correctly pairing lock files with their corresponding commit groups and properly handling binary files during split execution.
- Fixed skill loading to ensure that disabling a higher-priority provider does not drop same-named skills from enabled lower-priority providers.

## [16.3.8] - 2026-07-05

### Fixed

- Fixed the browser tool silently launching without its Puppeteer stealth patch: the patch was keyed to `puppeteer-core@25.1.0` while the resolved dependency had drifted to `25.3.0`, so Bun skipped it and Chrome ran with the `Runtime.enable` automation tell re-enabled. Regenerated the stealth patch against 25.3.0 and pinned `puppeteer-core` so the exact-version patch cannot silently deactivate on future drift.

## [16.3.7] - 2026-07-05

### Added

- Added support for reading full memory rows (working or episodic) via `read memory://<id>` under the mnemopi backend, returning a YAML-frontmatter header with metadata to prevent blind overwrites during edits.
- Updated the URI grammar to support `memory://root[/…]` for file-backed summaries and `memory://<memory-id>` for specific mnemopi IDs.

### Changed

- Updated `recall` and `memory_edit` tool prompts to document truncation markers and require reading a memory ID before updating a truncated preview.
- Parallelized resolution of system files (`SYSTEM.md`, `APPEND_SYSTEM.md`, and `TITLE_SYSTEM.md`) at startup to improve performance.
- Optimized TUI performance and reduced CPU usage during streaming and live tool calls by scoping renders to changed subtrees, interning the working-message shimmer palette, and memoizing copy-selector preview highlights.
- Loaded persisted Agent Hub subagents asynchronously to prevent blocking the TUI on directory walks.
- Cached persisted message keys in `AgentSession` to avoid repeated branch walks on message completion.
- Skipped TTSR delta buffering for text/thinking sources when no registered rules match.

### Fixed

- Fixed macOS Backspace behavior in the `/resume` picker for terminals delivering `\x7f` instead of `\e[3~`.
- Fixed queued follow-up message rows leaking into native terminal scrollback during live repaints by anchoring the pending-messages container.
- Fixed `/rename` title arguments treating `#` prompt-action tokens as autocomplete triggers instead of literal text.
- Fixed empty session `.jsonl` files accumulating in the sessions directory after a draft-then-clear exit cycle.
- Fixed advisor being disabled for the entire session when resolving to a reasoning model with no controllable effort surface (e.g., `devin/glm-5-2*`).
- Fixed legacy extension plugin validation failures by re-exporting relocated catalog symbols (such as `calculateCost`, `modelsAreEqual`, and `getBundledProviders`) through the legacy `pi-ai` root shim.
- Fixed legacy Pi extension imports of `DefaultResourceLoader` by adding a compatibility loader shim that translates `resourceLoader` into native session discovery options.
- Fixed legacy Pi extension reloads on POSIX to ensure same-process re-imports pick up edits across the entire dependency graph.
- Fixed bash tool pipeline execution preserving stale upstream output when the final stage was a stripped `head` or `tail` limiter.
- Fixed the status-line token-rate segment rendering as a clickable hyperlink in Ghostty.
- Fixed xAI `web_search` to prioritize `xai-oauth` credentials before falling back to `xai` API keys, and enforced result counts locally to avoid sending unsupported parameters.
- Fixed token-usage badges disappearing on session resume for empty automated assistant turns.
- Fixed `/model` search escaping the active provider tab and silently persisting a same-named model from a different provider as the default role.
- Fixed Esc key behavior to immediately silence active TTS audio playback (such as Kokoro) once an assistant reply finishes streaming.
- Fixed grep and bash tool guidance to instruct agents to use Rust-style patterns or `grep -E` instead of GNU BRE assumptions.
- Fixed tool-call renderers crashing the TUI when providers send array/object `path` arguments before schema validation.
- Fixed `glob` tool rejecting slash-only root searches (e.g., `path:"/"`) with a documented error instead of returning empty results.
- Fixed `omp read` hanging on PDFs whose inline-image binary payloads contain delimiter-looking bytes.
- Fixed `pi/<role>` model resolution crashing on YAML list-valued `modelRoles` entries.
- Fixed the snapcompact settings UI to expose `silver16-bw` and improved renderability warnings to report unsupported glyphs.
- Fixed session and status usage totals to preserve provider-reported orchestration tokens separately from input and cache-hit buckets.
- Fixed published `.d.ts` declaration files to be consumable under `moduleResolution: "node16" | "nodenext"` by rewriting relative specifiers to explicit `.js` extensions.
- Fixed `omitThinking` settings propagation so settings-aware streams request hidden thinking summaries when explicitly enabled.
- Preserved isolated branch-mode task output as a patch artifact when `commitToBranch` fails, surfacing the captured patch path through the evaluation failure message.
- Fixed task-class subagents dropping unresolved explicit model-role selectors before startup.
- Fixed large legacy snapcompact archives causing crashes on resume due to oversized archived frame payloads.
- Fixed LSP diagnostics staleness by sending watched-file change notifications to running language servers before reading edit-time diagnostics.
- Documented the bash tool timeout clamp (capped at 3600 seconds for async jobs) in the model-facing schema and prompt.
- Fixed `/fast on` for custom OpenAI-compatible providers serving OpenAI models, and reported unsupported models as unavailable.
- Fixed extension `pasteToEditor` and `setEditorText` prompt mutations leaving the editor visually stale by scheduling a repaint after mutations.
- Fixed session title generation, commit-message generation, speech-enhancer rewrites, and classifiers silently truncating on non-reasoning-flagged models that still emit thinking output.
- Fixed plan-mode "Approve and compact context" discarding queued operator turns and leaking internal plan-distillation prompts to extension hooks.
- Fixed malformed `pi.sendMessage` custom-message payloads persisting bare session entries that crashed subsequent resumes.
- Hid internal `display: false` session-update reminders from compact history and advisor transcripts.
- Fixed idle recap crashes caused by side-channel stream malformations.
- Applied WebSocket send backpressure with ordered drain retries to prevent unbounded buffer growth.
- Capped docs.rs gunzip decompressed size at 256 MB to prevent zip-bomb out-of-memory crashes.
- Deleted pre-created shell snapshot files when snapshot creation fails.
- Aborted underlying MCP calls when proxy tool timeouts fire.
- Surfaced unexpected JS eval worker exits via close listeners to prevent silent hangs.
- Cached failed `!command` config resolutions and timed out extension dynamic model fetches after 15 seconds.

## [16.3.6] - 2026-07-04

### Changed

- Hided abort labels for user-interruptions in the transcript to match silent abort behavior
- Updated transcript streaming to declare settled rows for scrollback exactness: `TranscriptContainer` reports one boundary (finalized blocks plus the first live block's `getTranscriptBlockSettledRows()`, fed by markdown's frozen-token prefix — completed content blocks in a streaming reply render final and settle in full, so long replies and visible thinking reach terminal scrollback as exact bytes mid-stream). The heuristic commit machinery (`deriveLiveCommitState` append-only detection, stable-prefix ratchet, volatile cooldowns, rewrite floors), `isTranscriptBlockCommitStable`, and the per-renderer `provisionalPendingPreview`/`provisionalPartialResult` flags are all removed. Ephemeral block retraction (displaceable todo/job cards, IRC cards) is now gated on `TranscriptContainer.isBlockUncommitted()` — cards whose rows already entered scrollback seal in place as history instead of being removed.
- Recovered auto-retry errors now compact in the transcript: once a retry succeeds, the superseded error rows (e.g. Anthropic `429 rate_limit_error` during account rotation) render as a single dim note like `rate-limited; switched account; retried` across live view, rebuilds, resume, and subagent/collab transcript views, and are excluded from model context on session resume. Terminal (unrecovered) errors keep full error rendering. The persisted marker is `retryRecovery` on the assistant message and `auto_retry_end` success events carry additive `recoveredErrors` data.

### Fixed

- Fixed raw `read` ranges not contributing to edit seen-line provenance, so re-reading an anchor range with `:raw` now unblocks hashline edits without adding non-raw line prefixes.
- Fixed replan-driven session title refresh updating the statusline but not the terminal window title: terminal-title updates now fire from the session-name-changed listener, so every `setSessionName` path (first-input titling, `/rename`, plan seeding, replan refresh) sets the OSC title consistently.
- Fixed user-interrupt aborts rendering the persisted `Interrupted by user` label in assistant transcripts; replay and live views now suppress that redundant line again while preserving generic/custom abort labels.
- Fixed streamed assistant text and thinking disappearing from terminal scrollback while a long turn ran, and Ctrl+O-expanded tool results showing up half-rendered above the viewport: everything that scrolls off the window now reaches native scrollback (exact bytes for settled content, a frozen what-you-saw snapshot for still-running blocks, repaired at most once when the block finalizes). Streaming eval/bash boxes no longer spray duplicated stale copies; user-initiated `!`/`$` execution blocks report a finalization contract.
- Fixed turn-ending provider errors rendering with a doubled blank gap above the `Error:` block (caller and error block each added a spacer).
- Fixed the write tool renderer crashing when persisted runtime content is a truthy non-string value; rendering now coerces display content before Windows CR normalization. ([#4495](https://github.com/can1357/oh-my-pi/issues/4495))
- Fixed cmux-backend `browser({action:"run"})` calls crashing the entire process with an unhandled rejection when the tab was released mid-run (e.g. a sibling subagent calling `browser({action:"close", all:true})` or a session-scoped tab reap). `runInTabWithSnapshot` in `tab-supervisor.ts` creates a `Promise.withResolvers()` triple so `releaseTab` can signal in-flight runs, but the cmux branch used to await `runCmuxCode(...)` directly and never awaited the local promise. When `releaseTab` rejected that orphaned promise ("Tab ... was closed"), Bun surfaced it as an unhandled rejection and the top-level handler tore the whole session down, killing every other tab and subagent sharing it. Both backends now await the same `promise` (so `pending.reject` always has an attached handler AND the caller sees `Tab "..." was closed` immediately instead of blocking to the run's timeout), and a new `pending.closeAc` is composed into the cmux run's abort signal so `wait(...)`, in-flight cmux socket calls, and the facade proxies unwind promptly when the tab is closed rather than leaking to their own timeout ([#4499](https://github.com/can1357/oh-my-pi/issues/4499)).

## [16.3.5] - 2026-07-04

### Fixed

- Fixed Mnemopi auto-retention so protocol markers are stripped from embedding and FTS projections while stored transcripts remain readable. ([#4395](https://github.com/can1357/oh-my-pi/issues/4395))
- Fixed mnemopi auto-retain storing cumulative full-session transcripts on every retention interval; subsequent retains now store only newly completed user-turn suffixes. ([#4396](https://github.com/can1357/oh-my-pi/issues/4396))
- Fixed large `artifact://` reads materializing entire MCP/tool artifacts before selector paging, preventing OOM crashes on unbounded raw reads and surfacing bounded read/search/copy guidance ([#4482](https://github.com/can1357/oh-my-pi/issues/4482)).
- Fixed `/mcp reauth` and `/mcp add` dropping OAuth scopes advertised via `WWW-Authenticate: Bearer scope="..."` challenges and via protected-resource metadata (`scopes_supported` / `scopes` / `scope`), which caused tokens to be issued without the required scopes and reconnects to fail with `insufficient_scope` ([#4467](https://github.com/can1357/oh-my-pi/issues/4467))
- Fixed task-branch merges aborting the whole cherry-pick range when a single commit was empty against HEAD (redundant with an already-applied change, or 3-way merged to HEAD); the sequencer now `--skip`s the empty commit and continues so later non-overlapping work still lands ([#4438](https://github.com/can1357/oh-my-pi/issues/4438)).
- Fixed write/edit LSP diagnostics for TypeScript files outside any project root by suppressing project-resolution noise while preserving real syntax errors ([#4401](https://github.com/can1357/oh-my-pi/issues/4401)).
- Fixed `/mcp reauth` against S256-only OAuth providers (Linear, and OAuth 2.1 flows generally) failing on Windows and other environments where the browser cannot auto-open. Two independent defects converged on Linear's `The plain PKCE method is not allowed. Use S256 instead.` error page: `openPath` invoked bare `rundll32` and silently swallowed the resulting `Executable not found in $PATH` when the Windows machine PATH no longer referenced `System32`, and `MCPAuthorizationLinkPrompt` composed a `Copy URL:` line wider than the viewport that `TUI#prepareLine` then silently truncated — trimming the trailing `code_challenge_method=S256` (RFC 7636 §4.3 treats a request with `code_challenge` and no method as `plain`). The MCP OAuth fallback, `/login`, setup wizard, auth-broker CLI, and login-dialog now advertise the short `OAuthAuthInfo.launchUrl` (loopback `/launch` route hosted by `OAuthCallbackFlow`) as the copy target; the OSC 8 hyperlink still carries the full URL for click-through; the MCP flow additionally stages the copy target on the clipboard via OSC 52; and the Windows opener now resolves `rundll32.exe` through `%SystemRoot%\System32\`, logging spawn failures and non-zero exits instead of dropping them ([#4418](https://github.com/can1357/oh-my-pi/issues/4418)).
- Fixed `lsp rename_file` aborting when an LSP server returns duplicate byte-identical non-empty text edits for the same range, such as tsserver `willRenameFiles` edits through barrel re-exports ([#4458](https://github.com/can1357/oh-my-pi/issues/4458)).
- Fixed Linux x64 `PI_TINY_DEVICE=cuda` tiny-model side runtimes missing ONNX Runtime CUDA provider binaries by repairing the `onnxruntime-node` CUDA sidecar install and preserving actionable CUDA diagnostics in `omp tiny-models download` output ([#4475](https://github.com/can1357/oh-my-pi/issues/4475)).
- Improved reliability of edits when file snapshots share identical 16-bit hash tags
- Fixed ACP `terminal/create` sending the bash tool's full shell line in `command` with no `args`, which broke spec-conformant clients that spawn `command`+`args` directly (no implicit shell) — any command containing a space, pipe, `&&`, redirect, or `$(...)` failed with `ENOENT` and the agent silently degraded to read-only tools. The bash tool now wraps the shell line before calling `clientBridge.createTerminal`, reusing the same shell binary + args the local `bash-executor` resolves via `settings.getShellConfig()` (Git Bash / `bash.exe` on Windows, `$SHELL` with `sh` fallback on POSIX) so bash semantics — `$VAR`, `$(...)`, `source`, POSIX quoting, `-l` — are preserved on both platforms. ([#4333](https://github.com/can1357/oh-my-pi/issues/4333))
- Fixed inference worker subprocesses (TTS, STT, tiny-model, mnemopi embeddings) discarding stderr, which left every unexpected exit — most visibly the local Kokoro TTS worker's recurring `exit code 7` crash loop — undiagnosable from the parent's logs. `createWorkerSubprocess` now pipes stderr without starting a live read while the worker is idle, then drains the stream after `onExit`, emits captured lines to `logger.debug` under an `<exitLabel> stderr` message, and keeps the last 16 KiB in a bounded ring that gets appended to the `Error` surfaced through `onError`. The exit surface is synchronized with the post-exit drain via `SpawnedSubprocess.stderrDrained`, so the full native trace shows up on the `tts: worker error` line without reintroducing event-loop liveness from unref'd workers. ([#4324](https://github.com/can1357/oh-my-pi/issues/4324))
- Fixed Windows session tail loss after atomic compaction rewrites by fencing append writers during full-file replacement and gating the atomic publish on a `commitGuard` that the storage backend checks synchronously before rename, so a concurrent `flushSync` (Ctrl+C / session-exit) is not overwritten by the stale body serialized before it ran. Covers post-compaction prompts, tool results, title changes, and exit diagnostics on the current JSONL path ([#4338](https://github.com/can1357/oh-my-pi/issues/4338)).

## [16.3.4] - 2026-07-03

### Fixed

- Fixed `omp usage` hiding sibling-only limits such as Claude 7 Day (Fable) on accounts whose current report omitted that scoped bucket; the account now renders an explicit `not reported` row instead of looking like the usage refresh skipped the column.

## [16.3.3] - 2026-07-02

### Breaking Changes

- Removed _input as a supported alias for the edit tool input field

### Changed

- Refined advisor note card visuals with a dedicated rail character and bold label headers
- Deferred session_stop extension hooks and incomplete-todo reminders until all agent-owned background jobs (such as async bash or task spawns) are fully idle
- Restyled the advisor note card so notes no longer blend into thinking output: bold label-tag header, heavier severity-tinted rail, and note body on the default text color instead of thinking-gray

### Fixed

- Fixed TUI loading animation sometimes failing to render during interactive mode status updates
- Fixed race conditions and potential hangs during agent startup by improving process lifecycle management
- Fixed RpcClient startup errors intermittently losing the child's stderr (e.g. the "Unknown provider" message) by waiting for the process to exit — and its stderr to fully drain — before reporting a failed start; also fixed an unhandled rejection when the agent process is killed before becoming ready
- Improved reliability of file edits when snapshots share identical hash tags
- Fixed terminal creation in ACP by properly wrapping shell commands and arguments, resolving execution failures (such as ENOENT errors) on Windows and POSIX platforms
- Fixed inference worker subprocesses (such as TTS, STT, and embeddings) discarding stderr, ensuring unexpected crashes and exit traces are properly captured and surfaced in logs
- Fixed potential session data loss on Windows during atomic compaction rewrites by preventing concurrent writes from overwriting the session file during exit or compaction
- Fixed transcript scrollback boundaries to prevent duplicate rows from appearing when live blocks grow
- Fixed macOS SSHFS mount detection to avoid redundant remounting attempts when the mountpoint is unavailable
- Fixed SSH streamed placeholders and partial frames leaving stale rows in the TUI viewport and scrollback
- Fixed Gemini web search to correctly honor the configured search model (providers.webSearchGeminiModel or GEMINI_SEARCH_MODEL) for both OAuth and Developer API grounding requests
- Fixed omp install rejecting valid npm package specifications
- Improved MCP OAuth reauthorization error messages when dynamic client registration is closed, directing users to configure client credentials
- Fixed omp update -l to correctly support the plugin-update shorthand for upgrading marketplace plugins
- Fixed /advisor on command to correctly rebuild the advisor runtime and bind to the newly configured model
- Fixed edit tool failures on large source files after a structural-summary read by automatically merging unseen anchor lines into the snapshot
- Fixed potential hangs and process leaks in the Debug Adapter Protocol (DAP) client by introducing write timeouts and ensuring detached adapter processes are terminated on connection failures
- Fixed status-line GitHub PR lookup hangs by enforcing a command timeout
- Fixed potential pipe-buffer deadlocks during plugin installation, uninstallation, and updates by concurrently draining stdout and stderr
- Fixed SSH tool hangs on unreachable hosts by enforcing a 30-second timeout on pre-command connection and host probes
- Fixed models.yml schema validation to surface warnings for invalid custom provider configurations instead of silently ignoring them
- Fixed potential network hangs in omp update, Hindsight recall, and Smithery registry lookups by adding fetch timeouts
- Reduced TUI CPU overhead during streaming and idle waits by dropping the redundant pre-render on every session event, iterating shimmer text in place instead of allocating a code-point array per animation frame, and coalescing the live-tool spinner render cadence to its glyph-advance rate ([#4353](https://github.com/can1357/oh-my-pi/issues/4353)).

## [16.3.2] - 2026-07-02

### Breaking Changes

- Changed search tool `paths` parameter to a single semicolon-delimited `path` string parameter

### Changed

- Reduced extension startup cost, especially on Windows, by reading each extension source-graph module from disk once per load instead of twice (the graph scan now feeds the load-time rewrite hook) ([#4196](https://github.com/can1357/oh-my-pi/issues/4196)).

### Fixed

- Fixed ALL-CAPS acronyms (e.g. `CNPG`, `ETL`, `JWT`) being lowered to title case in auto-generated session titles. `reconcileTitleCasing` (`packages/coding-agent/src/tiny/text.ts`) now maps ALL-CAPS source tokens into an `acronyms` table and restores them when the model produces a title-cased artifact (`Cnpg`), while still declining restoration on shouty input (`FIX the BUG NOW`, `ALL ERROR HANDLING`) via a consecutive-ALL-CAPS heuristic. Title prompts also instruct the model to preserve ALL-CAPS acronyms verbatim. ([#4220](https://github.com/can1357/oh-my-pi/issues/4220))
- Fixed cold-start `--model` resolution for extension providers whose catalogs come only from `fetchDynamicModels`, so fresh cached runtime models are available before session startup falls back or hard-fails. ([#4216](https://github.com/can1357/oh-my-pi/issues/4216))
- Fixed plugin and legacy extension discovery repeatedly re-reading plugin manifests and walking extension `node_modules` by caching results until plugin cache invalidation. ([#4197](https://github.com/can1357/oh-my-pi/issues/4197))
- Fixed `discoverExtensionPaths` invoking every registered extension-module provider (claude, codex, gemini, opencode) on startup and discarding all non-native results. The extension-module capability is now loaded with `providers: ["native"]`, skipping four foreign directory walks per session — noticeable on Windows where the walks are slowest ([#4198](https://github.com/can1357/oh-my-pi/issues/4198)).
- Fixed `/move` overlay running an `fs.statSync` per directory entry per keystroke; the directory listing cache now stores `Dirent[]` and classifies entries without a syscall, falling back to `statSync` only for symlink entries ([#4199](https://github.com/can1357/oh-my-pi/issues/4199)).
- Fixed default model switches being persisted without changing the active goal-mode session when the current context exceeded the target model window. ([#4219](https://github.com/can1357/oh-my-pi/issues/4219))
- Fixed live tool preview spinners staying pinned to their first frame for `eval` and shell-style renderers. ([#4170](https://github.com/can1357/oh-my-pi/issues/4170))
- Fixed isolated task merges failing when the parent working tree carried WIP for a file the isolated subagent also touched. `commitPatchToBranchWorktree` now tries plain apply and `git apply --3way` first (agent-only outcome when the WIP-side blob is tracked in HEAD), then falls back to seeding the temp worktree with the baseline WIP so the delta patch's HEAD+WIP context matches, and rewinds WIP-only files afterward so they don't leak into the branch commit. Covers untracked WIP files, staged-new WIP files, and overlaps `--3way` cannot resolve. ([#4136](https://github.com/can1357/oh-my-pi/issues/4136))
- Fixed `discoverAgents()` skipping `agents/` subdirectories inside OMP extension packages, so agents shipped by `omp plugin install`-ed npm plugins (e.g. `loom`) and `--extension`/`extensions:` settings roots now load the same way their sibling `skills/`, `hooks/`, `tools/` directories already do. The new scan goes through `listOmpExtensionRoots`, so Claude marketplace installs continue to flow through the `claude-plugins` provider without being double-counted. ([#3920](https://github.com/can1357/oh-my-pi/issues/3920))
- Fixed plan mode hanging without converging on `ask`/`resolve` after advisor cards, idle IRC messages, or follow-on turns. Plan-mode decision enforcement ran on only the non-synthetic `prompt()` return; continuation/wake paths settled via `agent_end` and bypassed it. Advisor cards and idle IRC are now recorded into context without waking an autonomous turn, and the `ask`/`resolve` decision is enforced at the universal `agent_end` terminal settle via a bounded-retry counter (provider-neutral `required`, both tools kept available) that reminds-then-forces a fixed number of times and then yields to the user — never looping, never silently ending plan mode un-converged. An `irc send await:true` to an idle plan-mode session now answers the sender through the existing ephemeral side-channel auto-reply instead of stranding it until its wait timeout, and a queued forced plan decision is dropped when its continuation is skipped or plan mode exits. ([#3910](https://github.com/can1357/oh-my-pi/issues/3910))
- Reduced subagent streaming CPU cost: the recent-output window no longer re-splits the full (up to 8 KB) tail on every streamed text token. Fragments without a newline extend the current last line in place, and a full recompute runs only when line boundaries actually change.
- Reduced task-render CPU cost: the task result frame (repainted ~30×/sec via the spinner) previously did 7+ full passes over the result set (`some`/`filter`/`reduce`); a single pass now derives the status booleans, footer counts, and request total, and incremental review extraction reuses the yield data the caller already normalized instead of re-normalizing it.
- Reduced model-resolution cost: `resolveModelRoleValue` now builds the preference context (an O(n) model-order map over all available models) once and reuses it across every fallback pattern instead of rebuilding it per pattern, and `matchModel` hoists the case-folded pattern once instead of `.toLowerCase()`-ing it for every candidate across each filter pass.
- Reduced read-tool allocation: line counting counts newlines directly instead of allocating via `split("\n")`, and the hashline formatter no longer counts the same content twice.
- Fixed the assistant-message streaming fast path dropping the transient flag, which disabled the transient render path (code-highlight skip and streaming prefix caches) on every same-shape streaming tick. In-flight renders now correctly skip per-tick syntax highlighting; highlighting applies once at message finalization.
- Fixed hidden goal-mode todo context: phase names and task text are now sanitized before prompt injection (no raw newlines or control characters forging extra context lines), and the block is only rendered with tool-accurate guidance when the `todo` tool is active or discoverable instead of unconditionally instructing the agent to call an unavailable tool.
- Fixed custom tool loading treating `process.exit()` from a tool module's import or factory as a host process exit instead of a recoverable load failure. Custom tools now load under the shared extension exit guard, so an exiting tool is skipped with a load error while remaining tools still load ([#1704](https://github.com/can1357/oh-my-pi/issues/1704)).

## [16.3.1] - 2026-07-02

### Breaking Changes

- Changed the `grep`, `glob`, and `ast_grep` tools to take a single optional `path` argument instead of a `paths` array. `path` accepts one path or a semicolon-delimited list (`src; tests`); omitting it searches the workspace root (`.`). Multi-path search, delimited expansion, and internal-URL scopes are unchanged. (`ast_edit` continues to take `paths`.)

### Added

- Added `speech.enhanced` setting to rewrite assistant output into natural spoken prose
- Added `speech.enhanced` setting: assistant output is rewritten into natural spoken prose by the tiny/smol model before synthesis — code blocks become one-clause descriptions, links speak their label or site name, numbers and symbols read naturally, lists become flowing sentences. Blocks are rewritten fence-aware and coalesced (bounded to two concurrent completions); any failed or timed-out rewrite falls back to the mechanical cleanup so speech never blocks on the model.

### Changed

- Redesigned speech vocalization for low latency and clean spoken content. Assistant markdown now runs through a speakable-text pipeline before synthesis: code blocks and tables are silent, links speak their label, bare URLs speak their host, inline-code ticks/emphasis/heading/bullet markers are stripped, and long file paths collapse to their basename. Segmentation is now parent-side and emits at sentence boundaries immediately (the previous engine-side splitter held each sentence until the next one arrived), with clause-level cuts for long sentences and an idle flush when generation stalls mid-sentence. macOS gains a gapless streaming playback backend (ffmpeg AudioToolbox, sox fallback) instead of spawning `afplay` per sentence.

### Fixed

- Fixed stuttering/latency in speech by running synthesis chunks through the player gaplessly
- Fixed race condition causing EPIPE errors and broken pipes during speech playback
- Fixed interrupted speech audio by ensuring segments queue and drain in order
- Fixed speech vocalization starting only after the entire reply was synthesized: ONNX inference blocks the TTS worker's event loop, so per-segment IPC audio chunks queued unflushed and arrived in one burst. Streaming sends now drain the IPC channel before the next segment's inference, cutting time-to-first-audio to ~1.5s regardless of reply length.
- Fixed an unhandled `EPIPE: broken pipe, write` rejection at the end of speech playback: the streaming player's `stop()` raced an un-awaited `FileSink.end()` against the backend SIGKILL, and mid-session writes never awaited the flush. Writes now await the flush (so a dead backend is detected and the chunk replays on the next candidate or the per-file path) and `stop()` swallows the expected teardown rejection.

## [16.3.0] - 2026-07-02

### Added

- Added `providers.anthropic.serverSideFallback` configuration option to opt into Anthropic's server-side-fallback beta chain, allowing Claude requests to automatically retry on alternative models when blocked by classifiers.
- Added `task.softRequestBudgetNotice` configuration option to enable subagent soft-budget wrap-up steering notices while keeping the graceful abort guard active.

### Changed

- Significantly optimized session loading and rendering performance, including a 10x speedup for streaming reveals on large messages, 35% faster session resumes for large files using native streaming JSONL parsing, and reduced overhead for edit-patch fallbacks.
- Improved TUI responsiveness and reduced CPU usage during long-running tool sessions by throttling status-line redraws and optimizing subagent persistence checks.
- Updated the tester subagent prompt to allow skipping tests for trivial changes.
- Improved DuckDuckGo web search error clarity and documented datacenter/shared-egress limitations in provider settings.

### Fixed

- Fixed session persistence corrupting Anthropic, OpenAI, and Google signed thinking blocks and reasoning payloads, ensuring cryptographic signatures and encrypted content are preserved verbatim to prevent API replay rejections (HTTP 400).
- Fixed several issues with the `apply_patch` and edit tools, including preventing dirty buffers on early aborts, rejecting overwrites of pre-existing files, stopping at the first failing file in multi-file operations, and pruning extremely large file snapshots to prevent session inflation.
- Fixed process termination (SIGTERM, SIGHUP, uncaught exceptions) to ensure editor drafts are saved, sessions shut down cleanly, and background jobs are cleaned up.
- Fixed `/quit` and `/exit` commands blocking session closure by introducing a shutdown budget and backgrounding remaining tasks.
- Fixed git clone and fetch operations being killed prematurely by applying a separate 30-minute deadline for network transfers instead of the standard 5-minute local-command timeout.
- Fixed git index corruption issues in `mergeTaskBranches` and `applyNestedPatches` when post-merge stash pops conflicted with the cherry-picked HEAD.
- Fixed collaboration (`/collab`) issues, including preventing teardowns from cancelling active host dialogs, sanitizing host-delivered errors for guests, and ensuring guest UI requests are correctly routed and rendered.
- Fixed RPC mode deferred shutdown (`pi.shutdown()`) and `abort_bash` commands from being blocked by active background bash processes.
- Fixed model discovery ignoring `NODE_EXTRA_CA_CERTS` and resolved a rare Bun garbage collection segfault during discovery.
- Fixed `task.maxConcurrency` and `task.maxRecursionDepth` limits being bypassed by sub-spawn paths or when queued spawns were cancelled.
- Fixed various TUI and rendering issues, including macOS Ghostty `Command+V` image pasting, CJK history rendering across compactions, status-line redraw crashes with BigInt values, and overlapping rows in the subagent progress tree.
- Fixed `/copy code` and `/copy cmd` commands being treated as normal prompts instead of copying the requested blocks.
- Fixed legacy tool compatibility issues for `createReadTool`, `createGrepTool`, and extension validation failures for `omp install pi-lean-ctx`.
- Improved robustness of MCP authentication error detection, Smithery command authorization failures, and streaming preview responsiveness for write, edit, and eval tools.
- Fixed llama.cpp router/preset mode reporting 128k context in the status bar for every preset picked from `/model` regardless of the preset's configured `--ctx-size`.
- Fixed post-rewind context to tell the agent the checkpoint completed and to make repeat `rewind` calls recover with guidance instead of a bare no-checkpoint error.
