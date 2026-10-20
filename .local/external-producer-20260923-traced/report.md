# Traced wave prerequisite failure

Aggregate: **BLOCKED**. Dispatch outcome: **failed**. Deployment: **NOT_ADMITTED**.
Task `task_cb75184c54d9`, dispatch `ctx_84ae4ed34c4b`.
This producer is not the final judge. No independent review or execution-host settlement is claimed.

## Completed

- Read the v3 trace contract and coordinator pre-dispatch baseline; queried qmd for `call-omp trace` (no directly relevant contract history retrieved).
- Captured producer initial and final read-only snapshots, including call-omp source bytes, Git identity, Git config/hook/attribute hashes, OMP launcher resolved executable hash, prior review evidence hashes, runtime metadata, Hermes SOUL hash and credential metadata only.
- Scanned effective included Git executable settings before any status/commit; no matching filter/process/fsmonitor/textconv/command/hooksPath/attributesFile/include settings returned. Bound exact pre-commit bytes in `pre-commit.bound.txt`. No Git status, commit, hook execution or remote action occurred.
- Recorded actual observer feasibility probes with argv, timestamp, exit and stderr in `commands.jsonl`.
- Produced three explicit NOT_RUN/BLOCKED receipts; each has zero attempts and zero retries.

## Blocking evidence and dynamic coverage limits

`/usr/sbin/dtrace -l -n syscall::open*:entry` exited 1: `DTrace requires additional privileges`. SIP is enabled; UID is 501. `/usr/bin/fs_usage -w -f filesys -t 1` exited 1: must run as root. These are prerequisite probes, not traces of an OMP scenario. An earlier mistaken `/usr/bin/dtrace` path returned not found; the correct `/usr/sbin/dtrace` probe above is decisive.

No adequate cross-process dynamic-load observer was established. No actual loaded scripts, modules, templates, runtime config, extensions, MCP inputs, native libraries or shared-cache entries for an OMP scenario were captured. macOS version/build and kernel identity were captured, but these are host identity only and do not prove a loaded dependency set. Static source hashes and launcher hashes are likewise not dynamic-load evidence.

Shell execution tracing would at most observe shell statements; Python audit hooks would at most observe instrumented Python interpreters after hook installation; loader diagnostics would at most observe supported loader events and can be filtered across protected processes. These are untested partial alternatives, not proven substitutes for the required observer. No injection, wrappers, OMP version invocation, provider invocation or extension/MCP execution was attempted.

Coordinator explicitly replied through `orca orchestration ask`: do not run the scenarios, do not elevate or weaken the contract, create three blocked receipts, make no commit, and settle failed. The returned text is saved in `coordinator-direction.json`.

## Baseline comparison

See `baseline-comparison.json` for all 22 individual comparisons and the missing categories. Starting and ending HEAD both equal `3c0caa8bdcb9c6b89a066ed8a7a00adab708fd60`; call-omp source tree, launcher, Git inputs/hooks/attributes and prior evidence remained equal across producer snapshots.

The coordinator snapshot supplies call-omp Git identity and launcher symlink metadata, but lacks the repository tree, executable hash/version, OMP config/extensions/MCP inputs, Git hook/filter/attribute/remote baseline and full prior evidence tree. A later snapshot cannot reconstruct those pre-dispatch facts. Producer snapshots begin after exploratory read-only commands, not at the exact dispatch instant.

Gateway state changed between coordinator and producer captures. Runtime OMP metadata, watched surfaces and process observations changed between producer captures. No timestamped actor evidence attributes those changes; their status is BLOCKED. This worker did not invoke OMP or mutate those surfaces. Volatile differences cannot be treated as either worker-caused or proven benign. Process snapshots record command names, not unrelated full argv or environments; they are not exact cancellation identity evidence.

## Files and verification

All newly created files are under `.local/external-producer-20260923-traced/`. No source repair was justified or made, and there is no local commit. `checklist.json` individually marks checks PASS/BLOCKED; PASS entries cover only their stated limited checks. `normal-receipt.json`, `controlled-failure-receipt.json`, and `cancellation-receipt.json` explicitly distinguish missing worker exit, business assertion and acceptance evidence.

Verification: JSON readback, receipt attempt counts, HEAD identity equality, source-tree equality, output permissions and SHA-256 manifest. No tests, linters, formatters or project-wide suites ran. Exact probe commands are logged; exploratory command coverage is described in `preflight-command-notes.md` and remains incomplete rather than being labeled PASS.

Remaining: adequate observer authority/capability, complete coordinator baseline with actor-attributed drift, then a separately authorized traced wave and independent review after positive host settlement. Do not retry these scenarios under this settled dispatch.
