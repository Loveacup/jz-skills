# Repo Import: Profile-Local Source + Staged-Only Audit

Use this when pushing an existing Hermes skill into `jz-skills` and the live source does **not** live under the default `~/.hermes/skills/` tree, or when the repo already has unrelated dirty files.

## Pattern

1. **Identify the actual loaded source**
   - `skill_view()` may show `skill_dir` under a profile, e.g. `~/.hermes/profiles/regent/skills/...`.
   - `deploy/sync-back.sh` may still read only default `~/.hermes/skills` via `HERMES_BASE`; do not assume it can pull profile-local skills.

2. **Manual repo copy is acceptable for profile-local sources**
   - Copy from the actual profile path into the repo skill directory with `rsync -a --delete` or equivalent.
   - Run the same sanitization expectations as `sync-back.sh` on the repo copy.
   - Do **not** mutate the live profile copy just to make `sync-back.sh` convenient.

3. **Patch both sync directions after adding a skill**
   - Forward deploy: `deploy/sync-all.sh` category mkdir + copy mapping.
   - Reverse sync: `deploy/sync-back.sh` `PAIRS` mapping.
   - README skill counts/tree must be updated in the same commit.

4. **Dirty worktree isolation**
   - If the repo already has unrelated local changes, stage explicit paths only.
   - Verify with `git diff --cached --name-status` and `git diff --cached --stat` before commit.
   - Do not use broad `git add .` in a dirty skill hub repo.

5. **Audit the staged set, not the whole repo**
   - Run secret/path/IP checks against `git diff --cached --name-only` so unrelated pre-existing files do not block the current import.
   - Still inspect full `git status --short` before/after push to confirm unrelated changes remain unstaged.

6. **Handle SSH remote false positives**
   - Email regexes may match `git@github.com` in README clone URLs.
   - Treat `git@github.com` as an allowed SSH remote literal, not as a leaked personal email.
   - Do not blanket-ignore all emails; only whitelist known VCS remote patterns.

## Minimal verification block

```bash
git diff --cached --check
bash -n deploy/sync-all.sh
bash -n deploy/sync-back.sh
git diff --cached --name-status
git diff --cached --stat
```

For secret audits, scan only cached paths and whitelist VCS SSH remotes such as `git@github.com`.
