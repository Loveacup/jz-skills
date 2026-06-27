# Cross-Platform Script Audit

## Scope

This audit covers the current helper scripts under `scripts/`:

- `check-version.sh`
- `orchestrate.sh`
- `sync-from-official.sh`
- `sync-from-github.sh`
- `push-to-github.sh`
- `install-skill.sh`

The goal is macOS and Windows portability for `omp-ops` skill maintenance.

## Summary

The current daily maintenance scripts now use portable Node.js implementations
under `scripts/lib/*.mjs`, with thin `.sh` wrappers for macOS/Git Bash/WSL and
thin `.ps1` wrappers for Windows PowerShell.

The remaining portability risk is mostly operational: Node, Git, and OMP must
exist on the runner PATH.

## Findings

### Resolved - Bash is no longer the business-logic runtime

Older helpers used `#!/bin/bash` plus Bash-specific features:

- `BASH_SOURCE`
- arrays
- `[[ ... =~ ... ]]`
- here-strings (`<<<`)
- `PIPESTATUS`
- function-local variables

The business logic has been moved to `scripts/lib/*.mjs`; wrappers now only
locate their directory and call Node.

Recommended fix:

- Keep `.sh` wrappers thin for macOS/Git Bash/WSL.
- Keep `.ps1` wrappers thin for Windows PowerShell.
- Keep future business logic in `scripts/lib/*.mjs`.

### Resolved - `jq` removed from daily helper logic

Older scripts used `jq -n` only to print JSON status. JSON output now comes from
Node helper code.

Affected scripts:

- `orchestrate.sh`
- `sync-from-official.sh`
- `sync-from-github.sh`
- `push-to-github.sh`
- `install-skill.sh`

Policy: do not reintroduce `jq` for daily maintenance output.

### P2 - `install-skill` remains optional and potentially destructive

The installer now uses the shared Node helper and supports Windows junctions,
but it still removes/replaces the target path. It must remain out of daily
maintenance.

Recommended fix:

- Keep this script out of daily maintenance.
- Replace with a portable installer that supports dry-run, explicit confirm,
  platform-aware paths, and no destructive default.
- Keep it optional and explicit.
- Prefer setting `OMP_OPS_INSTALL_TARGET` in tests instead of using the default
  runtime pool path.

### Resolved - Cache path resolution moved to Node

`orchestrate.sh` and `check-version.sh` write cache/lock files using:

- `$HOME/.cache/omp-ops-last-sync`
- `$SKILL_DIR/.orchestrate.lock`
- `$SKILL_DIR/.dirty`

Cache directory resolution now happens in `scripts/lib/common.mjs`.
`.dirty` remains a repo-local marker by design.

### Resolved - Git logic moved to Node

Git path handling currently uses slash paths such as `omp/omp-ops`, which Git
itself accepts cross-platform. The shell around it is the less portable part.

Git pathspecs remain slash-based because Git accepts them cross-platform.
Dirty detection and scoped staging now live in Node helpers.

### Resolved - Network fetch and JSON parsing centralized

`check-version.sh` and `sync-from-official.sh` both fetch official package
metadata and parse JSON inline.

`scripts/lib/common.mjs` now centralizes fetch, JSON output, semver-ish checks,
paths, cache resolution, and git helpers.

## Migration Plan

### Phase 1 - Document and contain

- Keep existing Bash scripts.
- Document that they require macOS, Git Bash, or WSL.
- Add this audit to `90_Automation/`.

### Phase 2 - Portable implementation layer

Create:

```text
scripts/lib/check-version.mjs
scripts/lib/sync-from-official.mjs
scripts/lib/verify.mjs
scripts/lib/release.mjs
```

Implemented for current daily helpers.

### Phase 3 - Native Windows entrypoints

If Windows native use is required without Git Bash/WSL, add:

```text
scripts/check-version.ps1
scripts/sync-from-official.ps1
scripts/verify.ps1
scripts/release.ps1
```

Implemented for current helpers through `.ps1` wrappers.

## Current Safe Invocation

Daily maintenance can run through:

- `.sh` wrappers on macOS, Git Bash, or WSL
- `.ps1` wrappers on Windows PowerShell
- direct `node scripts/lib/*.mjs` calls on any platform with Node
