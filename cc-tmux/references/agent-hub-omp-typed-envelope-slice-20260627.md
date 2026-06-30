# Agent-hub OMP typed lifecycle envelope slice · 2026-06-27

## Context

During agent-hub Phase 7 OMP lifecycle work, after registry/discover/render/apply/validate/audit-route/fail-closed runtime slices, Slice 8 introduced a typed OMP lifecycle envelope so review-worker does not depend only on regex text matching.

This belongs to the Codex → CC → Hermes STDD pattern: Codex produces the plan, CC implements, Hermes audits and owns final acceptance.

## Durable pattern

Use a typed metadata-only envelope as the structural front door for OMP lifecycle intents:

```js
{
  task: {
    type: 'omp.lifecycle',
    action: 'discover' | 'render-plan' | 'validate-metadata' | 'audit-metadata' | 'apply-plan',
    profile: 'page'
  },
  constraints: {
    execute: false,
    live: false,
    cross_profile: false
  },
  run_id: 'optional-safe-token'
}
```

Rules:

- `execute`, `live`, and `cross_profile` must be exactly `false`.
- `apply-plan` means planning metadata only; it must not imply apply execution.
- Typed envelope recognition happens before legacy regex detection.
- Legacy regex route tests stay as fallback compatibility.
- Valid and invalid typed envelopes both route to review/control plane with `execute=false`.
- OMP runtime lane remains unavailable unless a later gated runtime slice explicitly enables it.
- Metadata-only publish smoke must use an injected fake publisher; never open live NATS/network/env-derived endpoints in this slice.

## Files used in the Slice 8 implementation

- `iii/workers/omp-worker/src/envelope.js`
- `iii/workers/omp-worker/test/envelope.test.js`
- `iii/workers/review-worker/src/routing.js`
- `iii/workers/review-worker/test/routing.omp-envelope.test.js`
- `AGENTS.md` route snapshot

## Audit pitfall found

Initial implementation rejected unknown `task.action` but echoed the raw action value in an error message. Because review-worker attached `envelope_errors` to route decisions, a hostile envelope could leak a body/secret-shaped action string through decision JSON or publish payloads.

Bad pattern:

```js
unknown lifecycle action: ${typeof task.action === 'string' ? task.action : typeof task.action}
```

Fix pattern:

```js
const actionKind = task.action === undefined ? 'missing' : typeof task.action;
errors: [
  {
    code: 'UNKNOWN_ACTION',
    path: 'task.action',
    message: `unsupported action (kind: ${actionKind}); allowed: discover|render-plan|validate-metadata|audit-metadata|apply-plan`
  }
]
```

Never echo raw untrusted enum/string values in validation errors when those errors are propagated into route decisions or events. Report kind/category plus allowed values instead.

## Tests to require

At minimum:

- Valid typed envelope accepted and sanitized.
- `apply-plan` accepted only as non-executing metadata.
- Unknown action rejected without echoing raw action value.
- `execute:true`, `live:true`, `cross_profile:true` rejected.
- Forbidden fields (`payload/body/content/env/token/session/logs/memory/transcript/prompt`) rejected and absent from output JSON.
- Malformed input never throws.
- Review-worker recognizes typed envelope and routes `lane=review`, `execute=false`, OMP unavailable control_plane.
- Invalid typed envelope route does not leak hostile raw action or forbidden fields.
- Legacy regex route still passes.
- Injected fake publisher smoke keeps payload metadata-only and does not touch live NATS.
- `iii/config.yaml` still has no `omp-worker` registration.

## Verification commands from the slice

```bash
node --test iii/workers/omp-worker/test/envelope.test.js
npm test --prefix iii/workers/omp-worker
npm test --prefix iii/workers/review-worker
npm test --prefix iii/workers/gc-worker
npm test --prefix iii/workers/usage-worker
npm test --prefix iii/workers/codex-worker
npm test --prefix iii/workers/cc-worker
node iii/workers/omp-worker/src/index.js
```

Observed final totals in this run:

```text
envelope.test.js: 10/10
omp-worker: 109/109
review-worker: 46/46
gc-worker: 21/21
usage-worker: 29/29
codex-worker: 32/32
cc-worker: 52/52
Total: 289/289
```

## Audit focus for future similar slices

- Reject or sanitize before routing; route decisions must not carry raw input.
- Inspect every error field attached to decisions/events; errors are also an exfil path.
- Test hostile values in unexpected enum fields, not only forbidden field names.
- Keep route decisions `execute=false` until a separate high-risk gated runtime slice exists.
- Prefer fake/injected publisher tests for metadata event shape before any live bus smoke.
