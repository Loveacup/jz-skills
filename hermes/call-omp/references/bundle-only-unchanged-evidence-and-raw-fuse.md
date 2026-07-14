# Bundle-only audits: unchanged evidence and raw-output fuse

## Problem class

A bundle-only auditor may review only `diff.patch` and miss an important pre-existing test or contract in HEAD. This can create a false concern even when the unchanged test already exists. Separately, an OMP run may emit tens of megabytes of tool-loop reasoning despite an instruction not to run tools.

## Evidence package rule

For every criterion that depends on unchanged code, include a concise evidence excerpt in the Hermes verification summary:

- exact file and line range;
- relevant test name and key assertions;
- command, exit code, and test count;
- scoped diff name list;
- live-E2E result when applicable.

Do not assume a diff-only manifest lets the auditor discover unchanged tests. Keep secrets, signed URLs, cookies, headers, private endpoints, and raw network events out of the summary.

## Verdict handling

1. Monitor raw size even when `omp-send` exits 0.
2. If raw output exceeds the configured fuse (20 MB in the current workflow), do not call it pass merely because a compact JSON verdict exists.
3. Compare every concern against current source and Hermes command evidence.
4. If a concern is contradicted by a cited unchanged test, reject the verdict and record the exact evidence.
5. If two equivalent OMP attempts both tool-loop or generate oversized raw output, stop equivalent retries. Downgrade explicitly to Hermes original test evidence plus a Codex read-only independent review; report OMP as failed/degraded, never pass.

## Minimal verification summary template

```text
Scoped files: ...
Unchanged contract evidence: path:lines, test_name, key assertions
Targeted command/result/exit: ...
Full command/result/exit: ...
Release command/result/exit: ...
Live E2E: ...
Privacy statement: no secret/runtime-private values persisted
```
