# Agent-hub F0 delegation/audit lessons

Use for small contract slices delegated through CC where tests can pass while semantics are still wrong.

## Lessons

- Treat CC self-report and green tests as evidence, not verdict. Auditor must re-read the implementation and assert the contract semantics from the controlling spec/roadmap.
- For contract work, audit semantic invariants explicitly: accepted source enum, returned shape, fail-closed behavior, no hardcoded backend, and no raw content leakage.
- A done file can be stale. Check mtime and content against the latest task; if it still describes old failures or old counts, keep waiting or audit current files directly.
- New tmux/Claude panes may show previous completion output and leave the new task line sitting at the prompt. After `send-keys ... Enter`, inspect pane bottom; if the line is still after `❯`, press Enter once rather than resending the task.
- If CC stalls on mechanical test-input replacement after the semantic implementation is correct, the delegator may make a minimal auditor patch and rerun full verification instead of burning another CC turn.
- Evidence/report adapters need a second semantic audit beyond “no raw output copied”: verify the report has the project-level kind/schema, claims include an explicit `evidence_bound: true`, and the event carries a safe `metadata_ref` summary so downstream reviewers can locate the report context.
- Raw-field checks must include the upstream contract object too, not only the new `evidence`/`claims` input. A bridge/session object can reintroduce `body`, `transcript`, `output`, or other raw fields if the adapter trusts it blindly.
- Dimension/audit mappers need stricter fixture hygiene than ordinary routing tests: use deep clones (`structuredClone`, factory functions) for shared dimension fixtures. Shallow copies like `{ ...VALID_DIMENSIONS }` leave nested objects shared; deleting `intent.verdict` in one test can poison later event/metadata tests and create false contract failures.
- When a CC session exceeds the correction loop on a small mechanical issue, stop delegating: freeze/kill the session, read the current production/test files yourself, patch the minimal auditor fix, then rerun targeted + broader tests. Do not let CC keep editing after Hermes has repaired the fixture or contract, or it may overwrite the auditor patch.
- Evidence-dimension rules are policy, not convenience: `claim_ref` may coexist with strong anchors, but `claim_ref` alone is never sufficient — even when the dimension verdict is `fail`. A failed audit still needs a concrete evidence anchor (`test_ref`, `diff_ref`, `evidence_report_ref`, `command_output_ref`, etc.) locating why it failed.

## Audit checklist for contract slices

- Does implementation return the exact contract shape promised, not just a convenient envelope?
- Does generated `AgentRunEvent.source` equal the actual producer/backend?
- Does generated `AgentRunEvent.metadata_ref` carry enough safe summary data for downstream audit, instead of emitting a bare event?
- Does backend mismatch fail closed before event emission?
- Are evidence/session/bridge-contract fields refs or safe metadata only?
- Are self-reported tool claims explicitly marked as evidence-bound and rejected when no real evidence refs exist?
- Are forbidden raw fields checked recursively through objects and arrays across every input object, including upstream contracts?
- Are tests using valid domain enum values, not placeholder names that accidentally encode the wrong model?
- Were targeted tests and repository-level node tests rerun after auditor patches?
