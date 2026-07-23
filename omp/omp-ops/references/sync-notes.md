# Sync Notes

## 2026-07-24

- Official OMP 17.0.9 is now mirrored; `references/VERSION` tracks
  `17.0.9-0` and `sync-state.json` records the upstream sync timestamp.
- Authored guidance now records ordered web-search/image provider lists,
  explicit keyless Firecrawl search, and per-call `task` model/fallback
  selection. The new MCP Markdown rendering toggle and Hindsight/RPC/Auto QA
  changes are runtime or client-surface details outside this skill's operator
  reference boundary; consult the official mirrors when needed.
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
