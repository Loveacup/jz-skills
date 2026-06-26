# Codex Daily Maintenance

## Purpose

`omp-ops-skill` is the Codex-side daily maintenance automation for this skill.
It keeps the `omp-ops` skill healthy, synchronized with official OMP source
material, verified, and released from the `jz-skills` repository.

This is not the Agent Skills hub patrol and not OMP runtime/profile management.
It is also not part of normal OMP skill usage. Maintenance-only instructions
should live here, not in `SKILL.md`.

## Automation

| Field | Value |
|---|---|
| Automation id | `omp-ops-skill` |
| Schedule | Daily, 04:30 local automation time |
| Workspace | `/Users/alexcai/code/jz-skills` |
| Scope | `omp/omp-ops/` only |
| Release target | `origin/main` in `Loveacup/jz-skills` |

Routine maintenance in this scope does not require separate manual approval.
L3 actions outside this scope are not part of this automation.

## Boundaries

Allowed:

- read and edit files under `omp/omp-ops/`
- fetch official OMP documentation and version metadata
- update mirrored official references
- update authored references after semantic review
- add or improve helper scripts under `scripts/`
- run verification commands
- commit and push scoped `omp/omp-ops/` changes after verification

Forbidden:

- stage, commit, or modify files outside `omp/omp-ops/`
- read `~/.omp/**/agent.db`, `history.db`, `models.db`, sessions,
  terminal-sessions, logs, auth files, or env files
- write `.env`, real API keys, tokens, passwords, or OMP profile runtime files
- runtime repoint, profile apply, dependency install/upgrade, or broad repo
  maintenance

## Cross-Platform Script Policy

Daily maintenance must work on macOS and Windows.

Current shell helpers are Bash scripts. They are acceptable on macOS and on
Windows only when the runner provides a POSIX-compatible shell such as Git Bash
or WSL. New maintenance logic should prefer portable runtimes:

- Use Node.js or Python for non-trivial parsing, JSON handling, path logic,
  version comparison, and file updates.
- Keep Bash wrappers thin: locate the skill directory, call the portable helper,
  and forward exit codes.
- Avoid GNU-only shell flags and utilities unless there is a documented macOS
  and Windows fallback.
- Avoid platform-specific `find`, `sed -i`, `readlink -f`, `realpath`, `date`
  formatting, and path separator assumptions.
- Treat paths as data. Use helper code to normalize `/`, `\\`, drive letters,
  symlinks, and relative paths.
- Use Node `JSON.parse`, Python `json`, or `python3 -m json.tool` for JSON
  validation; do not parse JSON with `grep` or `sed`.
- Keep network fetch behavior explicit and fail closed when `curl`, `jq`, `git`,
  `node`, `python3`, or `omp` is unavailable.

Preferred helper shape:

```text
scripts/<task>.sh              thin compatibility wrapper
scripts/lib/<task>.mjs         portable implementation
```

or, when Python is guaranteed by the runner:

```text
scripts/<task>.sh              thin compatibility wrapper
scripts/lib/<task>.py          portable implementation
```

The wrapper should not contain business logic that would need to be duplicated
for Windows.

Current status: daily maintenance logic has moved to portable
`scripts/lib/*.mjs` implementations. The `.sh` and `.ps1` files are thin
wrappers for macOS/Git Bash/WSL and Windows PowerShell respectively.

## Maintenance Pipeline

1. Check repository state with `git status --short`.
2. Record scope-out changes, but do not touch them.
3. Read `references/VERSION`.
4. Fetch official OMP package version.
5. Run `scripts/check-version.sh` when present and validate JSON output.
6. Refresh official mirrors only when required.
7. Generate a maintenance plan from official diffs.
8. Use Codex semantic review to update authored references.
9. Run verification.
10. Release only scoped, verified `omp/omp-ops/` changes.

## Helper Script Contract

Prefer script-backed facts over ad hoc LLM judgment.

### Current Helpers

| Script | Role | Write scope |
|---|---|---|
| `scripts/check-version.sh` | Emit JSON status for local skill, GitHub skill, official OMP, local OMP, and actions. | Read-only |
| `scripts/sync-from-official.sh` | Mirror official tracked docs into `references/official/` and update sync state. | `references/official/`, `references/VERSION`, `references/sync-state.json` |
| `scripts/sync-from-github.sh` | Pull the published `omp-ops` skill from `Loveacup/jz-skills`. | `omp/omp-ops/` |
| `scripts/push-to-github.sh` | Stage, commit, and push verified scoped changes. | Git index for `omp/omp-ops/` only |
| `scripts/orchestrate.sh` | Run `check-version.sh` and execute returned action scripts with a lock/cache. | Depends on returned actions |
| `scripts/install-skill.sh` | Optional setup/linking helper. Not part of daily maintenance. | Runtime install target only when explicitly invoked |

### Planned Helpers

These helpers are desirable but not required yet:

| Script | Role | Write scope |
|---|---|---|
| `scripts/diff-official.sh` | Produce a compact change packet from official docs/changelog. | Read-only or temp output |
| `scripts/maintenance-plan.sh` | Map official changes to authored reference files requiring review. | Read-only or temp output |
| `scripts/verify.sh` | Run structural, JSON, line-count, scope, and secret-leak checks. | Read-only |
| `scripts/release.sh` | Wrapper around scoped release checks and `push-to-github.sh`. | Git index for `omp/omp-ops/` only |

If a helper is missing, Codex may use the smallest equivalent inline command and
must report the missing helper in the run summary.

## Migrated From Hot Path

The following concerns belong to this automation document rather than
`SKILL.md`:

- mandatory `scripts/orchestrate.sh` execution before every normal answer
- `sync-from-official`, `sync-from-github`, and `push-to-github` action routing
- GitHub skill version comparison and release behavior
- daily/periodic official-doc mirroring
- scoped commit and push rules

Dirty state is detected by both the `.dirty` marker used by sync scripts and
the git worktree state under `omp/omp-ops/`.

Partial failure behavior:

- If `sync-from-official.sh` succeeds and `push-to-github.sh` fails, the
  working tree remains dirty and `.dirty` is restored.
- The next maintenance run should treat this as a pending scoped release under
  `omp/omp-ops/`, not as a new official sync requirement.
- The automation should not roll back official mirrors automatically; it should
  rerun verification and retry the scoped release.

`SKILL.md` should stay focused on OMP operator knowledge: configuration,
providers, auth precedence, search, model roles, security, and troubleshooting.

## OMP Review Invocation

For OMP-assisted review, prefer a bounded `@file` review packet over letting OMP
discover files by itself.

Recommended pattern:

```bash
omp --cwd /Users/alexcai/code/jz-skills \
  --no-session \
  --max-time 120 \
  --mode json \
  --hide-thinking \
  -p \
  --skills=omp-ops \
  --no-tools \
  @omp/omp-ops/SKILL.md \
  @omp/omp-ops/90_Automation/README.md \
  @omp/omp-ops/90_Automation/01-codex-daily-maintenance.md \
  @omp/omp-ops/scripts/check-version.sh \
  @omp/omp-ops/scripts/orchestrate.sh \
  @omp/omp-ops/scripts/sync-from-official.sh \
  @omp/omp-ops/scripts/sync-from-github.sh \
  @omp/omp-ops/scripts/push-to-github.sh \
  @omp/omp-ops/references/architecture.md \
  @omp/omp-ops/references/security.md \
  @omp/omp-ops/references/providers/models.md \
  @omp/omp-ops/references/providers/search.md \
  "Read-only review these attached files. Do not use tools."
```

Why this pattern:

- `--mode json` exposes an event stream that Codex can monitor.
- `--max-time` prevents long-running or stuck reviews.
- `--no-tools` prevents accidental filesystem discovery or runtime reads.
- Explicit `@file` inputs let Codex control the review boundary.
- Large official mirrors such as `CHANGELOG.md` and
  `environment-variables.md` should usually be represented by file presence,
  size, and targeted excerpts instead of full-text review input.

Outer monitor requirements:

- Read JSON lines from stdout and record `session`, `turn_start`, `turn_end`,
  and final assistant text.
- Set an outer process timeout in addition to `--max-time`.
- If tools are ever enabled, terminate the process on forbidden tool calls that
  reference runtime databases, sessions, logs, auth files, env files, or paths
  outside `omp/omp-ops/`.
- Keep the final review output in the Codex run summary; do not write OMP
  session logs or runtime traces into the repository.

Large mirror summary examples:

```bash
wc -l omp/omp-ops/references/official/CHANGELOG.md
head -n 50 omp/omp-ops/references/official/CHANGELOG.md
grep -n "^##\\|provider\\|model\\|auth\\|search" \
  omp/omp-ops/references/official/environment-variables.md
```

Avoid this pattern for maintenance review:

```bash
omp -p "review the whole directory"
```

It is a black-box print run: Codex cannot see intermediate intent, and OMP may
spend time discovering files or waiting on hidden loops. If tool-enabled review
is ever needed, use `--mode json --tools=read,grep` and an outer monitor that
terminates the process on forbidden tool calls. The safer default remains
`@file` plus `--no-tools`.

## Authored Reference Updates

Official mirrors are source material, not the final skill guidance.

After official changes, Codex should review and update, as needed:

- `references/providers/search.md`
- `references/providers/models.md`
- `references/architecture.md`
- `references/security.md`
- `SKILL.md`
- `references/sync-notes.md`

Do not delete human-authored provider or architecture guidance only because the
official mirror changed. Preserve, amend, or mark uncertain impact in
`references/sync-notes.md`.

## Verification

Minimum checks before release:

- `scripts/check-version.sh` output is valid JSON
- `scripts/orchestrate.sh` exits without error when present
- `SKILL.md` is under 300 lines
- tracked official docs are present, including `models.md`
- `references/sync-state.json` is valid JSON
- diff under `omp/omp-ops/` contains no API keys, tokens, passwords, or secrets
- git index contains only `omp/omp-ops/` paths

## Output

Each run should report:

- official OMP version
- local OMP version, if available
- skill version
- scripts executed
- missing helper scripts
- changed files
- verification results
- commit URL, or no-op evidence
