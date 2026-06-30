# Agent-hub OMP lifecycle: control-plane contract + fail-closed runtime entry

## When this applies

Use this reference when implementing or reviewing agent-hub routing/lifecycle slices where a lane is recognized by the control plane before the runtime is actually enabled.

This came from agent-hub Phase 7 OMP lifecycle follow-up slices after registry/discover/render/apply/validate were already in place.

## Durable lesson

A lane being unavailable is not permission to make it invisible or untracked. Route decisions and metadata events must still make the control-plane contract explicit.

For every agent lane — including CLI-backed lanes like Codex — route decisions should carry a uniform control-plane block:

```js
control_plane: {
  monitoring_required: true,
  intervention_required: true,
  monitorable: boolean,
  intervenable: boolean,
  runtime_available: boolean,
  status: 'available' | 'unavailable' | 'review_only' | 'unsupported'
}
```

Suggested semantics:

- `cc`: `monitorable=true`, `intervenable=true`, `runtime_available=true`, `status='available'` when available.
- `codex`: even though it is CLI-backed/stateless, if the hub supports monitor/cancel/interrupt/status around runs, advertise `monitor`/`intervene` in the catalog and set `monitorable=true`, `intervenable=true`.
- `review`: `monitorable=true`, `intervenable=false`, `status='review_only'` — it gates/denies but does not steer a running agent.
- unavailable future lane such as `omp`: `monitorable=true` as control-plane metadata, `intervenable=false`, `runtime_available=false`, `status='unavailable'`.

Keep `execute=false` unless a separate, explicitly gated runtime slice enables execution.

## OMP routing pattern

For OMP lifecycle recognition before runtime enablement:

- Recognize lifecycle intents (`discover`, `render`, `validate`, `audit`, `apply-plan`, typed task/capability envelope).
- Route to `review`/control plane, not to an executable OMP lane.
- Add explicit decision codes:
  - `omp_runtime_unavailable`
  - `omp_runtime_disabled`
  - `omp_secret_access_denied`
  - `omp_cross_profile_execution_denied`
- Preserve `execute=false` and `requires_review=true`.
- Unsafe asks (real `.env`, session/log/memory reads, gateway enablement, cross-profile execution, lane registration) must be denied/reviewed explicitly, not silently ignored.
- Route event payloads should include the full decision, including `control_plane`, so NATS/audit consumers retain monitorability semantics.

## Metadata-only audit/event helper pattern

A lifecycle event builder should be allowlist-by-construction:

```js
metadata: {
  profile,
  lifecycle_action,
  status,
  decision_code,
  check_count,
  finding_count,
  error_count,
  warning_count,
  mcp_server_count,
  env_key_count,
  file_action_count,
  conflict_count
}
```

Never copy raw input. Drop unknown keys and forbidden content fields such as:

- env/MCP values
- command output
- prompt/body/content/transcript
- session/memory/log text
- credentials/tokens

Tests should serialize the event/result and assert recognizable secret/body markers are absent.

## Fail-closed runtime entry pattern

When a worker package already points `dev/start` to `src/index.js`, but the runtime should not be enabled yet, add a fail-closed entry instead of leaving a missing file or accidentally enabling runtime work.

Export static/control-plane APIs only:

```js
getWorkerMetadata()
getCapabilities()
describeRuntimeContract()
healthCheck()
handleUnsupportedExecution(request = {})
handleControlPlaneRequest(request = {})
```

Rules:

- `getWorkerMetadata()` reports `registered:false`, `runtime_available:false`, `execution_enabled:false`, `metadata_only:true`, `redacted:true`.
- `getCapabilities()` explicitly separates supported metadata/planning helpers from unsupported execution capabilities.
- `healthCheck()` is static-only and includes `external_runtime_checked:false`.
- `handleControlPlaneRequest()` only allows safe static types such as `metadata`, `capabilities`, `contract`, `health`.
- Every execution-shaped or unknown request returns unsupported with `execute:false`.
- Do not echo raw request `payload`, `body`, `content`, `env`, or `token`; at most echo a sanitized request type.
- Direct `node src/index.js` should exit 0 and print static fail-closed JSON.

Forbidden in the fail-closed entry:

- importing `fs`, `child_process`, `net`, `http`, `https`
- reading `process.env`
- touching real `~/.omp`, `.env`, or `mcp.json`
- profile apply/render-apply/live validate/smoke
- cross-profile execution
- iii config registration

## Tests to require

For routing/control-plane:

- Every route decision includes `control_plane` and `execute=false`.
- Codex/CC decisions are monitorable and intervenable when available.
- Review fallback is `review_only`.
- OMP preferred-lane fallback and lifecycle routes report runtime unavailable and not intervenable.
- Published route event payload includes `control_plane`.
- `iii/config.yaml` contains no OMP registration.

For fail-closed runtime entry:

- Import fails RED before `src/index.js` exists.
- Metadata/capabilities/contract/health return static safe values.
- Execution-shaped and unknown requests return unsupported with `execute=false` and no raw payload leakage.
- Source scan asserts no forbidden imports / no `process.env`.
- `node src/index.js` exits 0 and prints JSON fail-closed status.
- Existing review-worker OMP lifecycle route remains `execute=false` with `control_plane`.

## Review pitfall

Do not accept a slice just because OMP lifecycle routes carry monitorability fields. Check all fallback branches too, especially generic `preferred_lane:'omp'` or unavailable-lane branches. The first implementation often adds the contract only to the obvious lifecycle branch and forgets the generic fallback.
