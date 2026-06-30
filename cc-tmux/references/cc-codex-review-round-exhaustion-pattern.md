# CC + Codex Review Round Exhaustion Pattern

## Context

Date: 2026-06-28
Session: agent-hub Phase 8 Slice 2
Pattern: Codex plans → CC executes → Hermes audits → Codex re-reviews → ...

## Problem

Codex independent review found NEEDS_FIX. CC fixed. Re-review found another NEEDS_FIX. CC fixed again. Re-review found a third NEEDS_FIX. At this point:
- 3 rounds of review exceeded the "≤3 rounds" limit
- 2 rejections exceeded the "≤2 rejections" limit
- CC session froze during the third fix attempt (token frozen >3min)

## Root Cause Analysis

1. **CC is not good at "fix-only" tasks**: When CC has already done implementation in a session, giving it a follow-up "fix these specific issues" task often leads to confusion, path searching, or freeze.
2. **Incremental review finds deeper issues**: Each round of review examines the code more carefully, finding issues that previous rounds missed. This is normal but means the round count grows.
3. **Manual fix is faster for small targeted changes**: The fixes needed (add try-catch at 3 specific locations) were small and precise. Manual patch was faster than coordinating another CC session.

## Resolution

After CC froze, killed the session and manually applied the remaining fixes:
- `handleControlPlaneRequest` outer try-catch
- `handleUnsupportedExecution` inner try-catch around `safeRequestType`
- `list_hosts` dispatch try-catch around `handleListHosts`

Final verification passed (80/80 tests + malicious getter probes).

## Pattern: Escalation Decision Tree

```
Codex review → NEEDS_FIX
├── Round 1-2, rejection 1-2 → CC fix → re-review
├── Round 3 or rejection 3 → STOP automatic loop
│   ├── Fix is small and targeted (<10 lines, specific locations known)
│   │   → Manual patch by Hermes
│   └── Fix is large or architectural
│       → Fresh CC session with narrowed scope
│       → Or escalate to user for decision
└── CC freezes during fix → Kill session → Manual patch or fresh session
```

## Key Lesson

The "≤3 rounds, ≤2 rejections" rule is a **hard stop for automatic loops**, not a suggestion. When reached:
1. Do not start another CC session for the same fix
2. Assess fix size: small → manual patch; large → fresh CC session or user escalation
3. The goal is progress, not perfect automation

## Real-World Validation (2026-06-28, Phase 8 Slice 2)

| Round | Codex Verdict | CC Action | Result |
|-------|---------------|-----------|--------|
| 1 | NEEDS_FIX | CC fixed injected collaborator try-catch | 80/80 pass |
| 2 | NEEDS_FIX | CC fixed session.js cleanup/list + index.js dispatch | 80/80 pass |
| 3 | NEEDS_FIX | CC froze during fix attempt | Kill session → manual patch |
| Manual | — | Hermes patched `handleControlPlaneRequest` outer catch + `handleUnsupportedExecution` inner catch | 80/80 pass |
| Final Codex | PASS | — | Verified |

**Key insight**: Round 3's issue (malicious `request.type` getter) was architecturally subtle — the outer catch calling `handleUnsupportedExecution` which itself accessed `request.type`, causing recursive throw. This type of "catch body re-throws" bug is exactly why the escalation rule exists: CC is not good at diagnosing architectural throw-propagation chains.

## Codex Review Test Pattern: Malicious Getter Injection

Codex used this pattern to verify fail-closed boundaries:

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

This pattern should be used whenever verifying "never throws" contracts on functions that accept external objects.

## Related Pitfalls

- Pitfall #14: CC xhigh effort freeze
- Pitfall #16: Token freeze detection
- Pitfall #30: Opus UltraCode overthinking
- Pitfall #37: CC frozen during fix → manual patch (this session)
