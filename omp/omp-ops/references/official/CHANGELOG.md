# Changelog

## [Unreleased]

### Added

- Added `qwenTemplateReasoningEffort` to the `models.yml` `compat` schema, so the auto-enabled Qwen 3.8+ template effort dialect (`chat_template_kwargs.reasoning_effort`) can be switched off per provider/model for strict local servers that reject unknown `chat_template_kwargs`.

### Changed

- `/settings` rows can now carry a risk note: a warning glyph on the row plus a warning-colored line above the description. `External Thinking` (`externalThinking`, `--external-thinking`) is the first user — providers have flagged the request shape it produces as abuse, up to account-level enforcement, so both the settings entry and `--help` now say so.

## [17.3.8] - 2026-08-19

### Added

- Added `providers.cacheRetention` setting (`/settings` → Providers → Protocol) to control prompt-cache retention per request: `auto` keeps the provider default (Anthropic: 5m entries with idle keep-alive refreshes), `short` forces 5m, `long` restores 1h TTLs where supported and disables the keep-alive refresh loop, `none` disables prompt caching.

### Changed

- The `read` tool now materializes a local text file once per invocation instead of once per consumer. A ranged read of a file within the snapshot cap previously cost four opens and three UTF-8 decodes — an 8KiB binary sniff, a streaming scan for the rendered window, a whole-file read for bracket context, and another whole-file read to hash the snapshot — with two of those readers separately normalizing line endings; whole-file reads under the structural summarizer paid a fifth read. Byte counts and truncation boundaries are now measured on the buffered bytes, so they stay exact for content that is not valid UTF-8. Files above the snapshot cap keep streaming, since nothing on that path wants the whole file. Raw reads, which skip the tree-sitter parse that documented the old cost, no longer pay for it.
- Documented that `bash.patterns` gates the `bash` tool only and does not cover a shell that `eval` can spawn via subprocess, and that closing that path needs a `tools.approval.eval` policy — noted in `docs/bash-tool-runtime.md`, `docs/approval-mode.md`, and `docs/settings.md` ([#8838](https://github.com/can1357/oh-my-pi/issues/8838)).

### Fixed

- Fixed the `/btw` panel re-committing its frame to native scrollback on every update while the primary turn is still streaming: a live region that pins itself (an anchored HUD/panel such as `/btw`) no longer leaks its scrolled-off rows just because an unpinned transcript seam sits above it in the same frame ([#8793](https://github.com/can1357/oh-my-pi/issues/8793)).
- Fixed a submitted `/skill:<name>` command staying invisible in the transcript until its awaited preflight (memory recall, `before_agent_start` hooks, auto-thinking classification, pre-prompt compaction) finished, so a slow step such as a Hindsight auto-recall timeout made the command look unaccepted. Idle skill submissions now paint an optimistic row immediately — like a normal prompt — and reconcile it in place when the canonical `message_start` lands ([#8895](https://github.com/can1357/oh-my-pi/issues/8895)).
- Fixed broker-backed MCP OAuth credentials never refreshing, so remote OAuth MCP servers dropped out of `/mcp` once their access token expired under `omp auth-broker serve`. The client threw on the broker-redacted refresh sentinel instead of asking the broker to refresh, and the broker had no `mcp_oauth:*` refresh path (`POST /v1/credential/:id/refresh` answered `Unknown OAuth provider`). The client now routes redacted MCP refreshes through the broker, and the broker refreshes MCP credentials with a generic `refresh_token` grant from the credential's embedded token endpoint and client id — so the background refresher also keeps MCP tokens live ([#8933](https://github.com/can1357/oh-my-pi/issues/8933)).
- Fixed `omp commit` split-commit failing with `corrupt binary patch` when a split commit contains a binary file. `parseFileDiffs` split the captured diff on `"\ndiff --git "`, consuming the `\n` that terminates each block, and `patch.join` stripped trailing newlines — both dropped the blank line that terminates a `GIT binary patch` block, so the rebuilt patch was rejected by `git apply --binary`. Both trailing and mid-diff binary blocks now survive the parse/rebuild round-trip byte-exact ([#8899](https://github.com/can1357/oh-my-pi/issues/8899)).
- Fixed `omp update` (and other non-launch subcommands) crashing with `error: Unknown option '--cwd'` when a leading global launch flag preceded the subcommand — e.g. a shell alias/wrapper that runs `omp --cwd <dir> update`. `resolveCliArgv` hoisted the subcommand to the front but forwarded the launch-only flag into `update`'s strict `node:util.parseArgs` parser, which rejected it. Launch-global flags before a launch-shaped command (`acp`/`launch`) are still forwarded; before any other subcommand they are now stripped as inapplicable ([#8891](https://github.com/can1357/oh-my-pi/issues/8891)).
- Fixed Claude Code marketplace plugins ignoring the `enabledPlugins` switch in `~/.claude/settings.json` and `.claude/settings(.local).json`: a plugin turned off for a project no longer loads there, and a local-scope install enabled for a project loads even when its recorded `projectPath` is a different directory
- Fixed revived subagents (warm lifecycle reviver and cold persisted reviver) rebuilding the session without initializing the extension runtime, leaving every runtime action throwing `ExtensionRuntimeNotInitializedError`. An extension with a `tool_call` handler that touched a runtime action (e.g. `appendEntry`) then tripped the fail-closed gate in `emitToolCall` and blocked every tool — including the hidden `yield` — so the revived agent could neither finish nor exit and looped until killed. Both revivers now call the shared `initializeExtensions` helper, restoring runtime actions, `onError`, and the `session_start` event ([#8824](https://github.com/can1357/oh-my-pi/issues/8824)).
- Fixed `omp commit` split-commit crashing with a misleading `No diff found for <path>` when a staged binary (or any payload) pushed `git diff --cached --binary` past the 8 MiB subprocess output cap. The capture is truncated silently, so files sorting after the binary vanished from the parsed diff; the split flow now requests a complete diff and fails fast naming the real cause instead ([#8897](https://github.com/can1357/oh-my-pi/issues/8897)).
- Fixed a mid-run compaction being misread as a phantom overflow: after a compaction rebased the in-flight context snapshot, `getContextBreakdown` used message position (`anchorIndex >= cutoffCount`) as a freshness proxy, so an in-flight provider response whose request predated the compaction out-ranked the rebased estimate and reported the pre-compaction token count (~2.6x the real one). This tripped the "Compaction freed too little context to make progress" guard and drove the frame-rescue path on a byte-identical `tokensBefore`. Assistant context snapshots now carry a monotonic compaction epoch, and a post-cutoff anchor whose epoch predates the last compaction is no longer trusted over the rebased estimate ([#8887](https://github.com/can1357/oh-my-pi/issues/8887)).
- Fixed `after_provider_response` extension handlers receiving the primary session model in `ctx.model` and `ctx.models.current()` for cross-provider side requests. `ExtensionRunner.emitAfterProviderResponse` accepted the response model but discarded it, so a handler revoking a credential on an HTTP 402 could target the wrong provider. It now threads the response model into the context, matching `emitBeforeProviderRequest` ([#8955](https://github.com/can1357/oh-my-pi/issues/8955)).
- Fixed the TinyFish web search provider ignoring the `lang:`/`language:` query directive, so every request fell back to the API's US/English geolocation. `parsed.lang` now maps onto TinyFish's `location`/`language` parameters (e.g. `lang:it-it` → `location=IT&language=it`), matching the DuckDuckGo, Perplexity, and SearXNG providers ([#8913](https://github.com/can1357/oh-my-pi/issues/8913)).
- Fixed the `/model` Roles panel silently dropping roles and model-keyed fallback chains that fell past the visible panel height: the list had no scroll window, so entries below the cutoff were unreachable with no indication anything was missing. The panel now windows around the cursor like the provider list and shows an `↑/↓ N more` hint when rows are clipped ([#8817](https://github.com/can1357/oh-my-pi/issues/8817)).
- Fixed task and eval subagents discovering newly added agent definitions while resolving their role aliases from stale startup settings. Subagent preflight now atomically reloads persisted settings before agent discovery while preserving live runtime overrides.
- Fixed images returned by tools mounted under `xd://` rendering only as file links instead of inline terminal graphics.
- Resume Cursor idle-stall turns after completed MCP/todo tool results. The watchdog already closes the Connect stream, so unmarked blocks no longer need the `exec-resolved` marker to continue.
- Fixed the Web Search Provider Order settings summary showing providers excluded from web search ([#8884](https://github.com/can1357/oh-my-pi/issues/8884)).
- Fixed subagents aborting when external thinking exposes `think` as the required prelude before their remaining tools become callable ([#8909](https://github.com/can1357/oh-my-pi/pull/8909) by [@olegpulatov](https://github.com/olegpulatov)).
- Fixed session-title generation ignoring user `/skill:<name>` invocations, so titles now see the skill name and args instead of only later assistant text.
- Fixed destructive `rm` escaping the critical-pattern approval check when anything separates the flags from the target, so `rm -rf -- /`, `rm --recursive --force /` and `rm -rf --no-preserve-root /` are now classified critical like `rm -rf /`. `--no-preserve-root` is treated as critical wherever it appears, since it is what defeats coreutils' own refusal to recurse on `/`.
- Fixed thinking-loop aborts (`AIError.Flag.ThinkingLoop`) walking `retry.fallbackChains` and switching to another model family on attempt 1, so a healthy planning turn on Grok 4.6 (SuperGrok / Cursor OAuth) no longer gets replaced by whatever the chain lists next. The loop guard now re-samples the same model with its `thinking-loop-redirect` notice, and no longer parks the model selector on a fallback cooldown. ([#8760](https://github.com/can1357/oh-my-pi/issues/8760))
- Fixed the clipboard image-paste keybind attaching Finder's generated file icon instead of the copied image on macOS. Current Finder `Cmd+C` pasteboards advertise both a `public.file-url` and a generated 1024x1024 icon bitmap, so `arboard::get_image()` succeeded with the icon and `InputController.handleImagePaste` attached it before the file-URL branch was ever reached. The handler now probes `readMacFileUrlsFromClipboard()` before the bitmap representation, so an image file URL wins over the co-advertised icon; pure bitmap pasteboards (screenshots, browser copies) and non-image file URLs still fall through to the image/text paths ([#8769](https://github.com/can1357/oh-my-pi/issues/8769)).
- Fixed the Home Manager module (`programs.omp.settings`) breaking every launch on macOS with `Failed to acquire native file lock … Permission denied (os error 13)`. The declared config is now copied into `~/.omp/agent/config.yml` as a writable file via `home.activation` instead of a read-only `/nix/store` symlink, so OMP can acquire its config lock and persist runtime changes; `home-manager switch` still reapplies the declared settings ([#8775](https://github.com/can1357/oh-my-pi/issues/8775)).
- Fixed OpenCode MCP servers 401ing when config used OpenCode's `{env:VAR}`/`{file:path}` substitution (e.g. `Bearer {env:MCP_KEY}` headers); the OpenCode loader now expands those tokens the way OpenCode does instead of only `${VAR}` ([#8778](https://github.com/can1357/oh-my-pi/issues/8778)).
- Fixed `omp update` leaking Bun's raw `fetch()` error ("pass `verbose: true` in the second argument to fetch()") when a proxy environment variable (`HTTPS_PROXY`, `ALL_PROXY`, …) uses an unsupported scheme such as SOCKS; the update check now reports an actionable message naming the offending variable and the http/https proxy requirement ([#8784](https://github.com/can1357/oh-my-pi/issues/8784)).
- Fixed worker subprocesses (memory embeddings, tiny-model titles, TTS/STT, JS eval, browser relay, LSP mux, daemon broker) running with their cwd pinned to the CLI install directory. They share the agent's foreground process group, and terminal cwd heuristics such as kitty's `new_tab_with_cwd` pick the newest process in that group, so new terminal tabs opened in `~/.bun/install/global/node_modules/@oh-my-pi/pi-coding-agent/dist` while any worker was alive. Workers now spawn with the absolute host entry and inherit the agent's cwd.
- Preserved MCP `ImageContent` tool-result blocks so vision-capable models and the TUI can inspect returned images instead of receiving only a text placeholder ([#8687](https://github.com/can1357/oh-my-pi/issues/8687)).
- Fixed a whole-file `read` of a file with a UTF-8 BOM minting a hashline tag hashed from BOM-bearing text. Because the patcher's live read strips the BOM, the next edit to that file only applied through stale-hash recovery and reported that the file had changed externally when it had not.
- Extension bare imports of workspace members now resolve inside installed git-dependency monorepo plugins (the walk recognizes `workspaces` roots; installed node_modules copies still shadow members)
- Fixed `omp completions <shell>` hanging after writing shell completion scripts to stdout by invoking `postmortem.quit(0)` upon completion. Prevents lingering event loop handles (such as background timers or sockets loaded when inspecting command metadata) from pinning the process and blocking tools like `chezmoi`.
- Fixed `omp --smoke-test` recursively deleting unrelated directories in `os.tmpdir()` (tmux/ssh sockets, editor state, build trees). The smoke broker now keeps its runtime dir under a private parent, and the dead-scope reclaim refuses any root that is not the `daemons` container and only prunes entries named like a 16-hex daemon scope key ([#8721](https://github.com/can1357/oh-my-pi/issues/8721)).
- Fixed high CPU during multi-subagent / workflowz / orchestrate sessions: each live tool block (streaming args, a running partial tool, or a `task` subagent) armed its own 80ms spinner `setInterval` driving `requestComponentRender`, so N concurrent live blocks created N unsynchronized repaint timers that kept the render scheduler awake near-continuously. The per-block timers are now consolidated into a single shared spinner ticker that repaints every live block in one coalesced frame per glyph step, independent of block count ([#8731](https://github.com/can1357/oh-my-pi/issues/8731)).
- Fixed `omp update` writing to the PATH launcher instead of the running binary on binary-only releases (major bumps or `omp.dist: "binary"`): a foreign symlink — e.g. an admin symlink into a shared install — now resolves to its real binary in every distribution channel, avoiding an `EACCES` on a root-owned link directory or a split-brain copy that shadows the shared install. Package-manager launchers keep their deliberate in-place takeover. ([#8732](https://github.com/can1357/oh-my-pi/issues/8732))
- Added `.css` to the built-in Biome server `fileTypes` so CSS files route through Biome's linter/asserter by default instead of requiring a full per-project `fileTypes` override. ([#8741](https://github.com/can1357/oh-my-pi/pull/8741))
- Fixed memory extraction sending its instructions, few-shot examples, and the user's message as a single user turn, which caused small local models to echo the examples instead of extracting facts; instructions now travel as a system turn and the raw text as the user turn
- Fixed local title generation stopping on a stop string that appeared in the prompt instead of the generated tokens
- Fixed the Subagents HUD role display and restored generated task labels by keeping spawn handles separate from UI descriptions.
- Fixed `models.yml` custom-model providers declaring `auth: oauth` being rejected by validation with "apiKey is required", which forced a dummy `apiKey` that then shadowed the broker's OAuth tokens ([#8937](https://github.com/can1357/oh-my-pi/pull/8937) by [@usr-bin-roygbiv](https://github.com/usr-bin-roygbiv)).
- Provider-qualified model selectors (e.g. `anthropic/claude-opus-5`) now fail closed when the named provider is unavailable instead of silently re-binding to OpenRouter's same-named flat id and billing the aggregator ([#8832](https://github.com/can1357/oh-my-pi/issues/8832)).
- Fixed PlanYolo plan approval dropping all MCP tools: the post-handoff tool restore now accounts for MCP discovery that completed while planning instead of restoring a pre-discovery snapshot.
- Fixed parallel `web_search` calls hanging forever past the 60s timeout when the shared headless-browser daemon or page died mid-setup; browser fallback setup and teardown are now abort-protected ([#8865](https://github.com/can1357/oh-my-pi/issues/8865)).
- Fixed extension-package `.mcp.json` `${VAR}` env placeholders (stdio env/command/args/cwd, HTTP url/headers/oauth) reaching MCP servers unexpanded.
- Advisor blocker advisories raised inside the post-interrupt immune window now wake a new turn instead of parking as asides until the next user prompt.
- The exit banner only advertises `omp --resume <id>` when the session was actually written to disk, so the printed command no longer fails for sessions that ended before persistence ([#8860](https://github.com/can1357/oh-my-pi/issues/8860)).
- Fixed terminals that deliver Shift+Enter as a bare LF (or the legacy CSI `13;2~` form) getting a plain switch instead of summarize-and-switch in the `/tree` selector ([#8821](https://github.com/can1357/oh-my-pi/issues/8821)).
- Fixed OMP panicking at startup when the host environment contains a non-UTF-8 variable value; such entries are now skipped when copying the host environment into the shell ([#8925](https://github.com/can1357/oh-my-pi/issues/8925)).
- Fixed `/mcp reauth` refusing to run the OAuth flow for HTTP MCP servers that allow unauthenticated `initialize` but require auth for `tools/call`; endpoint discovery now runs against the server URL before giving up ([#8922](https://github.com/can1357/oh-my-pi/issues/8922)).

## [17.3.7] - 2026-08-17

### Changed

- Send the `omp/<version>` User-Agent on xAI chat (`xai` and `xai-oauth`) unless the request already set its own ([#8840](https://github.com/can1357/oh-my-pi/pull/8840) by [@Jaaneek](https://github.com/Jaaneek)).

## [17.3.6] - 2026-08-17

### Added

- Added `ExtensionAPI.registerFileWriteFallback(handler)` and `ExtensionAPI.registerFileDeleteFallback(handler)`, letting an extension supply a fallback writer or deleter that is consulted when a native `write`, `edit`, or `apply_patch` byte-write or unlink is denied with a permission error (`EPERM`/`EACCES`/`EROFS`) — for hosts that embed the agent inside a sandbox that denies direct filesystem access but exposes a privileged channel. The brokered path is symlink-resolved so a handler's allowlist sees the real destination, a destination that cannot be resolved is not brokered at all, and `req.sessionId` names the session that issued the mutation so a handler sharing the process-wide registry can enforce policy per session. See [`docs/extensions.md`](../../docs/extensions.md).

### Changed

- Updated the default model for XAI_API_KEY (xai) and SuperGrok OAuth (xai-oauth) to grok-4.6. Automatic model selection continues to prefer paid xai/grok-4.6 when only XAI_API_KEY is set, with xai-oauth/grok-4.6 still available explicitly.

### Fixed

- Fixed `omp stats` and `/stats` dashboards being unreachable from container hosts by accepting an explicit `--host` bind address while preserving the `127.0.0.1` default.

## [17.3.5] - 2026-08-16

### Added

- Added Extensions tab group to settings schema

### Changed

- Routed paid xAI models (XAI_API_KEY / xai/…) through the Responses API used by SuperGrok OAuth instead of Chat Completions, including reliable replay of encrypted reasoning content on follow-up turns.
- Updated the default model for XAI_API_KEY (xai) to grok-4.5, and the default SuperGrok OAuth (xai-oauth) model to grok-4.5. Automatic model selection continues to prefer paid xai/grok-4.5 when only XAI_API_KEY is set, with xai-oauth/grok-4.5 still available explicitly.
- Stopped sending presence/frequency penalties and stop sequences to xAI reasoning models such as grok-4.5, which reject them.

### Fixed

- Fixed `hub` job and wait lists hiding stale running subagent registrations that have no turn in flight, ensuring they remain visible so operators can cancel them
- Fixed external thinking scratchpads running alongside native reasoning on xAI Grok 4 and other reasoning-only Responses models that reject `reasoning.effort`
- Fixed llama.cpp model discovery producing a baseUrl without the /v1 prefix for non-Qwen models, causing 404 errors on OpenAI-compatible endpoints.
- Fixed prompt caching on open-weight providers (DeepSeek, Qwen, GLM, …) so tool schemas stay cached across directory changes and midnight rollovers.
- Fixed omp --fork omitting the source session's artifact directory, so CLI-created forks now preserve artifact:// references like interactive /fork.
- Fixed long ask option labels being hard-truncated at the terminal width; labels now wrap onto indented continuation lines.
- Fixed toggling display.showTokenUsage from /settings leaving existing token-usage rows stale until the transcript was rebuilt.
- Fixed mid-run auto-compaction blocking the live loop while waiting on extension handlers, which could hang after a snapcompact or context-full pass.
- Reduced peak memory for persisted subagent revival probes by streaming large file-backed session journals instead of loading them fully.
- Improved responsiveness of streaming edit previews for large diffs by rendering only the visible tail.
- Fixed repeated /btw panels committing transient frames to native scrollback and replaying conversation history after dismissal.
- Clarified that closing browser tool sessions releases managed handles without closing pages in spawned, CDP-connected, or relay browsers.
- Fixed interrupted vibe_wait calls being reported as elapsed timeout windows.
- Improved checkpoint/rewind prompt rendering to stay accurate after a rewind and be more concise.
- Fixed Cursor turns dying with HTTP/2 stream errors (NGHTTP2_INTERNAL_ERROR / NGHTTP2_REFUSED_STREAM) after tool calls already had results, instead of leaving the agent idle until the user typed "continue".
- Fixed mixed-case plugin tool names being lowercased during tool-set refresh, which unmounted them from xd:// whenever MCP tools connected.
- Fixed Exa MCP servers being unmounted when their config explicitly requests tools the native Exa integration does not provide, breaking /mcp reconnect exa.
- Fixed Claude Code custom tool discovery attempting to import non-module files from .claude/tools.
- Fixed Agent Hub parking a mid-spawn child session so subsequent task calls failed with an ownership error and the row could never be revived.
- Fixed the welcome banner displaying a stale model name when the session's active model changes after startup (e.g. after a delayed config load or an explicit /model switch).
- Fixed Nix standalone binaries retaining Bun's build-time package in their runtime closure.
- Fixed birch user/custom message card contrast on dark terminals, where chat bubbles could render light-on-light.
- Fixed hidden tool snapshots preventing long streamed assistant responses from entering terminal scrollback.
- Prevented omp models from loading ambient hook factories while preserving extension-contributed providers.
- Fixed the ask dialog's multi-select mode dead-ending on Enter; Space now toggles options and Enter submits the current selection.
- Fixed workspace diagnostics reporting a clean workspace when its checker crashed without producing output.
- Fixed manual /compact failing outright when a summarization request hit a transient provider overload.
- Fixed transient Anthropic failures (overloaded_error, rate_limit_error, 429/500/502/503/529) aborting or silently degrading side-effect-free background LLM calls such as session title generation, TTS speech enhancement, commit-message generation, thinking/stop classifiers, memory extraction/consolidation, and commit analysis/summary/changelog passes; these now retry with backoff honoring retry-after instead of failing or returning an indistinguishable empty result.
- Fixed the shared headless browser daemon launching from the macOS system Google Chrome bundle, which could cause macOS to route the user's link clicks to the automation daemon and silently swallow them; the daemon now prefers an isolated Chrome for Testing binary on macOS.
- Reclaimed abandoned daemon runtime directories under ~/.omp/run/daemons/, preventing unbounded growth of leftover Chromium profiles and broker state.
- Kept the welcome screen's Tips, LSP Servers, and Recent sessions visible when a long model name still leaves enough terminal width for both columns.
- Fixed focused shimmer animation frames (ultrathink, orchestrate, workflowz) repainting the full TUI too frequently, causing high CPU usage while composing prompts on WSL2.
- Fixed the /debug report bundle including unrelated historic sessions, leaking other sessions' files and bloating archives.
- Fixed adopted keep-alive agents remaining stuck in a running state in the registry after deferred turn settlement, and prevented stale refs from sustaining bare hub wait calls indefinitely.
- Fixed home-relative marketplace catalog paths not being expanded before cache access, preventing updates from writing into a literal ~ directory.
- Fixed broker-owned headless Chromium opening and retaining an unowned blank foreground window on Windows.
- Fixed the auto thinking classifier failing every turn on Anthropic models served through LiteLLM/Vertex due to a thinking-budget mismatch.
- Fixed always-ask approval prompts bypassing edit preview readiness when a built-in tool executes under its wire-level alias, such as edit running as apply_patch.
- Fixed lsp reload crashing non-rust-analyzer language servers by sending them a rust-analyzer-specific request; that request is now gated to rust-analyzer only.
- Fixed browser open failing with "Shared browser daemon unavailable" when HTTP_PROXY/HTTPS_PROXY is set, because liveness probes were incorrectly routed through the proxy.
- Fixed defaultThinkingLevel: auto skipping classification for user-invoked /skill:<name> turns, leaving the effort stuck on pending auto.
- Fixed custom-tool directory discovery recursing into subtrees despite a non-recursive default, which could crash startup when scanning large dependency directories such as Python venvs.
- Repaired torn session JSONL appends after disk-write failures, rewrote malformed resumed files before their next append, retried transient persistence failures, and surfaced failures in the TUI.
- Prevented Anthropic model fallback from replaying model-bound thinking blocks across models, and surfaced immutable-thinking errors without retrying the unchanged invalid turn.
- Fixed empty-stop failure messages always suggesting a context problem even when the provider billed output tokens; the message now reports the billed token count and points at a provider-side filter/translation issue when appropriate.
- Fixed a parked, session-less agent-registry entry with no reviver permanently poisoning its agent id, preventing fresh subagent spawns from reusing that id.
- Made extension tool-call timeouts configurable and paused them during user dialogs.
- Fixed /vibe cancellation leaving an in-flight model turn unaware that Vibe mode and its tools were removed.
- Fixed empty local-model stops lingering on the persisted active branch after retries, preventing them from resurfacing after reload or a mid-retry process kill.
- Fixed the Biome linter client silently dropping every diagnostic due to an outdated JSON output schema; it now supports Biome 2.x's diagnostic format.
- Fixed `hub jobs` and empty `hub wait` snapshots hiding running subagents that have no live turn, which removed the only way to discover and `hub cancel` a stale registration; such agents are listed again and flagged as having no turn in flight.
- Fixed external thinking being offered on xAI reasoning-only Responses models (grok-4 family) that reject `reasoning.effort`, where the private scratchpad ran alongside native reasoning instead of replacing it.
- Fixed the extension tool-call handler timeout rendering outside a titled section in `/settings` by registering its Extensions group on the Tools tab.

## [17.3.4] - 2026-08-14

### Changed

- Replaced the MuPDF-WASM PDF document backend with `pdf-inspector` through `@oh-my-pi/pi-natives`, preserving cached text conversion and PDF line selectors while reporting pages that need OCR.
- Restored `read <pdf>:` and `read <pdf>:<image>.png` page rendering by automatically capturing PDF pages through the headless Chromium browser tool.

### Fixed

- Fixed Streamable HTTP MCP sessions being invalidated by opening the optional GET SSE stream before sending `notifications/initialized`, which prevented Figma Dev Mode MCP from connecting ([#8514](https://github.com/can1357/oh-my-pi/issues/8514)).
- Fixed the `/hotkeys` table describing Ctrl+D (`app.exit`) as "Exit (when editor is empty)" when it actually exits unconditionally and saves the current prompt as a resumable draft ([#8530](https://github.com/can1357/oh-my-pi/issues/8530)).
- Fixed Ctrl+G external editors failing to launch on Windows because Bun re-quoted the embedded `cmd.exe /c` command line ([#8544](https://github.com/can1357/oh-my-pi/issues/8544)).

## [17.3.3] - 2026-08-14

### Fixed

- Automatically continued Gemini turns that stopped after thinking without final output, using a bounded final-answer reminder instead of exhausting generic retries.
- Retried Gemini `MALFORMED_FUNCTION_CALL` failures when every emitted tool call was proven unexecuted, while preserving real tool-result and visible-output replay guards.
- Kept current terminal retry errors in one pinned banner with attempt context while surfacing local continuation failures instead of stale provider errors.

## [17.3.2] - 2026-08-13

### Fixed

- Fixed the parent TUI stalling after a subagent submits its result until terminal focus or resize wakes the event loop ([#8462](https://github.com/can1357/oh-my-pi/issues/8462)).
- Fixed `omp update` misclassifying foreign npm/bun bin aliases while preserving package-manager ownership for globally linked checkouts ([#8468](https://github.com/can1357/oh-my-pi/issues/8468)).
- Fixed `read` hashline headers collapsing nested in-workspace paths to the bare basename, which let a same-basename file at the session cwd capture a verbatim follow-up `edit` and deterministically reject it with `hash is not from this session`. Headers now retain the workspace-relative path (e.g. `[src/settings.json#0063]`) ([#8482](https://github.com/can1357/oh-my-pi/issues/8482)).

## [17.3.1] - 2026-08-13

### Fixed

- Fixed Claude Code user discovery ignoring CLAUDE_CONFIG_DIR for configuration, plugins, MCP servers, and imported sessions.
- Fixed the status-line git branch display freezing after switching branches.
- Fixed Pi extension contexts omitting the runtime mode, which caused TUI guards to silently disable extension UI.
- Fixed extension-registered tool names being rejected by the --tools flag before extension discovery, which prevented least-privilege sessions from allowlisting plugin tools.
- Fixed omp plugin install failing with cloning errors for legacy Pi extensions whose tool schemas use legacy-typebox builders.
- Fixed omp update aborting with chmod ENOENT when concurrent update runs overlapped by using unique download temporary paths.
- Fixed the browser tool executable probe launching the user's installed GUI Chromium on Windows: the `--version` version probe from ecb22957 was Linux-scoped but ran for every platform candidate, so on Windows it could hand off to a running `chrome.exe`, open a normal browser window, then reject the candidate and fall back to cached Chrome for Testing. The probe is now confined to Linux ([#8445](https://github.com/can1357/oh-my-pi/issues/8445)).

## [17.3.0] - 2026-08-13

### Breaking Changes

- Removed the global `advisor.subagents` setting. Subagent advisors are now configured per agent via frontmatter or `task.agentAdvisor`. Existing configurations of `advisor.subagents: true` will automatically migrate to `task.agentAdvisor: { task: "on" }`.

### Added

- Added Astral `ty` as a built-in fallback Python LSP server (`ty server`), ordered behind `pyright`, `basedpyright`, and `pylsp`.
- Added first-party Nix support, including reproducible source builds for Linux and macOS, a pinned development shell, NixOS and Home Manager modules, and offline Bun dependency support.
- Added support for per-agent advisors configured via the `advisor` frontmatter field or the `task.agentAdvisor` settings, allowing different agents to be advised by different models.
- Redesigned the `/agents` interface as a fullscreen hub featuring a scope sidebar, type-to-filter search, a pinned detail pane, mouse support, and interactive property chips for configuring agent settings.
- Prepared for the upcoming npm package rename by updating `omp update` and startup version checks to follow the `omp.rename` pointer in the published manifest.

### Changed

- Updated `/usage`, `omp usage`, and the status line to display authoritative OpenCode Go quota usage directly from the official endpoint, replacing estimated costs with actual usage across three time windows (5h, 7d, and monthly).
- Documented the source-available local protocol relay and clarified that production collaboration relay binaries are not currently published.
- Enabled bounded Anthropic prompt-cache refreshes for the main agent loop while isolating advisor and side-channel requests from the shared refresh timer.

### Fixed

- Fixed multiple Language Server Protocol (LSP) issues, including concurrent sessions sharing backend overlays, stale document overlays after workspace edits, incorrect transactional edit advertisements, unhandled snippet placeholders in rust-analyzer, and failing to restore overwritten targets during failed file renames.
- Fixed LSP `diagnostics` incorrectly reporting success when all language servers failed.
- Fixed Hindsight memory scoping splitting repositories across multiple scopes on case-sensitive filesystems by lowercasing the project label.
- Fixed the CLI crashing at startup with a raw `AuthBrokerError` when the configured auth broker is unreachable, replacing it with an actionable error message.
- Fixed various resource and process leaks, including idle launch brokers staying alive indefinitely, stale MCP connections leaving child processes open, and undrained stdout in DAP `runInTerminal` requests.
- Fixed custom STB-backed vision providers failing to decode WebP images by automatically detecting image formats from bytes and normalizing WebP blocks.
- Fixed command-backed provider API keys (`!command`) staying pinned to cached values after receiving an HTTP 401 error.
- Fixed the `/agents` Control Center failing to open when model overrides are configured as YAML arrays.
- Fixed session-title generation regressions by restoring plain-sentence phrasing and name-fidelity instructions.
- Fixed agent-facing prompts and system instructions mentioning tools that are absent from the current session catalog.
- Fixed manual `/shake` discarding all tool results; it now retains a small recent tail of results to preserve active working context.
- Fixed `omp install` failing validation for extensions importing legacy `is<Tool>ToolResult` event guards.
- Fixed profile aliases generated by standalone binaries invoking Bun's embedded virtual script instead of the installed `omp` command.
- Fixed `/skill:<name>` tokens in `/plan` or `/vibe` inline prompts being treated as literal text instead of executing the skill.
- Fixed long streaming `write` previews stalling the TUI by optimizing file scanning and splitting.
- Fixed the Windows console disappearing when running commands like `/stats`.
- Fixed retry-fallback selection switching to a fallback model with a context window too small to hold the current session context.
- Fixed OpenCode discovery ignoring `opencode.jsonc` files and rejecting comments in `opencode.json`.
- Fixed WSL2 startup hanging forever when the Windows interop pipe is wedged: the WSL host-home discovery probes (`cmd.exe`, `wslpath`) now run under a 500ms hard timeout and fall back to the Linux `$HOME`/`~/.omp` candidates ([#8402](https://github.com/can1357/oh-my-pi/issues/8402)).

## [17.2.15] - 2026-08-12

### Added

- Added `--external-thinking` CLI flag to force external thinking tool activation.
- Added `omp compress` command, which uses an isolated, two-tool agent loop to rewrite single or multiple text files (supporting glob patterns and concurrent processing) into dense prompt registers.
- Expanded tool discovery in `omp cleanse` to support `staticcheck` and `golangci-lint` (Go); `mypy`, `pylint`, `flake8`, `ty`, and `basedpyright` (Python); `oxlint`, `deno lint`, `stylelint`, and `vue-tsc` (JS/TS); and `actionlint` (GitHub Workflows).
- Added support for natural language requests in `omp cleanse "<request>"`, which launches a discovery subagent to automatically inspect the project, determine the correct commands, and map outputs.
- Added an interactive picker to `omp cleanse` when run without arguments on a TTY, allowing users to run all checkers, select a specific checker, or describe what to fix.

### Changed

- Restricted the `think` tool to GPT, Claude, and Gemini transports that support native reasoning replacement.
- Increased the default subagent cap for `omp cleanse` from 8 to 32.

### Fixed

- Fixed a hang in headless `omp -p` runs when `plan.defaultOnStartup: true` is enabled by disabling the startup default in print mode.
- Fixed `display.hideToolActivity` failing to hide certain activity blocks, such as reminders, diagnostics, and completions.
- Fixed several issues in the MCP Streamable HTTP transport, including updating the negotiated protocol version to `2025-11-25`, resolving connection drops and SSE resumption gaps, and preventing double-execution of tools during auth refreshes.
- Fixed `/handoff` losing local artifacts (plans, scratch files, research notes) by copying them across the handoff session boundary.
- Replaced libarchive-based tar parsing with a hardened, in-process tar reader to prevent crashes and safely handle complex archive structures, symlinks, and sparse metadata.
- Fixed `Ctrl+O` tool-output expansion failing to reach launch-completion messages wrapped in the hidden tool activity container.

## [17.2.14] - 2026-08-11

### Added

- Added `externalThinking` setting for private scratchpad reasoning via the new `think` tool

## [17.2.13] - 2026-08-11

### Added

- Added `searxng.safesearch` setting option for SearXNG searches
- `omp update` now honors an `omp.dist` distribution field published in the release's npm manifest and treats major-version bumps without one as binary-only: bun/npm-managed installs are migrated to the standalone GitHub release binary in place instead of running a package-manager install that a non-npm release (e.g. a runtime change) would break. Windows script-shim installs (npm's `omp.cmd`/`omp.ps1`) are taken over seamlessly by installing `omp.exe` beside the shims and retiring them.
- Added support for Cloudflare AI Gateway routing for Gemini search
- Added support for Exa MCP search provider
- Added domain inclusion/exclusion filtering and URL deduplication for TinyFish search
- Fixed `/vibe` mode losing the pre-vibe toolset when a session already in vibe mode switches into another session that is also in vibe mode, which left `bash`, `edit`, `write`, `grep`, `glob`, `task`, and `hub` silently unavailable after exiting the mode; the pre-vibe toolset is now recorded on the `mode_change` entry and restored from there.
- Preserved extension-filtered pasted image payloads and source links when `/goal`, `/plan`, or `/vibe` submits the composer draft.
- Fixed Agent Hub lineage registration timestamps displaying in UTC instead of the user's local timezone.
- Fixed Python/Julia/Ruby eval kernels failing to start after their staged runner script was cleared mid-session (e.g. a macOS tmpdir sweep): the memoized runner path is now re-validated so a long-lived process self-heals instead of only recovering on restart ([#8140](https://github.com/can1357/oh-my-pi/issues/8140)).
- Fixed session resume fully reading and parsing the journal twice by reusing the entries already loaded by `SessionManager.open()` ([#8117](https://github.com/can1357/oh-my-pi/issues/8117)).
- Fixed RPC `message_end` frames being serialized more than once before output while preserving v1 and v2 wire bytes ([#8118](https://github.com/can1357/oh-my-pi/issues/8118)).
- Fixed message conversion caching strongly retaining the last session transcript and converted output after session disposal ([#8119](https://github.com/can1357/oh-my-pi/issues/8119)).
- Fixed timed-out LSP requests continuing to consume server CPU and block queued requests by sending `$/cancelRequest` ([#8116](https://github.com/can1357/oh-my-pi/issues/8116)).
- Fixed `shutdownAll()` leaving the configured LSP idle checker alive and preventing short-lived SDK hosts from exiting ([#8115](https://github.com/can1357/oh-my-pi/issues/8115)).
- Fixed terminal Mermaid borders and junctions using low-contrast UI chrome colors instead of the active theme's readable content color.
- Fixed Cursor provider sessions flooding bash/grep validation errors (`cwd`/`case`/`skip` "was undefined") when Cursor omitted optional exec-frame fields; the exec bridge now omits unset optional kwargs before tool execution and transcript synthesis.
- Added structured reset-reason logging to advisor context re-primes (issue #7226): every history-rewrite trigger (compact, auto-compaction, compaction-rescue, shake, drop-images, prune-tool-outputs, prune-stale-tool-results, conversation-boundary, context-maintenance) now emits an `advisor context reset` debug event with its reason, so full-transcript replays can be attributed to a concrete path.
- Added `quarantine-recovery` and `quarantine-retry-exhausted` reset reasons to advisor context-reset debug logs, so advisor full re-primes after quarantined output remain attributable without changing quarantine retry semantics (issue #7226).

### Changed

- Standardized first-party outbound User-Agent headers on `omp/<version>` via the shared `USER_AGENT` utility.

### Fixed

- Fixed `/usage`, `/advisor status`, and every other panel command answering only after the agent stopped working. Since `17.0.1` their output was queued until the turn settled (to stop mid-turn transcript mounts duplicating rows in native scrollback, issues #4806/#6767), and the deferral was silent, so on a long turn the command was indistinguishable from a dead one. The panel now renders immediately above the editor in an anchored container that is cleared and rebuilt in place, never entering the transcript, and the full output still lands in the transcript at the next settle. The preview is capped to 40% of the viewport (minimum 6 rows) so a tall report cannot push the prompt off screen.
- Fixed the todo panel showing no progress while the agent worked through a plan: every sub-todo read as unchecked no matter how far along the run was. Three causes, all in the collapsed (default) view — the walking viewport dropped *every* closed row, so a completion only ever removed a line and the card's strike-reveal animation ran against a row nobody rendered; the phase the agent was actually in was the one phase header rendered without a `done/total` count; and the 60s todo auto-clear deleted closed tasks from an unfinished plan, resetting the phase counter to `0/n` and renumbering the stages until the next `todo` call restored the real snapshot. The viewport now keeps the newest closed task as a checked lead row (additive to the open-task cap), every phase header carries its progress, counts include abandoned tasks, and auto-clear only fires once the whole list is settled.
- Status-line `usage` now renders monthly Cursor quotas (`mo N%`) in addition to the existing `5h` / `7d` windows ([#7998](https://github.com/can1357/oh-my-pi/pull/7998) by [@dnth](https://github.com/dnth)).
- Restored the `ctx.ui.custom()` overlay API that regressed after v0.45.6: `overlayOptions` (anchor/width/maxHeight/margin positioning and sizing) is now forwarded to `showOverlay` instead of a hardcoded full-cover geometry, `onHandle` receives the resulting `OverlayHandle`, and `OverlayHandle`/`OverlayOptions` are exported from the extension API types again.
- Fixed a content refusal that arrives after the model already emitted a tool call ending the turn outright instead of consulting the model fallback chain. When the refused turn produced nothing visible and every emitted tool call provably never executed (each paired with a synthetic `executed: false` result), the turn is now retryable and the configured `retry.fallbackChains` entry gets its chance, matching how a refusal with no tool calls already behaves.
- Fixed proxy discovery preferring the bundled catalog name over the proxy-reported name, so `omp models refresh` now updates stale display names (e.g. a proxy serving `longcat-2.0` as `"LongCat"` no longer shows the raw id).
- Fixed the compiled binary build on Windows: `Bun.Glob.scan` yields backslash-separated paths, which the legacy Pi virtual module used verbatim for export keys and generated identifiers, producing invalid JavaScript.
- Fixed Ctrl+O (`app.tools.expand`) not expanding truncated tool output while a tool-approval prompt or other selection dialog held keyboard focus, by promoting the shortcut to a global input listener that fires regardless of focus (it still defers to fullscreen overlays and the tree selector's own Ctrl+O filter cycle) ([#7837](https://github.com/can1357/oh-my-pi/issues/7837)).
- Fixed `omp commit` printing a wall of bundled source when a `pre-commit`/`commit-msg` hook refuses a commit: hook failures are now reported with the hook's own message, split plans report how far they got, and the command exits non-zero cleanly ([#7834](https://github.com/can1357/oh-my-pi/issues/7834)).
- Fixed `omp commit --push` exiting 0 without pushing when the working tree is already clean; it now pushes the existing commits (or fails non-zero if the push is refused) ([#7834](https://github.com/can1357/oh-my-pi/issues/7834)).
- Subagents spawned through a model-role alias now inherit that role's `retry.fallbackChains` entry instead of the `default` chain. Both spawn paths (`task` and vibe workers) expand the alias — the bundled `task` agent's `@task`, `sonic`/`scout`'s `@smol` — before it reaches the executor, so the role identity was lost and every child was pinned to the `default` chain, routing retries onto models the operator had deliberately kept out of the role's chain. Completes [#7694](https://github.com/can1357/oh-my-pi/pull/7694), which only covered agents whose unexpanded alias reached the executor ([#7910](https://github.com/can1357/oh-my-pi/pull/7910) by [@enieuwy](https://github.com/enieuwy)).
- Fixed standalone `AGENTS.md` discovery stopping at nested Git repository roots, so enclosing workspace instructions are loaded while home-level instructions remain scoped correctly.
- Split the advisor Session update delivery into per-source-message user messages (single `Agent.prompt(AgentMessage[])` call) so provider prompt caches grow with the session instead of staying pinned at the instructions/tools boundary; rendering stays byte-identical to the old single-block update.
- Restore the advisor primary-context dedup map when a failed advisor turn is rolled back, so retried batches re-deliver first-time plan/goal context in full instead of collapsing it to "(unchanged — still in effect)".
- Include all renderer-read fields (excludeFromContext, bashExecution command, pythonExecution code, branch/compaction summary + fromId, fileMention files) in advisor prefix fingerprints so clones changing only those fields correctly trigger a re-render.
- Fixed Gemini advisors treating a valid silent review as an empty-response failure, repeatedly retrying the turn and eventually dropping the advisor backlog. ([#8223](https://github.com/can1357/oh-my-pi/issues/8223))
- Fixed bash-tool commands receiving an unguarded `CI=1`, which broke clap-based CLIs (e.g. `tauri android build`) that parse `CI` as a strict boolean, and ignored the documented `PI_BASH_NO_CI` opt-out. The per-command env now injects clap-compatible `CI=true` and honors `PI_BASH_NO_CI`/`CLAUDE_BASH_NO_CI` ([#8229](https://github.com/can1357/oh-my-pi/issues/8229)).
- Fixed macOS key hints rendering the Linux/Windows modifier names `Alt` and `Super` across every hint surface (`/hotkeys`, status bar, autocomplete, pending-message bar, copy selector, ask dialog): `alt` now renders as `Option` and `super` as `Cmd` on darwin, and the static `/hotkeys` navigation rows are platform-aware instead of hardcoding macOS `Option`/`Cmd` names on every platform ([#8235](https://github.com/can1357/oh-my-pi/issues/8235)).
- Fixed `omp plugin uninstall <plugin> --dry-run` actually removing the plugin on both the npm and marketplace routes; dry-run now reports what would be removed and leaves installed plugin state unchanged ([#8178](https://github.com/can1357/oh-my-pi/issues/8178)).
- Fixed handled OMP shutdown persisting running subagents as terminally aborted instead of restoring their transcripts as parked and revivable. ([#8216](https://github.com/can1357/oh-my-pi/issues/8216))
- Fixed `always-ask` approval prompts opening before large edit previews finish rendering, preventing blind approvals ([#7957](https://github.com/can1357/oh-my-pi/issues/7957)).
- Fixed Pi-compatible extensions registering tools during asynchronous session startup being omitted from the live model tool registry.

### Removed

- Removed the `resolveAgentModelSource` model-resolver export, whose only use was being fed to `resolveExplicitModelRole`. Replaced by `resolveAgentModelSelection`, which returns the expanded `patterns` and the pre-expansion `role` together so a spawn path cannot derive one without the other ([#7910](https://github.com/can1357/oh-my-pi/pull/7910) by [@enieuwy](https://github.com/enieuwy)).
- A run is now attributed to the model that actually produced its output, not whichever model the session was last pointed at. A retry fallback that errored on its first request — an exhausted quota, a hard provider error — was credited with the whole run in the Agent Hub row and the settled task result, even when the previous model did every turn. Sessions expose the serving model directly, holding the last model that produced output while a candidate is armed but unproven, and transcript-derived history stops at the newest turn that produced output.

## [17.2.12] - 2026-08-08

### Fixed

- Fixed shell minimization replacing meaningful `rustc --print` output with `OK`.
- Fixed shell minimization altering outputs shorter than 1,000 characters; these now pass through unchanged.
- Fixed primary and advisor Codex sessions falling back to another provider before trying sibling accounts when an account lacks Trusted Access for Cyber approval.
- Fixed task subagent assistant turns being omitted from the per-model TPS/TTFT aggregates shown by `/models`. ([#8022](https://github.com/can1357/oh-my-pi/issues/8022))
- Fixed terminal-title spinner writes consuming CPU during WSL/ConPTY agent waits by using the same static working separator as native Windows ([#8012](https://github.com/can1357/oh-my-pi/issues/8012)).
- Fixed long-running sessions leaking memory for every completed keep-alive `task`/scout subagent: a disposed (parked) subagent's `AgentSession` stayed pinned through the lifecycle adoption record's reviver closure, and `dispose()` never released the message array, append-only provider transcript, session-manager entries, or the raw-SSE debug buffer, so heavy transcripts and captured provider wire frames accumulated for the process lifetime ([#8003](https://github.com/can1357/oh-my-pi/issues/8003)).
- Fixed Z.AI web search dropping sources and exposing raw JSON when MCP responses double-encode content text ([#8000](https://github.com/can1357/oh-my-pi/issues/8000)).
- Fixed `/handoff` masking empty/whitespace-only generation and harness-initiated aborts as "Handoff cancelled"; manual empty generation now surfaces a logged failure, harness aborts preserve their reason (or report "Handoff aborted by session"), and auto-handoff still falls back to context-full compaction ([#7993](https://github.com/can1357/oh-my-pi/issues/7993)).

## [17.2.11] - 2026-08-07

### Added

- Added support for the Agent Plugins 1.0.0 standard, enabling automatic discovery, validation, and secure execution of compliant plugin packages.
- Added the `omp share <session>` command to share saved sessions by ID prefix or file path without launching the agent.
- Added the `AGENT=1` environment variable to child processes spawned by `coding-agent` to allow downstream tools to detect agent-driven execution.

### Changed

- Consolidated Exa web-search configuration under `exa.enabled`, automatically migrating legacy `exa.enableSearch` values and removing obsolete Researcher and Websets settings.
- Removed stale `computer.backend` values during configuration migration.
- Updated documentation and error messages for the JavaScript/TypeScript debug adapter (`js-debug-adapter`) to clarify supported installation paths (Mason, standalone tarball, or `JS_DEBUG_DAP_SERVER`).

### Fixed

- Fixed an issue where `/reload-plugins` and the Agent Control Center failed to propagate updated agent definitions to existing tools without a restart.
- Fixed legacy Pi extensions failing to load when calling `pi.unregisterProvider()`, ensuring provider replacements take effect immediately.
- Fixed zero-width daemon readiness and wait regex matches being rejected by the hub wire decoder.
- Fixed proxy model discovery preferring bundled catalog names over proxy-reported names, allowing `omp models refresh` to correctly update display names.
- Fixed Windows compiled binary builds failing due to backslash-separated paths in `Bun.Glob.scan` producing invalid JavaScript in virtual modules.
- Fixed the Ctrl+O (`app.tools.expand`) shortcut not expanding truncated tool output when a tool-approval prompt or selection dialog had keyboard focus.
- Improved `omp commit` error reporting when pre-commit or commit-msg hooks fail, displaying the hook's own message and exiting non-zero cleanly instead of printing bundled source code.
- Fixed `omp commit --push` exiting with code 0 without pushing when the working tree is already clean; it now correctly pushes existing commits.
- Fixed `omp commit` exiting with code 0 when the commit agent failed and fell back to a mechanical commit; it now exits non-zero to indicate the fallback was used.
- Fixed strict output schemas being rejected when native JSON Schema definition maps contain `ref` or applicator branches use `properties` without `type`.
- Fixed shell syntax extraction in `cd <path> && ...` commands to prevent redirects, extra arguments, or shell expansions from being incorrectly absorbed into the structured working directory path.
- Applied reason-specific backoff to transient rate-limit retries and consolidated exhausted retry errors.
- Fixed session-tree rows rendering as empty bullets for bookkeeping entries (such as title changes, credential pins, and mode changes); these are now hidden by default and properly labeled in `all` mode.
- Fixed extension and custom tools inheriting same-named built-in TUI renderers, which could overwrite successful results with incorrect status text.
- Fixed prewalk lifecycle handling to prevent plan injection on rejected same-model/same-effort arms, ensure consumed plan nudges do not return after context rebuilds, and prevent settings-enabled prewalk from implicitly re-arming restored sessions.
- Fixed the todo completion reminder interrupting pauses when waiting for non-English questions (such as Chinese, Japanese, Korean, or Spanish prompts ending in `？` or `?`).
- Normalized resolved file paths in read summaries, PDF image handles, and notebook errors to prevent agents from learning malformed paths.
- Fixed a bug where a per-turn `before_agent_start` system prompt override was silently dropped during base-prompt rebuilds.
- Fixed ACP `session/load` and `session/resume` failing with `ACP session not found` for sessions created under the legacy hashed project-directory scheme by falling back to a global ID scan.
- Fixed `vault://<name>?op=...` commands targeting the active vault instead of the named vault in Obsidian CLI queries.
- Fixed the status-line `session_name` segment to honor the `statusLine.sessionAccent` setting, falling back to the theme's accent color when disabled.
- Fixed automatic `agent.continue()` paths failing to run context-fit maintenance when reverting to a smaller-context model after a cooldown expiry.
- Fixed `/handoff` reporting "Handoff cancelled" for actual generation or stream timeout errors, ensuring the real error is surfaced.

## [17.2.10] - 2026-08-06

### Breaking Changes

- Replaced the re-exported `zod` API with an `omptype`-backed compatibility facade (`@oh-my-pi/omptype/zod`). Plugins retain the standard Zod-style builder interface, but real Zod-specific APIs are no longer available.

### Added

- Added a `--trusted-extension <absolute-path>` CLI flag to load an exact extension-module allowlist, bypassing ambient extension discovery.
- Added resumable session details to fatal crash outputs, including a suggested `omp --resume <session-id>` command to quickly resume persisted live agent sessions.

### Changed

- Reworked the Ctrl+S Agent Hub into a responsive fullscreen roster and selected-agent inspector, featuring aggregate status/usage metrics, detailed per-agent views (task, model, activity, usage, lineage), roster and spawn-tree views, stable ordering, asynchronous persisted-session discovery, restored historical metadata, and improved keyboard and mouse navigation.
- Replaced `arktype` with `@oh-my-pi/omptype` for all tool parameter and configuration schemas, resulting in significantly faster startup times. Configuration schema errors are now reported via `OmpErrors` entries using the standard `path`/`problem` format.

### Fixed

- Fixed panel commands (such as `/usage` and `/advisor status`) appearing unresponsive during active turns by flushing the deferred-panel queue at every settle, terminal or not. The deferral itself stays silent: mounting a status line into the transcript mid-turn re-renders rows below the live block and duplicates them in native scrollback (issues #4806/#6767).
- Fixed the bundled `ts-no-tiny-functions` rule failing to match one-line arrow functions in files with trailing newlines.
- Fixed advisor refusals skipping the model fallback chain, and bounded refusal recovery to a single attempt per model to prevent infinite fallback loops.
- Fixed repeated `/mcp reauth` commands getting stuck by ensuring new reauthorization requests cancel and clean up any pending MCP OAuth login flows.
- Fixed WSL host-home resolution to build `/mnt/<drive>/...` fallback paths using POSIX semantics regardless of the host platform.
- Fixed Python evaluation shell helpers (`!cmd`, `%%bash`, `%pip`) letting child processes inherit the runner's stdin, which previously caused deadlocks on Windows. Additionally, `%%bash` now correctly resolves Git Bash on Windows.
- Fixed subagents spawned via model-role aliases incorrectly falling back to the `default` role's retry chain instead of their own configured role chain.
- Fixed Linux/X11 clipboard reads failing when `xclip` is missing but `xsel` is available.
- Hardened Linux Chromium executable detection to filter out non-executable files, invalid wrappers, and candidates that hang during version probes.
- Fixed Bash command preview crashes caused by malformed tool arguments containing non-string environment values.
- Fixed UI rendering in the model browser and model hub where `nerd`-preset role chips would overlap and obscure the first character of labels.
- Fixed Codex web search sending incompatible request shapes to certain models, which caused the hosted `web_search` tool to ignore them.
- Fixed resumed or rebuilt sessions incorrectly applying stale rewind reports from previous checkpoint cycles to new checkpoints.
- Fixed the `read` tool incorrectly parsing semicolon-delimited internal URLs (such as batched `skill://` resources) as a single invalid resource.
- Fixed `pi.getAllTools()` returning bare strings instead of `ToolInfo[]` objects, restoring compatibility with extensions built against the upstream contract.
- Fixed legacy extensions failing to load in compiled binaries when resolving bundled dependencies via dynamic `createRequire` factories.
- Fixed Wayland window activation and native input handling by correctly reporting them as unavailable rather than attempting unsupported foreground-delivery paths.
- Fixed live execution progress being hidden in the conversation view after approving a plan in the fullscreen Plan Review.
- Fixed `omp -r` failing to discover sessions created under the temporary hashed project-directory scheme by adding a one-way migration back to legacy path-based names.
- Prevented the `read` tool from advertising or resolving `memory://` URIs when the memory backend is disabled.
- Fixed the Shift-Tab thinking mode UI rendering the `off` state as a blank label, which made it appear that reasoning could not be disabled.
- Fixed parsing of POSIX `$EDITOR` commands that contain quoted arguments or executable paths with spaces.
- Fixed persisted Agent Hub rows losing the explicit caller model role when a subagent used a model override, preserving role provenance across restarts.
- Fixed unobserved promise rejections in browser helpers (such as `tab.waitForResponse()`) causing tab workers to hang or crash.

## [17.2.9] - 2026-08-05

### Breaking Changes

- Renamed `compareVersions` to `compareChangelogEntries` in `@oh-my-pi/pi-coding-agent/utils/changelog`. The function signature and behavior are unchanged; update imports to use the new name.

### Added

- Added automatic detection of common Ungoogled Chromium Linux installations for the browser tool.

### Changed

- Restored the legacy project-scoped session directory naming scheme and removed its automatic migration ([#7646](https://github.com/can1357/oh-my-pi/issues/7646)).
- Routed Bun install-cache pruning in `update-cli` through the shared `compareVersions` utility (`@oh-my-pi/pi-utils`), removing a duplicate local comparator that rounded large numeric version identifiers via `Number`.

### Fixed

- Retried concurrent-request caps with a short backoff without deleting valid Copilot credentials or rotating through sibling accounts.
- Fixed the default `textVerbosity` setting being forwarded to OpenAI Codex requests unless the user explicitly configures it, preserving Codex's native response-control defaults. ([#4949](https://github.com/can1357/oh-my-pi/issues/4949))
- Reduced streaming CPU usage by coalescing the cumulative `message_update` deltas of a turn at the event-controller dispatch boundary: at most one streaming-state rebuild runs per ~33ms window instead of one per token, cutting the per-token handler work that dominated the CPU profile of streaming sessions (especially at high token rates) while preserving per-delta speech output. Subscriber dispatch is serialized so a rapid stream tail (`message_update` → `message_end` → `agent_end`) cannot overtake the coalesced flush. ([#7443](https://github.com/can1357/oh-my-pi/issues/7443))
- Fixed translated MCP importers (Claude Code, Cursor, Gemini CLI, Windsurf, VS Code) silently dropping a server's `enabled: false` flag, so a server disabled at the source config stayed mounted; the flag is now propagated and honored like Codex, OpenCode, and native `mcp.json`. These importers now also load project entries before same-named user entries (matching native/Codex) so a project `enabled: false` suppresses a same-named user server ([#7652](https://github.com/can1357/oh-my-pi/issues/7652)).
- Removed the per-call `model` override from the eval `agent()` helper (all runtimes), completing the earlier task-tool removal (`9f8aa87dbf`). Subagents always use their selected agent's frontmatter model and settings; a legacy `model` argument is silently ignored, so an explicit `model: "default"` can no longer route children onto the parent session model ([#6438](https://github.com/can1357/oh-my-pi/issues/6438)).
- Fixed legacy Pi extension validation rejecting plugins such as `remote-pi` that import the package-root `convertToPng` image helper. ([#7610](https://github.com/can1357/oh-my-pi/issues/7610))
- Fixed the legacy session-directory migration silently deleting a live session's transcript when its filename collided with an existing entry in the destination: colliding entries are now preserved in place, the legacy directory is only removed when empty, and collisions/migration failures are logged ([#7593](https://github.com/can1357/oh-my-pi/issues/7593)).
- Fixed `PUPPETEER_EXECUTABLE_PATH` being ignored when a system Chrome installation was detected, preventing Windows users from selecting a compatible headless browser for the shared browser daemon ([#7601](https://github.com/can1357/oh-my-pi/issues/7601)).
- Fixed `openai-models-list` discovery ignoring server-advertised input modalities, so custom virtual tier IDs absent from the bundled catalog showed `images: no` even when the `/v1/models` response reported `input: ["text","image"]` ([#7583](https://github.com/can1357/oh-my-pi/issues/7583)).
- Exposed exact source line counts in read results when selector-based reads reach EOF, allowing protocol bridges to distinguish a returned slice from the complete file ([#7590](https://github.com/can1357/oh-my-pi/issues/7590)).
- Fixed `grep`/`glob` silently collapsing a semicolon-delimited `path` list to one literal path when the joined string was too long for the OS to name (`ENAMETOOLONG`) — a list of bare filenames past `NAME_MAX` or absolute paths past `PATH_MAX` failed with `Path not found: <whole list>` even though every entry existed. The multipath probe now treats `ENAMETOOLONG` as a definitively non-existent single path so the split proceeds, and `glob` surfaces a clean `Path not found` instead of leaking the raw errno ([#7597](https://github.com/can1357/oh-my-pi/issues/7597)).
- Fixed `--mode json` (and text) print mode truncating a large final record (e.g. a multi-MB `agent_end`) when the process exited before stdout drained, while still exiting 0. Per-event writes are now serialized on their own completion callbacks and shutdown blocks on the last one, so the terminal record is delivered in full ([#7635](https://github.com/can1357/oh-my-pi/issues/7635)).
- Fixed text print mode treating buffered partial responses as replay-unsafe, allowing transient mid-stream connection failures to retry without exposing duplicated output ([#7625](https://github.com/can1357/oh-my-pi/issues/7625)).
- Fixed Hindsight `autoRecall` intermittently not reaching the model: two recall paths shared the `hasRecalledForFirstTurn` flag, and the `agent_start` event path could consume it first and inject only via an unawaited background prompt rebuild that a fast turn outran. `beforeAgentStartPrompt` (awaited before the turn builds) is now the sole injection path ([#7568](https://github.com/can1357/oh-my-pi/issues/7568)).
- Fixed `read memory://<id>` returning a confusing "Unknown memory namespace" error under `memory.backend=hindsight` (Hindsight stores memories server-side and has no `memory://` addressing); the handler now returns a corrective pointer to `recall`/`reflect` so a stray read — steered by the shared `recall` tool description — self-corrects in one turn ([#7587](https://github.com/can1357/oh-my-pi/issues/7587)).
- Fixed extension/custom/hook tool wrappers stripping schema methods off `parameters`: `applyToolProxy` bound every callable property, and binding a schema (a plain function carrying `toJsonSchema`/`assert`) dropped those properties, breaking wire-schema detection and crashing the status-line token estimator with `JSON.stringify(schema) === undefined`. Prototype methods are still bound; own data properties and schema callables now pass through untouched.
- Fixed bug where `agent()` calls in eval cells ignored turn cancellation and continued running indefinitely
- Fixed the built-in `tail` printing `tail: Broken pipe` and failing when a downstream pipeline reader exited early (e.g. `tail -c N file.jsonl | jq …` with jq aborting on a parse error); it now exits silently with 141 (128+SIGPIPE) like a real tail, in every output path including `--follow`.
- Fixed the in-process ps shell builtin rejecting common procps/BSD format specifiers (`ps -o tpgid,...` failed with `unknown output format specifier`); added `tpgid`, `pri`, `flags`, real/effective user and group columns, `wchan`, fault counters, `sz`, and the STAT `+` foreground flag.
- Fixed Herdr rejecting the macOS development launcher because its foreground process was reported as `bun` instead of `omp`.
- Completed usage-aware model fallback across startup, queued turns, same-turn tool continuations, ACP/TUI confirmation cancellation, eligible account reselection, cooldown restoration, and isolated subagent settings so low-usage handoffs remain lossless and cannot consume cancelled queued work.
- Fixed Agent Hub opening and selection becoming O(all rows) on large rosters: row rendering is now lazy around the selected viewport, and observer lookup is O(1) by id instead of copy-sorting every session per row.
- Fixed the bash interceptor blocking `grep`/`cat`/`find` used as a downstream pipeline stage (e.g. `printf 'x\n' | grep x`); a stage consuming piped stdin cannot be replaced by a path-based dedicated tool, so it is no longer matched, while standalone and first-stage searches stay intercepted ([#7496](https://github.com/can1357/oh-my-pi/issues/7496)).
- Fixed floating rejections from cmux browser guest JavaScript terminating the main process and every active session; attributable rejections now fail the browser run as tool errors while unrelated process rejections retain the fatal path ([#7365](https://github.com/can1357/oh-my-pi/issues/7365)).
- Fixed the Windows bash tool silently taking down the whole omp process when a command blocked until its timeout: cancelling a timed-out run walked the spawned child's descendant tree from raw `th32ParentProcessID` links, and a recycled pid matching the harness's stale recorded parent pid could enumerate omp as a false descendant and `TerminateProcess` it, killing the session with no `session_exit` record. Run-cancellation sweeps now refuse to signal the harness or any process collected beneath it, while still reaping the timed-out target when it owns a recycled ancestor pid ([#7452](https://github.com/can1357/oh-my-pi/issues/7452)).
- Fixed the unexpected-stop guard (`features.unexpectedStopDetection`) never firing for thinking-only stops: `isUnexpectedStopCandidate` only counted non-whitespace `text` blocks, so a `stopReason: "stop"` turn whose sole content was a signed `thinking` block (a trapped response or a truncated reasoning fragment from reasoning models) bypassed classification and silently ended the turn mid-task. Such stops are now candidates and are classified on their thinking text ([#7499](https://github.com/can1357/oh-my-pi/issues/7499)).
- Fixed Task cancellation hanging forever when a child ignored abort or stalled during cleanup ([#7483](https://github.com/can1357/oh-my-pi/issues/7483)).
- Fixed LSP diagnostics being dropped when servers normalize file URI percent-encoding or Windows path casing.
- Fixed WSL sessions missing Agent Skills stored in the Windows host profile's `.agents/skills` directory. ([#3779](https://github.com/can1357/oh-my-pi/issues/3779))
- Fixed `omp setup python` to validate the same configured or discovered interpreter used by the Python eval runtime.
- Fixed self-update misclassifying glibc Linux hosts with an installed musl loader as musl hosts, which could download an unusable musl binary instead of the glibc release.
- Fixed a crash where opening the Agent Hub after a resume and moving the selection triggered an unbounded `ExtensionExitError` unhandled-rejection storm and exit 129. The postmortem module bound the native hard-exit at first evaluation; when the bundler deferred that evaluation into a `withHostGuard` window it froze the guard's throwing replacement, poisoning every later signal/fatal exit. The native exit is now resolved per call, and the guard stamps its replacement with the native primitive it shadows so mid-guard signals still exit ([#7393](https://github.com/can1357/oh-my-pi/issues/7393)).

## [17.2.8] - 2026-08-04

### Changed

- Upgraded the bundled omptype schema engine: intersection and pipe operators, bigint and RegExp literals in the string DSL, Standard Schema V1 interop, JSON Schema import via fromJsonSchema(), and richer union/collection error reporting.

## [17.2.7] - 2026-08-03

### Changed

- Replaced arktype with @oh-my-pi/omptype for tool parameter and config schemas, significantly improving startup performance with ~100x faster schema construction. Config schema errors are now reported via OmpErrors using the same path/problem structure.

### Fixed

- Fixed an issue where custom, extension, or hook tool wrappers stripped schema methods off parameters, causing wire-schema detection failures and status-line token estimator crashes.
- Fixed a bug where agent() calls in evaluation cells ignored turn cancellation and continued running indefinitely.
- Fixed the built-in tail command to exit silently with code 141 (SIGPIPE) instead of failing with a "Broken pipe" error when a downstream pipeline reader exits early.
- Fixed the in-process ps shell builtin to support common procps/BSD format specifiers, including tpgid, pri, flags, real/effective user/group columns, wchan, fault counters, sz, and the STAT + foreground flag.
- Fixed install.sh falsely reporting success on musl-based systems (such as Alpine Linux) when the binary fails to start; the installer now smoke-tests the binary, exits non-zero on failure, and provides remediation steps.
- Fixed Codex config.toml discovery incorrectly importing MCP servers that are configured with enabled = false.
- Fixed bash.patterns allow rules rejecting valid commands when quoted arguments contained shell metacharacters (such as Cargo benchmark regex filters).

## [17.2.6] - 2026-08-03
