# Action Affordance Contract Slice Review

Use when a renderer-facing/client-replaceability slice changes who decides whether a UI action is enabled.

## Trigger

- Frontend currently infers clickability from `node.state`, CSS, DOM, edge style, or labels.
- User emphasizes: frontend is replaceable and only displays/forwards intents.
- A map/UI contract has visible nodes or edges that are not currently reachable.

## Pattern

1. **Codex plans first**
   - Read-only, fixed output schema: goal, files, RED tests, minimal implementation, verification commands, risks, CC boundaries.
   - If the workdir is not a git repo, use `codex exec --skip-git-repo-check --sandbox read-only`.

2. **CC implements bounded slice**
   - Add RED tests that expose the old frontend inference.
   - Move action availability into the Engine/contract, e.g. `node.actions[]` with `{type, payload, enabled, disabled_reason}`.
   - Keep schema changes compatible when possible: optional field in schema, but fixture/engine tests can require it for the new slice.
   - Renderer and DOM-free probes must consume the contract; they must not recalculate legality.

3. **Hermes independently verifies**
   - Re-run target tests and full test suite.
   - Smoke real runtime payload: verify enabled/disabled actions are present in WebSocket/HTTP output.
   - Browser DOM smoke: only `enabled=true` elements receive click handlers/cursor; disabled nodes are still visible but not actionable.
   - Check event DB or persistent state did not change when the slice should be read-only/test-only.

## Acceptance checklist

- Engine emits action affordances.
- Renderer gates click/keyboard handlers on `action.enabled`, not `node.state` or edge style.
- DOM-free/non-Web probe consumes the same action affordances.
- A visible but unreachable/locked/rumored node does **not** produce a move intent.
- Server-side validation remains as final safety gate; do not remove it.
- Documentation/control-plane notes are updated if this changes a project invariant.

## Pitfalls

- Do not call this "frontend fix" if the decision still lives in the client; the point is to make the decision Engine-owned.
- Do not overfit disabled reasons when multiple paths exist. It is okay for the minimal slice to use `unreachable` as long as `enabled` is correct.
- Do not let compatibility fallback silently reintroduce inference. If old payload lacks `actions`, probes should return no enabled actions rather than guessing.
- Residual CC input like `commit this` must never be submitted unless the user explicitly authorized git actions.
