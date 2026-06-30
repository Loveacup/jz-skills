# Non-git Codex Planning Before CC

Use when a project follows **Codex plans / CC executes / Hermes audits**, but the working directory is intentionally not a git repository.

## Pattern

Do not initialize git or change the workdir just to make Codex happy for a planning-only pass. Use Codex's non-git/read-only flags and tightly bound the prompt:

```bash
cd /path/to/project
codex exec --skip-git-repo-check --sandbox read-only \
  'Planning only. Do not modify files, do not run tests, do not use qmd/Obsidian/network. Read only: server.py, tests/. Output next TDD slice, target files, RED tests, verification commands, risks.'
```

## If Codex times out or wanders

Retry once with a narrower file list and explicit bans:

- `no qmd`
- `no Obsidian`
- `no tests` if planning must not execute commands
- `no network`
- `read only these paths: ...`

Do **not** repeat the same broad prompt after a timeout.

## Handoff discipline

Codex output is a plan, not final truth:

1. Hermes audits/tightens the plan.
2. Hermes sends CC a bounded execution package with exact allowed files and unittest commands.
3. CC executes TDD.
4. Hermes reruns tests/smoke and owns the final verdict.

## Pitfalls

- Codex skill says git repos are the normal path; planning-only non-git is an explicit exception with `--skip-git-repo-check --sandbox read-only`.
- Do not let Codex read the whole Obsidian vault or qmd index when the task is local code planning.
- Do not let a planning prompt execute tests if the requested role is only planning.
