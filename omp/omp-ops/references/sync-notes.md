# Sync Notes

## 2026-08-31 — official mirror refresh (18.0.11)

- Official OMP remains `18.0.11`; upstream `main` changed the tracked
  environment-variable, provider, and changelog mirrors without a package
  version bump.
- Authored model guidance now includes the documented `cline-pass` provider
  and `CLINE_API_KEY`, while treating its subscription roster, quotas, and
  model metadata as provider-reported and subject to change.
- The Unreleased entries concern status/UI, edit-mode compatibility, config
  update preservation, notifications, Anthropic sampling, and context-file
  discovery. They do not establish additional stable operator guidance for
  architecture, security, search, or `SKILL.md`.
- Missing daily-maintenance helpers remain `verify.sh`, `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, and `release.sh`; this run uses
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and bounded
  inline comparison/verification.

## 2026-08-30 — 18.0.11 update

- Official OMP `18.0.11` synced successfully; `references/VERSION` now tracks
  `18.0.11-0`, and the official changelog, provider, model,
  environment-variable, skills, and sync-state mirrors were refreshed.
- Authored model guidance now records `compactionModel` and provider/model-level
  `remoteCompaction`, including the supported option keys and the custom
  endpoint boundary. Provider guidance also records the newly documented hosted
  providers and credential aliases; search guidance records TinyFish and the
  keyless `public` aggregate.
- The remaining 18.0.11 changes concern gallery/status UI, MCP OAuth discovery,
  retry and image recovery, plugin discovery, platform/runtime fixes, and
  diagnostics. They do not require additional authored architecture or security
  guidance.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-29 — 18.0.10 update

- Official OMP `18.0.9`–`18.0.10` synced successfully; `references/VERSION`
  now tracks `18.0.10-0`, and the official provider, environment-variable,
  changelog, and sync-state mirrors were refreshed.
- Authored model guidance now records the stable Cloudflare AI Gateway
  credential trio and login/environment boundary, plus the documented
  distinction between coding-plan login providers and standard Zhipu BigModel
  account-balance keys.
- The remaining 18.0.9–18.0.10 changes concern VCS internals, TUI/status
  display, retry/restart, session durability, MCP/ACP diagnostics, and runtime
  fixes; no additional architecture, security, or `SKILL.md` guidance was
  warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-28 — 18.0.8 update

- Official OMP `18.0.8` synced successfully; `references/VERSION` now tracks
  `18.0.8-0`, and the official changelog, model reference, and sync state were
  refreshed.
- The official model documentation expands the shared models.dev catalog
  refresh and cache/source-freshness behavior; authored model guidance now
  records the additive, cached, non-authoritative boundary and keeps provider
  endpoint discovery authoritative for account availability.
- The remaining release notes concern usage display, transcript recovery,
  startup/tool reconciliation, TUI/LSP/runtime fixes, and RPC launchers. They
  do not expose a stable provider, model, architecture, security, or `SKILL.md`
  contract for this skill; no authored guidance was invented.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-27 — 18.0.7 update

- Official OMP `18.0.6`–`18.0.7` synced successfully; `references/VERSION`
  now tracks `18.0.7-0`, and the official changelog plus sync state were
  refreshed.
- The 18.0.7 changelog adds usage-client reporting and clarifies browser relay,
  computer-tool, and MCP approval behavior. The tracked provider, model,
  environment-variable, and MCP configuration references expose no new stable
  authored schema for this skill, so no additional operator guidance was
  invented.
- The remaining 18.0.6–18.0.7 changes concern the git TUI, transcript/rendering,
  extensions, runtime recovery, and platform fixes; no additional provider,
  architecture, security, or `SKILL.md` guidance was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-26 — 18.0.5 update

- Official OMP `18.0.5` synced successfully; `references/VERSION` now tracks
  `18.0.5-0`, and the official changelog, provider, model,
  environment-variable, and sync-state mirrors were refreshed.
- Added authored model guidance for the new `yolo-auto` provider and its
  `YOLO_AUTO_API_KEY`, plus the custom-model `thinking.requiresEffort: false`
  compatibility switch. The switch should be used only after backend
  verification because it changes explicit reasoning-off request shaping.
- The remaining 18.0.5 changes concern git/TUI, transcript/rendering,
  benchmarking, plugin discovery, login flow, and runtime/platform fixes; no
  additional stable provider, architecture, security, or `SKILL.md` guidance
  was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-25 — 18.0.4 update

- Official OMP `18.0.4` synced successfully; `references/VERSION` now tracks
  `18.0.4-1`, and the official changelog, provider, environment-variable, and
  sync-state mirrors were refreshed.
- Added authored DeepInfra guidance: authenticate with `DEEPINFRA_API_KEY`,
  select image generation through `providers.imageOrder` or a per-request
  `provider: deepinfra`, and select DeepInfra TTS with `providers.tts`.
- The remaining 18.0.4 changes concern the `omp git` and Extensions TUI,
  streaming/rendering behavior, edit validation, transcript stability, and
  platform/runtime fixes; no additional provider, architecture, security, or
  `SKILL.md` guidance was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-23 — 18.0.0 update

- Official OMP `18.0.0` synced successfully; `references/VERSION` now tracks
  `18.0.0-0`, and the official changelog/environment mirror plus sync state
  were refreshed.
- Authored search guidance now records the new Perplexity model selectors and
  Firecrawl endpoint override, plus the corresponding Gemini endpoint boundary
  from the official environment reference.
- The remaining 18.0.0 release changes are editor/UI, transcript, benchmark,
  edit-tool, and runtime fixes; no additional authored model, architecture, or
  security guidance was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review.

## 2026-08-22 — 17.4.2 update

- Official OMP `17.4.2` synced successfully; `references/VERSION` now tracks
  `17.4.2-0`, and the official changelog plus sync state were refreshed.
- Authored security and model guidance version markers were corrected to match
  the official 17.4.1 changelog placement for the External Thinking warning and
  `qwenTemplateReasoningEffort` compatibility field.
- The 17.4.1–17.4.2 changes otherwise concern composer attachments, image URL
  brokering, CLI reference documentation, UI/runtime fixes, and compatibility
  hardening; no additional stable `omp-ops` operator guidance was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review.

## 2026-08-21 — 17.4.0 update

- Official OMP `17.4.0` synced successfully; `references/VERSION` now tracks
  `17.4.0-1`, and the official mirror includes the new tokenizer and LiteLLM
  discovery behavior.
- Authored guidance now documents `tokenizer` for ambiguous proxy model ids,
  LiteLLM's Responses-versus-Chat-Completions routing, the new ordered
  `compaction.methodOrder`, speculative async compaction, the context gauge,
  and `extendedContext` settings, and the External Thinking provider-risk
  warning.
- The remaining 17.4.0 changes are runtime, UI, extension, or platform fixes;
  no additional `omp-ops` operator guidance was warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review.

## 2026-08-20 — 17.3.8 update

- Official OMP `17.3.8` synced successfully; `references/VERSION` now tracks
  `17.3.8-0`, and `sync-state.json` records the upstream sync timestamp.
- Authored model guidance now documents `qwenTemplateReasoningEffort`, which
  lets Qwen 3.8+ local models route selected effort through the chat-template
  reasoning argument; strict servers that reject unknown template kwargs should
  set it to `false`.
- The new `providers.cacheRetention` setting and the external-thinking risk
  note are present in the official changelog, but the tracked configuration
  mirrors do not expose enough stable schema detail to add safe authored
  operator guidance. The remaining 17.3.8 changes are runtime, UI, security
  hardening, or bug fixes and require no `omp-ops` reference changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and
  `release.sh`; this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and inline semantic review.

## 2026-08-18 — 17.3.6–17.3.7 daily maintenance

- Official OMP `17.3.7` is mirrored; `references/VERSION` tracks `17.3.7-0`
  and `sync-state.json` records the official sync.
- Authored model guidance now tracks the 17.3.6 xAI default change to
  `grok-4.6` for both `xai` and `xai-oauth`, while retaining the Responses API
  and reasoning-parameter restriction guidance from 17.3.5.
- The 17.3.6 extension file-write/delete fallback API and `omp stats --host`
  support are recorded as extension/runtime behavior in the official mirror;
  no operator configuration or security guidance was added because the
  changelog does not establish a stable `omp-ops` setting or workflow.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; `fetch-official.sh`
  is also absent, while `sync-from-official.sh` is the available equivalent.

## 2026-08-11 — daily maintenance

- Official OMP remains `17.2.12`; the official mirrors were refreshed and only
  `references/sync-state.json` changed because of the new sync timestamp.
- The 17.2.11–17.2.12 official material was reviewed again; no additional
  authored provider, model, architecture, security, or `SKILL.md` guidance was
  warranted.
- Skill maintenance revision advanced to `17.2.12-3`; missing daily-maintenance
  helpers remain `fetch-official.sh`, `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`.

## 2026-08-08 — 17.2.10 maintenance follow-up

- Re-ran the official mirror sync for OMP 17.2.10. The upstream `Unreleased`
  changelog now includes Agent Plugins, remote MCP header/origin enforcement,
  and the Exa enablement migration.
- The sync helper incorrectly reset an existing same-version skill revision
  (`17.2.10-1` to `17.2.10-0`). The helper now preserves the revision when the
  official base version is unchanged and resets it only for a new official
  version.
- Authored guidance records the confirmed Exa `exa.enabled` migration and the
  remote MCP/plugin security boundaries. No `SKILL.md` change was made because
  it is already 299 lines; no provider/model architecture change was warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`.

## 2026-08-07 — 17.2.10 update

- Official OMP 17.2.10 synced successfully; `references/VERSION` now tracks
  `17.2.10-0`, and `sync-state.json` records the refreshed mirror.
- Authored security guidance now records the exact-path
  `--trusted-extension` allowlist, which is an operator-facing extension
  loading boundary. The `omptype`-backed Zod compatibility facade is a
  plugin-author API change and does not require operator guidance here.
- The remaining 17.2.10 changes are Agent Hub UI, crash-resume output,
  schema/runtime, platform, browser, and session behavior; no additional
  authored provider, model, architecture, or security update is warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and `push-to-github.sh` plus bounded inline review
  and verification.

## 2026-08-05 — 17.2.8 update

- Official OMP 17.2.8 synced successfully; `references/VERSION` now tracks
  `17.2.8-0`, and `sync-state.json` records the refreshed mirror.
- The tracked official configuration/provider/model documents are unchanged
  from the prior mirror. The 17.2.8 changelog contains a bundled `omptype`
  schema-engine upgrade (string-DSL intersection/pipe operators, bigint and
  RegExp literals, Standard Schema V1 interop, JSON Schema import, and richer
  union/collection errors); this does not establish a new operator setting or
  provider/auth rule, so no authored reference update is warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run used `check-version.sh`, `orchestrate.sh`, and
  `sync-from-official.sh` plus bounded inline review and verification.

## 2026-08-04 — 17.2.5–17.2.6 update

- Official OMP 17.2.5–17.2.6 synced successfully; `references/VERSION` now
  tracks `17.2.6-0`, and `sync-state.json` records the refreshed mirror.
- Semantic review covered the changelog and all tracked official docs. The
  operator-visible additions include MCP `requestIdFormat` plus user-level
  `enabledServers`/`disabledServers` precedence, provider discovery
  `timeoutMs`, remote compaction, custom-tool ArkType/restricted-session
  behavior, browser relay/desktop sessions, and new environment controls.
- Authored guidance now records `/reset`, the 17.2.5 computer/edit breaking
  changes, `.env` empty-value and `OMP_*`/`PI_*` precedence, and provider
  discovery `timeoutMs`. MCP allow/deny overrides, imported-config precedence,
  and exact runtime/profile migration steps remain in the official mirror;
  do not infer those steps from the changelog alone.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run used `check-version.sh`, `orchestrate.sh`, and
  `sync-from-official.sh` plus bounded inline review and verification.

## 2026-08-03 — 17.2.4 update

- Official OMP 17.2.4 synced successfully; `references/VERSION` now tracks
  `17.2.4-0`, and the official changelog mirror was refreshed.
- Semantic review covered the 17.2.4 changelog and the tracked official
  configuration docs. The release adds computer/desktop sessions, browser
  relay, shared LSP brokering, `--service-tier`, and web-search timeout
  behavior, but the mirrored configuration docs do not expose enough stable
  configuration shape to add authored guidance safely. MCP `requestIdFormat`
  and provider discovery timeout details likewise remain changelog-only here;
  consult the official mirror before advising on them.
- No authored provider, model, architecture, security, or `SKILL.md` update
  was warranted. The Windows exact-case environment lookup fix is recorded as
  a runtime safety fix, not a new credential precedence rule.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run used `check-version.sh`, `orchestrate.sh`, and
  `sync-from-official.sh` plus bounded inline review and verification.

## 2026-07-31 — 17.2.1 update

- Official OMP 17.2.0–17.2.1 mirrors were refreshed; `references/VERSION` now
  tracks `17.2.1-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance now records the changed credential precedence, `/login
  exa`, `providers.autoThinkingMaxEffort`, and the opt-in `security.enabled`
  workflow with the reserved `security://` namespace. The remaining changelog
  items are primarily runtime, TUI, bridge, extension, and transport behavior.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  this run used the existing `check-version.sh`, `orchestrate.sh`, and
  `sync-from-official.sh` plus bounded inline review and verification.

## 2026-07-29

- Official OMP 17.1.7–17.1.8 is now mirrored; `references/VERSION` tracks
  `17.1.8-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance records the 17.1.7 migration from
  `inspect_image.enabled` to tri-state `inspect_image.mode`, plus the
  session-scoped `/vision` controls. It also records the operator-facing
  `omp cleanse`, conversational `/guided-goal`, and `tab.screenshot()` path
  behavior. The remaining 17.1.7–17.1.8 entries are runtime, UI,
  compatibility, or bug-fix changes without a new
  provider/security/architecture reference requirement.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-28

- Official OMP 17.1.6 is now mirrored; `references/VERSION` tracks
  `17.1.6-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance now records that `task.effort` is opt-in through
  `task.enableEffort` and that `task.maxEffort` caps effort across retries.
  The remaining 17.1.5–17.1.6 changelog items are runtime, UI, or tool
  implementation fixes without additional operator-reference changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-27

- Official OMP 17.1.4 is now mirrored; `references/VERSION` tracks
  `17.1.4-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance corrected the removed per-call `task`/`agent()` model
  selector and retained `task.effort`; security guidance now records config
  list redaction and the Anthropic OAuth grant-lifetime warning. Credential
  tombstones, Computer Use lifecycle details, Windows shell discovery, and
  other changelog items are runtime/UI behavior without additional operator
  reference changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-26

- Official OMP 17.1.3 is now mirrored; `references/VERSION` tracks
  `17.1.3-0` and `sync-state.json` records the upstream sync timestamp.
- Semantic review found no authored operator-reference update required. The
  17.1.3 changelog is limited to `find -exec` output isolation, mixed-language
  `ast_edit` inference, `retain` streaming-render resilience, and isolated
  session settings initialization; these are runtime/tool implementation fixes
  rather than new configuration or provider guidance.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-25

- Official OMP 17.1.2 is now mirrored; `references/VERSION` tracks
  `17.1.2-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance now records per-call `task.effort`, SearXNG
  `searxng.engines`, and the shared search-query directive/post-filter behavior.
  The expanded embedded shell builtins and remaining changelog items are
  runtime/tool-surface changes; consult the official mirror when needed and do
  not duplicate them into operator configuration guidance.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-24

- Official OMP 17.0.9 is now mirrored; `references/VERSION` tracks
  `17.0.9-1` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance now records ordered web-search/image provider lists,
  explicit keyless Firecrawl search, and per-call `task` model/fallback
  selection, plus the `task.isolation.apply` and `mcp.renderMarkdownResults`
  operator settings. Hindsight/RPC/Auto QA changes are runtime or client-surface
  details outside this skill's operator reference boundary; consult the official
  mirrors when needed.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-23

- Official OMP remains 17.0.7. The official mirror was refreshed and reviewed;
  tracked documentation content is unchanged, so no authored reference update
  was required. `references/VERSION` advances the maintenance revision to
  `17.0.7-2` and `sync-state.json` records the current sync timestamp.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-22

- Official OMP 17.0.7 is now mirrored; `references/VERSION` tracks `17.0.7-0`
  and `sync-state.json` records the upstream sync timestamp.
- Semantic review covered the 17.0.6–17.0.7 changelog and official provider
  documentation. Authored guidance now records exact `@`-prefixed gateway model
  ids, Codex-subscription image generation, Codex custom-endpoint credential
  isolation, and organization/workspace-scoped Anthropic and ChatGPT OAuth.
  The remaining release changes are runtime, UI, transport, or compatibility
  fixes and do not require operator-reference changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-20

- Official OMP 17.0.5 is now mirrored; `references/VERSION` tracks
  `17.0.5-0` and `sync-state.json` records the upstream sync timestamp.
- Semantic review found no new authored operator guidance required. The
  release adds Codex-subscription image generation and OTLP logs/metrics,
  while the existing references already cover `openai-codex`, fallback
  wildcard behavior, and `PI_CONFIG_FILES`; the remaining changes are
  runtime, UI, or compatibility fixes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-19

- Official OMP `17.0.4` synced cleanly. `references/VERSION` now tracks
  `17.0.4-0`; the official mirrors refreshed `CHANGELOG.md`,
  `environment-variables.md`, and `sync-state.json`.
- Authored review added the new `PI_CONFIG_FILES` settings-overlay behavior to
  `architecture.md`, `providers/models.md`, and `SKILL.md`. The 17.0.4 changelog
  otherwise contains runtime performance, recorder, task-schema, terminal, and
  shutdown fixes that do not require operator-reference changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-18

- Official OMP 17.0.3 synced cleanly. `references/VERSION` now tracks
  `17.0.3-0`; the official mirrors refreshed `CHANGELOG.md`,
  `environment-variables.md`, and `models.md`, and `references/sync-state.json`
  records the upstream sync timestamp.
- Authored review added the LiteLLM management-route discovery/fallback rules,
  the removal of Bing/Yahoo HTML-scraping search providers, and the updated
  `PI_TUI_RESIZE_IN_PLACE` semantics. The remaining 17.0.2/17.0.3 changes are
  runtime/TUI/plugin lifecycle fixes and do not require authored operator
  guidance changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` are available.

## 2026-07-17

- Official OMP 17.0.1 synced cleanly. `references/VERSION` now tracks
  `17.0.1-0`; the official mirrors refreshed `CHANGELOG.md` and
  `environment-variables.md`, and `references/sync-state.json` records the
  upstream sync timestamp.
- Authored review captured the xAI web-search proxy/header and OAuth-token
  boundary fix in `SKILL.md` and provider search/model guidance. The release
  is otherwise primarily plugin renderer resilience, CLI/path portability,
  TUI/session lifecycle fixes, and Windows/BSD-compatible builtins.
  The updated `PI_TUI_RESIZE_IN_PLACE` wording remains in the official mirror
  as source material; no authored TUI configuration section currently exists.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `check-version.sh`, `sync-from-official.sh`, and the existing orchestration
  and push helpers remain available.

## 2026-07-16

- Official OMP 17.0.0 synced cleanly. `references/VERSION` now tracks
  `17.0.0-0`; the official mirrors refreshed `CHANGELOG.md` and
  `custom-tools.md`, and `references/sync-state.json` records the upstream
  sync timestamp.
- Authored follow-up documents the 17.0.0 `hub`/`xd://` tool transport,
  removal of BM25 discovery, hidden `resolve`, the SSH agent, and legacy
  `report_finding` in `SKILL.md`, `references/providers/models.md`, and
  `references/architecture.md`. No provider-auth or security guidance change
  was required.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `fetch-official.sh`, and `release.sh`;
  `orchestrate.sh`, `sync-from-official.sh`, and `push-to-github.sh` were used.

## 2026-07-15

- Official OMP 16.5.1 synced cleanly. `references/VERSION` now tracks
  `16.5.1-1`, and the official mirrors refreshed for the 16.5.0/16.5.1
  changelog, provider organization-scoped Anthropic OAuth behavior, and
  `models.yml`/`models.yaml` plus `@role` selector semantics.
- Authored follow-up updated `SKILL.md`, `references/providers/models.md`, and
  `references/architecture.md`. The official changelog also contains runtime
  fixes for TUI, kernels, MCP, launch, retry fallback, and Windows packaging;
  no authored guidance change was needed for those items.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; `fetch-official.sh`
  is not present, so the existing `sync-from-official.sh` helper was used.

## 2026-07-13

- Official OMP 16.4.8 synced cleanly. `references/VERSION` now tracks
  `16.4.8-0`, `references/sync-state.json` records the new upstream timestamp,
  and the official changelog mirror refreshed to include the 16.4.8 release.
  Authored follow-up was limited to `references/providers/search.md`, `SKILL.md`,
  and this note; no architecture or security rewrite was needed.
- Missing daily-maintenance helpers in this repo remain
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`.
  `check-version.sh` and `orchestrate.sh` are present and usable.

## 2026-07-12

- Official OMP 16.4.5 was already mirrored in the local official docs. This
  maintenance run refreshed `references/sync-state.json` and bumped the skill
  revision to `16.4.5-1` without any authored reference changes.
## 2026-07-11

- Official OMP 16.4.2 sync refreshed `references/VERSION`,
  `references/sync-state.json`, and the official changelog mirror. I reviewed
  the changelog and updated authored references to add `novita` provider auth
  plus the `:max` thinking suffix in `references/providers/models.md`,
  `references/architecture.md`, and `SKILL.md`.

## 2026-07-10

- Official OMP 16.3.14 sync refreshed `references/VERSION`,
  `references/sync-state.json`, and the official changelog mirror. I reviewed
  the changelog and did not need authored updates in
  `references/providers/models.md`, `references/providers/search.md`,
  `references/architecture.md`, or `references/security.md` for this run.
## 2026-07-06

- Official OMP 16.3.11 sync refreshed `references/VERSION` and the official
  changelog mirror. Authored updates were limited to `SKILL.md` and
  `references/providers/models.md` for marker-based session-title parsing and
  `llama.cpp` `input_modalities` handling.

## 2026-07-05

- Official OMP 16.3.6 sync completed successfully after a networked retry.
  The refreshed changelog is mostly transcript/scrollback/retry/title behavior
  work and did not require authored updates to `architecture.md`,
  `security.md`, `providers/search.md`, or `providers/models.md` in this run.

## 2026-07-03

- Official OMP 16.3.2 changed `grep`, `glob`, and `ast_grep` from a `paths`
  array to a single `path` string that may contain semicolon-delimited
  entries. Captured this in the recent-notes section of `SKILL.md`; no other
  authored reference updates were needed in this run.

## 2026-06-28

- Official OMP 16.2.2 adds the `tiny` model role for lightweight background
  tasks. Authored docs now mention `tiny` in `providers/models.md`,
  `architecture.md`, and `SKILL.md`.
- Official 16.2.2 also mentions a new `textVerbosity` setting in the
  changelog, but the current mirrored docs do not expose a dedicated settings
  section yet. Keep this as a follow-up until the official docs surface the
  configuration shape.

## 2026-06-28 — 16.2.3 update

- Official OMP 16.2.3 enables V2 streaming remote compaction by default
  for compatible models. New config keys: `compaction.remoteStreamingV2Enabled`,
  `compaction.v2RetainedMessageBudget`.
- Multi-advisor support via `WATCHDOG.yml`/`WATCHDOG.yaml` files, with
  per-advisor models, tool subsets, and instructions. Added `/advisor configure`
  TUI. Advisors now have full tool access (no longer read-only).
- New settings: `statusLine.compactThinkingLevel` (glyph render of thinking
  level), `edit.citationTags` (OpenAI citation-marker emission).
- Session titles are now mutable with auto-replan refreshes and idle recaps.
- Fixed 30+ bugs across compaction, reasoning, MCP SSE transport, SSH,
  OpenAI/Codex session rehydration, skill prompts as user turns, and more.
- Linux desktop notifications via D-Bus (`PI_NO_DESKTOP_NOTIFY=1` to disable).
- Catalog pricing and context window updates for several models.
- Reasoning capability disabled for multiple providers in catalog.
## 2026-07-28 — 17.1.6 update

- Official mirrors refreshed from `can1357/oh-my-pi` to OMP 17.1.6;
  `references/VERSION` now tracks `17.1.6-0`.
- Authored provider guidance now includes the newly documented
  `siliconflow` / `siliconflow-cn` providers and their environment variables.
- The official environment-variable docs also add
  `PI_TUI_RAW_BACKSPACE_IS_CTRL` for SSH/container hops involving a Windows
  Terminal client. This is recorded as a terminal troubleshooting detail, not
  added to the core operator workflow.
- No authored architecture or security changes were warranted by the
  17.1.5–17.1.6 changelog entries reviewed in this run.
## 2026-07-31 — 17.2.2 update

- Official OMP 17.2.2 synced successfully; `references/VERSION` now tracks
  `17.2.2-0`, and the official changelog/environment-variable mirrors were
  refreshed.
- Authored guidance was limited to `SKILL.md`: the Ctrl+L live-mode shortcut
  and Alt+L display reset, unified PUT/CUT editing grammar, and Kitty/tmux
  placeholder controls. No provider, model, architecture, or security
  reference changes were warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-11 — 17.2.14 update

- Official OMP 17.2.14 synced successfully; `references/VERSION` now tracks
  `17.2.14-0`, and the official changelog, skills mirror, and sync state were
  refreshed.
- The 17.2.13–17.2.14 changes add SearXNG safe-search configuration,
  Cloudflare AI Gateway and Exa MCP search support, TinyFish domain filtering,
  the `externalThinking` setting, and distribution-aware update behavior.
  Existing authored search and security guidance covers the operator-facing
  boundaries; no additional authored provider, model, architecture, security,
  or `SKILL.md` changes were warranted.
- The official skills mirror also clarifies `AGENTS.md` ancestor discovery;
  this does not change the `omp-ops` operator workflow.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  the existing `sync-from-official.sh` helper was used.

## 2026-08-02 — 17.2.3 update

- Official OMP 17.2.3 synced successfully; `references/VERSION` now tracks
  `17.2.3-0`, and the tracked official changelog mirror was refreshed.
- Authored search and `SKILL.md` guidance now notes that Codex Web Search SSE
  errors preserve backend codes/messages, improving diagnosis of provider,
  credential, and endpoint failures.
- The remaining 17.2.3 changes concern prompt notation, shared headless
  Chromium lifecycle, and background-process cleanup. They do not change this
  skill's configuration, provider, model, or security guidance, so no further
  authored reference changes were warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-06 — 17.2.9 update

- Official OMP 17.2.9 synced successfully; `references/VERSION` now tracks
  `17.2.9-0`, and all seven tracked official mirrors plus sync state were
  refreshed.
- Authored architecture guidance now records that translated MCP importers
  preserve `enabled: false` and load project entries before same-named user
  entries for Claude Code, Codex, Gemini CLI, Cursor, Windsurf, and VS Code;
  OpenCode remains user-first.
- The remaining 17.2.9 changes concern browser discovery, Agent Hub/TUI,
  session migration, streaming/runtime robustness, and internal helpers. They
  do not warrant additional provider, model, or security guidance in this
  skill.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-07 — 17.2.10 update

- Official OMP 17.2.10 synced successfully; all seven tracked official mirrors
  and sync state were refreshed.
- The release adds extension-facing `omptype` compatibility changes and a
  trusted-extension allowlist; the latter is already covered in
  `references/security.md`. Agent Hub and stability fixes do not require new
  operator guidance in this skill.
- Added the missed operator-facing `providers.webSearchTimeoutSeconds` note to
  `references/providers/search.md`, based on the 17.2.5 official configuration
  change surfaced during this review.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, `release.sh`, and `fetch-official.sh`;
  the existing `sync-from-official.sh` helper was used.

## 2026-08-09 — 17.2.12 update

- Official OMP 17.2.12 synced successfully; `references/VERSION` now tracks
  `17.2.12-0`, and the tracked official mirrors plus sync state were refreshed.
- The 17.2.11–17.2.12 changelog entries concern Agent Plugins, session sharing,
  child-process metadata, provider fallback, web-search rendering, and runtime
  stability. No additional operator-facing provider, model, architecture, or
  security guidance was warranted.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-10 — daily maintenance

- Official OMP remains `17.2.12`; the official mirrors were refreshed and only
  `references/sync-state.json` changed because of the new sync timestamp.
- The 17.2.12 official material was reviewed again; no additional authored
  provider, model, architecture, security, or `SKILL.md` guidance was needed.
- Skill maintenance revision advanced to `17.2.12-2`; missing daily-maintenance
  helpers remain `fetch-official.sh`, `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`.

## 2026-08-09 — 17.2.12 update

- Official OMP 17.2.12 synced successfully; `references/VERSION` now tracks
  `17.2.12-0`, and the tracked official changelog mirror plus sync state were
  refreshed.
- The release fixes shell-output minimization, Codex Trusted Access account
  selection, keep-alive subagent memory retention, Z.AI MCP double-encoded
  search responses, `/handoff` error reporting, and model usage aggregation.
  These are runtime/stability fixes and do not warrant new provider, model,
  architecture, security, or `SKILL.md` operator guidance.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-13 — 17.3.1 update

- Official OMP 17.3.1 synced successfully; `references/VERSION` now tracks
  `17.3.1-0`, the official changelog and model mirror were refreshed, and sync
  state was updated.
- The 17.3.0 breaking change removes global `advisor.subagents`; authored
  architecture guidance now points operators to per-agent `advisor`
  frontmatter or `task.agentAdvisor`, including the automatic migration.
- Authored model guidance now documents `imageInputDecoder: stb` for custom
  vision backends that need WebP normalization. The remaining 17.3.0–17.3.1
  changes are runtime, packaging, UI, LSP, or platform fixes and do not
  warrant further provider, security, or `SKILL.md` changes.
- Missing daily-maintenance helpers remain `diff-official.sh`,
  `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the existing
  `sync-from-official.sh` helper was used.

## 2026-08-15 — 17.3.4 update

- Official OMP 17.3.2–17.3.4 synced successfully; `references/VERSION` now
  tracks `17.3.4-0`, the changelog and Antigravity environment-variable
  mirror were refreshed, and sync state was updated.
- The release changes are PDF backend/rendering, MCP Streamable HTTP
  interoperability, Gemini retry behavior, TUI/path/update fixes, and
  platform stability fixes. Existing authored guidance is sufficient; no new
  provider, model, architecture, security, or `SKILL.md` operator guidance
  is warranted. The new Antigravity User-Agent override variables are
  low-level client metadata rather than provider configuration rules.
- Missing daily-maintenance helpers remain `verify.sh`, `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, and `release.sh`; this run uses
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` plus bounded inline review and verification.

## 2026-08-17 — 17.3.5 update

- Official OMP 17.3.5 synced successfully; `references/VERSION` now tracks
  `17.3.5-0`, the official changelog mirror was refreshed, and sync state was
  updated.
- Added authored xAI guidance: paid `xai` and `xai-oauth` models use the
  Responses API, default to `grok-4.5`, and reject presence/frequency
  penalties and stop sequences for reasoning models. The Extensions settings
  group and remaining runtime/stability fixes do not require additional
  operator guidance in this skill.
- Missing daily-maintenance helpers remain `verify.sh`, `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, and `release.sh`; this run uses
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` plus bounded inline review and verification.

## 2026-08-18 — 17.3.7 update

- Official OMP 17.3.7 synced successfully; `references/VERSION` now tracks
  `17.3.7-0`, the official changelog mirror was refreshed, and sync state was
  updated.
- Authored model guidance now tracks the 17.3.6 xAI default change from
  `grok-4.5` to `grok-4.6`; the Responses API routing and reasoning-model
  parameter restrictions remain applicable.
- The 17.3.6 extension filesystem fallback and stats `--host` support are
  extension/runtime details and do not require additional `omp-ops` guidance.
- Missing daily-maintenance helpers remain `verify.sh`, `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, and `release.sh`; this run uses
  `check-version.sh`, `orchestrate.sh`, `sync-from-official.sh`, and
  `push-to-github.sh` plus bounded inline review and verification.

## 2026-08-12 — 17.2.15 update

- Official OMP 17.2.15 synced successfully; `references/VERSION` now tracks
  `17.2.15-0`, the official changelog mirror was refreshed, and sync state was
  updated.
- The release adds `--external-thinking`, `omp compress`, and broader /
  natural-language `omp cleanse` support; these are CLI/workflow additions
  outside the `omp-ops` operator guidance surface.
- The remaining changes concern think-tool transport eligibility, headless
  print-mode startup, MCP Streamable HTTP interoperability, handoff artifact
  copying, tar parsing hardening, display activity, and cleanse defaults. No
  additional authored provider, model, architecture, security, or `SKILL.md`
  guidance was warranted.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`; the
  existing `sync-from-official.sh` helper was used.

## 2026-08-24 — 18.0.3 update

- Official OMP 18.0.1–18.0.3 synced successfully; `references/VERSION` now
  tracks `18.0.3-1`, the official changelog mirror was refreshed, and sync
  state was updated.
- The 18.0.1 changelog announces provider-wide Amazon Bedrock guardrail
  settings, but the tracked official `models.md` mirror does not expose the
  setting names or schema. No authored configuration guidance was added to
  avoid inventing an unsupported contract; revisit when official schema
  documentation is available.
- The remaining changes are update-channel selection, edit parse-repair,
  transcript/UI behavior, runtime stability, and compatibility fixes. They do
  not require new provider, model, architecture, security, or `SKILL.md`
  guidance.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and bounded inline review and verification.

## 2026-08-30 — 18.0.11 update

- Official OMP 18.0.11 mirrors were refreshed for the changelog, environment
  variables, providers, models, and skills references; `references/VERSION`
  now tracks `18.0.11-0` and sync state records the official version.
- Authored model guidance adds the documented `compactionModel` and
  `remoteCompaction` options, with provider-support and endpoint caution.
  New provider aliases, search credentials, model-selection details, skill
  invocation provenance, and the compact status-line display are already
  represented by the refreshed official mirrors or existing authored guidance.
  The remaining release notes are runtime, UI, reliability, or bug fixes and
  do not warrant additional operator guidance.
- Missing daily-maintenance helpers remain `fetch-official.sh`,
  `diff-official.sh`, `maintenance-plan.sh`, `verify.sh`, and `release.sh`;
  this run uses `check-version.sh`, `orchestrate.sh`,
  `sync-from-official.sh`, and bounded inline verification.
