# Fail-Closed Nested Try-Catch Pattern

## Context

Date: 2026-06-28
Session: agent-hub Phase 8 Slice 2 ssh-worker
Problem: Injected collaborators (session store, registry, request objects) can have malicious getters that throw. Simple inner try-catch is not enough.

## The Discovery

Initial approach: Wrap injected collaborator calls in try-catch.

```javascript
// remote.js — inner try-catch
function acquireRemote(request, deps) {
  try {
    const created = sessions.create({...});
  } catch {
    return fail('injected_collaborator_failed');
  }
}
```

This handles `sessions.create()` throwing, but Codex review found two more issues:

1. **`request.type` getter throws**: `isPlainObject(request) && typeof request.type === 'string'` — `isPlainObject` itself doesn't trigger getters (only checks `typeof`), but `typeof request.type === 'string'` **does** read the property, triggering a throwing getter. The exception bubbles out of `handleControlPlaneRequest`.
   - *Note*: Simply wrapping `typeof request.type` in try-catch is insufficient because the fallback path (`handleUnsupportedExecution`) also accesses `request.type`.

2. **`handleUnsupportedExecution` recursively throws**: When the outer catch calls `handleUnsupportedExecution(request)`, it internally calls `safeRequestType(request)` which also accesses `request.type` — causing the same throw, but now uncaught.
   - *This is the subtle bug*: the catch body itself throws, creating an infinite throw loop if not handled.

3. **`deps.registry` getter throws**: `handleListHosts(deps)` accesses `deps.registry` — if registry is a getter that throws, it bubbles.

## The Fix (Three Layers)

### Layer 1: Outermost try-catch in entry point

```javascript
export function handleControlPlaneRequest(request = {}, deps = {}) {
  try {
    return _handleControlPlaneRequest(request, deps);
  } catch {
    return handleUnsupportedExecution(request);
  }
}
```

This catches ANYTHING that bubbles out of the inner logic.

### Layer 2: Inner try-catch in `handleUnsupportedExecution`

```javascript
export function handleUnsupportedExecution(request = {}) {
  let requested_type = 'unknown';
  try {
    requested_type = safeRequestType(request);
  } catch {
    // Malicious getter — fail closed silently
  }
  return { ok: false, decision_code: 'unsupported', requested_type, ... };
}
```

This prevents the recursive throw when the outer catch calls `handleUnsupportedExecution`.

### Layer 3: Dispatch-specific try-catch

```javascript
case 'list_hosts':
  try {
    result = handleListHosts(deps);
  } catch {
    return handleUnsupportedExecution(request);
  }
  break;
```

This catches registry getter throws during specific dispatch paths.

## Verification

```javascript
// Test 1: malicious request.type getter
const badReq = {};
Object.defineProperty(badReq, 'type', {
  get() { throw new Error('type boom'); }
});
const r = handleControlPlaneRequest(badReq, {});
assert.equal(r.decision_code, 'ssh_remote_execution_unsupported');

// Test 2: malicious deps.registry getter
const badDeps = {};
Object.defineProperty(badDeps, 'registry', {
  get() { throw new Error('registry boom'); }
});
const r2 = handleControlPlaneRequest({type:'list_hosts'}, badDeps);
assert.equal(r2.decision_code, 'ssh_remote_execution_unsupported');
```

## Key Lesson

Fail-closed is not just "wrap the obvious calls". It's "assume ANY property access on ANY injected object can throw, and layer catches at every level".

The pattern:
1. **Outer catch**: catches anything that bubbles out of the main logic
2. **Inner catches**: prevent the outer catch's fallback from itself throwing
3. **Dispatch catches**: catch specific path exceptions before they reach the outer catch

## When to Apply

- Any function that accepts objects from untrusted/external sources
- Worker entry points that process requests from message queues/NATS
- Any "never throws" contract boundary

## Related

- Pitfall #23: grep -f empty line matching everything
- Agent-hub control plane fail-closed runtime pattern
