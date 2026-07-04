# Changelog

## [Unreleased]

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
- Fixed grep/ast_grep search scopes rejecting `www.` and collapsed-scheme (`https:/host`) URL spellings.
- Fixed ctrl+p role-model cycling getting stuck on one transition and skipping every other role.
- Fixed interactive bash status line not updating after directory changes (cd).
- Fixed session title refreshes ignoring user `TITLE_SYSTEM.md` overrides during replans, and prevented auto-generated titles from incorrectly preserving all-caps text from user messages.
- Fixed the live todo HUD going stale during long tool-use loops by adding mid-run reminders for incomplete items.
- Fixed `/shake` and mid-stream chat rebuilds erasing active LLM output.
- Fixed Tavily web search to retry without recency filters if no content is returned.
- Fixed user-configured LiteLLM discovery providers keeping stale reseller display-name suffixes for up to 24 hours after upgrade by invalidating the warm model cache.

## [16.2.13] - 2026-07-01

### Fixed

- Fixed `models.yml` remote compaction schema support for V2 streaming endpoint fields. ([#4146](https://github.com/can1357/oh-my-pi/issues/4146))
- Fixed the SSH tool to reject `cwd` values of `~` and `~/...` before sending guaranteed-bad quoted tilde paths to remote POSIX shells. ([#4002](https://github.com/can1357/oh-my-pi/issues/4002))

## [16.2.12] - 2026-07-01

### Breaking Changes

- Removed the canonical-alias grouping and resolution layer. The `equivalence` key (`overrides`/`exclude`) in `models.yml`/`models.json` is now inert, and canonical-related methods have been removed from `ModelRegistry`.
- Removed the "CANONICAL" tab from the interactive model selector and the `omp models canonical` subcommand.

### Changed

- Simplified model selection and matching by resolving bare model IDs in `--model`, `modelRoles`, and `enabledModels` via exact/flat-ID and provider-preference matching instead of cross-spelling canonical coalescing.
- Improved cold start performance by removing the catalog-wide canonical index build from the startup path.

### Fixed

- Fixed the write tool not streaming execution progress to the TUI while files are being written.
- Fixed live tool-call argument previews disappearing while arguments stream.
- Fixed the LSP tool ignoring timeouts and abort signals during cold-starts and notification writes.
- Fixed the browser tool leaking Chromium/Puppeteer processes when operations are aborted or when an agent session is disposed.
- Added a configurable 30-second timeout (`extensionHandlerTimeoutMs`) to extension tool call handlers to prevent hung third-party extensions from blocking execution, and fixed a timer leak keeping the CLI alive.
- Fixed the built-in `fd` tool ignoring shell cancellation (such as Ctrl-C or timeouts) during directory walks.
- Fixed MCP stdio requests hanging indefinitely past their configured timeouts when the child subprocess stops draining stdin.
- Fixed Python eval shell helpers buffering child-process output by streaming chunks and truncating oversized output.
- Fixed cached model edit variants failing to update when changing project directories.
- Fixed subagents with structured output schemas failing validation by correctly wrapping the schema in the system prompt.
- Fixed MCP Streamable HTTP request and notification timeouts staying unarmed during stalled response body reads.
- Fixed evaluation and task spawn defaults to respect restricted agent spawn lists.
- Fixed timed-out `browser.run` calls leaving evaluated JavaScript continuations running.
- Fixed performance degradation in session context and branch path reconstruction on deep linear histories.
- Fixed agents repeating the same tool call across turns without corrective steering by wiring the cross-turn tool-call loop guard into sessions.
- Fixed OpenAI-compatible model discovery (including LM Studio) reporting flat default context windows when proxies omit context length metadata, by resolving discovered IDs against the bundled model reference catalog to inherit accurate context windows, output limits, display names, modalities, and reasoning support.

## [16.2.11] - 2026-07-01

### Fixed

- Fixed model-discovery requests (Ollama, Llama.cpp, LM Studio, OpenAI, LiteLLM, vLLM) failing to clear timeouts after completion, preventing potential memory and timer leaks.
- Fixed grep and ripgrep built-in tools ignoring shell abort and timeout signals during recursive directory walks, allowing them to be interrupted immediately.
- Fixed omp setup speech returning prematurely before Whisper STT downloads complete, and improved error reporting for worker download failures.
- Fixed high memory usage in multi-target ast_grep searches by only retaining the final page window while preserving exact match and file counts.
- Fixed async job manager disposal and task cancellation handling to properly release session semaphores when aborted.
- Updated and expanded omp:// documentation coverage for managed memory, skill tools, image/speech generation, and package CLIs.

## [16.2.10] - 2026-06-30

### Changed

- Updated grep warnings to clarify that large files are partially searched rather than entirely skipped
- Renamed the filesystem walker worker count environment variable from PI_GREP_WORKERS to PI_WALK_WORKERS
- Centralized filesystem traversal policy in `pi-walker`.
- Changed the in-session `/resume` session picker to open as a fullscreen window on the terminal's alternate screen, matching the startup `--resume` picker and `/settings`. It borrows the alt buffer for its lifetime (the transcript is untouched underneath) and enables mouse tracking — the wheel scrolls the list and a left click resumes the row under the pointer — with the keybinding hint and bottom border pinned to the screen bottom. Previously it mounted inline in the editor slot and rendered compactly without mouse support.

### Fixed

- Fixed Git subcommands ignoring repository paths by stripping ambient Git environment variables
- Fixed concurrent bash commands cross-killing each other on cancel/timeout. Cancellation cleanup previously walked the whole host process tree and signalled every descendant spawned since a per-run baseline, so cancelling or timing out one command could SIGTERM an unrelated command's child still running in parallel (it looked "new" relative to the canceller's baseline). Each run now tracks only the processes it actually spawned (via a brush-core spawn-observer hook) and scopes its TERM/KILL waves to that set, leaving concurrent runs untouched.
- Fixed `/skill:<name>` invocation losing the user's prompt context when the slash token was reached mid-prompt via the autocomplete. The slash-command parser now recognizes a `/skill:<name>` token surrounded by whitespace in non-slash, non-local-execution drafts (in addition to the leading form) and threads the surrounding prose through to the skill as `args`, so the typed prompt survives both in the editor (see the TUI changelog) and in the dispatched skill message. Drafts that already begin with another slash command (`/compact /skill:foo`), a bash sigil (`!echo /skill:foo`, `!!echo /skill:foo`), or a python sigil (`$ run.py /skill:foo`, `$$ run.py /skill:foo`) keep their existing dispatcher precedence and are not hijacked by the mid-prompt skill parser. Applies to the interactive TUI, ACP, and RPC dispatch paths via the shared `parseSkillInvocation` helper in `extensibility/skills` ([#3913](https://github.com/can1357/oh-my-pi/issues/3913)).
- Fixed the incomplete-todo reminder drifting to the bottom of the screen and piling up as dozens of duplicate copies in native scrollback. The reminder rendered in a dedicated anchored live-region container (`todoReminderContainer`) pinned above the editor, so it re-rendered in place every frame and — being taller than the viewport on short terminals while the subagent/job HUD churned below it — had its top rows committed to scrollback again on each reflow. It is now committed once into the transcript as a regular block (the same path TTSR notifications use), so it stays anchored in history where it fired.
- Fixed subagent frontmatter `thinkingLevel` being overridden by `modelRoles.task` model suffixes. ([#3915](https://github.com/can1357/oh-my-pi/issues/3915))
- Fixed Ruff LSP auto-detection for Windows Python virtualenvs by checking `.venv/Scripts`, `venv/Scripts`, and `.env/Scripts` before falling back to PATH. ([#3916](https://github.com/can1357/oh-my-pi/issues/3916))

## [16.2.9] - 2026-06-30

### Breaking Changes

- Renamed the built-in quick_task subagent to sonic; update any task spawns or configurations referencing quick_task by name.

### Added

- Added the llama3.2:3b local model option for memory and auto-thinking tasks, utilizing a quantized ONNX model.
- Added a built-in Tester subagent designed to write high-signal tests for behavior, invariants, and edge cases while avoiding redundant or low-value tests.
- Added a Speech-to-Text submit trigger setting to auto-submit dictation on release, on complete sentences, or via a spoken submit command.
- Added a loop-guard mechanism that detects thinking/response loops and injects a system notice during auto-retries to guide the model to break the pattern and take a concrete next step.

### Changed

- Renamed the Speech-to-Text (STT) setting label from "TTS Submit Trigger" to "Speech-to-Text Submit Trigger".

### Fixed

- Fixed an issue where mid-run compaction was incorrectly skipped when a persisted assistant display variant shared a persistence key but differed in content from the live message.
- Fixed duplicate placeholder cards being created when streamed tool blocks started with an empty ID.
- Fixed omp debug --profile failing on Bun by treating the optional --allow-natives-syntax flag as best-effort when v8.setFlagsFromString is unavailable.
- Fixed release binaries missing the compiled tiny-model Transformers.js version pin, preventing runtime resolution issues on certain platforms like Homebrew Darwin arm64.
- Fixed MCP OAuth flows silently falling back to a random redirect port when the preferred port (default 3000) was busy, which caused authentication failures with strict providers. The flow now fails fast with a configuration error when a static client ID is pinned, while dynamic registration flows continue to use fallback ports.
- Fixed /mcp reauth and /mcp add commands ignoring the Escape key during OAuth authentication, allowing users to cancel the flow immediately instead of waiting for the timeout.

### Removed

- Removed the built-in oracle subagent.

## [16.2.8] - 2026-06-30

### Added

- Added built-in Go coding rules including `go-add-cleanup`, `go-bench-loop`, `go-exp-promoted`, `go-ioutil`, `go-join-hostport`, `go-new-expr`, `go-rand-v2`, and `go-range-int`

### Changed

- Relaxed strict bash tool constraints regarding the use of search, grep, ls, and find commands

### Fixed

- Fixed auto-compaction dead-ends by automatically triggering a shake rescue to elide oversized tails
- Improved compaction warning message to suggest running `/shake images` for irreducible image tails
- Fixed `grep`/`search` direct execution to accept JSON-array string `paths` for string-or-array inputs. ([#3873](https://github.com/can1357/oh-my-pi/issues/3873))
- Fixed auto-compaction dead-ending with "Compaction freed too little context to make progress" when a single recent turn (large tool output, heavy fenced/XML block) is itself bigger than the recovery band — `findCutPoint` can't cut inside one message, so the summarizer had no lever left. The guard now runs an artifact-backed `shake` elide pass over the oversized tail and re-tests headroom before pausing, and the remaining warning points at `/shake images` for image-only tails it can't elide. ([#3786](https://github.com/can1357/oh-my-pi/issues/3786))
- Fixed reviewer/`task` subagents whose incremental `yield` (`type: ["overall_correctness"]`, `type: ["findings"]`, …) carried a value that mismatched the matching property's sub-schema being silently accepted and then post-mortem rejected with `schema_violation` — opaquely swapping the agent's accepted output for an error blob. The yield tool now validates each incremental section's `data` against its top-level property's sub-schema (items schema for array-typed labels) and surfaces the same retry feedback as terminal yields, so models like `deepseek-v4-pro` that emit `"Correct"`/`"correct."`/`"approved"` for an enum field get up to three corrective retries; the existing `MAX_SCHEMA_RETRIES` override then accepts the value with `SUBAGENT_WARNING_SCHEMA_OVERRIDDEN` instead of losing the entire result. Unknown labels stay unconstrained ([#3870](https://github.com/can1357/oh-my-pi/issues/3870)).
- Fixed streaming tool-call previews (notably `write`) showing an empty body for the entire streaming phase by surfacing the partial JSON already in hand on the first reveal, then pacing only subsequent growth ([#3881](https://github.com/can1357/oh-my-pi/issues/3881)).
- Fixed hashline edit mode preserving UTF-8 BOM bytes on edited files. ([#3867](https://github.com/can1357/oh-my-pi/issues/3867))
- Fixed slow local LLM streams by forwarding persisted stream timeout settings (`providers.streamFirstEventTimeoutSeconds`, `providers.streamIdleTimeoutSeconds`) into model requests, so users can widen or disable watchdogs without environment variables. ([#3878](https://github.com/can1357/oh-my-pi/issues/3878))
- Fixed the bash interceptor blocking `echo` / `printf` redirects to `/dev/null`, `/dev/tty`, `/dev/stdout`, and `/dev/stderr` device sinks while still directing real file writes to the write tool. ([#3763](https://github.com/can1357/oh-my-pi/issues/3763))
- Fixed long snapcompact sessions re-sending multi-megabyte standing image archives on every provider request by enforcing a per-request frame byte budget, letting auto-compaction fall back to context-full summaries when snapcompact output is too large, and omitting legacy over-budget frames from rebuilt LLM contexts. ([#3792](https://github.com/can1357/oh-my-pi/issues/3792))

## [16.2.7] - 2026-06-30

### Breaking Changes

- Replaced the global `serviceTier` and `fastModeScope` settings with granular, per-family settings (`tier.openai`, `tier.anthropic`, and `tier.google`) to control service tiers, subagents, advisors, and `/fast` mode targets.

### Changed

- Improved binary file detection and terminal handling to prevent corruption from non-UTF-8 content, and updated file summaries to explicitly note skipped binary files.
- Enhanced context compaction (snapcompact) to resolve shapes contextually based on rendered text content.

### Fixed

- Improved reliability of DuckDuckGo web searches by updating browser request headers and parameters
- Fixed an issue where CJK (Chinese, Japanese, Korean) history could become unrenderable during repeated context compactions.
- Fixed a memory exhaustion bug in the TUI when using `/resume` on large previous sessions.
- Fixed an issue where the `irc` inbox missed messages that arrived while the recipient agent was already running.
- Fixed a startup hang caused by system-prompt GPU detection blocking and repeatedly running failed probes.
- Improved error reporting for `omp tiny-models download` by displaying the actual worker-side download error.
- Resolved status inconsistencies between `/extensions`, `/mcp list`, and the dashboard, ensuring MCP server states, allowlists/denylists, and configuration files (like `mcp.json`) stay fully synchronized.
- Improved branch-mode task merges to preserve the agent's original commit history (messages and authors) and fixed a bug where merges were rejected due to unrelated dirty changes in the parent checkout.
- Fixed an issue where the `Working...` loader spinner would prematurely disappear or fail to re-arm after a subagent (`task`) tool completed or during transient overlays (such as auto-compaction or auto-retry).

## [16.2.6] - 2026-06-29

### Changed

- Optimized argument streaming performance by throttling JSON re-parsing for renderers that do not require raw input.

### Fixed

- Fixed memory leaks in the benchmark CLI by ensuring provider sessions are properly closed upon completion.
- Fixed TUI rendering lag and shimmer frame starvation during streamed tool-call argument previews.
- Fixed llama.cpp discovery mapping unlimited output limits (max_tokens = -1 / n_predict = -1) to the generic 32K cap instead of the actual discovered runtime context window.
- Fixed memory exhaustion on Ctrl+C flush for large resumed sessions with repeated compaction summaries, and improved fork session previews starting with developer or assistant turns.
- Fixed omp search applying web search provider filters before resolving its implicit provider chain.
- Fixed Gemini web search to support standard GEMINI_API_KEY developer API credentials for native Google Search grounding, in addition to Cloud Code Assist OAuth.
- Fixed the bash interceptor blocking echo and printf redirects to standard device sinks (such as /dev/null, /dev/tty, /dev/stdout, and /dev/stderr).
- Fixed session file size inflation in the edit tool by pruning extremely large oldText and newText snapshots (over 32 KB) from tool-result details, while preserving visible diffs, paths, lines, and diagnostic metadata.
- Fixed Windows MCP stdio launches for PATH-resolved npx.cmd shims by preserving the cmd.exe wrapper path to keep subprocess stdio attached.
- Fixed the DuckDuckGo web_search provider returning empty results for non-encyclopedic queries by switching from the Instant Answer API to parsing the HTML frontend, and added clear error handling for bot-challenge throttling.
- Fixed Windows --extension paths with spaces or \\?\ prefixes being truncated or incorrectly passed to Bun import/spawn APIs.
- Fixed /mcp reauth compatibility with Cloudflare by aligning OAuth prompt behavior with the reference MCP SDK and updating the client label to oh-my-pi.

## [16.2.5] - 2026-06-28

### Changed

- Status line now collapses a linked git worktree path to the project name with a worktree icon, leaving the git segment to show the branch once instead of repeating it in the path.

### Fixed

- Fixed Ollama and llama.cpp discovery overestimating local context windows by using model training metadata instead of the runtime `num_ctx` / `n_ctx`, which could let compaction retry prompts that llama.cpp rejects as over context. ([#3752](https://github.com/can1357/oh-my-pi/issues/3752))
- Fixed isolated subagent worktrees embedding long task ids and `merged` in the working path; isolation now uses compact hashed segments with an `m` mount dir. ([#3756](https://github.com/can1357/oh-my-pi/issues/3756))
- Fixed recoverable context-overflow compaction keeping the failed assistant error turn in visible session history after scheduling the retry. ([#3747](https://github.com/can1357/oh-my-pi/issues/3747))
- Fixed editing a file read from outside the workspace (e.g. `~/.claude/settings.json`) failing with "File not found": the read snapshot header now carries the full out-of-workspace path so the edit resolves it directly instead of against the working directory.
- Fixed subagents spawned with an output schema (`agent(..., schema=...)`, `task` with structured output) failing with `schema_violation: missing required fields` since the typed-yield rework: a `type: "result"` finalize carrying the full object was assembled as a section named `result`, nesting the payload one level deep. String-typed yields are now treated as terminal finalizers (their data is the complete result), only array-typed yields form accumulating sections, and a data-less finalize keeps accumulated sections instead of collapsing to the last assistant turn.
- Fixed the per-provider concurrency cap (e.g. `providers.ollama-cloud.maxConcurrency`) bracketing the whole subagent lifecycle, which deadlocked any spawn tree wider than the cap because parents held every slot while waiting for children queued on the same cap. The semaphore now wraps each provider HTTP request, so a parent's slot frees between turns and child subagents can acquire while their parent's tool calls are running. ([#3749](https://github.com/can1357/oh-my-pi/issues/3749))
- Fixed Ctrl+Q / Ctrl+Enter follow-up submissions sending the literal `[Paste #N]` marker instead of the expanded paste body ([#3737](https://github.com/can1357/oh-my-pi/issues/3737)).

## [16.2.4] - 2026-06-28

### Fixed

- Fixed todo-reminder HUD rendering outside durable chat history while preserving native collapsing and auto-clear behavior.
- Fixed goal-mode continuations losing track of persisted todo progress, ensuring autonomous goal turns reconcile stale in-progress items before moving to subsequent tasks.
- Fixed the /move <dir> command to correctly relocate the current session and its artifacts to the target directory, allowing /resume to work seamlessly from the new location.
- Fixed omp update leaving behind stale Bun install-cache directories for globally installed packages.
- Fixed a reconnection loop issue in /collab sessions caused by oversized entries (such as large tool outputs) by truncating replicated payloads that exceed 1 MB.
- Fixed autolearn and local memory writes mutating Anthropic prompt-cache prefixes mid-session, ensuring prompt injections remain session-stable.

## [16.2.3] - 2026-06-28

### Added

- Added support for multiple configurable advisors via WATCHDOG.yml/WATCHDOG.yaml files, allowing per-advisor models, tool subsets, and instructions.
- Added /advisor configure, a full-screen, mouse-driven TUI to easily manage the advisor roster, configure models, toggle tool permissions, and edit instructions.
- Added full unified edit diffs to advisor transcripts, allowing advisors to see changes directly without re-reading files.
- Added the statusLine.compactThinkingLevel setting to render the model segment's thinking level as a single leading glyph instead of a separate text suffix.
- Added support for tracking reasoning tokens in session and advisor statistics.
- Added Remote Compaction V2 streaming configuration settings (compaction.remoteStreamingV2Enabled and compaction.v2RetainedMessageBudget) to control token budgets and toggle V2 streaming for remote compaction.
- Added the edit.citationTags setting to emit model-facing hashline section headers as OpenAI citation markers with opaque source IDs, along with citation-marker unwrapping for hashline edit parsing, diff previews, and streaming matching.
- Added mutable session titles with automatic replan title refreshes and configurable idle recaps.
- Added support for incremental yield submissions with typed sections and final results for subagents.

### Changed

- Reduced session file size by removing redundant thinking signatures already present in payloads
- Advisors can now be granted any built-in agent tool (including edit, write, and bash), removing the previous read-only restriction.
- Improved the debug log and raw SSE stream viewers with a wider, bordered overlay, clearer status indicators, dynamic layouts, and mouse support for scrolling and interaction.
- Updated the idle recap feature to use an LLM-generated summary of where things stand (anchored by the live goal and active todo task) instead of a static status line.
- Refined interrupted thinking system instructions to encourage smoother continuation.

### Fixed

- Fixed array-typed output schema validation by correctly assembling incremental yields into lists.
- Fixed OpenAI/Codex compatibility by removing top-level schema combinators from tool parameters.
- Fixed validation errors for untyped final yields in strict-mode providers by allowing null types.
- Fixed Alt+M default-role model configuration being disabled by the current session's context size.
- Fixed MCP type: "sse" servers by adding the legacy HTTP+SSE endpoint handshake and streaming JSON-RPC response path.
- Fixed interrupted reasoning blocks being incorrectly stripped when they contained a valid signature.
- Fixed interrupted thinking being lost in LLM provider requests after user interrupts by properly stripping trailing reasoning blocks from assistant turns while preserving them in the UI and session history.
- Fixed the live todo HUD going stale during long tool-use loops by introducing a mid-run reconciliation reminder that prompts the agent to update incomplete items.
- Fixed resumed OpenAI and OpenAI-Codex sessions losing encrypted reasoning and native assistant turns during rehydration.
- Fixed the ask tool's custom answer editor dropping the original question and option list while typing.
- Fixed auto-snapcompact failing the session on local blockers (such as text-only active models, high non-ASCII transcripts, or context budget overflows) by gracefully downgrading automatic maintenance to context-full compaction.
- Fixed autoresearch's before_agent_start handler crashing when the system prompt was undefined.
- Fixed OMP exiting silently during startup when encountering standalone Codex hook scripts in ~/.codex/hooks/.
- Fixed unreachable keyboard shortcuts in HTML session exports by changing the "toggle thinking" and "toggle tools" shortcuts from Ctrl+T and Ctrl+O to bare T and O keys.
- Fixed user-invoked /skill: prompts reaching model providers as developer turns instead of user turns, including during compaction.
- Fixed reasoning streaming being locked off for OpenAI-compatible providers that stream reasoning content without advertising reasoning support in model metadata.
- Fixed /shake and other mid-stream chat rebuilds erasing live LLM output by preserving the in-flight streaming components and pending tools.
- Fixed the time_spent status-line segment ticking continuously during idle sessions by ensuring it only accumulates active agent execution windows and resets correctly across session switches.
- Fixed expanded pending SSH previews committing provisional rows to native scrollback before the final result render.
- Fixed ssh:// rejecting POSIX-capable remotes whose login-shell classification was ambiguous by verifying a working transfer shell directly and gating transfers on that capability.

### Removed

- Removed history URI support for reading agent transcripts

## [16.2.2] - 2026-06-27

### Added

- Added a new `tiny` model role for consolidated online task handling.
- Added a `textVerbosity` setting to control OpenAI and Codex response detail.

### Changed

- Simplified the status line subagent display by removing running state and hub hint indicators.
- Updated online title, memory, and classification tasks to prioritize the new `tiny` model role.

### Fixed

- Improved reliability of auto-retry logic for aborted requests by standardizing error classification across model adapters and ensuring stale session states are reset.
- Enhanced MCP authentication error detection, header-based server discovery, and 401/403 authorization failure detection during Smithery commands and HTTP RPCs.
- Fixed auto-generated session titles incorrectly preserving user all-caps text, ensuring proper sentence casing while still respecting intentional mixed-case identifiers.
- Fixed Tavily web search with recency filters to automatically retry without a time range if Tavily returns an empty HTTP 200 response.
- Fixed TUI thought stream stalling and `ui.loop-blocked` warnings during subagent-heavy runs by optimizing the mid-run compaction persistence check.
- Fixed marketplace-installed plugins incorrectly appearing in both the npm plugin list and the extension-package status provider.
- Fixed inconsistent OpenRouter prompt-cache hits on `/advisor` turns by ensuring advisor agents inherit the same provider-shaping options, hooks, and settings as the main agent.
- Fixed path-scoped TTSR (Targeted Tool Safety Rules) evaluation for `hashline` and `apply_patch` edit streams, ensuring rules are correctly applied to file paths parsed from section headers and envelope markers without leaking across file scopes.

## [16.2.1] - 2026-06-27

### Added

- Included project context files (AGENTS.md, etc.) in the advisor's system prompt to ensure adherence to user-defined project rules
- Added project context files (AGENTS.md and the like) to the advisor's system prompt, so the read-only reviewer judges against the user's standing project rules the same way the main agent does.

### Fixed

- Fixed live ACP `generate_image` updates resolving OMP-internal image blob refs before sending renderable image content to clients. ([#3623](https://github.com/can1357/oh-my-pi/issues/3623))
- Fixed Claude marketplace plugin `.mcp.json` MCP servers to expand environment variables in `url` and `headers` before connecting. ([#3621](https://github.com/can1357/oh-my-pi/issues/3621))

## [16.2.0] - 2026-06-27

### Breaking Changes

- Renamed the `search` tool to `grep` and the `find` tool to `glob`. Existing user settings are automatically migrated to the new configuration keys.

### Added

- Added `ssh://host/path` support to `read`, `search`, and `write` tools for single text files and directory listings on pre-configured POSIX SSH hosts.
- Added an interactive `/move` overlay with path autocompletion and directory creation prompts, starting a fresh session in the target directory while leaving the previous session resumable.
- Added support for file deletion and moving within file editing operations.
- Added `providers.maxInFlightRequests` setting to cap concurrent LLM requests per provider across local OMP processes.
- Added support for `discovery.type: litellm` in `models.yml` to automatically discover model metadata from LiteLLM gateways.
- Added `models.yml` configuration options `remoteCompaction` and `compactionModel` to run compaction on a separate model or opt into provider-native compaction.
- Added project, user, and plugin-level `dap.json` and `dap.yaml` support for defining or overriding debugger adapters used by the `debug` tool.
- Added TinyFish, DuckDuckGo, xAI, and Firecrawl web search providers.
- Added an Appearance setting for OSC 9;4 native terminal progress indicators during active agent turns and context maintenance.
- Added Loop Guard "Tool-Call Reminder" to automatically interrupt Gemini reasoning loops that generate excessive planning headers without acting.

### Changed

- Redesigned the persistent Todo HUD as a compact connector tree with fixed-budget stage previews
- Anchored status and HUD containers to prevent redundant UI elements in terminal scrollback
- Redesigned the persistent Todo HUD to render active stages as a connector tree, capping the number of displayed stages and tasks to keep the plan overview concise and stable.
- Anchored the status row container directly between the HUD and the editor to prevent redundant UI elements from piling up in terminal scrollback.
- Optimized edit tool UI: delete and single-file move operations now render as compact status rows
- Improved terminal output for file-level edits (delete/move) to display accurate paths and state
- Refined edit renderer to prevent misleading "No changes" messages in multi-file operations
- Changed the `inlineToolDescriptors` setting from a boolean to a three-way enum (`auto` | `on` | `off`), defaulting to `auto` to inline descriptors only for Gemini models.
- Added caching for successful document conversions (PDFs, Office documents, EPUBs) to avoid redundant conversions on repeated reads.
- Moved the `Working…` activity indicator below the sticky todo and subagent HUDs so it sits just above the editor instead of floating atop the todo panel.

### Fixed

- Fixed Z.AI web search to initialize the Streamable HTTP MCP session before calling `web_search_prime`, preserving the returned session ID for authenticated tool calls. ([#3619](https://github.com/can1357/oh-my-pi/issues/3619))
- Fixed terminal hangs on Ctrl+Z (SIGTSTP) after running bash tool calls, and insulated MCP stdio servers from terminal job-control signals.
- Fixed macOS `Cmd+V` silently dropping image-only clipboard pastes in supported terminals.
- Fixed an infinite loop in auto-compaction when a single recent turn exceeded the compaction threshold.
- Fixed an issue where the advisor could enter a spam loop of repeated blocker injections, polluting the transcript.
- Fixed Claude API and Anthropic classifier refusals polluting the replayed session context or persisting as assistant dialogue.
- Fixed MCP tool calls failing with strict-schema servers by stripping internal metadata fields at the MCP boundary.
- Fixed a terminal freeze/hang when a subagent abort was triggered.
- Fixed thinking blocks appearing in the UI when thinking level is "off" for providers that return them anyway.
- Fixed GitLab Duo Agent namespace/project discovery and authentication flow hangs.
- Hardened and improved `ssh://` protocol handling, including support for IPv6 brackets, percent-encoded hosts, port validation, and POSIX shell restrictions, while preventing unsupported tools from attempting SSH connections.
- Fixed TUI usage display fraction resolution and added expiry dates for banked Codex rate-limit resets to the `/usage` display.
- Fixed a rendering issue where long-running SSH commands left stale pending headers in terminal scrollback.
