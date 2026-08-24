# Changelog

## [Unreleased]

### Added

- Added side-by-side image and SVG previews to `omp git`, including local Git LFS object resolution and explicit placeholders for unavailable or unsupported binary content.
- Added the `omp if-bench` command: a zero-tool instruction-following and working-memory benchmark that drives one cached conversation per model, adding one more glyph array action every turn while a `nya{1,N}` directive moves through the prompt, with a live turn-ladder board and a ranked scoreboard
- Added `q` shortcut to exit the git TUI
- Added a third state to the git TUI whitespace toggle (`b`): beyond ignoring whitespace-only line changes, it hides formatting-only changes (indentation, line splits/joins, blank lines) and import-only changes in TypeScript/JavaScript, Rust, and Go
- Compressed single-child directory chains in the sidebar tree view

### Changed

- Made `omp git` stream file contents into an off-thread native differ, paint complete lines immediately, progressively apply syntax highlighting, and defer large commit file statistics until after the first interactive frame.
- Added `r` shortcut to refresh the git state
- Added `s`/`u` shortcuts to stage/unstage files directly from the sidebar
- Added `space` shortcut as page down in the diff pane
- Expanded `omp git` keyboard navigation: `alt+↓`/`alt+↑` jump hunks and roll into the adjacent file at the edges, `]`/`[` switch files, `←`/`→` collapse/expand sidebar directories, `enter` opens the selected file, vim motions (`j`/`k`/`h`/`l`/`g`/`G`) work in both panes, `1`–`4` pick a diff view directly, and `c` jumps to the commit form.

### Fixed

- Fixed resize and display replays, ensuring stable rendering and full transcript flushing on agent shutdown
- Fixed fast tool completions leaving a permanent running summary that blocked transcript retirement and squeezed later tool output.
- Fixed `omp git` hunk navigation (`alt+↓`/`alt+↑`) appearing to do nothing while the file sidebar had focus: the diff cursor band now stays visible (dimmed) when the pane is unfocused.

## [18.0.4] - 2026-08-24

### Added

- Added the `omp git` command (and `/git` slash command): an interactive, fullscreen repository TUI featuring a split/inline/hunk diff viewer with minimap scrollbar, syntax highlighting, a staging sidebar with line-level staging, commit composer with amend support, and author avatars. Supports keyboard navigation, full mouse interaction, and pinning views to specific commits via `omp git <revision>`.
- Overhauled the `/extensions` Extension Control Center into a fullscreen alternate-screen dashboard with mouse support, tab navigation, unified inspector views across extension types, live MCP connection management, and expandable details (`Ctrl+O`).
- Added support for live syntax highlighting in streaming markdown code blocks.
- Added an immediately editable startup composer for interactive launches, preserving drafts typed while session initialization is in progress.

### Changed

- Improved streaming markdown and thinking block rendering performance on long sessions by batching token updates and eliminating redundant re-processing.
- Optimized streaming edit verification and session restoration for large files and history-heavy sessions.

### Fixed

- Fixed invalid streamed edit patches occasionally reaching the edit tool instead of being stopped early.
- Fixed `!` shell commands on zsh/fish by running them inside a real PTY, resolving terminal option errors and preserving ANSI color formatting.
- Fixed transcript layout corruption and viewport compression caused by interrupted streams, empty blocks, or collapsed wrapped diff lines.
- Fixed transcript scrollback loss where output below sticky cards (such as hub-wait or todo) failed to commit to terminal history.
- Improved HTTP 413 error handling: accurately distinguish between true token-context overflows and provider byte/media budget limits, persist terminal errors across sessions, and enable proper fallback-chain model switching.
- Fixed discovery-backed session models failing to restore when resuming sessions with `omp --resume` or `--continue`.
- Fixed browser tool initial launch timeouts on slow or cold host environments.
- Fixed eval runtime probes hanging on Windows due to inherited stdin handles.
- Fixed Claude models replaying partial thinking blocks as conversation text when interrupted mid-turn.
- Fixed image request failures with Kimi Code and Moonshot models by ensuring inline base64 image delivery.
- Fixed SQLite WAL-mode databases without sidecars failing to open in the Read tool.
- Fixed pasted image thumbnail rendering in the composer attachment preview.
- Fixed Linux startup event loop delays caused by legacy extension cache fsync churn.
- Fixed subagent advisors abandoning reviews on the final yield turn during session teardown.
- Fixed `/todo` expand/collapse commands and corrected `/shake thinking` reporting.

## [18.0.3] - 2026-08-23

### Added

- Added opt-in edit auto-repair (`edit.autoRepair.enabled`): when an edit breaks a file's AST parse, the smol model repairs the broken region in place — validated by re-parse, revert-rejected, and surfaced as a diff in the tool result — instead of only warning.

### Fixed

- Resolved cursor drift and text duplication caused by overlapping or out-of-bounds spelling ranges
- Squeezed transcript tool rows no longer render as a bare unstyled `╭─ Hub` frame: a squeezed block keeps its real render whenever it fits the allocated rows, and blocks that genuinely overflow fold to a themed frame that names the tool's activity (e.g. `Hub · send → Main`).
- Python/Ruby/Julia eval cells that hit their wall-clock timeout during a `parallel()`/`agent()`/`tool.*` fan-out no longer get their kernel force-killed (losing all session state): the timeout now aborts in-flight bridge calls so the runner unwinds as a clean KeyboardInterrupt and the kernel survives.
- Multi-select ask options whose labels end in `(Recommended)` now show their checked state and avoid duplicate recommendation suffixes ([#9452](https://github.com/can1357/oh-my-pi/issues/9452)).

## [18.0.2] - 2026-08-23

### Added

- Added update channels: `omp update --canary` installs canary prereleases from the npm `canary` dist-tag and `omp update --stable` switches back; the chosen channel persists and drives the startup update check.

### Changed

- Unexpected Stops now offers None, Mechanical (default), and Smart modes; Smart adds small-model classification to recover text-only stops.

### Fixed

- Fixed crash during update output when theme configuration is missing
- Fixed flickering typo undercurls while typing by projecting state during revalidation
- Fixed self-update on Windows leaving the `omp` command missing or stuck on the previous version when package-manager reinstalls fail on running files
- Ctrl+T now toggles every thinking block in the transcript, including blocks already retired to terminal history ([#9440](https://github.com/can1357/oh-my-pi/issues/9440)).
- Copilot Grok 4.6 Responses streams that repeatedly close after thinking now stop after one same-model retry instead of consuming the full retry budget ([#9427](https://github.com/can1357/oh-my-pi/issues/9427)).
- `/mcp test` now reports cancellation immediately when Esc is pressed during a slow config lookup, instead of staying suspended until the read settles ([#9419](https://github.com/can1357/oh-my-pi/issues/9419)).
- Fixed remote browser relay endpoints advertising a client-local CDP WebSocket URL: `/json/version` now reflects a valid request `Host` and falls back to the relay's loopback address when it is absent or unusable.
- Restored red/green and syntax highlighting in edit-tool result bodies ([#9439](https://github.com/can1357/oh-my-pi/issues/9439)).
- Fixed goal mode failing to start (`No such tool: xd://goal`) when `goal.enabled` was turned on after the session had already started; the `goal` tool is now registered lazily on goal-mode entry ([#9444](https://github.com/can1357/oh-my-pi/issues/9444)).

## [18.0.1] - 2026-08-23

### Added

- Plan review can save a plan to a chosen path and start a new session.
- Edit results now warn when an edit leaves a previously parsing file unparseable, independent of the `edit.blackbox.enabled` recorder.
- Added provider-wide Amazon Bedrock guardrail settings to models configuration, including custom models.
- Added the `/pin` slash command to pin and unpin sessions so they stay at the top of the `--resume` picker UI.
- Optional edit parse-regression capture appends the before/after content, model, variant, and arguments to `~/.omp/agent/edit-blackbox.jsonl` when `edit.blackbox.enabled` is enabled.

### Changed

- Bash commands now automatically transition to the background by default when exceeding the threshold
- Transcript blocks now retire to terminal history as explicit ordered batches, active tools collapse to compact indicators under viewport pressure, and the `tui.scrollbackRebuild` and `tui.resizeScrollback` settings were removed.
- Transcript retirement is now capacity-driven: finalized blocks (and the welcome header) stay live in the viewport — reflowing to the current width on resize and visible the instant a message is submitted — and only commit to immutable terminal history when the screen runs out of room.
- Resizing no longer duplicates the editor and status rows: the settled repaint recovers its anchor from the terminal's own cursor-position report after reflow.
- The Advisor agent's guidance now prioritizes concrete technical risks and transcript-evident execution failures, while strictly prohibiting meta-advice on user intent, ceremony, or workflow narration.
- Edit-tool inline selections whose text contains the divider character itself (box-drawing code) are now resolved instead of failing the batch: a trailing divider reads as a deletion, an odd count splits at the middle divider, an even count reads as a deletion of the selected text, each with an advisory note.
- The welcome screen's recent-sessions list no longer content-scans every session file in the project directory: session titles are indexed in history.db as they are created/renamed, and startup resolves the newest files by mtime with a per-file scan fallback that backfills the index (cuts the pre-input startup transition by ~250ms per 10k sessions).
- Interactive startup no longer re-runs slash-command discovery: the composer's autocomplete reuses the discovery pass that session construction already performed.
- Interactive startup now reuses the prepaint composer's in-flight recent-session load, starts custom-command discovery with the other independent filesystem scans, and overlaps auth-cache/config reads with settings initialization instead of repeating or serializing them.
- Interactive startup now commits the complete composer frame synchronously before `session_start` hooks, lazily materializes only cached model providers needed by the configured default role, and starts cache-aware online runtime-provider discovery after the first UI paint.
- Advisor criteria for `concern` and `blocker` levels are expanded to better identify serializing independent tasks, bypassing specialized tools, ignoring verified sources, and premature yielding before convergence.
- The Advisor is now explicitly instructed to promote clean code cutovers (deleting obsolete paths and tests) unless backwards compatibility is required by the user or project rules.
- The advisor now flags transcript-evident execution failures—missed parallelism, overplanning, ungrounded assumptions, unnecessary abstraction, incomplete scope, stubs, and thin verification—before they force user steering.
- Slash-command autocomplete now collapses skills into a single `/skill:` row; the individual skills list once the prefix reaches `/skill:` (accepting the row with Tab/Enter expands it in place).
- `omp cleanse` and `/cleanse` now dispatch repair subagents while checkers are still running: diagnostics stream in (parsed from partial checker output every 5s), new files spawn workers up to the agent cap with least-loaded batching, and late diagnostics for a file being repaired are steered into the owning worker's chat instead of waiting for the full diagnostic pass.
- Suggested plan save filenames now come from a dedicated 1-3 word topic prompt instead of the sentence-length session title (e.g. `PYO3_METHODS_PLAN.md` instead of `SPLIT_PYENVIRONMENTBACKEND_REQUEST_INTO_PYO3_METHODS_PLAN.md`), with verbose fallbacks trimmed at a word boundary.
- Subagents in a shared working tree no longer run formatters, linters, or project-wide builds/test suites unless their assignment asks for it; validation runs once by the main agent.
- Context file deduplication now checks paragraph containment instead of byte-exact matching: a less-authoritative file whose normalized paragraphs appear contiguously within a more authoritative file is omitted, reducing redundant prompt context.
- Context file containment dedup now sorts by depth descending internally, treating files without a depth as least authoritative, so concatenated multi-root or user-level context cannot drop a closer-to-cwd file.
- Paragraph splitting for containment comparison is now fenced-code-block-aware: text inside a fenced example in a more authoritative file no longer counts as a contained instruction, preventing active context rules from being discarded.

### Fixed

- Fixed UI jitter in the edit tool gutter by reserving space for line counts
- Edit-tool add lines written directly above a `` gap now insert under their anchor line instead of splicing at the post-gap anchor, often mid-line without a newline.
- Edit-tool add lines may contain literal selection-marker glyphs; such payloads previously failed with an unusable corrected payload.
- A bare edit selection whose REWRITE restates the whole line now replaces the full line instead of duplicating the line's prefix and suffix around the span.
- A mid-line `…` in an edit REWRITE no longer re-emits a multi-line capture, so literal ellipses inside strings survive.
- Fixed double-Esc (session tree / branch selector) appearing dead on long sessions: opening it no longer replays the entire transcript through the terminal (which blocked for tens of seconds on PTY backpressure and cleared native scrollback), only the viewport repaints.
- Fixed prompt history whitespace duplicates: prompts are normalized on save (CRLF folded, per-line trailing padding stripped) so terminal-copy resubmissions upsert instead of adding a near-identical row, and a one-time pass collapses existing padded duplicates keeping the latest submission's metadata.
- Fixed prompt history duplicates: each prompt is now stored once with its latest project path, session ID, and submission time, and session resume or transcript rebuilds no longer repopulate persistent history.
- `/models` no longer shows dead sidebar tabs for unconfigured Ollama, llama.cpp, and LM Studio endpoints; explicitly configured endpoints remain visible for diagnosis ([#2761](https://github.com/can1357/oh-my-pi/issues/2761)).
- Fixed prompt input lag under CPU load while file and macOS spelling completions are active.
- Fixed blank `mnemopi.dbPath` settings silently creating volatile memory banks instead of using persistent agent storage ([#9360](https://github.com/can1357/oh-my-pi/issues/9360)).
- Fixed legacy Pi extensions being reparsed on every startup because their persistent parse cache could not be created ([#9339](https://github.com/can1357/oh-my-pi/pull/9339) by [@walodayeet](https://github.com/walodayeet)).
- Fixed Kitty text-sized Markdown headings activating before `tui.textSizing` is enabled.
- Fixed terminal-title updates racing the TUI's off-thread output pump, which could tear an escape sequence mid-frame and print the title (e.g. `0;π ∴ <session title>`) into the editor line as if typed.
- Fixed the edit tool corrupting files on unified-diff-shaped payloads: missing-separator recovery no longer hijacks `-`/`+` bodies (which deleted matched anchors and duplicated the surrounding block); they now flow to the unified-diff reinterpretation.
- Fixed the edit tool writing literal `…` lines: a whole-line rewrite gap with no captured MATCH gap now fails closed with guidance instead of splicing an ellipsis into the file.
- Fixed status text retaining hidden DCS, PM, and APC payloads after escape-sequence sanitization.
- Fixed extension load errors truncating explicitly excluded package import specifiers.
- Fixed subagents crashing before their first turn when an extension contributed a tool or skill without a `description`; the context-breakdown token estimate now coalesces missing descriptions and system-prompt sections instead of passing `undefined` to the tokenizer ([#9331](https://github.com/can1357/oh-my-pi/issues/9331)).
- Clarified that Mnemopi `/memory enqueue` only promotes working memories older than the configured consolidation gate (12 hours by default) and that normal shutdown does not run bank sleep ([#9356](https://github.com/can1357/oh-my-pi/issues/9356)).
- Fixed asynchronous V2 remote compaction dropping user and tool messages added after its speculative snapshot ([#9351](https://github.com/can1357/oh-my-pi/issues/9351)).
- Fixed startup crashes when temporary Git worktrees point to repository metadata that the current user cannot access.
- Hidden custom tools (`hidden: true`) stay out of the parent session's active set and `/tools` unless `--tools` or an agent `tools:` list names them. They used to be always-included.
- Hidden custom tools (`hidden: true`) stay out of the parent session's active set and the TUI's `/tools` list unless `--tools` or an agent `tools:` list names them. They used to be always-included.
- Fixed edit retries suggesting the same invalid payload and permission prompts showing unknown paths for sloppy edits ([#9350](https://github.com/can1357/oh-my-pi/issues/9350)).
- Fixed Agent Hub aborted rows failing to open their read-only transcript when selected with Enter.
- Fixed `/mcp test` leaving a stale "(esc to cancel)" hint after the test finished and swallowing Esc presses during the grace window; the hint now stops advertising Esc once the test settles, a late Esc shows an "already finished" status instead of silently doing nothing, and one Esc press consumes the cancellation ownership so the next Esc reaches the running turn ([#9173](https://github.com/can1357/oh-my-pi/issues/9173)).
- Fixed MCP request timeouts surfacing as `Unexpected end of JSON input` instead of `Request timeout after Nms` when the abort lands mid-JSON-body read, including when the caller's signal aborts after the timer fires ([#9048](https://github.com/can1357/oh-my-pi/issues/9048)).
- Fixed streamed `xd://` device writes (including MCP tools) looking like a hung in-flight call while the model is still thinking; they now show as queued until the tool actually starts.
- Fixed `/clear` and `/new` keeping a stale `AGENTS.md` (and other context files) in the system prompt; a new session now re-reads them from disk ([#9273](https://github.com/can1357/oh-my-pi/issues/9273)).
- Auto-continue turns that die mid-tool-call with `OpenAI completions stream closed before a finish_reason was received` (and the Responses/Azure "closed before a terminal response event" variants): premature gateway stream closes now classify like idle stalls and HTTP/2 resets, so a resolved tool turn is continued after its preserved partial output instead of surfacing the error.
- Todo tool schemas now identify `items` as valid for single-phase `init` and `append`.
- Fixed Todo tool guidance to clarify that blocked tasks never auto-promote after state-changing operations (#8121).
- Fixed timed-out or interrupted glob searches keeping native filesystem workers alive and blocking subsequent agent turns.
- Fixed legacy Pi extensions being re-parsed on every launch instead of using the persistent cache ([#9170](https://github.com/can1357/oh-my-pi/pull/9170) by [@fmguerreiro](https://github.com/fmguerreiro)).
- `/mcp reload` now picks up external edits to `mcp.json`.
- Fixed `lsp reload` clearing active language-server settings instead of reapplying them.
- Fixed workspace diagnostics skipping lower-priority languages in polyglot project roots ([#8385](https://github.com/can1357/oh-my-pi/issues/8385)).
- Fixed isolated task cleanup deleting the only branch that retained an agent's commits after apply-back failed ([#9216](https://github.com/can1357/oh-my-pi/pull/9216), thanks [@Mustaqeem66](https://github.com/Mustaqeem66)).
- Fixed bare `hub wait` calls reporting nothing to wait for while an already-queued bus message remained unread.
- Fixed Code Mode activating for sessions whose caller never enabled `eval`, which handed restricted subagents an unrestricted JS runtime; the eval transport must now be part of the caller's own tool set.
- Fixed Code Mode dropping `write` from the direct surface when plan mode starts, and dropping `task` delegation guidance from the plan prompt once `task` is reachable only through the eval bridge.
- Fixed the eval tool advertising bridged declarations for tools the model can still call directly, such as a plan-mode transport `write`, by reading the partition the session actually applied.
- Fixed Code Mode turn metadata resolving a wire-name collision by tool registry order, and mishandling tools named after `Object.prototype` members or after the eval bridge's own internal operations (`__agent__`, `__budget__`, `__completion__`, `__concurrency__`).
- Fixed generated Code Mode declarations rendering an array of a union as `"a" | "b"[]`, which models read as a scalar-or-array type and submitted invalid arguments against.
- Fixed SDK sessions with a custom agent directory inheriting process-global model overrides instead of loading that directory's own `models.yml`.
- Fixed Eval guidance that implied `agent()` children share parent kernel state and advertised them when spawning was disabled.
- Fixed Bash guidance that implied raising `timeout` extends foreground execution beyond the auto-background threshold.
- Fixed Bash and Eval guidance that implied raising `timeout` extends foreground execution beyond the auto-background threshold ([#9155](https://github.com/can1357/oh-my-pi/pull/9155) by [@MikeeI](https://github.com/MikeeI)).
- Status-line usage no longer combines quota windows scoped to different models or tiers ([#9138](https://github.com/can1357/oh-my-pi/issues/9138)).
- Fixed `PI_PROXY` being ignored outside provider streams: the CLI now installs it on the process-wide `fetch` at startup, so OAuth token refresh/login, usage probes, and model discovery are proxied too. Combined with the Anthropic transport fix in `pi-ai`, a region-blocked machine reaching Anthropic through a proxy no longer fails with `403 Request not allowed`.
- Subagent failures now name the resolved provider and model that produced the error ([#9137](https://github.com/can1357/oh-my-pi/pull/9137) by [@Mustaqeem66](https://github.com/Mustaqeem66))
- Fixed read-only subagents (`scout`, restricted-tool custom agents) crashing before their first prompt when extensions register callable tool schemas.
- Fixed smart paste dropping text from X11 clipboard owners whose image read fails instead of reporting no image.
- Fixed `formatContent` silently swallowing formatter errors: the empty `catch {}` was replaced with per-server error tracking, and failed formatter requests now surface as `FileFormatResult.FAILED` instead of being misclassified as unchanged ([#8388](https://github.com/can1357/oh-my-pi/issues/8388)).
- Fixed `formatContent` reporting no-formatter as unchanged: when no configured server supports formatting, the result is now correctly classified as `FileFormatResult.UNSUPPORTED` ([#8388](https://github.com/can1357/oh-my-pi/issues/8388)).
- Fixed MCP request timeouts surfacing as `Unexpected end of JSON input` instead of `Request timeout after Nms` when the abort lands mid-JSON-body read.
- Fixed CJS modules being misclassified as ESM when imported from an ESM parent module. The extension loader now identifies unshadowed CommonJS syntax from Babel's parsed AST before deferring to the importer's module kind. This resolves `SyntaxError: Missing 'default' export` for packages with conditional exports (e.g. playwright-core) where an ESM wrapper re-exports from a CJS entry, while ambiguous files continue to inherit their importer's classification.

## [18.0.0] - 2026-08-22

### Added

- Added the `omp render` command to replay session threads and benchmark transcript pipeline performance.
- Added configurable typo detection (`Ctrl+.` suggestions), Tab word completion, and opt-in autocorrect to the macOS prompt editor.
- Added a live benchmark dashboard to `omp bench` with real-time performance estimates, p50/p95 statistics, distinct input/output throughput metrics, cost tracking, mixed challenge suites by default, and a `--prefill-bytes` option for synthetic prefill benchmarks.
- Added the `/shake thinking` command to strip model reasoning blocks from session history.
- Added icon support and usage-frequency ranking to slash-command autocomplete suggestions.
- Enhanced the edit tool to support `＋`-prefixed line insertions, unified diff formats, bare selection replacements, and robust recovery for common syntax variations and ambiguous match spans.
- Startup composer now renders immediately using cached session and theme data, allowing typing before session initialization finishes without dropping keystrokes.

### Changed

- Session history rewinds (via `Esc-Esc` or `/tree`) now truncate transcript tails in place instead of clearing and replaying the entire terminal scrollback.
- Switched the fallback edit mode to `sloppy` for models lacking hashline support.
- macOS spelling checks now run in the background to avoid blocking editor rendering and keystroke responsiveness.
- Word completions accepted via Tab now insert a trailing space when not immediately followed by whitespace or punctuation.
- Increased default visible autocomplete dropdown rows to 10 and added the `autocompleteMaxVisible` configuration setting.
- Slash-command descriptions in the autocomplete popup now truncate to two lines instead of wrapping indefinitely.

### Fixed

- Fixed streaming code blocks not rendering syntax highlighting live until completion.
- Fixed an issue where interrupting Claude during reasoning would replay partial thinking blocks on subsequent turns and cause API rejection errors.
- Fixed session resume performance by avoiding redundant edit-matching execution across historical transcripts.
- Fixed image requests to Kimi Code / Moonshot failing with 400 errors by sending inline base64 images directly.
- Fixed reading WAL-mode SQLite databases that do not have active `-wal` or `-shm` files.
- Fixed terminal transcript layout corruption on Windows caused by collapsed edit results with long wrapped diff lines ([#9302](https://github.com/can1357/oh-my-pi/issues/9302)).
- Fixed disappearing terminal scrollback history below updating cards such as background jobs or hub status cards.
- Fixed pasted image attachment thumbnails rendering as blank boxes in Kitty terminal graphics mode.
- Fixed context gauge display issues in the status line for unnamed sessions.
- Fixed accurate benchmark input token counts on providers with automatic prompt caching.
- Fixed C# files incorrectly displaying D3.js icons in edit results ([#9323](https://github.com/can1357/oh-my-pi/issues/9323)).
- Fixed incorrect token delta reporting in expanded context compaction summaries when pre-compaction usage was omitted by the provider ([#9293](https://github.com/can1357/oh-my-pi/issues/9293)).

## [17.4.4] - 2026-08-22

### Added

- Added the `tui.resizeScrollback` setting (default `append`) controlling how a settled width resize refreshes pane scrollback when the terminal repaints in place (tmux/screen/Zellij panes, in-place direct terminals). Multiplexers rewrap old output naively on width changes, leaving history hard-broken at the old width; `append` re-emits the transcript at the new width below it (one fresh copy per settled resize), `rebuild` clears pane history first so it holds exactly one current-width copy (needs a host that honors ED3, like tmux; erases pre-session scrollback), and `preserve` keeps the old-width history untouched with zero growth ([#8193](https://github.com/can1357/oh-my-pi/issues/8193)).

### Fixed

- Fixed the composer image chip painting its right border inside the card and mangling the thumbnail's first row: the Kitty placement prefix was counted as visible width, breaking the thumbnail centering.
- Fixed edit-tool whole-line inserts (an insert selection alone on its own line) splicing into the anchor line instead of landing on a new line when the anchor was the last matched line, preceded a blank line, or sat at EOF.
- Edit tool prompt now documents whole-line insert selections and that a REWRITE `…` with no captured MATCH gap is written to the file literally.
- Fixed multiplexer width resizes (tmux/screen/Zellij/cmux/Herdr panes) replaying the entire transcript into pane history — one duplicated transcript copy and seconds of visible scrolling per width change. The width-epoch boundary now resolves for real transcripts: finalized blocks without `getTranscriptBlockVersion` are treated as immutable per the documented contract, Container-derived blocks without a nested epoch source fall back to whole-segment stability instead of failing, and bash/eval/tool/read-group blocks report a block version for their genuine post-finalize mutations. The interactive resize listener no longer marks every SIGWINCH as "render pending", which forced the conservative replay-from-row-zero fallback on every settled resize ([#8193](https://github.com/can1357/oh-my-pi/issues/8193), [#7026](https://github.com/can1357/oh-my-pi/issues/7026)).

## [17.4.3] - 2026-08-21

### Fixed

- Fixed the edit tool rejecting payloads containing a glued `«»` line: after MATCH it now reads as the mistyped `»` separator, elsewhere as a stray terminator to drop.

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
- Added DeepInfra backends for the `image_gen` tool (via the OpenAI-compatible images endpoint, selectable via `providers.imageOrder` or a per-request `provider: deepinfra`) and the `tts` tool (`providers.tts: deepinfra`, MP3 or WAV).
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
