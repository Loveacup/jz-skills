# Changelog

## [Unreleased]

### Added

- Added the `retry.waitForUsageReset` setting: when a provider reports usage-limit exhaustion with a reset time (5-hour or weekly quota windows on any provider), the session sleeps until the reset instead of failing fast past `retry.maxDelayMs`.

### Fixed

- Report oversized selected lines that cannot fit after read context, with a working raw recovery selector instead of a looping continuation hint ([#10775](https://github.com/can1357/oh-my-pi/issues/10775)).
- Fixed WorkPool child sessions crashing during startup while constructing their incremental `yield` tool schema.
- Commit summaries written in Vietnamese, Korean, and other accented scripts are no longer rejected for exceeding the length limit, and keep their accents as typed.

## [18.1.10] - 2026-09-04

### Changed

- Subagent `yield` now takes `data`/`error` directly instead of nesting them under a `result` wrapper.

### Fixed

- Fixed Codex V2 remote compaction rebuilding the request prefix differently from normal turns, restoring prompt-cache reuse ([#10786](https://github.com/can1357/oh-my-pi/issues/10786)).
- Restored mouse clicks, hover, and wheel scrolling in Plan Review.

## [18.1.9] - 2026-09-04

### Breaking Changes

- Browser and computer automation now use JavaScript/Python evaluation preludes with reusable tab and element handles, replacing the previous standalone tool schemas and object-shaped run APIs.
- Replaced the `inspect_image` tool and `/vision` controls with `read <image>?q=<question>` for image questions; text-only models now receive image metadata and guidance for using this selector.
- Renamed `inspect_image.timeoutMs` to `images.questionTimeoutMs`; existing settings are migrated automatically.

### Added

- Bash now extracts Kitty and Sixel terminal graphics as image results for foreground, failed, manual, and background executions.
- Markdown links to existing local files and resources are now clickable while preserving their displayed URLs.
- Added `/switch <model>` for session-only model changes, with the same model selectors and completions supported by `--model`; ACP `/model <model>` accepts these selectors as well.
- Added the `worktree.cleanSource` setting to reset and clean the original checkout when creating a worktree with `/wt`.
- Expanded the computer JavaScript/Python evaluation prelude with direct desktop, window, screenshot, accessibility, and element interaction helpers, while keeping `computer.run` available for multi-step scripts.

### Changed

- Agent delegation is now model-aware, allowing some models to favor focused inline work instead of spawning subagents.

### Fixed

- Fixed fallback authorization-code prompts remaining active after native OAuth callback completion.
- Fixed reciprocal idle subagents repeatedly waking one another indefinitely.
- Fixed `/wt` and `git worktree add` failing when the new worktree targeted the same commit as the clean source checkout.
- Fixed omp-installed marketplace plugins and `--plugin-dir` plugins losing their skills when the Claude plugin source was not separately enabled ([#10743](https://github.com/can1357/oh-my-pi/issues/10743)).
- Fixed session accent colors rendering as bright white in terminals without truecolor support, including Terminal.app ([#10759](https://github.com/can1357/oh-my-pi/issues/10759)).
- Rules with `enabled: false` frontmatter are now omitted during discovery, matching disabled skills ([#10769](https://github.com/can1357/oh-my-pi/issues/10769)).
- Fixed large MCP tool-result previews losing the relevant tail content when an oversized output line preceded it ([#10761](https://github.com/can1357/oh-my-pi/issues/10761)).
- Fixed `Ctrl+V` replacing CJK characters with `?` when pasting from XWayland clipboard owners on Wayland ([#10762](https://github.com/can1357/oh-my-pi/issues/10762)).
- Fixed byte-limited artifact reads reporting the displayed byte count instead of the actual read limit ([#10764](https://github.com/can1357/oh-my-pi/issues/10764)).
- Fixed read-tool truncation notices incorrectly reporting zero delivered lines or bytes when previewing a partial oversized line ([#10768](https://github.com/can1357/oh-my-pi/issues/10768)).
- Fixed Mnemopi removing explicitly retained or learned long-term memory after sessions longer than 24 hours by consolidating eligible working memory at session start ([#10770](https://github.com/can1357/oh-my-pi/issues/10770)).

### Removed

- Removed the librarian agent.

## [18.1.8] - 2026-09-03

### Fixed

- Improved background task results with structured output schemas: parsed results are now available through the `agent://<id>` resource, while large or invalid inline JSON is replaced with a reliable pointer to the complete result.
- Background task artifacts are retained long enough for follow-up turns to read them, including failed tasks that lack valid structured output, and are cleaned up without blocking shutdown or leaking resources.
- Fixed context compaction incorrectly accepting archived history that was larger because of opaque reasoning data, allowing the next compaction strategy to run instead.
- Fixed the Model Hub sidebar jumping to the top when provider refreshes rebuild the list; the focused model, or its nearest remaining entry, is now preserved.
- Fixed the `inspect_image` status hint showing the wrong model after switching between image-capable model roles.
- Fixed multi-minute TUI freezes during subagent activity and batch execution.

## [18.1.7] - 2026-09-03

### Breaking Changes

- Removed the Ruby and Julia eval backends and related interpreter configuration; eval now supports Python and JavaScript only.
- Removed the eval parallel() and pipeline() helpers. agent() and completion() now return handles immediately, and wait(handles) provides synchronization.
- Python eval tool calls are now asynchronous coroutines, matching JavaScript; use await tool.read({...}) and similar calls.

### Added

- Added asynchronous eval agent and completion handles with status, cancellation, messaging, waiting, and automatic result delivery for unwaited background work.
- Added eval workpools for queueing items onto the least context-loaded keep-alive subagent with configurable concurrency; the pool name is its async-job ID for `hub wait`, `.peek()` gives a non-consuming snapshot, per-item `{key, data|error}` yields finish batches incrementally, and `eval.workpool.freshAgents` opts into a new agent per item.
- Added support for defining eval tools in Python with @tool or JavaScript with tool(fn, schema), and exposing them to subagents through task, agent, and workpool calls. Configure availability with eval.tools.enabled.
- Added native Windows ARM64 binaries with architecture-aware installation and updates.
- Added an MLX backend for running local tiny models on Apple silicon. Configure providers.tinyModelDevice=mlx, or use PI_TINY_DEVICE=mlx or metal, to run title generation, memory tasks, and automatic thinking classification with MLX models, with an ONNX CPU fallback when Python is unavailable.
- Added Qwen3 1.7B as a local memory and thinking-classification model for the MLX backend.

### Changed

- Local tiny models for titles, memory, and automatic thinking classification now share on-demand workers across omp processes, reducing redundant resource usage; workers stop automatically after inactivity.
- PI_TINY_DEVICE=metal now selects the MLX backend on macOS.
- Updated agent reactions to trigger on the opening emoji instead of requiring a newline, consuming any following whitespace.

### Fixed

- Fixed transient provider retries incorrectly failing with an “Agent is already processing” error.
- Fixed user-scope marketplace plugins installed through omp losing their skills when the Claude plugin source was not separately enabled.
- Fixed hashline edits failing when targets included apply_patch markers, while rejecting ambiguous bracketed targets instead of editing the wrong path.
- Fixed bracketed hashline edit targets being reported as undefined to extension path allowlists.
- Fixed MCP tools discovered during startup disappearing after plan-mode approval or when leaving default-on plan mode.
- Fixed ACP clients receiving invalid file locations or updates for released terminals, preventing invalid worktree scans and terminal errors on Windows.

## [18.1.6] - 2026-09-03

### Breaking Changes

- Replaced the local session-title model choices with LFM2.5 230M, LFM2.5 350M, and Falcon H1 Tiny 90M.
- Reserved main and sub as built-in subagent definition names; custom agents can no longer use these names.

### Added

- Added agent reactions: a reply that opens with a lone emoji line shows the emoji as a badge on your message bubble instead of in the text; toggle the prompt invitation with the tui.reactions setting.
- Added video attachment and reading support through ffmpeg, including preview grids with metadata and timestamp/frame selectors such as :412 and :1h5m42s.
- Enhanced the model picker with intelligence indicators, catalog TPS estimates, provider-aware ranking, and provider-supplied badges and descriptions.
- Added detailed, non-summarized findings for scout agents through the report definition field, and subagent result relay so read-only agents can return data to their originating agent.
- Added agent-scoped rules using an agents frontmatter field with glob matching, including support for inspecting applicable rules with omp ttsr list and omp ttsr test --agent.
- Added non-interrupting extension messages through deliverAs: "aside" for pi.sendMessage and pi.sendUserMessage.
- Added copy and open controls for rendered blocks and links, including /copy link and the /open command.
- Added option-click cursor positioning in the prompt entry box.
- Added the configurable opencode display layout, with a corresponding first-run and upgrade setup option.
- Added the skillful prompt setting and /skillful command to control whether available skills are listed in the system prompt.
- Added Firecrawl as an optional providers.fetch backend for URL reading, configurable with FIRECRAWL_API_KEY and FIRECRAWL_BASE_URL.
- Added provider request metadata configuration for usage and cost attribution, including Amazon Bedrock request headers and User-Agent customization.
- Added the :-N read selector for reading the last N lines from files, directories, archives, artifacts, internal URLs, and web URLs, including combinations such as :raw:-60.
- Added an opt-in extension status-line segment for displaying custom statuses inline.
- Added injectV1: false to openai-models-list discovery for OpenAI-compatible gateways whose model endpoint is rooted at a versioned URL.
- Added provider-reported credits and routed-model counts to /session statistics.
- Added CLINE_API_KEY to the CLI environment help for native ClinePass subscription inference.
- Expanded Devin model selectors to support native CLI aliases, dotted upstream names, and dynamic effort-route identifiers.
- Standalone CLAUDE.md files in the project root and ancestor directories are now loaded as project context alongside AGENTS.md files.

### Changed

- Session history is now sorted by modification time, then creation time, then file path.
- Increased the maximum file snapshot size to 4 MB.
- Edit tools now provide streamed diff previews while applying changes.
- Approved plan content is included directly in agent history, reducing redundant reads.
- power.sleepPrevention now works on Linux and Windows. Its idle default keeps long-running sessions awake on those platforms; set it to off to restore the previous behavior.
- Unsupported-model errors no longer include incorrect retry instructions.

### Fixed

- Fixed local title models receiving unsupported online examples and failing with certain tokenizer templates.
- Fixed model picker search selection so it moves to the best matching result after results change.
- Fixed /new sometimes reviving the previous conversation in the current process or after a restart.
- Fixed raw text escaping in agent responses.
- Fixed structured subagent result previews being truncated incorrectly.
- Fixed /usage taking several seconds to become responsive on large statistics databases.
- Fixed the status line not appearing correctly in the first startup frame.
- Fixed shell builtins reporting broken-pipe errors when downstream commands exit early.
- Fixed provider-qualified model roles with dotted revisions resolving to the wrong provider or model.
- Fixed agent-scoped rules being lost when subagents are restored, and fixed rule:// URLs and rule inspection to consistently use the calling agent's applicable rules.
- Fixed extension and user asides being stranded, delivered to the wrong session, or incorrectly interrupting or restarting turns during session changes and image processing.
- Fixed parent steering messages arriving during a subagent's final result from preventing that result from being committed.
- Fixed messages typed while an edit or write tool was streaming from discarding the completed tool call and triggering unnecessary regeneration.
- Fixed self-hosted Firecrawl URLs with origin-only base URLs from gaining an extra slash.
- Fixed omp commit auto-staging from including macOS Unicode-normalization duplicates or files ignored by nested .gitignore rules.

## [18.1.5] - 2026-09-03

### Added

- Added Abliteration provider support to `/login`, including `ABLITERATION_API_KEY` configuration and help text.
- Added clone-first Git worktree support that carries over ignored build artifacts when creating worktrees, with a configurable `worktree.clone` setting and fallback to a standard checkout. This is supported by `github pr_checkout`, `omp worktree add`, and `git worktree add` commands entered through the Bash tool.
- Added the `omp worktree add` command with Git-compatible branch, detach, path, and commit options.
- Added `/wt` (alias `/worktree`) to create a linked worktree with uncommitted changes and move the current session into it while leaving the original checkout untouched.

### Changed

- Foreign user-level configuration sources (`~/.cursor`, `~/.codex`, `~/.claude`, `~/.gemini`, `~/.config/opencode`, `~/.codeium/windsurf`) are now opt-in via `enabledProviders`, while project-level configurations in CWD and `.agents` continue to load by default.
- Split subagent isolation configuration into `task.isolation.enabled` and `isolation.backend`; existing `task.isolation.mode` settings are migrated automatically.
- Updated the built-in `smol` and `slow` model priority chains to favor newer recommended models and remove older model generations.
- Improved unsupported-model error messages by removing retry guidance that does not apply.

### Fixed

- Fixed automatic title generation so `--no-title` also prevents todo-initialization title refreshes, while automatic titles retain the selected OAuth account without sharing foreground request identity.
- Fixed provider errors so they wrap to the terminal width and remain readable in the transcript and pinned error banner, with long messages available through the expansion hint.
- Fixed Gemini malformed function-call turns so textual tool-call output is rejected conversationally and the session can continue instead of stopping with a pinned error.
- Fixed auto-compaction recovery getting stuck in repeated retries when models return empty length-limited responses; it now stops with an actionable error.
- Fixed MCP servers failing to reconnect after transient startup handshake timeouts.
- Fixed programs supervised by `hub start` hanging when querying terminal capabilities.
- Fixed large pastes followed immediately by Enter so the input is submitted with the pasted content instead of being left in the large-paste menu.

### Removed

- Removed the bundled `designer` subagent and `designer` model role; `modelRoles.designer` and `@designer` are no longer built in.

## [18.1.3] - 2026-09-02

### Changed

- The `doubleEscapeAction` setting now accepts `tree`, so double-Escape can open the session tree instead of the rewind selector.
- Updated the visual representation for the IRC tool from "irc" to "#"
- Rewinding to a user message (double-Escape, `/branch`) now branches within the current session — the old path stays reachable in `/tree` — instead of forking a child session; `/rewind` is an alias for `/branch` ([#10565](https://github.com/can1357/oh-my-pi/pull/10565) by [@anatoli-tsinovoy](https://github.com/anatoli-tsinovoy)).

### Fixed

- Active sessions now keep memory proportional to truncated raw SSE and tool outputs instead of retaining complete oversized backing strings ([#10547](https://github.com/can1357/oh-my-pi/issues/10547)).
- Anthropic sessions now keep tool-roster changes and warm-prefix pruning from invalidating preserved thinking or the prompt cache.
- TypeScript code intelligence now works on TypeScript 7 projects: the built-in `typescript-native` server runs `tsc --lsp --stdio` when the resolved TypeScript install no longer ships `tsserver.js`, replacing `typescript-language-server` for that project.
- Claude marketplace MCP servers now resolve environment placeholders in stdio environment values instead of passing strings such as `${NAME:-}` literally ([#10481](https://github.com/can1357/oh-my-pi/pull/10481) by [@mrexodia](https://github.com/mrexodia)).
- Fixed prewalk conflicting with `todo.eager=always`: the forced eager-todo prelude ("call todo first this turn") was injected alongside the prewalk plan nudge ("write a complete plan first, then todo"), giving the model contradictory instructions; the eager-todo prelude is now suppressed only when prewalk will perform a handoff ([#10510](https://github.com/can1357/oh-my-pi/issues/10510)).
- Fixed `authHeader: true` + command-backed `apiKey` discovery providers (no explicit `headers:` block) resending a stale bearer after a 401 force-refresh; discovered models now re-derive `Authorization` from the live `apiKey` each request ([#10551](https://github.com/can1357/oh-my-pi/issues/10551)).
- Fixed the embedded shell's `command -v`/`-V` honoring only the first operand: it now iterates every name like bash/zsh, printing one line per resolved name and skipping misses ([#10544](https://github.com/can1357/oh-my-pi/issues/10544)).
- Fixed hard-killed subagents vanishing from the agent registry under concurrent fan-out: `AgentLifecycleManager.release` now applies the terminal `aborted` transition before awaiting the tombstone sidecar write, closing a race where the dying session's own dispose-path unregister deleted the ref instead of leaving it as a tombstone ([#10531](https://github.com/can1357/oh-my-pi/issues/10531)).
- `omp commit` now keeps extension-provided model credentials available in its nested commit-agent session ([#10528](https://github.com/can1357/oh-my-pi/issues/10528)).
- MCP tool results now surface `structuredContent`: servers that return their payload in the structured channel while keeping `content` a terse ack (e.g. rhizome-mcp) are no longer data-less to the model ([#10522](https://github.com/can1357/oh-my-pi/issues/10522)).
- Fixed the Agent Hub roster shuffling erratically while open: rows no longer re-sort on every agent heartbeat, so the list stays stable and navigable with many active agents ([#10524](https://github.com/can1357/oh-my-pi/issues/10524)).
- Exiting Vibe mode now removes its restrictions from subsequent model turns, including restored sessions ([#10500](https://github.com/can1357/oh-my-pi/issues/10500)).
- Fixed all-sessions listing (`Tab` in session picker) and cross-project resume failing when sessions are stored under `XDG_DATA_HOME`; `listAllSessions` now scans the active `getSessionsDir()` root instead of hardcoding `~/.omp/agent/sessions`.
- Fixed the Nerd Font context icon showing a Windows logo instead of a generic window ([#10476](https://github.com/can1357/oh-my-pi/pull/10476) by [@erickmazer](https://github.com/erickmazer)).
- The debug terminal snapshot now reports Herdr (and CMUX) as the multiplexer wrapping the session, matching the TUI's pane-identity detection instead of only tmux/screen/zellij.
- Fixed vibe mode becoming un-exitable after branching a session (including via `/btw`), which previously failed with "Vibe parent session changed before mode exit could be persisted." ([#10468](https://github.com/can1357/oh-my-pi/issues/10468)).
- Fixed HTML session exports reordering interleaved assistant text, thinking, images, and tool calls in the transcript, and split matching text/tool sidebar rows with block-accurate navigation. ([#10253](https://github.com/can1357/oh-my-pi/pull/10253) by [@realcoderandom](https://github.com/realcoderandom))
- Fixed the built-in `grep` and `sed` treating a basic regular expression as an extended one: a bare `+` is now the literal and `\+` the operator, patterns like `^+` or `s/^\+/` no longer match every line, `^` anchors inside `\(…\)` and after `\|`, and a repetition operator with nothing to repeat is reported instead of silently selecting the whole file ([#10298](https://github.com/can1357/oh-my-pi/pull/10298) by [@mruangutai](https://github.com/mruangutai)).
- Fixed RPC `prompt` responses for `/skill:*` commands arriving only after the entire prompt-dispatch pipeline finished (usage preflight, compaction, provider calls): under provider stress that outlasts any client prompt timeout, so hosts reported the prompt as rejected while the turn was in fact running. The skill branch now builds the skill prompt eagerly (preserving the immediate error for an unreadable skill file) and dispatches the expensive pipeline asynchronously after answering, matching plain prompts; when the dispatch is cancelled before a turn starts (e.g. an abort overtakes usage preflight), the session now reports it through the non-invoked  completion frame instead of leaving hosts waiting for an  that never comes ([#10249](https://github.com/can1357/oh-my-pi/pull/10249) by [@cwr250](https://github.com/cwr250)).
- Fixed stale `omp-plugins.lock.json` entries loading leftover `node_modules` trees for plugins no longer declared in an existing `package.json` — the orphaned copy double-loaded its extensions. Lockfile-only plugins remain supported for manifest-less roots and symlinked packages (`omp plugin link`, marketplace runtime packages); stale entries are skipped with a warning.

## [18.1.2] - 2026-09-01

### Added

- Recover stray <SM:EDIT> payloads emitted as plain text into real edit tool calls, with support for disabling this behavior through the edit.recoverInlineEdits setting.
- Advisors now receive context from the active memory backend, including project decisions and recalled instructions; advisors also gain the recall tool when supported by the backend.

### Changed

- Replaced the sloppy edit format's symbolic markers with a clearer XML-based format using <SM:EDIT>, <SM:FIND>, and <SM:PUT> tags. Edit errors now include copy-ready XML payloads.
- Increased the default input delay for the trace CLI to 3 seconds.

### Fixed

- Improved chat history stability in long-running sessions by avoiding unnecessary updates when date or directory context changes.
- Fixed the trace CLI hanging during proxy connections and added support for forward HTTP proxies.
- Fixed newly started sessions using stale model context-window limits after background model discovery completes; the active model now refreshes automatically so context usage and compaction thresholds match the model catalog.

## [18.1.1] - 2026-09-01

### Fixed

- Fixed a native crash (and multi-gigabyte committed-memory growth held until exit) when git status ran over worktrees with tens of thousands of untracked files: whole-worktree porcelain status now runs through the git CLI with bounded output capture, falling back to the in-process gitoxide walk only when git is not installed, and any panic escaping a native VCS operation now surfaces as a structured `VcsError` instead of a process-level failure.

## [18.1.0] - 2026-09-01

### Added

- Added the `/trace` slash command to display session trace URLs in the stats dashboard.
- Added support for OpenAI-compatible gateways whose model-list endpoint is rooted at a versioned URL, with an `injectV1: false` discovery option to request `{baseUrl}/models` directly.
- Added provider-reported credits and concrete routed-model counts to `/session` statistics.
- Added `CLINE_API_KEY` to CLI environment help for native ClinePass subscription inference.
- Expanded Devin model selection to support native CLI aliases, dotted upstream model names, and raw effort-route identifiers.
- Added provider-supplied model metadata to `/models`, including new, beta, and recommended badges plus model descriptions.
- Standalone `CLAUDE.md` files in project and ancestor directories are now loaded as context alongside `AGENTS.md`, while preserving config-directory precedence.
- Added an Activity view to Agent Hub with searchable and filterable timelines spanning live progress and persisted transcripts; `/hub` is now the live-operations entry point while `/agents` retains Control Center behavior.
- Added an `icon.advisorClosed` symbol-theme token: the advisor eye in the status line now closes once the advisor has finished reviewing and will not add further comments.

### Changed

- Disabled hashline editing for Kimi, Mimo, DeepSeek Flash, and Stepfun models for improved stability.
- Reworked `/usage` into a fullscreen dashboard overlay (no transcript output): a compact per-provider subscriptions grid with untouched providers collapsed into one line, a GitHub-style daily activity heatmap fed by local stats, and the classic full report one keypress away.
- Reworked transcript navigation with a fullscreen rewind selector opened by double-Escape, supporting rendered-item navigation, user-turn jumps, branching rewinds, and alternate session-tree branch selection.
- Updated `/copy` to use the fullscreen transcript selector, allowing users to copy a turn or navigate into nested content such as code, quotes, commands, and tool output.

### Fixed

- Improved edit-tool error guidance for operations missing the `»` separator, identifying redundant context-only operations
- Fixed OAuth provider `modifyModels` projections being silently dropped after a discovery refresh introduced live-config headers.
- Edit-tool `＋`/`－` line operations now match their anchors leniently across whitespace drift (indentation, blank-line miscounts) instead of failing with a byte-for-byte error; a note reports the lenient match.
- Fixed an edit-tool REWRITE consisting only of `＋` add lines silently replacing (deleting) the matched text; it now inserts after the kept MATCH.
- Edit-tool no-match errors now name MATCH lines that exist nowhere in the file and suggest marking them with `＋`, and errors without a located region no longer append a misleading file-head "closest match" preview.
- Fixed ordinary CLI startup eagerly loading the computer worker graph (native desktop addon and early environment), restoring lazy startup and profile `.env` ordering.
- Fixed online auto-thinking classifier usage being omitted from session token and cost totals.
- Fixed image generation with custom provider endpoints when using `openai-codex` credentials and a non-OpenAI chat model.
- Fixed custom hook UI factories not receiving the documented `keybindings` argument.
- Fixed MCP OAuth token exchange for authorization endpoints that use a different resource indicator.
- Fixed custom extension `web_search` tools being shadowed by the built-in search tool.
- Fixed Agent Hub task boards collapsing to summary rows after returning from a focused session.
- Improved Linux ARM64 browser startup messaging when managed Chrome for Testing builds are unavailable, with guidance for using system Chromium or `PUPPETEER_EXECUTABLE_PATH`.
- Fixed resuming image-heavy sessions that previously terminated while replaying transcripts.
- Fixed custom agents declaring `hub` being incorrectly treated as read-only.
- Restored compatibility for legacy Pi extensions that import `calculateContextTokens` or use the synchronous `SettingsManager.create()` API.
- Fixed custom model overrides being lost during configuration updates.
- Clarified that the default task-delegation setting follows the selected model's policy.
- Fixed `/rename` without a title interrupting active session activity.
- Fixed the Nerd Font notification persisting incorrectly after theme configuration.
- Fixed sampling parameter errors with newer Anthropic models.
- Long OpenCode Go usage-limit waits now switch replay-safe turns to a configured alternate provider when the delay exceeds `retry.maxDelayMs`.
- Fixed OpenAI Codex Responses tool results being lost when composite and plain tool-call identifiers did not match.
- Fixed `/tan` background agents failing to resolve credentials for providers supplied by extensions.
- Fixed Mnemopi saving session transcripts on exit when automatic retention is disabled.
- Fixed configuration writes through chained symlinks so the final target and intermediate links are preserved.
- Fixed direct tool calls using full `xd://` device URLs.
- Fixed command-backed headers in custom discovery providers being resolved for discovered models.
- Fixed Windows drive paths pasted under WSL being resolved through their `/mnt/<drive>` mounts for images and file reads.
- Improved sloppy/SPARSE edit no-match guidance so low-confidence matches are clearly presented without unsafe copy-ready operations.
- Fixed agents in Hub wait loops failing to respond to user steering messages.
- Fixed `/tan` sessions inheriting parent costs and overstating subagent totals.
- Fixed prompt action labels being truncated.
- Fixed assistant text being truncated when a tool call begins during streaming.
- Fixed the advisor dropping concerns when catching up on multiple turns and improved review context with bounded tool-result excerpts plus complete `ask` exchanges.
- Fixed bash command timeouts being delayed by child processes holding output pipes open, while improving timeout reporting and cleanup.
- Fixed retry countdowns and capped-wait errors displaying floating-point noise in millisecond durations.
- Prevented browser `app.path` from terminating existing same-executable applications when no reusable CDP endpoint is available.
- Fixed top-level errors overwriting the active composer before terminal restoration.
- Fixed Enter being ignored during the first turn when omp starts with an initial prompt.

## [18.0.11] - 2026-08-29

### Added

- Added gallery previews for composer and status-line components, with CLI filters for browsing by surface, composer, or segment.

### Changed

- The status line now displays the thinking level as a compact icon alongside the model name by default; set `statusLine.compactThinkingLevel` to `false` to restore the previous display.

### Fixed

- Fixed MCP OAuth discovery for shared API gateways and authorization servers with nested paths, including Keycloak realms, so authentication targets the correct resource issuer and supports endpoint and dynamic client-registration discovery.
- Fixed credential rotation for HTTP 402 payment-required responses so sibling credentials are tried before model fallback without misclassifying informative non-quota errors.
- Transport errors after a complete, non-executed tool call can now retry through configured retry budgets and fallback chains when it is safe to do so, instead of ending the turn prematurely.
- Improved handling of truncated or otherwise undecodable images so they produce an actionable error and no longer permanently block subsequent requests or resumed sessions.
- Fixed Sharpshooter consolidation preserving memory files and queued changes when an empty replacement is returned.
- Fixed `omp plugin features` so it discovers marketplace-installed plugins.
- Fixed Escape handling when closing the `/session` information panel; the panel now retains focus until dismissed.
- Fixed the thinking-block visibility toggle so streamed reasoning is correctly hidden when thinking blocks are set to hidden.
- Reduced high idle CPU usage while the agent is working.
- Fixed resumed advisor subscription usage being displayed as a dollar amount instead of as a subscription.
- Fixed relative API addresses whose names end in image extensions being pasted as text instead of incorrectly treated as missing local image files.
- Fixed chat Markdown links and bare URLs so they become clickable OSC 8 hyperlinks when `tui.hyperlinks=always` is enabled.
- Fixed unreadable composer text on light terminal backgrounds when using transparent composer styles.
- Fixed `retry.fallbackChains` warnings for valid selectors from providers whose model discovery is still pending; validation now updates after discovery completes.
- Fixed visible browser windows launched by OMP so page content resizes with the operating-system window.
- Fixed Python evaluation hanging on Windows when importing native-extension modules such as NumPy.
- Fixed subagent extension context helpers so `ctx.getContextUsage()` and `ctx.compact()` operate on the child session.
- Fixed `lsp diagnostics` incorrectly reporting success for project-aware pull-diagnostic servers when diagnostics time out or fail.
- Corrected labels under `Settings > Context > Compaction Token Limit`.
- Fixed orphaned pages, iframes, and workers accumulating in the shared headless browser after abnormal OMP session termination.

## [18.0.10] - 2026-08-28

### Added

- Added the Sharpshooter memory backend for tracking friction-earned project decisions, with `/memory queue` and `/memory sync` controls.
- Added `/restart` to relaunch omp with its original launch flags and resume the current session in place.
- Added the `band` composer shape, a flush powerline status band above the prompt; it is now the default while existing `composer.shape` settings remain unchanged.
- Added in-place retry for interrupted or failed tool calls: use F5, Alt+R (`app.retry`), or `/retry` to replay an intact failed batch without an additional model round trip.
- Improved the working status display with a timed braille spinner, streamed intent, session accent colors across relevant status elements, and theme-aware session accent generation.
- Updated the `unicode` and `ascii` symbol presets to use `π`/`pi` for the brand icon, avoiding tofu on fonts without the nerd-font glyph.

### Changed

- The `/review` command's PR-style comparison now uses the merge base against the current branch, excluding commits that exist only on the base branch; selecting the current branch reports no changes.
- Prompt history is now persisted immediately when submitted, and session database state is checkpointed on exit to improve durability and prevent unbounded WAL growth.

### Fixed

- Fixed edit-tool parsing of `－`-prefixed MATCH lines so they correctly represent whole-line deletions and can be replaced by a following `＋` run.
- Fixed interrupted and failed Python evaluation cells being reported as successful results instead of errors, improving model handling, telemetry, retries, and background-job failure reporting.
- Fixed native-extension imports such as `numpy` hanging indefinitely in the Python evaluation tool on Windows.
- Fixed a macOS composer display issue where undercurl could remain attached to stale text after rapid typing.
- Improved `xd://` MCP failure messages with actionable transport stages, failure categories, server and tool context, retryability, trace IDs, and redacted JSON-RPC details.
- Fixed ACP `read` tool-call locations so clients such as Zed Follow receive the resolved filesystem path rather than the OMP line-range selector.

## [18.0.9] - 2026-08-28

### Breaking Changes

- Removed the `git` and `jj` wrapper modules from the SDK surface. VCS operations are now available through `@oh-my-pi/pi-natives/vcs`, including native handles and typed `VcsError` support; the package continues to re-export the `github` (gh CLI) helpers.

### Changed

- `extendedContext` now defaults to off: models with premium long-context pricing tiers (e.g. GPT-5.6 1M) stay capped at their standard-pricing window unless the setting or `/extended-context on` enables the extended window.

### Fixed

- Improved terminal readability on light backgrounds by ensuring TUI surfaces use contrasting foreground colors.
- Coalesced simultaneous autonomous continuation requests to prevent repeated calls while the agent is busy, with clearer continuation diagnostics.
- Fixed Snapcompact so it skips or falls back when compaction would not reduce context size, and now compacts text in mixed tool results while preserving all source images.
- Added Google Antigravity daily quota usage to the status line.
- Fixed status-line background-work counts so queued tasks and evaluation jobs remain visible without double-counting running subagents.
- Fixed nested subagent visibility in RPC subscriptions, the subagent HUD, `get_subagents`, `subagent_*` events, and `get_subagent_messages`.
- Fixed `omp token` refreshing local MCP OAuth credentials without blocking or losing rotating refresh tokens, and preserved OpenCode MCP OAuth configuration during discovery.
- Prevented process crashes caused by socket-closed errors and unhandled promise rejections during concurrent subagent shutdowns, timeouts, and MCP transport disconnects.
- Fixed automatic startup model selection so ambient AWS credentials do not incorrectly select an unavailable Amazon Bedrock model over a provider the user has authenticated with.
- Kept embedded context usage visible in the status line when long session names or paths consume available space.
- Added a status message when `CTRL-O` toggles tool-output expansion.
- Fixed `omp usage` to report Codex Chat and Spark capacity meters separately when they share a usage window.

## [18.0.8] - 2026-08-27

### Added

- Transcript usage rows now show the total prompt-to-yield time (Δ + clock, including tool calls) after the turn timestamp, opt-in via `display.showTurnTime` (off by default).
- `omp usage` now shows Z.AI GLM Coding Plan credit quotas (5h + weekly) with the subscribed plan tier.
- The usage status line now labels untiered quota windows with the report's plan tier, surfacing Z.AI Coding Plan (`pro`) and Codex plan names next to the 5h/7d percentages.

### Fixed

- Fixed corrupt session headers silently overwriting recoverable transcripts during resume ([#9915](https://github.com/can1357/oh-my-pi/issues/9915)).
- Fixed a startup race that left a new session with almost no tools and an empty skill inventory. An early reconcile could commit a small live tool set as the permanent enabled set. The enabled set is now seeded from the construction-time tool slate, and `reconcileCodeMode` samples it inside the registry mutation lock.
- Fixed `snapcompact` compaction frames larger than the persistence limit being truncated into invalid image base64 on session resume, which made the provider reject every subsequent request with HTTP 400; already-corrupted archives now resume from their retained source text instead ([#9901](https://github.com/can1357/oh-my-pi/issues/9901)).
- Fixed prompts hanging when a successful automatic retry ended through an early terminal path such as `yield`.
- Fixed `hub` `send await:true` blocking for the full IRC timeout when the awaited agent finished without replying; the send now settles as soon as the peer stops ([#9913](https://github.com/can1357/oh-my-pi/issues/9913)).
- Fixed workspace symbol searches reporting success when every configured language server failed; partial failures now remain visible alongside successful results ([#8387](https://github.com/can1357/oh-my-pi/issues/8387)).
- Handle denied working-directory changes without crashing resume, move, or startup flows.
- Fixed Cursor-only sessions becoming permanently unusable after replaying orphaned async tool results.
- Fixed `!command` config values (`auth.broker.url`, `auth.broker.token`, custom headers) passing inherited file descriptors to the resolution command; on POSIX these commands now run under `/bin/sh` (Windows keeps the built-in shell and is unchanged)
- Fixed `providers.amazon-bedrock` guardrail, transport, and header settings being dropped for models referenced by an inference-profile ARN.
- Fixed the welcome screen staying at its original width after a terminal resize; a settled rebuild now recomposes it at the new width like the rest of the transcript.
- Fixed `omp if-bench` ending an Anthropic model's run on a transient `Refusal (cyber)` classification; the cyber classifier is stochastic near the threshold, so a refused turn is now retried with a fresh session (up to 3 attempts) before it is scored as a run-ending provider failure.
- Fixed streamed assistant responses crashing when a later provider delta revised earlier Markdown; assistant output now stays mutable until finalization.
- Fixed an orphaned foreground tool card surviving a later agent turn and pinning the entire transcript outside native scrollback; new turns now seal abandoned cards while preserving background-task updates.
- Fixed resize and display replays to include naturally emitted active-head rows in one atomic bottom-first transaction without rewinding lifecycle state, while graceful shutdown still drains every eligible final suffix.
- Fixed terminal resizes lagging on large transcripts: the transient resize repaint now renders only the visible tail instead of the entire committed transcript per resize event.
- Fixed cache-miss dividers crashing completed streamed assistant messages after stable rows had entered native history; cache-miss status now trails the assistant output.
- Fixed quitting re-streaming the entire committed transcript when a resize-triggered scrollback replay was still pending; shutdown now flushes only genuinely un-retired rows.
- Fixed fast tool completions leaving a permanent running summary that blocked transcript retirement and squeezed later tool output.
- Fixed `omp git` hunk navigation (`alt+↓`/`alt+↑`) appearing to do nothing while the file sidebar had focus: the diff cursor band now stays visible (dimmed) when the pane is unfocused.
- Fixed the git TUI sidebar jumping back to the top of the file list after staging or unstaging a file; selection now stays on the nearest remaining row
- Fixed the `aarch64-linux` `nix build` output segfaulting in the dynamic loader before startup by repointing the stale `DT_VERDEF` that `patchelf` leaves behind when it grows `.dynamic`, and surfaced smoke-test signal deaths in the build log instead of masking them ([#9881](https://github.com/can1357/oh-my-pi/issues/9881)).
- Added custom RPC launcher builders so embedded clients can transport omp RPC through SSH and remote process managers.

## [18.0.7] - 2026-08-26

### Added

- Git and Jujutsu operations now run in-process (gitoxide/jj-lib) instead of spawning `git`/`jj` subprocesses — faster status lines, diffs, staging, and worktree operations. The git binary is only used for credential-bound network transfers (push/fetch/clone) and reftable repositories.
- Status lines, footers, reviews, project identity, cleanse, and autoresearch reads now work in pure Jujutsu workspaces as well as Git checkouts.
- Include token usage statistics in inspect_image tool output
- Pressing the session model shortcut (alt+p) again inside the picker toggles a red Task mode that switches the Task subagent's model for this session instead.
- Git TUI: an AI staging wand next to "Stage All" asks "What should we stage?" and stages only the matching changes — the tiny/smol model picks the matching files from the whole change list, then filters their hunks in parallel; file-scoped requests ("git stuff") stage the picked files whole, content-scoped ones ("all comment changes") stage only the matching hunks.

### Changed

- Enforce a 5-minute timeout and 8 MiB output limit for GitHub CLI operations
- Apply a 30-minute timeout for marketplace plugin repository cloning
- Improve large file handling with blob streaming and explicit truncation support

### Fixed

- Fixed the VCS status line counting every file inside an untracked directory instead of collapsing it to one entry like `git status`.
- Fixed git TUI sidebar wheel scrolling snapping back to the selected row after staging or collapsing entries; the list now follows the selection only when it actually changes.
- Fixed `inspect_image` selecting a text-only vision/default role when an image-capable model was available on the active provider.
- Improved unexpected-stop recovery for reasoning-only stalls by requiring the next concrete tool action instead of repeated analysis.
- The edit tool now repairs a stray closing marker typed in place of the divider in a selection (`old⟫new` inside one selection instead of `old│new`) and applies the intended replacement with a note, instead of failing with an unmatched-marker error.

## [18.0.7] - 2026-08-26

### Added

- Added nonblocking shared model-catalog refresh with cached startup hydration and source freshness diagnostics, allowing newly published models for known providers to appear without a binary release.
- Added `omp usage clients` to report per-client token usage recorded by the auth broker, including the machine and application responsible for usage by provider. Supports `--days` and `--json` output.

### Changed

- Improved `omp git` responsiveness by streaming file contents, rendering complete lines promptly, progressively applying syntax highlighting, and deferring large commit statistics until after the first interactive frame.
- Expanded `omp git` navigation and editing shortcuts: refresh with `r`, stage or unstage files and directories with `s`, `u`, or `space`, navigate hunks and files with keyboard shortcuts, use Vim-style motions in both panes, select diff views with `1`–`4`, and open the commit form with `c`.
- Standardized completed edit results across edit modes with hashline-style paths and numbered previews.
- Documented browser relay behavior more clearly, including that `browser.relay` can enable relay access independently of `app.relay` and that a relayed session operates in the user's logged-in browser.
- Clarified the computer tool documentation: `desktop.window()` must be awaited, and `win.ax()` returns a textual accessibility-tree snapshot rather than a structured node list.

### Fixed

- Fixed hub process waits being incorrectly prolonged or satisfied by a replacement process after an automatic restart.
- Preserved an explicitly empty `tools: []` configuration for agent definitions instead of adding default work tools.
- Corrected MCP per-tool approval configuration documentation and behavior to use registered tool names for deny policies.
- Made `/branch` consistently open the branch-from-message selector regardless of the `doubleEscapeAction` setting.
- Improved ACP behavior when prompting during an active turn by returning a typed `session_busy` JSON-RPC error instead of an opaque internal error.
- Fixed `--model <id>:<effort>` losing its effort setting when cycling back to the `default` role; an explicit `--thinking` setting continues to take precedence.
- Fixed extension-registered Codex models configured with `preferWebsockets: false` from attempting a WebSocket connection.
- Fixed stale command-generated provider and model-override credentials after HTTP 401 responses by refreshing credentials before retrying.
- Fixed extensions configured in `.omp/config.yml` not exposing their bundled skills, hooks, tools, commands, rules, prompts, and MCP configuration for discovery.
- Fixed compiled extensions that could not import public coding-agent registry modules.
- Fixed extension-provided environment variables being lost in user shell commands and prevented environment changes from one hook from affecting later commands.
- Fixed imported and legacy sessions with missing usage metadata from dropping RPC lifecycle events.
- Fixed GitHub and GitHub Enterprise issue, pull-request, and tool lookups to preserve and use the repository's actual host.
- Fixed binary installation when GitHub returns minified release metadata.
- Fixed `omp bench` and `omp if-bench` resolving credential-scoped dynamic models already listed by `omp models`.
- Fixed checkpoint and rewind recovery in Codex Code Mode.
- Fixed truncated `ask` questions being displayed incorrectly when expanded with Ctrl+O.
- Fixed the welcome screen and transcript layout not adapting correctly after terminal resizes.
- Made `omp if-bench` retry transient Anthropic cyber-safety refusals before treating them as run-ending failures.
- Fixed streamed assistant responses when later provider updates revise earlier Markdown.
- Fixed abandoned foreground tool cards and fast tool completions from blocking transcript scrolling or later output.
- Improved transcript replay and shutdown behavior so terminal resizes and exits do not duplicate, lose, or unnecessarily re-render committed output.
- Fixed cache-miss status messages from disrupting completed streamed assistant responses.
- Fixed YAML rewrites for settings, migrated configuration, and keybindings from adding trailing spaces to nested mapping headers.
- Fixed `/model` role-cycle icons overlapping their ordinal on terminals with full-width icon rendering.
- Improved `/collab` QR-code fallbacks so the browser join URL remains visible when the code is clipped or cannot fit.
- Fixed hub and child peer listings from exposing parked agents as active model context, while restoring accurate running, idle, parked, shown, and truncated counts.
- Fixed browser relay clients hanging when enabling the Runtime domain on a tab shared with another client.
- Fixed browser relay sessions leaving Chrome's debugging infobar attached after the last client releases a tab.
- Fixed interactive TTSR interruptions being displayed as errors when the rule injection succeeded.
- Fixed cold interactive launches duplicating the welcome header in Windows console scrollback.
