# Agent-hub OMP lifecycle STDD slice notes (2026-06-27)

Session lesson from building Phase 7 `omp-worker` slices under the Codex → CC → Hermes pattern.

## Slice sequence that worked

1. **registry + validator**
   - Static registry fixture under `agent-hub-skill/config/`.
   - Pure validators for profile names, permissions, subjects, and paths.
   - Do not register the runtime lane yet.
2. **discover read-only**
   - Metadata-only discovery of `~/.omp/agent` and `~/.omp/profiles/*/agent`.
   - `.env`: existence/type/readability/mode-known only.
   - `agent.db`: existence/type only.
   - `logs`: existence/type only; never list logs.
   - Fake FS tests assert `readFile` call count is zero.
3. **render plan**
   - Pure `renderProfilePlan(profileEntry, options)`.
   - `execute=false`, `requires_review=true`, `redacted=true`, `overwrite=false`.
   - Only plan `config.yml`, `mcp.json`, `.env.example`; never real `.env`.
   - Existing targets become conflicts, not write actions.
4. **apply skeleton**
   - Default dry-run; writes require `confirm:true && dryRun:false`.
   - Use injected fake FS only in tests; no Node FS adapter yet.
   - Content must be supplied by `action.content` or `contentByKind`; apply does not invent templates.
   - Re-check existence before write and use exclusive create (`flag:'wx'`).
   - Critical audit blocker: a denylist for `.env` / `iii/config.yaml` is not enough. Add a positive allowlist before any adapter access: `~/.omp/profiles/<valid-profile>/agent/<expected-basename>` or an equivalent absolute tail.
5. **validate helpers**
   - Pure helpers over injected inputs only.
   - `.env` validation outputs key names and `KEY=***` preview only.
   - `mcp.json` validation accepts injected object/string and outputs command/args count/env key names only.
   - Summary is whitelist-built metadata only; do not copy session/memory/log/body/content/transcript fields.
6. **metadata-only audit/event + route recognition**
   - Add pure audit/event helpers that build lifecycle events from injected metadata only.
   - Event metadata must be allowlisted by construction; never pass through raw input. Drop env values, MCP env values, command output, prompt body, session/memory/log/transcript/content.
   - Route recognition may identify OMP lifecycle intents, but must still return `execute=false`, review/control-plane fallback, and leave `iii/config.yaml` unmodified.
   - Unsafe OMP asks should be explicit denials/review decisions: secret/session/log/memory reads, cross-profile execution, gateway enablement, runtime/lane registration.
   - User clarified the durable architecture rule: **all agent lanes, including CLI-backed lanes such as Codex, must be continuously monitorable and intervenable**. Encode this as a uniform `control_plane` contract on every route decision, not just OMP-specific branches.
   - Useful shape: `control_plane: { monitoring_required:true, intervention_required:true, monitorable, intervenable, runtime_available, status }`.
   - For disabled OMP runtime: `runtime_available:false`, `intervenable:false`, `status:'unavailable'`; for review fallback: `status:'review_only'`; for CC/Codex execution lanes: monitorable/intervenable true when their catalog capabilities support it.
   - Ensure NATS route event payloads include the full decision with `control_plane`, so event consumers do not lose the monitoring/intervention contract.

## Audit/closeout checklist

- Re-run focused tests plus adjacent regressions yourself; do not trust CC self-report.
- For agent-hub, also run all worker tests before commit when the slice touches shared policy/safety boundaries.
- Check forbidden files explicitly: `iii/config.yaml`, runtime registration, real `~/.omp`, and any routing side effect.
- For routing/control-plane changes, assert **every** route decision has an explicit monitoring/intervention contract and `execute=false` remains unchanged.
- Static leak scan for obvious key/token/value leakage in source and tests.
- Update both Obsidian authority docs and in-repo snapshots (`AGENTS.md`, README/roadmap if present).
- Refresh qmd after Obsidian edits.
- Commit/push only after the above evidence is fresh.

## Residual-input pattern

CC repeatedly left next-step suggestions in the input box (`proceed to Slice 3`, `commit this`, `git diff ...`). Do not press Enter. If the user authorized continuous execution, Hermes may kill/finish the verified session and start the next slice from a fresh Codex plan. Otherwise preserve evidence and ask.
