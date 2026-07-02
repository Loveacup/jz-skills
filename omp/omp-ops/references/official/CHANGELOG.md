# Changelog

## [Unreleased]

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
- Fixed garbled casing in auto-generated session titles by reconciling title tokens against the user's original messages.
- Fixed IRC broadcasts rendering twice in the main agent's transcript.
- Improved the persistent Todo HUD styling and progress indicators to make it self-describing and visually distinct.
- Fixed browser screenshots reporting `0x0` dimensions when image headers expose real dimensions.
- Fixed `snapcompact` compaction silently falling back to LLM summaries when local preflight rejects the archive.
- Fixed `snapcompact` compaction silently falling back to an LLM summary when local preflight rejects the archive; manual and auto snapcompact now fail locally with the blocker instead of making provider calls. ([#3599](https://github.com/can1357/oh-my-pi/issues/3599))
- Fixed garbled casing in auto-generated session titles. `normalizeGeneratedTitle` (`packages/coding-agent/src/tiny/text.ts`) used to force Title Case via a `\b\p{Ll}` regex, capitalizing function words ("for" → "For") and amplifying stray model capitals ("dAemon" → "DAemon"). It now reconciles each title token against the user's own message: tokens typed verbatim are kept; proper nouns the user cased distinctively are restored when the model flattened them ("tinyvmm" → "TinyVMM"); lowercase words carrying a stray interior capital the user never wrote are flattened ("dAemon" → "daemon"); and model-cased PascalCase proper nouns ("GitHub", "OAuth") are left untouched. Restoration is limited to distinctively cased source tokens so a message that merely starts with "For" can't force a mid-title "for" to "For". Applies to both the local tiny-model and online pi/smol title paths.
- Fixed IRC broadcasts (`to: "all"`) rendering twice in the main agent's transcript. A subagent broadcast fans out one `bus.send` per live peer, and `listVisibleTo` always includes `Main`, so the main agent received the body once as its own `irc:incoming` card *and* once per other recipient as an `irc:relay` observation of the sibling legs (`Sender → Other`) — identical text shown N+1 times. `IrcTool.#executeSend` now sets `suppressRelay` on every broadcast leg when `Main` is among the targets (it already has the body via its direct incoming card), and `IrcBus.send` skips `#relayToMainUi` for suppressed legs. Direct sub→sub relays, direct messages to `Main`, and `Main`'s own outbound sends are unaffected.
- Fixed Claude API refusals polluting the replayed session context and causing later prompts to refuse again. ([#3592](https://github.com/can1357/oh-my-pi/issues/3592))
- Fixed browser screenshots reporting `0x0` dimensions when `Bun.Image` rejects an image whose PNG/JPEG header still exposes real dimensions. ([#3577](https://github.com/can1357/oh-my-pi/issues/3577))
- Fixed Anthropic classifier refusals being persisted as assistant dialogue after no fallback handled them; refusal stops are now displayed as errors but pruned from active and saved context before the next prompt. ([#3591](https://github.com/can1357/oh-my-pi/issues/3591))
- Fixed the `eval` `tool.*` bridge leaking the harness-internal `i` ("intent") field into MCP `tools/call` requests, so strict-schema servers (Linear, anything with `additionalProperties:false` / Zod `.strict()`) rejected every call with `-32602 unrecognized_keys: ["i"]` while the same call via the direct model tool-call path succeeded. `MCPTool.execute` / `DeferredMCPTool.execute` (`packages/coding-agent/src/mcp/tool-bridge.ts`) now strip `INTENT_FIELD` at the MCP boundary, so an MCP call behaves identically whether issued by the model directly or via the eval `tool.*` bridge; servers that legitimately declare `i` as a real parameter keep it untouched. ([#3575](https://github.com/can1357/oh-my-pi/issues/3575))
- Fixed the advisor entering a spam loop in which it emitted hundreds of repeated `Stop.`, `Done.`, and `No issue; continue.` `<advisory severity="blocker">` injections, polluting the primary transcript and destabilizing the watched agent after the task was already complete. The advisor system prompt's rules ("at most one `advise` per update", "NEVER send the same advice twice") are now enforced in code by a new `AdvisorEmissionGuard` on the `enqueueAdvice` boundary in `AgentSession`: it normalizes each note (case-insensitive, punctuation-folded), drops content-free self-talk filler (`stop`/`done`/`no issue continue`/`lgtm`/etc.), dedupes by exact normalized text across the session (bounded FIFO history), and rate-limits to one accepted note per advisor model prompt cycle. Reset on advisor reset (compaction, session switch, `/new`) so a re-primed reviewer can re-raise old issues. ([#3520](https://github.com/can1357/oh-my-pi/issues/3520))
- Fixed auto-compaction thrashing on a session whose single most-recent kept turn already exceeds the compaction threshold. `prepareCompaction` keeps that turn verbatim (`findCutPoint` never cuts at tool results), so the rewritten context stays above threshold; the context-full / snapcompact success tail scheduled the agent-authored auto-continue (and the overflow/incomplete retry) unconditionally, so the next `agent_end` re-entered `#checkCompaction` over the same oversized tail and re-fired forever. This is the residual loop left after #3247 capped snapcompact's own frame projection — once the frame cap drops below one frame, snapcompact is skipped and the context-full summarizer path still made no headroom. `#runAutoCompaction` now gates the threshold auto-continue on a post-maintenance headroom check (`#compactionCreatedHeadroom`, sharing shake's `COMPACTION_RECOVERY_BAND` hysteresis from #2275) and the overflow/incomplete retry on a separate fit check (`#compactionCreatedRetryFit`, measured after the failed turn is dropped) so a recoverable overflow that fits the window still retries; when a pass frees too little for the relevant path it pauses automatic maintenance and emits a single warning instead of looping. The post-turn threshold check also ignores an assistant's stale pre-compaction `usage` so the scheduled auto-continue cannot re-trip on the kept assistant's old high token count. The headroom check now treats any residual at or below the recovery band as progress: the band sits strictly under the compaction threshold, so a stale/tool-output prune that already pushed the trigger sub-band no longer makes a residual that merely holds the line report a false "no progress" and suppress a valid auto-continue.
- Fixed the advisor prompt allowing confident root-cause claims about tool-call arguments absent from its reviewed transcript, so timeout advice now has to cite observed fields instead of inventing mechanisms like `paths[0]` array flattening. ([#3483](https://github.com/can1357/oh-my-pi/issues/3483))
- Fixed eval `agent()` helper subagents remaining visible as idle/IRC-revivable peers after the helper call returns; one-shot eval subagents now dispose and unregister at completion. ([#3407](https://github.com/can1357/oh-my-pi/pull/3407))
- Fixed the parent interactive prompt wedging (frozen, 0% CPU) after a subagent's yield-triggered abort. The executor's abort monitor and abort listener each called `session.abort()` fire-and-forget, so `runSubprocess` could resolve and adopt the subagent before its abort cleanup finished clearing in-flight session state. Active-subagent aborts are now deduped through a single cached cleanup promise that the subprocess awaits (bounded) before finalizing. ([#2805](https://github.com/can1357/oh-my-pi/issues/2805))
- Fixed thinking blocks appearing in the UI when thinking level is "off". Some providers (MiniMax, GLM, DeepSeek) return thinking blocks even with reasoning disabled; thinking blocks are now auto-hidden when the thinking level is "off", regardless of the `hideThinkingBlock` setting. Toggling thinking block visibility while thinking is off shows a status message instead of silently no-op'ing. ([#626](https://github.com/can1357/oh-my-pi/issues/626))
- Fixed the TUI usage display failing to resolve a used fraction for limits that only populate `remainingFraction` (no `usedFraction`, `used`/`limit`, or `percent`+`used`). The TUI's local `resolveFraction` was missing the inverted-remaining fallback that the shared `resolveUsedFraction` from `@oh-my-pi/pi-ai` already handles — replaced the local copy with the shared function so the TUI and CLI paths resolve fractions identically.
- Fixed long-running SSH command boxes leaving a stale `⏳ SSH: [host]` header above the final `⇄ SSH: [host]` header in terminal scrollback. The SSH renderer now keeps its partial-result chrome on the pending icon/state and opts the block out of stream-commit while `isPartial` holds (via the new `ToolRenderer.provisionalPartialResult` flag honored by `ToolExecutionComponent.isTranscriptBlockCommitStable`), so the stable-prefix ratchet can't promote the partial header to native scrollback only to have the final render strand it above the settled frame ([#3177](https://github.com/can1357/oh-my-pi/issues/3177)).
- Fixed Gemini over-planning runs that emit long chains of thinking headers (`**Refining …**`, `## Examining …`) without ever issuing a tool call. The session now interrupts that stream, discards the partial reasoning turn, injects a hidden tool-call reminder, and continues with the corrective context instead of burning the full budget on planning.
- Fixed `Cmd+V` on macOS silently dropping image-only clipboard pastes (screenshot via `Cmd+Shift+5` "save to clipboard", Chrome image copy, …) — the user had to fall back to `Ctrl+V`. Follow-up to #3506: that fix handled clipboards exposing a file URL or path; the screenshot path leaves only raw image bytes on the pasteboard. macOS terminals (iTerm2, Terminal.app, Warp, Ghostty without OSC 5522, Windows Terminal forwarding, …) intercept `Cmd+V` and read `NSPasteboardTypeString` first; for an image-only clipboard that read returns `""`, so the terminal forwards a complete-but-empty bracketed paste (`\x1b[200~\x1b[201~`). `CustomEditor.handleInput` inserted the empty payload and the keystroke disappeared. `CustomEditor` now runs its own `BracketedPasteHandler` ahead of the inherited handler so the assembled paste payload is routed regardless of whether the start marker, payload, and end marker arrive in one stdin chunk or are fragmented across several (Windows Terminal under load, certain SSH muxes, tmux extended-keys passthrough, …). Strict-zero-length assembled payloads route to the same `onPasteImage` smart reader the `app.clipboard.pasteImage` keybind uses (attaches the clipboard image, or falls back to the #1628 smart text paste / "clipboard is empty" diagnostic); explicit image-file paths route to `onPasteImagePath` (the #3506 path also benefits from split-chunk assembly); everything else hands off to the base editor's `pasteText` so `[Paste #N]` markers, autocomplete, and undo state stay intact. Whitespace-only pastes are preserved as literal text. Trailing keystrokes that arrive in the same stdin read as the paste (a user hitting `Enter` right after `Cmd+V`) are queued behind the in-flight clipboard read and only dispatched once the image has reached `pendingImages`, so submit can't fire against an empty draft and leave the image stranded on the next prompt. ([#3601](https://github.com/can1357/oh-my-pi/issues/3601))

## [16.1.23] - 2026-06-26

### Added

- Added `compaction.midTurnEnabled` for mid-turn threshold auto-compaction before the next tool-loop provider request. ([#3525](https://github.com/can1357/oh-my-pi/issues/3525))
- Added `grep -q`/`--quiet`/`--silent` and `-x`/`--line-regexp` to the in-process `grep` builtin used by the bash tool. `-q` suppresses all stdout and exits 0 on the first match (short-circuiting, with match status taking precedence over read errors per GNU); `-x` anchors each pattern to whole lines. Unblocks shell conditionals such as `grep -qx "$applet" <(strings bin)`.
- Added plan-mode guidance (hashline edit mode only) steering the agent to revise the plan file section-by-section with `SWAP.BLK`/`DEL.BLK`/`INS.BLK.POST` anchored on markdown headings — a heading resolves its whole section (through nested deeper headings), so the agent can rewrite, drop, or append sections without rewriting the file.
- Added `tui.renderMermaid` to control Mermaid fenced-block ASCII rendering; disabling it also removes the Mermaid diagram hint from the generated system prompt so Mermaid blocks fall back to ordinary highlighted code fences.
- Added `/resume <session-id>` in the interactive command system, reusing the existing session-id/prefix resolver while bare `/resume` still opens the selector.
- Added manual `omp gc` storage maintenance with `gc.*` defaults for blob sweeping, cold-session archiving, and SQLite WAL checkpointing.

### Fixed

- Fixed `/resume <session-id>` in the interactive TUI only searching the active cwd's session directory; id-prefix lookup now falls back to sessions from other cwd buckets like CLI `--resume <session-id>`.
- Fixed plan mode rejecting edits to plan artifacts when models refer to them by bare filenames
- Fixed absolute paths to session-owned artifacts being incorrectly routed through the editor bridge
- Fixed Windows stdio MCP wrapper chains spawning visible PowerShell/cmd windows on startup after the #3544 fix. `StdioTransport.connect()` now probes whether OMP already has an inheritable console and `resolveStdioSpawnCommand` skips `windowsHide`/`CREATE_NO_WINDOW` in that case, so `cmd.exe`/PowerShell grandchildren reuse the terminal console instead of allocating visible conhosts during MCP startup or reconnects. ([#3567](https://github.com/can1357/oh-my-pi/issues/3567))
- Fixed Kimi-family models defaulting to hashline edit mode; they now fall back to `replace` unless `edit.modelVariants`, `PI_EDIT_VARIANT`, or `PI_STRICT_EDIT_MODE` explicitly opts into hashline.
- Fixed MCP OAuth discovery rejecting Atlassian-style cross-host issuer metadata during the resource-server fallback probe; issuer matching now remains enforced for advertised auth-server candidates but no longer blocks fallback metadata where the resource host and authorization-server issuer differ. ([#3551](https://github.com/can1357/oh-my-pi/issues/3551))
- Fixed plan approval applying the wrong execution model when the model-tier slider sat on the model that exit would restore. The match check now compares the selected role's effective thinking level against the pre-plan thinking level, so picking the active planning tier is retained and picking a same-model tier with an explicit thinking suffix (e.g. `default = sonnet:off` while plan-mode raised thinking to `high`) goes through `applyRoleModel` instead of silently restoring the pre-plan level. ([#3554](https://github.com/can1357/oh-my-pi/issues/3554))
- Fixed plan approval applying the wrong execution model when the model-tier slider sat on the model that exit would restore. The match check now compares the selected role's effective thinking level against the pre-plan thinking level, and a singleton cycle (only `modelRoles.plan` configured, default unset, so `getRoleModelCycle` synthesizes a lone `default` entry from the active plan model and the slider stays hidden) is no longer pinned as the execution tier — approval falls through to the pre-plan restore instead of silently switching back to the plan model. ([#3554](https://github.com/can1357/oh-my-pi/issues/3554))
- Fixed the `eval` Julia kernel showing only runner-internal backtrace frames (`at top-level scope (./none:N)`, `at main (…runner-…jl:635)`) with no exception type or message, making cell errors undebuggable. The host renderer (`packages/coding-agent/src/eval/kernel-base.ts`) displays a non-empty `traceback` verbatim and only falls back to `ename: evalue` when it is empty; the Python and Ruby runners embed the rendered error in `traceback`, but the Julia runner (`packages/coding-agent/src/eval/jl/runner.jl`) built `traceback` from stack frames only, so the message was dropped. `emit_error` now seeds `traceback` with the `showerror` output (matching the REPL's `ERROR:` text) ahead of the frames.
- Fixed Windows stdio MCP servers timing out (and popping a visible terminal) when their direct child was a `cmd.exe` wrapper that itself launched a console grandchild — `node` wrappers, `npx.cmd -y mcp-remote`, similar nested shells. `StdioTransport.connect()` unconditionally passed `detached: true` to `Bun.spawn`, but Windows has no SIGTSTP/SIGTTIN to escape; `detached` only maps to `CreateProcess(DETACHED_PROCESS)`, which strips the parent's inherited console. The hidden direct `cmd.exe` lost its console, so the grandchild allocated a brand-new visible conhost whose stdout no longer routed through OMP's pipe — the proxy reported the bridge was up while OMP timed out waiting for the MCP `initialize` response. `resolveStdioSpawnCommand` now returns `detached: false` for every Windows return shape (direct `.exe`, cmd.exe-wrapped batch / unresolvable command, npm cmd-shim launched through node) and keeps `detached: true` on POSIX, where the original SIGTSTP/SIGTTIN reason still holds; `connect()` consumes the resolved flag. ([#3544](https://github.com/can1357/oh-my-pi/issues/3544))
- Fixed the LSP tool's per-cwd config cache (`getConfig` in `packages/coding-agent/src/lsp/index.ts`) never being invalidated, so `.omp/lsp.json`, root markers, and plugin LSP configs added after the first LSP call stayed invisible for the remainder of the process — even after `reload *`. The cached observation persists across chat sessions because OMP is a single-process binary, so users were stuck on `No language servers configured` until they killed the process. The `reload` handler now drops the cwd's cache entry and re-runs `loadConfig` before iterating servers, so the explicit refresh request behaves as the prompt documents. ([#3546](https://github.com/can1357/oh-my-pi/issues/3546))
- Fixed stale snapcompact archive state being reintroduced at the AgentSession manual and auto LLM compaction save paths; `preserveData.snapcompact` is now stripped after hook- and result-supplied preserve data are merged, so a prior snapcompact pass can no longer leak frames into a later context-full compaction. ([#3561](https://github.com/can1357/oh-my-pi/pull/3561) by [@serverinspector](https://github.com/serverinspector))
- Fixed the snapcompact→context-full migration shipping the prior archive's plaintext to the summarization provider without secret redaction. When secrets are configured, the migrated archive's `text`/`textHead`/`textTail` regions are now obfuscated alongside the previous summary, while opaque provider-replay state (OpenAI remote-compaction `encrypted_content`) stays byte-identical. ([#3561](https://github.com/can1357/oh-my-pi/pull/3561))
- Fixed fresh interactive launches ignoring `modelRoles.default` when the configured default lives on an extension-registered provider (e.g. an openai-compat plugin's `posthog/claude-opus-4-8`). `createAgentSession` resolved the default role before extension factories registered their providers, so the role-pointed model wasn't visible there; on a fresh launch (no `-c`/`--resume`) the post-extension fallback then went straight to `pickDefaultAvailableModel`, replacing the user's configured default with the first bundled provider default with auth (commonly `openai/gpt-5.5` when `OPENAI_API_KEY` was set). The fallback now retries the default-role lookup against the post-extension allowed-model set — including its explicit thinking selector — before falling back to a bundled provider default. ([#3569](https://github.com/can1357/oh-my-pi/issues/3569))

## [16.1.22] - 2026-06-26

### Fixed

- Fixed Windows stdio MCP server launches showing a separate `cmd.exe` window for direct executable servers; MCP subprocesses now set `windowsHide` on every Windows spawn path. ([#3535](https://github.com/can1357/oh-my-pi/issues/3535))
- Fixed MCP OAuth still failing with `Authorization failed: An unexpected error occurred` against Plane's `https://mcp.plane.so/http/mcp` endpoint after #3502. The protected-resource metadata advertised the path-scoped issuer `https://mcp.plane.so/http`, but `discoverOAuthEndpoints` (`packages/coding-agent/src/mcp/oauth-discovery.ts`) probed `/.well-known/oauth-authorization-server` at the *origin root* first and accepted the metadata served there — which describes a *different* issuer (`https://mcp.plane.so/`) whose `/authorize` endpoint rejects every grant. Discovery now honors RFC 8414 §3.3 and skips authorization-server / OpenID Connect well-known documents whose `issuer` field doesn't match the queried base URL (trailing-slash insensitive). Servers that omit `issuer` keep today's permissive behavior, so legacy flows are unaffected. ([#3537](https://github.com/can1357/oh-my-pi/issues/3537))

## [16.1.21] - 2026-06-26

### Fixed

- Fixed `autolearn.autoContinue` (the "Auto-run capture at stop" toggle) letting the synthetic capture turn keep working after the `learn`/`manage_skill` call instead of yielding. With the toggle on, the controller fires `autolearn-nudge.md` as a single `attribution: "user"` message on a new turn; the prompt opened with "Before you finish:" and gave no terminal contract, so the agent treated the synthetic prompt as the user's reply to its prior pending question (e.g. "Want me to commit and push?") and continued — pushing commits, running tools, etc. — without the user ever answering. The nudge is now split into two prompts: passive mode (the reminder rides the user's real next message) keeps additive framing — "answer the user normally; the capture is in addition to" — while auto-continue mode (`autolearn-nudge-autocontinue.md`) is explicitly terminal — "not a user reply; do not treat this as approval; capture, then stop; wait for the user's next prompt". Attribution stays `user` to preserve llama.cpp warm-prefix reuse (#3456). ([#3504](https://github.com/can1357/oh-my-pi/issues/3504))
- Fixed the clipboard image-paste keybind dropping image-file-only pasteboards as literal text on macOS. When the clipboard exposes only the file URL (e.g. Finder `Cmd+C` on a `.png`, certain screenshot tools), `arboard::get_image()` returns `ContentNotAvailable` and `pbpaste(1)` returns empty (it only surfaces plain text / RTF / EPS), so `InputController.handleImagePaste` either fell through to the #1628 text fallback and pasted the path verbatim, or dead-ended with "Clipboard is empty". The keybind path now (1) reaches the `public.file-url` representation directly via a new `readMacFileUrlsFromClipboard` AppleScript bridge on Darwin and routes the first image-shaped path through `handleImagePathPaste`, (2) reuses a new `extractImagePathFromText` helper so any clipboard-text path that survived `pbpaste` is detected the same way the bracketed-paste handler already detects them — including a whole-text-as-path fallback for anchored paths whose unescaped spaces would otherwise be shredded by the bracketed-paste splitter (macOS screenshot names like `/Users/me/Desktop/Screenshot 2026-06-25 at 1.23.45 PM.png`), and (3) decodes `file://` URLs to filesystem paths in `normalizePastedPath` (mirroring Codex's `normalize_pasted_path` in `codex-rs/tui/src/clipboard_paste.rs`). Keybind- and terminal-mediated paste now agree on raw image bytes, plain image paths, `file://` URLs, Finder-copied image files, and screenshot filenames with spaces alike. ([#3506](https://github.com/can1357/oh-my-pi/issues/3506))
- Fixed compiled-binary validation for legacy `pi.extensions` packages whose source imports worker-only coding-agent subpaths or extension-local package subpaths such as `typebox/value`; `omp install @charmland/pi-hyper-provider`, `omp plugin doctor`, and runtime provider discovery now use a main-thread-safe load path. ([#3508](https://github.com/can1357/oh-my-pi/issues/3508))
- Fixed repeated todo updates in one TUI turn stacking full todo panels; superseded todo snapshots now stay live until the next todo update replaces them or the turn ends. ([#3516](https://github.com/can1357/oh-my-pi/issues/3516))
- Fixed MCP OAuth authorization failing with `Authorization failed: An unexpected error occurred` against authorization servers (Plane is the live example) that reject redundant fallback `resource` indicators. OMP now drops same-origin resources only when it synthesized them from the server URL fallback (e.g. `https://mcp.plane.so/http/mcp`). Provider-advertised resources from OAuth/protected-resource discovery or an embedded authorization-URL `resource` query parameter are preserved even when they are same-origin or origin-only, so gateway-hosted MCP services can still request the audience they advertised. The refresh-token path uses the same policy, filtered against the authorization-server origin persisted on the credential as `authorizationUrl`, with `tokenUrl`'s origin as the legacy fallback when that field is absent. ([#3502](https://github.com/can1357/oh-my-pi/issues/3502))

## [16.1.20] - 2026-06-25

### Fixed

- Fixed Ctrl+Z hanging the terminal after any tool call had run: the TUI tore down (`ui.stop()`) but the process kept running in `Sl+` state, leaving the user with a dead terminal recoverable only via `kill -9`. The embedded `brush-core` shell behind every bash tool call installs a tokio SIGTSTP listener on `Process::wait` (`crates/brush-core-vendored/src/sys/unix/signal.rs::tstp_signal_listener` → `tokio::signal::unix::signal(SIGTSTP)`); per tokio's contract, the first call for a SignalKind permanently replaces the kernel-default handler for the lifetime of the process. So the first bash invocation — even `/usr/bin/true` — silently overrode SIGTSTP's "stop" default, and `InputController.handleCtrlZ`'s subsequent `process.kill(0, "SIGTSTP")` was swallowed by tokio. The handler now sends `SIGSTOP` (uncatchable, unblockable, unignorable) to the foreground process group, so the kernel parks omp regardless of installed handlers and the shell sees the whole job stop even when omp runs behind a wrapper (`npx`, `pnpm exec`, `bunx`, …) or as one stage of a pipeline. MCP stdio servers now spawn detached into their own session — they're insulated both from terminal job-control signals (which used to stop their process trees and leave the JSONL read loop blocked on silent pipes) and from the new pgid=0 suspend itself ([#3461](https://github.com/can1357/oh-my-pi/issues/3461)).
- Fixed image-only composer submissions while the agent is streaming being treated as empty input, which dropped the image or aborted the active turn when another message was queued. Pending pasted images now count as submit content for Enter and Ctrl+Enter follow-ups. ([#3467](https://github.com/can1357/oh-my-pi/issues/3467))
- Fixed `omp gallery --state` accepting lifecycle tokens that did not match displayed state labels and rendering unknown state values as `· undefined`; displayed labels now work as aliases, invalid values fail with a valid-token list, and failed gallery fixtures visibly render failures. ([#3473](https://github.com/can1357/oh-my-pi/issues/3473))
- Fixed the bash tool's snapshotted `mise()` shell function dying with `command: command not found:` because `$__MISE_EXE` was empty in the replay shell. `generateSnapshotScript` captured the function via `declare -f`/`typeset -f` but only ever re-exported `PATH`, so every other env var the rc file set (notably the `*_EXE` sidecar `mise activate` exports) was lost; the function body then expanded `command "$__MISE_EXE" "$@"` to `command "" …` and died with exit 127. The snapshot script now scans captured function bodies for `$VAR` / `${VAR…}` references and re-emits `export NAME='value'` for each referenced var that is currently set (with a denylist for shell-internal names like `PATH`/`HOME`/`BASH_*`/`LC_*` plus a likely-secret denylist for `*TOKEN*`/`*SECRET*`/`*API_KEY*`/`*PASSWORD*`/`*PRIVATE_KEY*`/`*ACCESS_KEY*`/`*CREDENTIAL*`/`*SESSION_KEY*`), the snapshot script `umask 077`s itself and the JS caller chmods the snapshot file/dir to `0600`/`0700` so the new export pass can't leak secrets into a shared tmp dir. Fixes mise, asdf shims, direnv-style helpers, and other activation idioms that pair a function with a helper env var. `getShellConfigFile` now also honours `env.HOME` (falling back to `os.homedir()`) so sandboxed callers can target a non-default rc. ([#3470](https://github.com/can1357/oh-my-pi/issues/3470))
- Fixed concise `history://` transcript rendering for `find` and `search` so scoped `paths` arguments are visible instead of being hidden behind JSON fallback output or omitted when a search `pattern` is present. ([#3482](https://github.com/can1357/oh-my-pi/issues/3482))
- Fixed manual `/compact` leaving `session.isCompacting` false while active-turn abort teardown awaited, so the first steer/follow-up typed during compaction startup now routes through the compaction queue instead of being lost. ([#3485](https://github.com/can1357/oh-my-pi/issues/3485))
- Fixed ollama-cloud task/subagent fan-out exceeding the provider's three-request concurrency cap by adding a provider-specific subagent limiter, and let configured task/smol/advisor model roles inherit the default retry fallback chain when they do not define their own chain. ([#3464](https://github.com/can1357/oh-my-pi/issues/3464))
- Fixed the per-provider subagent concurrency limiter (e.g. `providers.ollama-cloud.maxConcurrency`) being replaced with a fresh semaphore whenever the configured limit changed, which orphaned the in-flight slots on the old instance and let a runtime or mixed limit value exceed the cap. The limiter now resizes a single shared semaphore in place — raising the ceiling admits queued waiters immediately, lowering it drains in-flight holders without admitting past the new cap. ([#3464](https://github.com/can1357/oh-my-pi/issues/3464))
- Fixed a background-task spawn slot leaking from the `task.maxConcurrency` limiter when progress reporting threw between acquiring the slot and entering the guarded run: `markRunning`/`reportProgress` now run inside the try whose `finally` releases the semaphore, so a failed progress report can no longer permanently shrink subagent concurrency. ([#3464](https://github.com/can1357/oh-my-pi/issues/3464))
- Fixed active goal runs that successfully call `yield` and then receive a trailing empty assistant `stop` skipping threshold compaction; post-yield empty-stop suppression now still anchors active-goal compaction on the yield-bearing assistant turn, so long-running tasks continue after maintenance instead of settling early.

## [16.1.19] - 2026-06-25

### Fixed

- Fixed `omp install <plugin>` failing extension validation in compiled-binary mode with `Cannot find module '@(scope)/pi-ai/oauth' from '<plugin>/src/oauth.ts'` (and any other non-wildcard pi-* subpath import like `@oh-my-pi/pi-coding-agent/tools`). The bundled-registry override map seeded by `__buildLegacyPiPackageRootOverrides` only covered the bare package roots, so `rewriteLegacyPiImports` rewrote `@(scope)/pi-ai/oauth` to `@oh-my-pi/pi-ai/oauth`, fell through to `Bun.resolveSync` (which bunfs can't satisfy on Bun 1.3.14+), then left the original specifier alone — at which point Bun's native resolver failed because most plugins declare `@(scope)/pi-ai` as a `peerDependency` only and never materialize a real install. The new `scripts/generate-legacy-pi-bundled-registry.ts` reads every bundled pi-* package's non-wildcard `exports` field and emits both the heavy `legacy-pi-bundled-registry.ts` (static imports + map) and a light `legacy-pi-bundled-keys.ts` (statically imported by `legacy-pi-compat.ts` to seed the override map without the cascade through `legacy-pi-coding-agent-shim → ../index → export/html/...`). `scripts/build-binary.ts` now runs the generator before `bun build --compile`. ([#3442](https://github.com/can1357/oh-my-pi/issues/3442))
- Fixed `skill://` tool resolution losing loaded session skills when a tool runs outside the session-initialization module state. Internal URL resolution now prefers the caller's `session.skills` snapshot before falling back to the process-global skill list, so `read skill://<name>` works across tool execution boundaries. ([#3436](https://github.com/can1357/oh-my-pi/issues/3436))
- Fixed `@image` mentions on OpenAI Codex Responses (chatgpt.com `gpt-5.5` and siblings) failing with `Codex error event: [OneOfParam] [input[N].content[…]] [invalid_enum_value] Invalid value: 'input_image'. Supported values are: 'input_text'.`. `convertToLlm` for `fileMention` always emitted a `developer`-role message, so the auto-attached image landed in a Responses content array that the Codex backend (and OpenAI Responses generally) only allows to carry `input_text`. #3421's previous fix only stopped the Codex Responses Lite header from going out on image-bearing turns; the full transport kept rejecting the same payload. `convertToLlm` now splits a mixed-content `fileMention` into two messages — text-only files stay on `developer` (so the auto-read context keeps instruction priority), while image-bearing files ride on `user` (the only Responses content slot that accepts `input_image`). ([#3443](https://github.com/can1357/oh-my-pi/issues/3443))
- Fixed `local://` binary attachments being decoded with `Bun.file().text()` before read-tool file safeguards could reject or stream them. `read local://...` now routes file-backed resources through the normal filesystem reader, the protocol handler refuses known binary/container resources without materializing their bytes, and the streaming reader's NUL-byte refusal now also covers binary blobs whose first newline lies beyond the byte budget (videos, archives) — those previously bypassed the per-line scan and surfaced as decoded mojibake. ([#3448](https://github.com/can1357/oh-my-pi/issues/3448))

## [16.1.18] - 2026-06-25

### Added

- Added --list flag to view stored OAuth accounts for a provider
- Added --account flag to select a specific OAuth account by index for token retrieval
- Added mouse support for navigation, selection, and toggling in the extensions dashboard

### Changed

- Enabled fullscreen alternate-screen mode for the extensions dashboard
- Improved tab navigation to mute empty enabled providers while keeping disabled ones selectable
- `/extensions` (the Extension Control Center) now opens as a fullscreen window on the terminal's alternate screen, matching `/settings`: it borrows the alt buffer for its lifetime (the transcript is untouched underneath) and uses the same modern chrome — a titled rounded frame, the shared `TabBar` for provider switching, and a divider/footer layout. The dashboard is now mouse-aware: the wheel scrolls the list (and the detail inspector, which gained its own scroll viewport), hovering highlights tabs and rows, and clicking selects a row or — when it is already selected — toggles it; clicking a provider tab switches to it. Empty enabled providers are unselectable while disabled providers stay selectable so their master switch can re-enable them.

### Fixed

- Fixed `omp install` of legacy pi extensions failing with `Cannot find module '/$bunfs/root/packages/coding-agent/src/extensibility/typebox.js'` on every released `omp-<platform>-<arch>` binary. Commit `dc5c93462f` removed worker entrypoints from `scripts/ci-release-build-binaries.ts`; the inline comment then claimed the legacy-shim and package-barrel entrypoints (`typebox.ts`, `legacy-pi-{ai,coding-agent}-shim.ts`, `packages/{agent,natives,tui,utils}/...`) were "still" passed to `bun build --compile`, but they had never been re-added. The release binaries shipped without those files in bunfs, so `legacy-pi-compat.ts` redirected `typebox` imports to a bunfs path that didn't exist. `__resolveTypeBoxShimPath` now mirrors `__validateLegacyPiPackageRootOverrides` (#2168) by dropping the override when the shim file is missing, so a missing shim falls through to native `node_modules` resolution instead of emitting a dead bunfs URL ([#3414](https://github.com/can1357/oh-my-pi/issues/3414)).
- Fixed every legacy `@(scope)/pi-*` and `@sinclair/typebox` import failing to load on the `omp-darwin-arm64` release binary (and any other `omp` built with Bun 1.3.14). `__validateLegacyPiPackageRootOverrides` and the `rewriteLegacyPiImports` emit path both depended on `--compile` extras being reachable as `/$bunfs/root/...` filesystem entries, but Bun 1.3.14 stopped exposing them through every API (`fs.existsSync`, `Bun.file().exists()`, `Bun.resolveSync`, `await import()` on the bunfs path or its `file://` URL all fail; only `/$bunfs/root/<binary-name>` itself answers). `legacy-pi-compat.ts` now keeps a JS-heap reference to every bundled pi-* surface in a lazy-loaded sibling `legacy-pi-bundled-registry.ts` and serves them through an `omp-legacy-pi-bundled:` virtual namespace whose `Bun.plugin().onLoad` returns synthetic re-exports — no bunfs path ever leaves the module in compiled mode, and dev / source-link / installed-package modes keep the historical `file://` rewrite. The matching `--compile` extras in `scripts/build-binary.ts`, the shared `scripts/binary-entrypoints.ts` list, and the dead `BUNFS_PACKAGE_ROOT` / `bunfsPath` / `__computeBunfsPackageRoot` / `__joinBunfsPath` helpers are gone. ([#3423](https://github.com/can1357/oh-my-pi/issues/3423))

## [16.1.17] - 2026-06-24

### Fixed

- Fixed mnemopi auto-retain extracting facts/entities from assistant-authored transcript turns. `MnemopiSessionState.retainMessages` still stores the full multi-role window for episodic recall, but passes only user-authored turns as `extractText`, so assistant prose containing `always`/`never` no longer becomes durable user `Instruction:` memory. ([#3372](https://github.com/can1357/oh-my-pi/issues/3372))
- Fixed lazy tool auto-downloads hanging when `Bun.write(dest, response)` receives a streaming `fetch()` `Response`; tool assets now stream the response body to disk with the existing download abort signal and remove partial files on abort. ([#3369](https://github.com/can1357/oh-my-pi/issues/3369))
- Fixed profile-alias installer producing backslash-separated paths for bash/zsh/fish config files on Windows. `path.join` was used unconditionally, producing Windows-style paths that POSIX shells can't resolve. The installer now uses `path.posix.join` for non-Windows platforms and normalizes script paths to forward slashes for POSIX shell alias blocks, so `omp --alias` works correctly in Git Bash and WSL.
- Fixed pasted or dragged non-image file paths in the TUI prompt staying as inert raw text; existing files now attach as clean `local://attachment-N.<ext>` references while image paths keep the image attachment flow. ([#3360](https://github.com/can1357/oh-my-pi/issues/3360))
- Slash commands are now recorded in input history (Up Arrow recall). Previously only 4 commands (`/plan`, `/goal`, `/mcp`, `/ssh`) stored their text; all other built-in slash commands were silently skipped because `executeBuiltinSlashCommand` returned `true` before `addToHistory` was called. History is now centralized in the input controller after successful command dispatch. Commands that may carry secrets (`/login <url>` with OAuth callback params, `/mcp add --token <token>`) are excluded from history to prevent credential leakage ([#3148](https://github.com/can1357/oh-my-pi/issues/3148))
- Fixed the `ask` tool's "Other (type your own)" free-text editor (prompt-style `HookEditorComponent`) ignoring Ctrl+Q and Ctrl+Enter, so Windows Terminal users who learned the `app.message.followUp` chord from the main editor (#1903 / fixed by #1905) got zero feedback on submit. The hook-style and main-editor surfaces honored `matchesAppFollowUp`; the prompt-style handler did not, leaving plain Enter as the sole submit path and Ctrl+Enter falling through to Editor as a newline (silently swallowed by WT). `#handlePromptStyleInput` now checks `matchesAppFollowUp` first — mirroring `#handleHookStyleInput` — and the hint reads `enter or ctrl+q submit` so the chord is discoverable. ([#3353](https://github.com/can1357/oh-my-pi/issues/3353))
- Fixed the TUI freezing when a tool approval prompt fires while `/settings` (or the Extensions/Agents dashboard) is open. The fullscreen overlay's close handler restored focus to the editor it had captured at open time, but `ExtensionUiController` had since swapped the editor out of the editor slot for the approval prompt — so on exit the visible prompt sat unreachable while keystrokes routed to the now-unmounted editor (no Enter/Up/Down/Esc response, only Ctrl+C escaped). `SelectorController` now restores focus to whatever currently owns the editor slot via a `focusActiveEditorArea()` helper, applied to settings, extensions dashboard, and agents dashboard close paths. ([#3349](https://github.com/can1357/oh-my-pi/issues/3349))
- Fixed `/settings` coercing enum/text values to display strings before handing them to the TUI list, preventing YAML numeric enum values from reaching native truncation ([#3338](https://github.com/can1357/oh-my-pi/issues/3338)).
- Fixed all extension loading silently failing on the cross-compiled `omp-darwin-arm64` release binary (downloaded directly or via a Homebrew tap wrapper) because `__computeBunfsPackageRoot` mis-handled `import.meta.dir = "//root/omp-darwin-arm64"`. Bun 1.3.14 reports `<bunfs-root>/<binary-name>` for the compiled entry's `import.meta.dir`, but the pre-fix function joined `metaDir + "packages"` and produced `/root/omp-darwin-arm64/packages` — the binary basename was baked into every bunfs path, so the TypeBox/legacy-pi shims and every `@oh-my-pi/pi-*` package-root override failed `existsSync` validation and `resolveCanonicalPiSpecifier` fell through to a bunfs `Bun.resolveSync` that also could not find the module. The function now detects the bunfs-root + binary-basename shape (`path.basename(path.dirname(metaDir)) === "root"`) and strips the trailing binary segment by slicing the original `metaDir`; the production bunfs shim join path also preserves Bun's bunfs-native `//root` / `B:\~BUN\root` prefix that `path.join` would otherwise collapse. ([#3329](https://github.com/can1357/oh-my-pi/issues/3329))
- Fixed llama.cpp discovery to prefer per-model `/v1/models` `meta.n_ctx`/`meta.n_ctx_train` values, refresh selected models after lazy load, and bypass fresh-cache reuse so server restarts update context windows. ([#3310](https://github.com/can1357/oh-my-pi/issues/3310))
- Fixed `task.maxConcurrency: 0` serializing subagent spawns instead of running them unbounded. The settings UI labels `0` as "Unlimited", but the session-scoped spawn `Semaphore` clamped `max` via `Math.max(1, max)`, so the second subagent body in a batch always waited for the first to release the seat. The constructor now treats `max <= 0` (and any non-finite input) as unbounded via `Number.POSITIVE_INFINITY`, matching the eval `parallel()`/`pipeline()` worker-pool semantics ([#3305](https://github.com/can1357/oh-my-pi/issues/3305)).
- Fixed MCP tool calls forwarding empty optional placeholder arguments (`""` and `{}`) to `tools/call`; optional placeholders are now omitted while required fields and meaningful falsy values are preserved. ([#3302](https://github.com/can1357/oh-my-pi/issues/3302))
- Fixed the welcome `Tip:` line rendering with hardcoded `#b48cff` / `#9ccfff` pastels plus a manual `\x1b[2m` dim, so any light theme dropped the body to ~1.5:1 contrast (well under WCAG AA). `renderWelcomeTip` in `packages/coding-agent/src/modes/components/welcome.ts` now paints the label through `theme.fg("customMessageLabel", …)` and the body through `theme.fg("muted", …)` (no manual dim), so the line tracks the active theme and stays legible on light backgrounds. ([#3337](https://github.com/can1357/oh-my-pi/issues/3337))
- Fixed `omp usage` and the `/usage` command duplicating provider-wide disclaimer notes (e.g. OpenCode Go's "OMP-observed spend only") once per account × limit window. Provider-level notes now render once above the per-account sections in the TUI, CLI, and ACP render paths, and identical per-limit notes are deduplicated in the TUI aggregate renderer. ([#3268](https://github.com/can1357/oh-my-pi/issues/3268))
- Fixed the welcome panel advertising `? for keyboard shortcuts` after the `?` shortcut was deliberately removed (commit dcf482c4c). The tips section now points users at `/hotkeys` instead. ([#1614](https://github.com/can1357/oh-my-pi/issues/1614))
- Fixed Devin provider models silently producing empty responses under the default `defaultThinkingLevel: auto`. Devin models advertise `reasoning: true` but no `thinking.efforts` (Cascade selects effort by routing to sibling model ids, not a wire param), so `getSupportedEfforts(model)` was empty; `clampAutoThinkingEffort` returned the classifier-picked effort as-is, which then tripped `requireSupportedEffort` in `pi-ai/stream.ts` with `Thinking effort low is not supported by devin/<id>. Supported efforts: ` (silently swallowed by the TUI). `clampAutoThinkingEffort` now returns `undefined` when the model has no controllable effort surface, matching `clampThinkingLevelForModel`; the auto-thinking turn hook also short-circuits the classifier call for these models. ([#3356](https://github.com/can1357/oh-my-pi/issues/3356))
- Fixed `omp tiny-models download` exiting before its unref'd worker subprocess could install the runtime or download model weights. The tiny-model client now references the worker while requests are pending so standalone CLI downloads wait for `Downloaded ...` / `Failed ...` completion. ([#3291](https://github.com/can1357/oh-my-pi/issues/3291))
- Fixed marketplace plugin installs registering only in `installed_plugins.json` and never in the runtime plugin tree, leaving slash commands and extensions unavailable after `omp plugin install name@marketplace`. The runtime loader now also enumerates the project-scope plugins root (`<projectAnchor>/.omp/plugins`) so `--scope project` installs surface alongside user-scope installs, with project entries shadowing same-named user entries ([#3244](https://github.com/can1357/oh-my-pi/issues/3244)).
