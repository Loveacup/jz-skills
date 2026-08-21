# Changelog

## [Unreleased]

## [17.4.2] - 2026-08-21

### Added

- Added an opt-in image URL broker (`images.urls.enabled`) that publishes outgoing images through an ordered chain of backends instead of sending inline base64 to URL-fetching providers
- Composer attachment chips (ported from omp2): pasted images and large text pastes stage as rounded preview cards above the prompt — image cards show a live thumbnail (Kitty Unicode placeholders) with pixel dimensions, text cards a snippet with `+N lines`/`N chars` — while the editor buffer holds a compact `<icon> #N` token in the card's identity color.

### Changed

- Pasted images now insert only the `[Image #N, WxH]` marker; the redundant trailing `attachment://N` URI is no longer added to the composer.
- Added a consolidated CLI reference (`docs/cli-reference.md`) documenting every top-level subcommand and launch flag, including headless print mode (`--print`/`-p`, `--print-thoughts`) ([#9252](https://github.com/can1357/oh-my-pi/issues/9252))

### Fixed

- Fixed unreadable colors in macOS Terminal.app by using its supported 256-color mode ([#9162](https://github.com/can1357/oh-my-pi/issues/9162)).
- Fixed Esc after a fast `/mcp test` result aborting the active agent turn instead of consuming the advertised cancellation input ([#9173](https://github.com/can1357/oh-my-pi/issues/9173)).
- Fixed task spawns crashing when legacy boolean per-agent prewalk or advisor overrides are present in `config.yml`.
- Fixed ACP `session/prompt` requests hanging forever when a builtin slash command's residual prompt (e.g. `/force:<tool> /some-command`) resolved locally, which also wedged all subsequent prompts on the session ([#9206](https://github.com/can1357/oh-my-pi/issues/9206)).
- Fixed eval-spawned subagent output being omitted from per-turn output-token budgets, including failed and isolated runs ([#9187](https://github.com/can1357/oh-my-pi/issues/9187)).
- Fixed `/compact` over RPC blocking the serialized command queue for the full summarization round-trip, so a follow-up `abort` could not interrupt it ([#9200](https://github.com/can1357/oh-my-pi/issues/9200)).
- Fixed RPC UI select requests dropping option descriptions, allowing hosts to render described choices ([#9175](https://github.com/can1357/oh-my-pi/issues/9175)).
- Fixed `/todo edit` failing with "Could not parse Markdown" when checklist items had backslash-escaped brackets (`- \[x\]`), which editors and markdown renderers commonly emit ([#9188](https://github.com/can1357/oh-my-pi/issues/9188)).
- Fixed `omp setup --check`/`--json` with no component printing usage text to stdout and exiting 0; it now errors on stderr and exits non-zero so scripted JSON health checks fail loudly ([#9221](https://github.com/can1357/oh-my-pi/issues/9221)).
- Fixed an aggressive `task.maxRuntimeMs` mislabeling committed subagent outcomes: a budget-killed run is no longer reported as a runtime-limit timeout, and a subagent that yielded a complete result before the deadline is no longer reported as aborted when teardown crosses the deadline ([#9191](https://github.com/can1357/oh-my-pi/issues/9191)).
- Fixed startup fallback-chain warnings for discovered OpenCode Zen, OpenCode Go, and GitHub Copilot models cached under credential-scoped IDs ([#9205](https://github.com/can1357/oh-my-pi/issues/9205)).
- Fixed interactive `/models` and Ctrl+P cycling omitting an `enabledModels`/`--models` model discovered by a background provider refresh (e.g. `opencode-go/ox-alpha-free`) after startup, by rebuilding the scoped list once discovery completes ([#9220](https://github.com/can1357/oh-my-pi/issues/9220)).
- Documented how to enable, trigger, target, and manually re-arm prewalk ([#9179](https://github.com/can1357/oh-my-pi/issues/9179)).
- Pasted images and large text pastes appear in the composer as compact icon tokens instead of bracketed markers; the bracketed form remains the outgoing/stored format, and the transcript renders it back as the compact chip.
- Deleting an attachment's inline token now removes the attachment from the submission (surviving image markers are renumbered).
- Restored prompts (esc-esc, `/tree`, branch, queued-message dequeue, failed-submit recovery) collapse image markers back into clickable atomic chip tokens and re-materialize their file links instead of degrading to dead text.

## [17.4.1] - 2026-08-21

### Added

- Added `PERSONALITY.md` support: `~/.omp/agent/PERSONALITY.md` (profile/XDG-aware agent dir) replaces the system prompt's personality block text; `personality: none` still omits the block ([#8528](https://github.com/can1357/oh-my-pi/issues/8528))
- Sloppy edits now support inline replacements with `⟪old│new⟫` syntax (`⟪old│⟫` for deletions and `⟪│new⟫` for insertions), alongside automatic recovery for common formatting mistakes without needing a retry.
- Sloppy edits now recover operations that mix `⟪old│new⟫` inline replacements with a `»` REWRITE instead of failing the payload: a redundant REWRITE is dropped, a diverging one is applied as the final text, and a note explains the interpretation.
- Expanded archive support in `read` and `write` tools: `read` can now inspect and extract members from `.rar`, `.7z`, `.iso`, `.cab`, `.deb`, `.rpm`, `.cpio`, `.ar`/`.a`, `.lzh`, `.arj`, compressed tar files (`.tar.bz2`, `.tar.xz`, `.tar.zst`), package formats (`.whl`, `.ipa`, `.xpi`, `.vsix`, `.nupkg`, `.cbz`, `.cbr`), `.asar` archives, and single-file compressed streams; `write` can create `.tar.zst` and update `.asar` archives.
- Added Code Mode for Codex `code_mode_only` models via `providers.openai-codex.codeMode` (`off`/`on`/`auto`), demoting non-essential tools into an eval bridge with generated TypeScript definitions.
- MCP tool names longer than 64 characters are now automatically truncated with a deterministic hash suffix to comply with strict provider validators.
- Marketplace-installed plugins with manifest settings can now be configured through `omp plugin config` and Settings → Plugins.
- Configured discovery providers with `authHeader` now preserve cached models across application restarts.
- Added repeat read warning hints when identical file content is read multiple times.
- Explicit DAP adapters can now attach without a PID or port when `attachDefaults` provide the target arguments.
- Added `isProjectTrusted()` compatibility shim to `ExtensionContext` for extensions targeting upstream per-directory trust gates.

### Changed

- Added `compaction.asyncEnabled` (default: on) to speculatively summarize context in the background before hitting threshold limits, avoiding blocking summarization pauses.
- Replaced `compaction.strategy` and `compaction.remoteEnabled` with an ordered `compaction.methodOrder` preference list.
- Handoff maintenance (`/handoff` and automatic handoff compaction) now commits generated summaries directly to the active session instead of starting a new session.
- Added `extendedContext` setting (`/settings` → Context → General, default: on) to optionally clamp models with premium long-context pricing tiers (such as OpenAI GPT-5.6 Sol/Terra/Luna) to standard-pricing token limits before compaction triggers.
- Token counting and token estimations are now dynamically scoped to each specific model tokenizer rather than using a single process-global tokenizer.
- `omp cleanse` and `/cleanse` now feature a live interactive status board displaying active checkers, repair subagents, tool metrics, and token/cost totals in real time.
- Eval-bridge nested `tool.<name>()` calls now enforce ACP permission gates and tool allowlists identically to direct tool calls.
- Added `tokenizer` option to custom models and `modelOverrides` to allow overriding the local tokenizer family for proxied model endpoints.
- Added `qwenTemplateReasoningEffort` to the `models.yml` `compat` schema to configure or disable reasoning effort flags for strict local inference servers.
- Settings menus now support click-to-toggle and drag-to-reorder for list items, as well as warning indicators and risk notes on sensitive options such as External Thinking.
- Supervised process completion notices now render as compact single-line entries.
- The todo HUD header now displays a consolidated progress bar showing task completion across all stages.
- `/settings` rows can now carry a risk note: a warning glyph on the row plus a warning-colored line above the description. `External Thinking` (`externalThinking`, `--external-thinking`) is the first user — providers have flagged the request shape it produces as abuse, up to account-level enforcement, so both the settings entry and `--help` now say so.

### Fixed

- Fixed regional HTTP 401 data-residency errors during Codex chat, web search, and image generation requests by passing token residency metadata on requests.
- Fixed macOS SSH ControlMaster socket creation failures caused by `sun_path` length limits when using named profiles.
- Fixed an issue where Nix-packaged builds failed to load on-demand native addons (`onnxruntime-node`/`sherpa-onnx`) due to missing shared C++ runtime library paths.
- Fixed external editor spawning (Ctrl+G, plan review, `/todo edit`) failing to attach to visible terminals for editors like `emacsclient`.
- Fixed `omp --resume` spinning at 100% CPU when new session entries arrived during initial transcript rendering.
- Fixed session resume hints and fatal exit messages omitting the active `--profile` argument.
- Fixed MCP OAuth authorization requests failing on pre-registered clients with restricted scopes by using RFC 9728 `scopes_supported`.
- Fixed isolated task subagents causing out-of-memory crashes on repositories with large uncommitted binary files by pre-sizing diffs and enforcing snapshot limits.
- Fixed LM Studio and lazy-loaded local models retaining uninitialized context lengths by re-probing loaded context lengths after initial inference.
- Fixed project-scoped Claude Code marketplace plugins incorrectly loading into sessions in other projects.
- Fixed configured advisors backed by discoverable providers remaining inactive on initial session startup until manually toggled.
- Fixed resolving `--model @<role>` failing for roles backed by discovery providers like oMLX, Ollama, and llama-swap.
- Fixed retry fallback chains stopping prematurely when encountering nested fallback configurations, and fixed session role priority during fallback chain selection.
- Fixed cancelled prompts disappearing upon abort during turn setup, properly restoring user text and attachments to the input editor.
- Fixed built-in shell utilities (`grep`, `rg`, `diff`, `find`, `timeout`, `top`, `date`, `head`, `tail`, `stat`, `truncate`, `kill`) across numerous POSIX/GNU/BSD compatibility edge cases and early-pipeline SIGPIPE handling.
- Fixed Cursor sessions missing standard string-replacement edit tooling after server tool injection.
- Fixed `hub wait` duplicating frozen rows into native scrollback during viewport overflow.
- Fixed dark-theme contrast issues on markdown code-fence headers.
- Fixed prompt guidance and descriptions for Task tools and SSH usage.
- ACP editor clients that support elicitation forms (Zed) can now use `ask`, so the agent can pose single-choice, multi-select, and free-text questions inline instead of guessing.
- `/retry` and `/handoff` now work over ACP, so editor clients (Zed) list them and can run them instead of sending the text to the model.
- Added `qwenTemplateReasoningEffort` to the `models.yml` `compat` schema, so the auto-enabled Qwen 3.8+ template effort dialect (`chat_template_kwargs.reasoning_effort`) can be switched off per provider/model for strict local servers that reject unknown `chat_template_kwargs`.
- Extensions can provide a normalized `usage` provider through `pi.registerProvider()`. Its reports now flow through AuthStorage caching, history, and usage displays, and the override is removed when the extension provider is unregistered.

## [17.4.0] - 2026-08-20

### Added

- `/cleanse` (and `omp cleanse`) — run the checker/repair loop in-session, with a live status board of running checkers, repair subagents, and token/cost totals.
- `omp ps` — interactive monitor for daemon-supervised background processes.
- Composer layouts — `composer.shape` picks the editor frame (rounded box, Claude Code rules, upstream-pi rules, borderless), with live previews in `/settings` and the setup wizard.
- Context line — `statusLine.contextLine` gauge (`percentage`, `annotated`, `embedded`) showing context usage and compaction boundaries.
- Backgroundable Python — `eval` cells can run async and auto-background like `bash`, with configurable thresholds.
- Local Claude token counting — Anthropic-family tokens now count via a native local tokenizer, and every counter (session maintenance, advisor, stats, context tools) uses the active model's own tokenizer.
- `extendedContext` setting — pick whether models with premium long-context pricing (272K/1M tiers on Codex-class models) use the extended window or compact early and stay on standard pricing.
- `/extended-context` — toggle premium long-context windows without leaving the session.
- Speculative compaction — with `compaction.asyncEnabled`, all compaction modes compact in parallel while the session continues, then splice the result in instantly.
- `tokenizer` property on custom models and `modelOverrides` to pin the tokenizer family for proxy models.
- `qwenTemplateReasoningEffort` in `models.yml` `compat` to disable the Qwen 3.8+ reasoning-effort template parameter for strict local servers.
- Click-to-toggle and drag-to-reorder for list-valued editors in `/settings`.
- `icon.subscription` and `icon.advisor` symbol-theme tokens (Nerd Font, Unicode, ASCII).

### Changed

- Typing anywhere in the /models UI now immediately focuses the model list for instant search and arrow navigation.
- Revamped the todo HUD — overall progress renders along the tree-spine connector with smooth completion transitions.
- Compaction divider now names the maintenance method that fired (`remote-compacted`, `soft-compacted`, `handed-off`, `snap-compacted`) and shows the before → after context size (e.g. `256K→20K`).
- `/handoff` (and automatic handoff compaction) now compacts in place, replacing the session context instead of forking a new session.
- Compaction method priorities — `compaction.methodOrder` takes an ordered preference list (e.g. `[remote, snap]` uses remote compaction where the provider supports it, such as OpenAI, and snap everywhere else), replacing `compaction.strategy`/`compaction.remoteEnabled`.
- Unified inline overlays and selectors (model picker, settings, `/cleanse`) into one titled rounded-box panel style.
- Risk badges and warnings on `/settings` rows, starting with External Thinking.
- Faster CLI Startup

### Fixed

- `/models` keeps `auto` thinking on non-default roles such as `task` instead of changing the active model and displaying the role as `max`.
- Subagent `yield` structured results no longer get corrupted by lossy argument repairs; prompt guidance improved for weak callers.
- GitHub `file_read` returns proper image blocks and direct view URLs for image/binary files.
- Cancelled prompts during pre-stream turn setup restore the text and image attachments to the editor.
- `top` builtin accepts single-dash macOS flags such as `-pid` and `-stats`.
- GNU/BSD compat sweep across built-in shell utilities (`timeout`, `diff`, `find`, `date`, `tail`, `head`, `rg`, `stat`, `truncate`, `cksum`, `sleep`, `which`, `nohup`, `kill`).

## [17.3.8] - 2026-08-19

- Fixed unquoted internal URLs in `bash` commands consuming adjacent shell operators into the resolved filesystem path.

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
