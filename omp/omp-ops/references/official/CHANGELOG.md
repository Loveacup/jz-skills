# Changelog

## [Unreleased]

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
