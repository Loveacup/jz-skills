# Agent-hub usage-worker CPU hot-loop hardening (2026-06-27)

## When this applies

Use this pattern when an iii worker periodically shells out to a CLI and the host shows sustained CPU/swap pressure, especially when the worker is managed by iii VM isolation and the CLI may spawn grandchildren.

This case: `usage-worker` periodically ran `npx ccusage claude --json`; the iii VM burned ~125% CPU and swap was high. Stopping the worker removed the VM, but short-lived `ccusage --json` process trees could still appear.

## Operational triage

1. Pause feature work and inspect live process state.
2. Identify the exact hot worker/process (`ps`, `iii worker list`, relevant logs).
3. Stop the specific iii worker through iii first, not blind `kill -9`:
   - `iii worker stop usage-worker`
4. Confirm the worker is absent/stopped and only unrelated workers remain.
5. Check for leaked CLI child/grandchild processes (`ccusage`, `npx`, `node`) and clean only if they persist or burn CPU.
6. Do not restart the problematic worker until the code fix is committed and a bounded smoke is explicitly authorized.

## Code hardening pattern

For a periodic collector that invokes a CLI:

- Add timeout to the CLI execution.
- Add singleflight around periodic collection so intervals cannot overlap.
- Prefer injected dependencies for tests; never call the real CLI in unit tests.
- If the CLI is invoked through a wrapper (`npx`, `npm exec`, shell), do **process-tree** cleanup, not just direct-child cleanup.

### POSIX process-group kill pattern

Use `spawn()` instead of `execFile()` when grandchildren matter:

```js
const child = spawn('npx', ['ccusage', 'claude', '--json'], {
  stdio: ['ignore', 'pipe', 'pipe'],
  detached: process.platform !== 'win32',
});

// timeout / maxBuffer
if (process.platform !== 'win32') {
  process.kill(-child.pid, 'SIGKILL'); // negative pid => process group
} else {
  child.kill('SIGKILL');
}
```

Why: `execFile(..., { timeout })` kills the direct `npx` process, but a `node`/native CLI grandchild may survive as an orphan.

### Buffer hardening

If stdout and stderr are both collected:

- Track `stdoutBytes` and `stderrBytes`.
- Enforce a shared budget in **both** handlers: `stdoutBytes + stderrBytes > maxBuffer`.
- Keep stderr preview bounded (e.g. first 2KB) rather than retaining unbounded stderr.
- Kill the process group on timeout or buffer overrun.

Pitfall caught by review: checking `stdoutBytes > maxBuffer` only in stdout and `stdoutBytes + stderrBytes` only in stderr lets `stderr first, stdout second` bypass the shared budget.

## Tests to require

Unit tests should use fake child processes (`EventEmitter` + `PassThrough`) and injected `spawnImpl` / `killImpl`.

Required cases:

- command/args/options include `detached` on POSIX
- success parses stdout JSON
- timeout kills `-pid` and rejects `CCUSAGE_TIMEOUT`
- stdout over maxBuffer kills and rejects `CCUSAGE_MAX_BUFFER`
- stderr over maxBuffer kills and rejects `CCUSAGE_MAX_BUFFER`
- stderr first + stdout second exceeding shared budget also kills/rejects
- huge stderr remains preview-bounded
- spawn error propagates
- periodic singleflight skips overlap and releases after success/failure

## Codex review value

This session validated the Codex→CC→Hermes loop:

- CC implemented the first pass.
- Codex found that `execFile` timeout would not reliably kill grandchildren.
- After process-group fix, Codex found stderr memory was still unbounded.
- After stderr cap, Codex found the mixed stdout/stderr arrival-order hole.
- Hermes reproduced the exact probe, verified the fix, then committed.

Treat Codex review as an independent adversarial reviewer for resource-control patches; do not stop at tests passing if process lifecycle or resource bounds are involved.

## Commit boundary

Only commit after:

- all targeted tests pass
- related worker tests pass
- static `node --check` / `git diff --check` pass
- worker remains stopped/absent unless live smoke was explicitly authorized
- no hot process remains attributable to the patched worker
