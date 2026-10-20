# WRR v6.1 evidence bundle lessons (2026-07-02)

Context: WRR v6.1 EngineHealthPolicy Packages D1/H5 used Codex planning → CC execution → Hermes verification → OMP audit.

## Durable lessons

1. **Do not rely on quiet pytest progress as audit evidence.**
   - `pytest -q` progress dots plus warning tail may omit the final `N passed` line when captured/truncated.
   - For OMP/auditor bundles, include an explicit one-line summary written by Hermes from a real run: command, exit code, `N passed`, deselections/warnings.
   - Example: `env -u WRR_V6_ROUTER PYTHONPATH=. pytest -q tests/unit -k 'not openalex_live_single_source' -> 417 passed, 1 deselected (exit 0)`.

2. **Untracked new files are invisible to plain `git diff --stat`.**
   - If a package adds a new file, the bundle must include it explicitly: `git status --short`, an artificial/new-file stat line, and the full file content.
   - Do not let a reviewer infer a new file from `git diff --stat`; it will not appear until staged or `git add -N` is used.

3. **CC completion artifact is not final truth, but it is enough to freeze.**
   - If `/tmp/<result>.md` exists, expected docs/code diff is present, and Hermes can independently run gates, freeze the CC worktree and audit it.
   - If the pane later shows prediction text such as `commit this`, ignore it. Hermes owns commit decisions.

4. **Docs-only packages still need runtime gates when they document behavior.**
   - For WRR v6.1 H5, the correct gate was: targeted health-policy tests, non-live sweep, compileall, and CLI JSON parse smoke.
   - The point is to prove the documented behavior still matches runtime reality, even if the diff is docs-only.

## Minimal OMP bundle checklist

- `git status --short`
- changed file list, including untracked files
- diff/stat for tracked files
- full content for any untracked new files
- complete relevant diff hunks
- command summaries with exit codes and pass counts
- caveats for expected non-zero CLI exits (e.g. doctor exit 1 due unhealthy local env while JSON parses)
