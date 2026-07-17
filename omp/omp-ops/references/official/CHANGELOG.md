# Changelog

## [Unreleased]

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
- Fixed `registerTool` demoting essential built-in tools to `discoverable` when a re-registration omitted `loadMode`.
- Fixed the advisor skipping the next user instruction after auto-learn accepted and pruned a terminal empty assistant stop.
- Fixed built-in advisors retrying quota- or rate-limited providers instead of applying the matching `retry.fallbackChains` model chain.
- Updated model selector status messages to use role tags (`SMOL`, `SLOW`) instead of display names (`Fast`, `Thinking`) for consistency.
- Fixed Cursor models receiving only top-level tools by forwarding mounted `xd://` devices through Cursor's request-context MCP catalog.
- Fixed Windows bash crashes when a piped command times out while flushing output.
- Fixed a race condition where hub/IRC `send` and `ensureLive` could inject into a subagent session during disposal.
- Migrated legacy nested/dotted configuration keys (`dev.autoqa.consent` and `todo.reminders.max`) to flat keys (`dev.autoqaConsent` and `todo.remindersMax`) on settings load.
- Fixed keyboard input dying after the first keypress when a custom tool module attaches a stdin consumer at import time.
- Fixed the alignment of the ask tool's custom-input dialog to start at column 0.
- Fixed advisor context maintenance undercounting the provider context by anchoring compaction decisions on provider-reported context usage.
- Fixed RPC mode (`--mode rpc`) crashing on non-JSON stdin lines; malformed lines are now reported as errors while the frame loop continues.
- Fixed local llama.cpp Qwen-family models not honoring the `--thinking off` flag.
- Documented the `ultrathink`, `orchestrate`, and `workflowz` magic keywords, including their effects, matching rules, and settings.
- Fixed `/clear` autocomplete selecting `/autoresearch` and updated `/clear` to start a new session as an alias for `/new`.
- Fixed `/review` aborting entirely when GitHub rejects a pull request's aggregate diff for exceeding the line limit by falling back to the paginated per-file endpoint.
- Fixed `/q` + Enter running `/queue` instead of `/quit` by adding an explicit `q` alias to `/quit`.
- Fixed Ctrl+L (`app.display.reset`) not refreshing the dark/light theme on certain terminals by issuing a background re-query before repainting.
- Fixed a failing advisor stalling the primary agent: the per-turn catch-up gate parked the primary for up to its full 30s budget while a broken advisor (unsupported model, dead endpoint, render bug) retried — and an advisor exception could abort the primary's turn-end outright. A failing advisor now releases parked waiters the moment its turn fails (before any async hook), refuses new parks until a turn succeeds, and the turn-end boundary isolates advisor exceptions completely; a failed render restores the delta cursor so nothing is lost when the advisor recovers.
- Fixed advisors retrying a permanently rejected request forever (e.g. `invalid_request_error: model not supported with this account`): unlike quota exhaustion — which pauses with a notice until an explicit reset — this class notified once and silently kept re-attempting every turn, re-building heavy context in a shared daemon. The runtime now hard-stops after a permanent rejection or three consecutive backlog-drop cycles, with a visible notice; an explicit reset (`/new`, config rebuild, restart) re-enables it. `waitForCatchup` resolves immediately while halted so the primary agent is never parked on a runtime that cannot drain.

## [17.0.1] - 2026-07-16

### Removed

- Fixed a crash when a plugin/custom tool renderer returns a component that throws during its later `render()` pass (e.g. `TypeError: th.bold is not a function` from a plugin that styles its header off an object without a `bold` method). `ToolExecutionComponent` now wraps every renderer-returned call/result component so a throwing `render()` degrades to the safe fallback (tool label or raw result text) instead of taking down the transcript ([#4978](https://github.com/can1357/oh-my-pi/issues/4978)).
- Fixed `/login` for paste-code providers (Codex, Anthropic, Gemini CLI, GitLab Duo, Antigravity, Devin) dropping the pasted fallback redirect URL: the login dialog captured focus but never mounted an input, and the "complete pairing with `/login <url>`" tip pointed at the hidden, unfocused editor. The dialog now mounts a focused input for the manual code/URL paste ([#5339](https://github.com/can1357/oh-my-pi/issues/5339)).
- Fixed `/tan` and `/fork` clones cold-missing the provider prompt cache: the per-turn supersede/useless-result prune rewrote the live context without persisting it, so file-based forks and resume rebuilt a divergent (un-pruned) prefix and re-wrote the entire cache
- Fixed `/tan` pinning the clone's prompt-cache key to the parent's session id instead of the parent's effective cache key, dropping shard affinity when the parent was itself a fork or tan
- Fixed `/resume` and plan approval exposing the previous session while their asynchronous session replacement was still loading by keeping fullscreen overlays mounted until the rebuilt transcript is ready ([#5319](https://github.com/can1357/oh-my-pi/issues/5319)).
- Fixed inconsistent history rendering when toggling the display setting for compacted items
- Fixed configured `retry.fallbackChains` never engaging on non-retryable provider errors (e.g. "Cloud Code Assist API returned an empty response"): a hard error on a model covered by a fallback chain now switches to the next candidate instead of failing the turn, while still never backoff-retrying the failing model itself
- Fixed transcript rebuilds (compaction, `/compact`, and toggling history display) repainting content below stale scrollback when collapsing history; rebuilds now correctly clear the scrollback buffer when history is collapsed
- Improved auto-compaction to automatically drop images and elide content when context is tight, and added persistent warning badges to the compaction divider when manual intervention is required
- Fixed backgrounded Bash blocks continuing to repaint with live and final job output; they now freeze with a compact job notice while completion is delivered separately
- Fixed the downshift plan nudge silently ending the run with no code written when the model answered with a text-only reply (no tool call): the agent loop treats a tool-call-free turn as a natural stop and never prompts again, which the nudge's own "write the plan in your next reply" instruction makes common. The nudge now explicitly tells the model this is a checkpoint, not a final answer, and the session forces one more turn whenever a post-nudge reply lands with zero tool calls
- Fixed launch tool rendering stacking a stale pending header over a bare `✓ Launch` line and raw text: the tool now uses a merged registry renderer with one per-op status header (op, target, `state · pid · uptime` meta), stripped log cursor suffixes, capped collapsed log/list previews, and a launch tool glyph
- Fixed confusing launch start/wait results when readiness timed out with the log pattern already matched (readiness needs log AND port): the result printed a contradictory `Ready: <match>` next to `Readiness timed out` without naming the failing condition. Daemon snapshots now carry the unmet conditions (`readyPending`), and start/wait results state exactly what never happened (e.g. `port 3100 on 127.0.0.1 never accepted connections`); the TUI shows a `waiting on port` badge on starting daemons
- Fixed the in-process `stat` builtin mangling BSD-style invocations like `stat -f "%Sm %N" file` (macOS muscle memory): GNU `-f` means `--file-system`, so the format string was treated as a file operand — printing filesystem info for the real operands and erroring with `cannot read file system information for '%Sm %N'`. A `-f` whose format value contains `%` is now detected as BSD syntax and translated to the GNU equivalent (`%Sm`→`%y`, `%N`→`%n`, `%z`→`%s`, epoch/`S`-form times, owner/group/permission and `H`/`L` sub-field directives, `-L`/`-n`/`-q`/`-F` flag clusters, with `%n`/`%t` as literal newline/tab); directives with no GNU counterpart fail with a clear `unsupported BSD format directive` error
- Fixed the remaining GNU-flavored shell builtins that broke under macOS/BSD muscle memory, using the same unambiguous-detection approach as the `stat` fix (only invocations that are invalid or nonsensical under GNU semantics are reinterpreted; unsupported BSD forms fail loudly instead of producing wrong output): `date -r <epoch>` formats the epoch when no such file exists (GNU `-r FILE` mtime preserved), signed `date -v±N<unit>` adjustments translate to `-d` relative dates and `-j` is accepted (`-j -f` strptime parse mode and field-set `-v` error clearly); `sed -i '' 's/…/…/' file` drops the BSD empty backup-suffix token instead of treating it as the script; `mktemp -t prefix` without X's creates `$TMPDIR/prefix.XXXXXXXXXX` (the GNU `too few X's` error path); `tail -r` reverses input by delegating to `tac` (with `-n`/`-c`/`-f` combinations erroring clearly); `find -E` maps to `-regextype posix-extended` ahead of the expression; `base64 -D` decodes as an alias of `-d`; and `ln -sfh` works via a `-h` alias of `--no-dereference` (clap's `-h` help short is dropped to match real GNU/BSD ln; `--help` unchanged)
- Fixed the browser tool crashing the whole process (parent session and every subagent) when a CDP world re-acquire failed mid-navigation: the stealth `puppeteer-core` patch called the bare `debugError` logger, which is `undefined` while the `puppeteer:error` debug channel is disabled (the default), turning a transient acquire failure into a fatal `TypeError` unhandled rejection. The patched `FrameManager`/`WebWorker` acquire paths now use `debugCatchError` ([#5296](https://github.com/can1357/oh-my-pi/issues/5296))
- Fixed a role with a `:high` thinking suffix resolving to a longer sibling model whose id embeds the tier name (e.g. `kimi-for-coding:high` → `kimi-for-coding-highspeed`). The thinking suffix is now stripped before any fuzzy match, so `provider/model:high` keeps the exact model at high effort ([#5151](https://github.com/can1357/oh-my-pi/issues/5151)).

### Fixed

- Fixed the `omp grep` CLI subcommand failing on paths with a stray leading colon (e.g. `:/abs/path`); it now routes the path argument through `expandPath` like `read`/`edit`/in-agent `grep`. Broadened `expandPath`'s leading-colon strip to also recover Windows-style shapes (`:C:\repo\file`, `:.\src`, `:..\rel`, `:\\server\share`) ([#5624](https://github.com/can1357/oh-my-pi/issues/5624)).
- Fixed the `tail` builtin exiting the entire omp process with code 13 on Windows when its output pipe broke (e.g. `seq ... | tail -n 3 | head -n 0`); a broken pipe now surfaces as a normal error instead of calling `std::process::exit` ([#5609](https://github.com/can1357/oh-my-pi/issues/5609)).
- Fixed a late advisor `blocker` after a terminal primary answer being deferred to the next user turn instead of continuing the current turn: `resolveAdvisorDeliveryChannel` preserved every interrupting severity as a passive card once the primary ended with a terminal text answer and no queued work remained, so a `blocker` flagging a mistake in the final output sat idle until the next prompt. A `blocker` now steers a triggered turn so the primary acknowledges and continues before the turn is considered done; a late `concern` still preserves as a visible card ([#5628](https://github.com/can1357/oh-my-pi/issues/5628)).
- Fixed independently keyed extension hook statuses sharing one truncated line; each status now renders on its own deterministic line ([#5617](https://github.com/can1357/oh-my-pi/issues/5617)).
- Fixed xAI web search bypassing configured `xai` / `xai-oauth` proxy endpoints and headers, while preventing official OAuth tokens from being sent to custom endpoints ([#5599](https://github.com/can1357/oh-my-pi/issues/5599)).
- Fixed `models.yml` rejecting the Anthropic `compat.supportsEagerToolInputStreaming` override for custom endpoints ([#5572](https://github.com/can1357/oh-my-pi/issues/5572)).
- Fixed long streamed table responses duplicating in terminal scrollback when later rows widened an earlier column.
- Fixed Bash internal URLs remaining unresolved when used as unquoted arguments inside command substitutions ([#5535](https://github.com/can1357/oh-my-pi/issues/5535)).
- Fixed the built-in `fd` printing `fd: Broken pipe (os error 32)` when a downstream pipeline reader exited early (e.g. `fd … | head`); it now exits silently with 141 (128+SIGPIPE), matching real fd.
- Fixed prewalk repeatedly continuing after a bash-only task such as `commit` had already completed ([#5551](https://github.com/can1357/oh-my-pi/issues/5551)).

### Added

- Fixed the Codex `config.toml` MCP importer dropping `cwd` and leaving relative `command` values unrooted, which broke the bundled Codex Computer Use server (`ENOENT` on spawn); relative `command`/`cwd` now resolve against the Codex config directory like the claude-plugins/omp-plugins providers ([#5561](https://github.com/can1357/oh-my-pi/issues/5561)).
- Fixed streamed replace-mode edits with `ssh://` paths terminating the active prompt before normal tool dispatch ([#5552](https://github.com/can1357/oh-my-pi/issues/5552)).
- Fixed concurrent provider OAuth refreshes from invalidating Anthropic's rotating refresh token, and prevented background usage probes from permanently disabling credentials after refresh failures ([#5396](https://github.com/can1357/oh-my-pi/issues/5396)).
- Restored the regression test guarding compiled-binary web-search header generation: `browser-headers.ts` lazily constructs `header-generator` and falls back to a static Chrome profile when its `data_files` are absent, but the test defending that contract had been removed. Without the guard, a compiled binary threw `ENOENT` at import time, breaking the Bing `web_search` provider (`undefined is not a constructor`) and extension loading / `omp plugin install`. ([#5256](https://github.com/can1357/oh-my-pi/issues/5256))
- Fixed browser tabs hanging indefinitely at `Closing <tab>` when a worker, CDP target, browser process, or cmux surface stalls during teardown; close deadlines now release the operation with backend, tab, and pending-resource diagnostics. ([#5259](https://github.com/can1357/oh-my-pi/issues/5259))
- Fixed the `agent://<parent>/<child>` slash form failing to resolve a nested subagent's output: the path segment was always treated as a jq JSON-extraction key against `<parent>.md`, so a precise-planner reading its own scout child (`agent://Plan/Scout`) got `Not found`. The slash is now a hierarchy separator first (`agent://Parent/Child` → `Parent.Child.md`), falling back to JSON extraction only when no nested output matches the path. ([#5238](https://github.com/can1357/oh-my-pi/issues/5238))
- Fixed fullscreen Plan Review jumping to the top while scrolling when a transient terminal resize or Markdown reflow made the body temporarily non-scrollable. ([#5232](https://github.com/can1357/oh-my-pi/issues/5232))
- Fixed `generate_image` preferring Antigravity over the active session provider and stopping instead of trying the next credentialed provider after an image HTTP failure. ([#5218](https://github.com/can1357/oh-my-pi/issues/5218))
- Fixed `/reload-plugins`, plugin setting changes, and `manage_skill` writes leaving runtime skills and `skill://` resolution stale until restart; sessions now rediscover enabled skills and rebuild `/skill:<name>` commands before the next prompt ([#4996](https://github.com/can1357/oh-my-pi/issues/4996)).
- Fixed documented `omp marketplace`/`discover`/`upgrade`/`uninstall`/`enable`/`disable` CLI verbs silently leaking to the model as a launch prompt instead of managing plugins. `omp marketplace add xyz` (and similar multi-word invocations following the documented `omp plugin <action>` grammar) now surface a hint pointing at the real `omp plugin <action>` command, while genuine prose prompts beginning with these words still route to `launch` ([#4845](https://github.com/can1357/oh-my-pi/issues/4845)).
- Fixed `/mcp`, `/mcp list`, and `/tools` output duplicating in terminal scrollback when invoked during agent streaming by deferring command panels until the active turn ends ([#4806](https://github.com/can1357/oh-my-pi/issues/4806)).
- Fixed bash/eval/ssh output that was only per-line column-capped being misreported as byte-window truncation, which appended a bogus `Showing lines X-Y of Z (…B limit). Read artifact://N for full output` footer even though every line was shown. Column-cap trimming now surfaces solely as the `Some lines truncated to N chars` notice ([#4735](https://github.com/can1357/oh-my-pi/issues/4735)).
- Fixed the `nerd` status-line preset's session icon using a removed Nerd Fonts v2 codepoint instead of the current Nerd Fonts v3 mapping ([#4795](https://github.com/can1357/oh-my-pi/issues/4795)).
- Fixed omp crashing at startup (`TypeError: undefined is not an object (evaluating 'this.#theme.symbols.boxRound')`) after installing a plugin whose custom editor subclasses `CustomEditor`/`Editor` and forwards the upstream-pi `super(tui, theme, keybindings)` constructor — the arg order that `setEditorComponent`'s factory contract advertises. `CustomEditor` now resolves the real `EditorTheme` by shape rather than position and captures a leading `TUI` for plugin overrides ([#4766](https://github.com/can1357/oh-my-pi/issues/4766)).
- Fixed `Other` response editors leaving Windows Terminal IME candidate windows at the terminal edge by forwarding dialog focus to the nested editor ([#4760](https://github.com/can1357/oh-my-pi/issues/4760)).
- Rendered and persisted native OpenAI Responses `image_generation_call` results as session images ([#4768](https://github.com/can1357/oh-my-pi/issues/4768)).
- Fixed ACP stdio EOF/EPIPE disconnects bypassing awaited session teardown and leaving in-flight tool calls pending in persisted rollouts ([#4788](https://github.com/can1357/oh-my-pi/issues/4788)).
- Routed the print-mode assistant-error/aborted exit, RPC `pi.shutdown()` and stdin-EOF shutdowns, and the extension command-context `shutdown()` through the awaited, idempotent `session.dispose()` before `process.exit()`, so the bounded browser reaper (`releaseTabsForOwner`) always runs and OMP-owned Chromium no longer outlives the process ([#5643](https://github.com/can1357/oh-my-pi/issues/5643)).

## [17.0.0] - 2026-07-15

### Breaking Changes

- Merged the `irc`, `job`, and `launch` tools into a single unified `hub` tool (`loadMode: "essential"`). Messaging, job control, and process supervision operations are now routed through this single tool. SDK: `IrcTool`, `JobTool`, `LaunchTool`, `IrcDetails`, and `JobToolDetails` have been removed in favor of `HubTool`, `CoordinationDetails`, `LaunchToolDetails`, and `hubToolRenderer` from `tools/hub`.
- Removed the hidden `resolve` tool. Staged actions are now finalized through three plain-text resolution devices: `xd://resolve` (apply preview), `xd://reject` (discard preview), and `xd://propose` (submit a plan slug/title for approval). The `write` tool is now auto-included whenever a deferrable tool is present or plan mode is enabled. SDK: `ResolveTool` and `HIDDEN_TOOLS.resolve` have been removed in favor of `dispatchResolutionDevice()` and `queueResolveHandler()`.
- Unified tool presentation on `loadMode` (`essential` | `discoverable`), replacing the custom-tool `xdev?: boolean` opt-out. Custom, extension, MCP, RPC host, image-generation, and TTS tools now default to `discoverable` and mount under `xd://` when enabled. `generate_image`, `tts`, and MCP tools are now exposed as `xd://` devices in default sessions instead of shipping their schemas top-level.
- Removed the BM25 tool-discovery system, including the `search_tool_bm25` tool, the `tools.discoveryMode`, `mcp.discoveryMode`, and `mcp.discoveryDefaultServers` settings, and per-tool MCP selection. All connected MCP tools are now enabled and mounted under the `xd://` transport. SDK: `search_tool_bm25`, the `tool-discovery` module, and associated `AgentSession` discovery/MCP-selection methods have been removed.
- Removed the legacy `report_finding` tool. Reviewer agents now record findings through incremental `yield` sections. SDK: `reportFindingTool` and `HIDDEN_TOOLS.report_finding` have been removed.
- Removed the `ssh` agent tool (remote command execution). The `ssh://` read/write/search protocol, the `omp ssh` host-management CLI, and SSH host discovery are retained. SDK: `SshTool`, `loadSshTool`, the `ssh/ssh-executor` module, and `AgentSession.refreshSshTool` have been removed.
- Removed the `tools.essentialOverride` setting, the `mcp_tool_selection` session message type, and the `xdev` `--tools` token.

### Added

- Added `xd://` virtual tool devices (controlled by the `tools.xdev` setting, default on), allowing mounted tools to be discovered via `read xd://`, documented via `read xd://<tool>`, and executed via `write xd://<tool>`.
- Added the `edit.enforceSeenLines` setting (default off) to gate the hashline seen-line guard. When enabled, edits anchored on lines that a prior `read` or `grep` never displayed are rejected.
- Added per-agent prewalk for subagents, featuring a `prewalk` frontmatter field, a `task.agentPrewalk` settings override toggled from the `/agents` dashboard, and a `task.prewalk` boolean (default off) to arm the bundled generic `task` agent.

### Changed

- Renamed `"dev.autoqa.consent"` to `"dev.autoqaConsent"` and `"todo.reminders.max"` to `"todo.remindersMax"` to eliminate nested configuration prefix collisions in standard JSON/YAML.
- Made the hashline seen-line guard opt-in and off by default, and stopped excluding column-clipped (>512-char) lines from a snapshot's seen set, allowing single-line edits on long lines to apply without a full-width re-read.
- Changed the default `astGrep.enabled` setting to `false`.
- Batched todo operations with real tool calls to prevent solo todo turns and extra round trips.
- Changed all bundled TTSR rules to warn instead of interrupting generation.
- Renamed the system prompt's project-context section wrapper from `<context>` to `<repo-rules>` to prevent collisions with the `task` tool's `context` parameter under in-band XML tool dialects.
- Rendered `read xd://` calls in a compact grouped read view instead of a full tool-execution card.
- Updated `--tools` to reject unknown tool names with a usage error instead of silently narrowing the toolset.
- Capped the `xd://` device docs inlined into the system prompt to a 48k-char budget (10k per device) to prevent large MCP catalogs from bloating requests; devices past the cap are listed by name and summary and fetched on demand. External (dynamic-mount) tool descriptions embed at most 200 chars — schemas stay intact, full text via `read xd://<tool>`.
- Dead BM25-discovery settings keys (`tools.discoveryMode`, `tools.essentialOverride`, `mcp.discoveryMode`, `mcp.discoveryDefaultServers`) are cleaned from configs on load; `tools.xdev` keeps its default (`true`).
- Mid-session `xd://` mount changes (e.g. MCP connect/disconnect) no longer rewrite the system prompt: the delta is announced to the model as a steered system notice ("these tools became available" / "no longer mounted"), so the provider prompt cache stays intact; device docs join the prompt on the next unrelated rebuild.

### Fixed

- Fixed a bug where a nested configuration value (like `dev.autoqa.consent` / `dev.autoqaConsent`) would incorrectly satisfy a parent key lookup (like `dev.autoqa`), causing Auto QA to be enabled and prompt for consent by default when it should have been disabled.
- Fixed compiled appserver startup deadlocking before socket creation when user extensions were present.
- Fixed Bash internal URLs remaining unresolved when used as unquoted arguments inside command substitutions.
- Fixed `--tools` silently dropping hidden tool names like `xdev` and `yield`.
- Fixed the built-in `fd` printing broken pipe errors when a downstream pipeline reader exited early; it now exits silently with status 141.
- Fixed prewalk repeatedly continuing after a bash-only task (such as `commit`) had already completed.
- Fixed the Bash tool hanging when in-process commands read process substitution operands.
- Fixed `/share` and `/export` web views rendering inline Markdown inside list items as literal text.
- Fixed plan-mode re-entry dropping a new plan request when a prior plan artifact existed; re-entry now anchors on the new request and folds old-plan corrections into it.
- Fixed ACP clients rendering `xd://` device dispatches as file edits; they now map to an `execute`-kind tool call titled with the device URL.
- Fixed non-yolo approval modes double-prompting for `xd://` device dispatches.
- Fixed TTSR rules with leading inline regex flags failing to compile and being silently dropped in Bun/JS environments, and recovered scope tokens and sibling values from malformed frontmatter.

## [16.5.2] - 2026-07-14

### Breaking Changes

- Removed the separate `selector` parameters from `read` and `grep`; line ranges and read modes must now be appended to `path`.

### Added

- Added a `generate_image.enabled` setting (Settings › Tools › Generate Image) to allow toggling the image generation tool.

### Changed

- Expanded provider rate-limit response header ingestion to all supported providers with header parsers (previously Anthropic-only), enabling proactive account rotation for multi-account sessions before hitting 429 errors.
- Restored CPU model metadata in workstation prompts on non-Linux hosts.

### Fixed

- Fixed `omp config list --json` output truncation at 64 KiB when stdout is piped.
- Fixed vim-style navigation (`h`/`j`/`k`/`l`) under the Kitty keyboard protocol.
- Fixed `/guided-goal` throwing `Model not found` errors on websocket-only Codex models by routing the interview through the session's provider transport and reusing a single isolated side session.
- Fixed `tool_result` extension handlers being unable to rewrite the model-visible content of a thrown tool failure.
- Fixed intermittent Perplexity OAuth web search failures (401 errors) caused by transient transport drops on the ask endpoint.
- Fixed the `generate_image` tool ignoring `--no-tools` and explicit tool whitelists.
- Fixed markerless prose thinking preambles incorrectly becoming session titles when title models omit the `<title>` marker.
- Fixed the agent recreating a todo list immediately after a user clears it with `/todo rm`.
- Fixed internal-URL autocomplete (`agent://`, `skill://`, `omp://`, etc.) not triggering inside slash command arguments.
- Fixed the browser tool hanging indefinitely during tab closure when the headless Chromium process is wedged on Windows.
- Fixed `history://` URLs failing to resolve for unregistered, released, or resumed subagents by falling back to scanning artifacts directories on disk.
- Fixed eval cells treating `timeout: 0` as a one-second deadline and reporting session-deadline cancellations as user aborts.
- Fixed MCP OAuth dynamic client registration for pathful authorization-server issuers by preserving the discovered registration endpoint.
- Fixed the `launch` tool failing to start Windows executables due to double-escaped PTY commands and arguments.
- Fixed the built-in advisor warning `Advisor unavailable` for silent reviews: a content-less stop is a valid "nothing to add" outcome and is never retried or warned about, regardless of reported token usage ([#5212](https://github.com/can1357/oh-my-pi/issues/5212) follow-up).
- Fixed `read`, `edit`, and `grep` tools failing on paths with a stray leading colon emitted by some models.
- Fixed git plugin re-installs retaining stale commits by fetching Bun's cached clone before updating the lockfile pin.
- Fixed overlapping Bash timeout and interrupt cleanup to explicitly abort isolated shells instead of leaving child processes running.
- Fixed a bug where generic provider aborts arriving as `stopReason: "error"` were not auto-retried.
- Fixed switching from a vision model to a text-only model mid-session sending historical image blocks to the new provider.
- Fixed inline images in Agent Hub transcripts by routing replayed images through the shared image budget and Kitty placeholder renderer.
- Fixed OSC 5522 paste in direct API-key login prompts being routed to the hidden main chat editor instead of the focused credential field.
- Fixed plugin installation failures when an ES module extension synchronously requires CommonJS helpers.
- Fixed GitHub code search rejecting empty optional date placeholders.
- Fixed `/tree` navigation onto a `/skill:` injection node landing on the incorrect entry.
- Fixed interactive TUI sessions crashing with concurrent JS runtime errors when the JS eval worker falls back to the in-process inline path.
- Fixed compaction aborting instead of trying an authenticated fallback model when Amazon Bedrock credential resolution fails.
- Fixed full-context forks and `/tan` clones cold-missing OpenAI prompt caches by properly persisting and inheriting provider prompt-cache keys.
- Fixed Codex advisor requests using local session labels as provider session IDs.
- Fixed macOS stdio MCP servers launching in a detached session, allowing the TCC Apple Events permission prompt to trigger.
- Fixed the ask tool timeout to auto-select the recommended option when the UI selector does not settle.
- Fixed LSP workspace diagnostics for Go workspaces to correctly recognize `go.work` roots and include all used modules.
- Fixed interactive OAuth login success messages waiting on background model discovery.
- Fixed Windows bash tool crashes when an explicit timeout fires while a piped command is still streaming.
- Fixed subagent `yield` tool calls being discarded when the soft request budget hard-aborted the same assistant turn.
- Fixed `--tools` filtering in interactive sessions disabling deferred MCP tools.
- Fixed kept-alive task subagents entering repeated provider-call loops after an IRC wake and terminal yield.
- Fixed manual `/compact` with the snapcompact strategy hard-failing on text-only active models.
- Fixed the empty-editor `←←` gesture trapping input when opening the Agent Hub from persisted/parked subagents.
- Fixed eval `read()` URI handling in Python and JS runtimes to correctly delegate URI reads and pass pagination arguments.
- Fixed discovered plugin `.mcp.json` stdio servers launching relative `command` or `cwd` values against the session cwd instead of the plugin's config directory.
- Fixed Model Hub DEFAULT role assignments with `auto` retaining a stale concrete reasoning suffix after restart.
- Fixed configured `retry.fallbackChains` failing to engage on non-retryable provider errors.
- Fixed backgrounded Bash blocks continuing to repaint with live output after completion.
- Fixed `--reasoning-slide-plan` silently ending the run with no code written when the model answered with a text-only reply.
- Fixed launch tool rendering issues, including stacked pending headers and confusing start/wait results when readiness timed out.
- Fixed the in-process `stat` and other GNU-flavored shell builtins (such as `date`, `sed`, `mktemp`, `tail`, `find`, `base64`, and `ln`) mangling or failing on macOS/BSD-style invocations.

## [16.5.1] - 2026-07-14

### Changed

- Enhanced Anthropic credential and usage management to support organization-scoped accounts, including displaying organization names in /usage, /logout, omp token --list, and OAuth login success messages, resolving active-account matching for shared organizations, and deduplicating identities during migration.

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

- Added invocation-specific schemas to task subagents and unified task/eval agent execution, including host-enforced read-only plan-mode agents ([#5279](https://github.com/can1357/oh-my-pi/issues/5279))

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
