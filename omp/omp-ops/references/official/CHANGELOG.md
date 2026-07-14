# Changelog

## [Unreleased]

## [16.5.1] - 2026-07-14

### Changed

- Enhanced Anthropic credential and usage management to support organization-scoped accounts, including displaying organization names in /usage, /logout, omp token --list, and OAuth login success messages, resolving active-account matching for shared organizations, and deduplicating identities during migration.

### Fixed

- Fixed compatibility of GNU-flavored shell builtins (such as stat, date, sed, mktemp, tail, find, base64, and ln) when invoked with macOS/BSD-style arguments.
- Fixed subagent model and thinking level resolution to correctly respect the configured modelRoles.task selector instead of intermittently falling back to the parent session's model.
- Fixed TUI rendering issues, including preventing macOS runtime diagnostics from painting into the viewport, bounding transcript retention in long sessions, and fixing scrollback repainting when collapsing history.
- Fixed /tan and /fork clones failing to inherit or persist the parent session's prompt cache keys.
- Fixed Python and JavaScript evaluation kernels suspending the CLI on subprocess foregrounding, deadlocking on non-serializable values, or losing in-flight subagent work during external aborts.
- Fixed configured retry.fallbackChains failing to engage when encountering non-retryable provider errors.
- Improved auto-compaction to automatically drop images and elide content when context is tight, and added persistent warning badges to the compaction divider when manual intervention is required.
- Fixed the downshift plan nudge silently ending runs with no code written when the model answered with a text-only reply.
- Fixed launch tool rendering and status reporting, including resolving contradictory readiness timeout messages and preventing backgrounded Bash blocks from continuing to repaint.
- Fixed Advisor containment and timing issues, preventing hallucinated tool calls from contaminating later advice and ensuring late-arriving transcript deltas are coalesced before advisor calls.
- Fixed omp update on npm-managed Windows installations to prevent downloaded release binaries from overwriting npm launchers.
- Fixed --max-time duration values (e.g., 5s, 10m, 1h) being ignored instead of setting a session deadline.
- Fixed omp plugin install --force failing with a dependency loop when replacing an existing pinned Git plugin source.
- Fixed MCP tools receiving session image attachments as raw local:// URIs instead of resolving them to local filesystem paths.
- Fixed Pyright LSP semantic requests hanging during startup.
- Fixed Codex web search requests for GPT-5.6 Responses-Lite models.
- Fixed custom model/provider configuration discovery to correctly load ~/.omp/agent/models.yaml when models.yml is absent.

## [16.5.0] - 2026-07-13

### Breaking Changes

- Replaced the `--reasoning-slide-*` flag family with a unified `--prewalk` mechanism (`--prewalk`, `--prewalk-into <model>`, and `--no-prewalk`) to manage model handoffs during execution.

### Added

- Added a new `--prewalk` execution flow (with `--prewalk-into <model>` and `--no-prewalk` overrides) that starts tasks on a strong model for planning and todo initialization before handing off to a faster, cheaper model for implementation.
 - Added a status line annotation for the active prewalk phase (armed or active).
 - Added the `tui.scrollbackRebuild` setting to gate the erase-and-replay native scrollback rebuild mechanism (defaults to off).
- Added a display setting to toggle between collapsing or keeping compacted history inline in live session displays.
- Added a compact session-only model picker (Alt+P) for quick model switching, featuring `@` search to quickly list and apply configured quick roles.
- Redesigned Agent Hub entries into a cleaner two-line card layout showing identity, active model, reasoning level, age, and task description.
- Added a project-scoped `launch` tool (gated by `launch.enabled`) for managing shared long-running services and debuggers, featuring readiness probes, bounded logs, PTY input, restart policies, and automatic teardown.
- Added support for `detached` launches, allowing standalone services to survive broker shutdowns and reconnect to subsequent sessions.

### Changed

- Updated JSON logs (`--mode json`) to include provider payloads in auto-compaction events.
- Updated tangential agent forks (`/tan`) to ignore parent session history and focus exclusively on the new request, hardening isolation with cleared todo lists and concurrent editing warnings.
- Added visual markers in the transcript for elided tool calls that have no corresponding result.
- Updated the status event log to prioritize the most recent entries in the display window.
- Upgraded `@agentclientprotocol/sdk` to version 1.2.1.

### Fixed

- Fixed terminal scrollback duplication issues with expanded streaming edit previews (Ctrl+O) by using a viewport-sized tail window.
- Fixed custom model role resolution and alias parsing, ensuring canonical role selectors (`@role`) and thinking suffixes resolve correctly across all configuration surfaces.
- Fixed quadratic growth in JSON logs by eliding redundant message snapshots and payloads.
- Fixed prompt cache misses and incorrect cache key pinning for `/tan` and `/fork` clones.
- Fixed inconsistent history rendering and scrollback repainting when toggling the display setting for compacted items.
- Fixed `retry.fallbackChains` failing to engage on non-retryable provider errors, ensuring the agent correctly falls back to the next candidate model.
- Improved auto-compaction to automatically drop images and elide content when context is tight, and added persistent warning badges when manual intervention is required.
- Fixed backgrounded Bash blocks continuing to repaint with live output; they now freeze with a compact job notice while completion is delivered separately.
- Fixed rendering, status display, and PTY control sequence formatting issues in the `launch` tool.
- Fixed in-process shell builtins (including `stat`, `date`, `sed`, `mktemp`, `tail`, `find`, `base64`, and `ln`) to correctly detect and translate macOS/BSD-style arguments and flags, preventing failures caused by GNU-only assumptions.

### Removed

- Removed the `--prewalk-boomerang` feature and its associated configuration setting.
- Removed the unreliable Bing and Yahoo HTML-scraping web search providers.

## [16.4.8] - 2026-07-12

### Added

- Added a predicate form to the browser run's `wait()` helper: `wait(fn, { timeout?, interval? })` polls the function (sync or async) until truthy and resolves with that value, failing with a named timeout error (deadline clamped under the cell budget so it always beats the opaque whole-cell timeout) instead of Bun's `sleep expects a number` or a whole-cell stall from in-page polling Promises; both `wait` forms now register in the stall diagnosis of cell timeouts
- Added `--reasoning-slide-model` and `--reasoning-slide-turns` to switch a running agent from its initial model after a fixed number of completed assistant turns
- Added `--reasoning-slide-plan` (with `--reasoning-slide-plan-at`) to steer a hidden deep-planning nudge into the run before the reasoning slide; the switch is held until a substantial plan turn actually lands (bounded by a grace window) and the nudge is scrubbed from the LLM context at the switch so the fast model inherits only the produced plan
- Added `--reasoning-slide-on-action` to trigger the reasoning slide at the first completed turn that ran an edit/write tool instead of a fixed turn count (bash is excluded — it doubles as exploration)

### Changed

- Replaced the Alt+P / `/switch` temporary model selector's fullscreen /models hub with a compact full-width floating overlay anchored above the editor (~40% of the terminal height): just the searchable model list — no provider sidebar or role management — with the session's active model highlighted and preselected
- Improved tab recovery after timeouts by automatically clearing pending navigation and JS dialogs
- Made `tab.goto` navigation failures catchable with a named error instead of triggering a whole-cell timeout
- Made `tab.evaluate` run in the page's main JavaScript world so page-defined globals are available without a directive
- Enhanced cell timeout messages to include identification of stalled operations and blocking JS dialogs
- Browser `run` on a tab the supervisor force-killed now reports the kill reason instead of a bare "not alive"
- Refined agent workflow to prioritize smoke testing and reduce mandatory upfront test generation

### Fixed

- Fixed the eval tool's status-event tree truncating from the bottom: the newest `log()` progress lines were hidden behind an `… N more` marker while the oldest stayed visible; the tree now shows a tail window behind an `… N earlier` marker, and the expanded view widens to the viewport instead of a fixed 10 events
- Fixed the `//!world=main` directive being silently ignored for string expressions passed to raw Puppeteer evaluation APIs
- Fixed tab reuse issues where hung navigation or unhandled modals would cause initialization to stall and trigger a force-kill
- Improved search reliability for Perplexity provider by forcing retrieval for all queries
- Fixed JS eval cells losing top-level `function` and `var` declarations across cells when the defining cell contained top-level `await` — the async wrapper scoped them to the cell's IIFE instead of publishing them to the worker global

## [16.4.7] - 2026-07-12

### Added

- Enabled Home and End keyboard navigation in the model browser
- Added a `c` hotkey in the plan-review overlay that copies the current reviewed plan markdown to the system clipboard, including in-overlay edits.

### Changed

- Streamlined list view styling by removing inline model role chips from row entries
- Reworked /models hub selection visuals: the background highlight band is reserved for mouse hover, the keyboard position is a cursor glyph drawn only in the pane that owns the arrow keys, and the sidebar's active scope renders as a bold accent label
- Removed the redundant "login" label from inactive (locked) provider entries in the Model Hub sidebar

### Fixed

- Fixed PageUp/PageDown in the model browser wrapping past the list edges instead of clamping
- Fixed the hover highlight sticking to the last hovered model row when the pointer moved into the provider sidebar

## [16.4.6] - 2026-07-12

### Added

- Added `invalidate` action to the usage command to clear cached usage reports
- Added model-oriented keys and wildcard entries to `retry.fallbackChains`: a `provider/model-id` key attaches a fallback chain to that exact model, a `provider/*` key covers every current or future model of a provider, and a `provider/*` chain entry keeps the failing model's id while swapping the provider (`google-antigravity/x` → `google/x`) — so fallbacks survive role and model reassignments without config edits. Keys resolve by specificity: exact model, then provider wildcard, then role, then `default`.
- Added fallback-chain editing to the /models Roles view: each role's `retry.fallbackChains` entries render as indented rows beneath it, `f` picks a fallback model to append, Enter on an entry replaces it, `x`/backspace removes it, and `[`/`]` (or shift+↑/↓) reorder the chain.
- Added model-keyed fallback management to the /models Roles view: model and `provider/*` chains render as a separate section below the roles (divider + "+ New fallback…" row for creating one by picking the protected model, then keying it by model or provider), with the same replace/remove/reorder editing as role chains; the model strip gains `fallbacks:<model>` and `fallbacks:<provider>/*` chips as shortcuts.
- Added `/queue <message>` plus `->` / `=>` composer shorthand for follow-up messages that wait until the agent yields. The shorthand opens a dim `Queueing` header and splits sequential numeric, Roman-numeral, or alphabetic lists into separately highlighted queue entries.
- Added per-model TPS/TTFT tracking: every completed assistant turn folds its timing into recency-weighted aggregates in `~/.omp/agent.db`, and the /models browser shows measured speed — a right-aligned `118t/s` column on wide terminals (plus TTFT, e.g. `0.9s 118t/s`, when wider) and `~118t/s · 0.9s ttft` facts in the selection detail line — with no dependency on the `omp stats` session scan.

### Changed

- Retain completed and abandoned tasks in session history for improved context on resume
- Changed the Model Hub `retry-fallback` strip chip to append the model to the default fallback chain instead of prepending it, matching the chain-building order of the Roles view (already-registered models are a no-op).
- Changed per-model perf recording (`recordModelPerf`) to be deferred like prompt history: samples are batched and written to `agent.db` in one transaction ~100ms later, keeping SQLite writes off the turn-completion hot path.

### Fixed

- Fixed failure to trigger model fallback when the retry budget is exhausted by credential rotation
- Fixed uncontrollable mouse-wheel scrolling in the /models hub: the wheel moved the selection (one step per wheel event, so a single trackpad flick skipped many rows) and wrapped from the bottom back to the top. Wheel scrolling now pans the list viewport only, clamps at the ends, and leaves the selection where it is; keyboard navigation still scrolls the selection into view. Likewise, the wheel over the provider sidebar no longer switches the active scope (or triggers provider refreshes) — it just scrolls the sidebar.
- Fixed TPS being inflated several-fold when a provider hides reasoning tokens until late in the stream (e.g. `google/gemini-3.5` vs `google-vertex/gemini-3.5` reporting 648 vs 186 TPS for identical durations): `omp bench`, the per-turn usage row, and the /models perf aggregates now measure tokens/sec over the total request duration instead of the post-TTFT decode window, matching `omp stats`. Stored perf aggregates are purged and re-backfilled from stats history with the corrected math on first launch.
- Fixed the model-perf stats.db backfill freezing the TUI (~30s on multi-million-row stats databases) when /models triggered it: the import is now fire-and-forget, walks the newest rows in small chunks with event-loop yields between them, and is bounded to 90 days / 256 newest samples per model — beyond either bound the recency decay would erase the contribution anyway.
- Fixed compiled release binaries bundling `fastembed` and baking the build-machine `@anush008/tokenizers` path; native runtime dependencies now stay external for every compiled build path so Mnemopi resolves its on-demand install instead. ([#5195](https://github.com/can1357/oh-my-pi/issues/5195))
- Fixed `/btw` side-channel turns on Codex models such as `gpt-5.6-luna` by preserving the session websocket preference instead of forcing SSE, and made Esc dismiss the active `/btw` panel before interrupting loop/maintenance work. ([#5213](https://github.com/can1357/oh-my-pi/issues/5213))
- Fixed the Model Hub role-assignment strip hiding the selected chip once the row overflowed; the strip now scrolls horizontally, truncating passed chips behind a leading ellipsis so the selection (plus one chip of lookahead) stays visible.
- Fixed mouse hover and clicks in the /models Roles view landing one row above the pointer (the row mapping subtracted the status row twice).
- Fixed model search keeping the most-recently-used model on top of the results: match quality now ranks first (an exact `gpt-5.5` beats the active `gpt-5.6-sol`), with MRU order only breaking ties between equally good matches.

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

