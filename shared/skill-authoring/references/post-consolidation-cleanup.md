# Post-Consolidation Cleanup — Orphan Detection & Removal

When skills are consolidated into an umbrella (N→1), `sync-all.sh` deploys the new umbrella but does **NOT** remove the old standalone skill directories from the deployed pool. These orphans persist indefinitely — `sync-all.sh` is additive-only. The `skill-integrity-watchdog` cron job detects them as "new skills added to pool vs baseline" (INFO level) when it does full-depth enumeration.

## Detection: Watchdog vs Actual New Skills

Watchdog "new" alerts can be:

| Type | Signal | Action |
|:---|:---|:---|
| Legitimate new skills | Added intentionally via sync | Update baseline |
| Orphaned standalone dirs | Predate consolidation, should have been deleted | **Clean up** |
| Nested duplicates | `cp -r` bug in sync-all.sh | Fix script + delete |

### How to distinguish

1. **Check git history:** `git log --oneline -- shared/<skill>/` in jz-skills
2. **Check file timestamps:** orphans predate the consolidation commit
3. **Check if the skill is listed as `replaces:`** in the umbrella's frontmatter
4. **Check sync-all.sh:** if the orphan is still in deploy lines, it'll come back after cleanup

## Cleanup Workflow

### Step 1: Delete orphans from deployed pool

```bash
rm -rf ~/.hermes/skills/category/orphan-skill-name/
```

### Step 2: Fix sync-all.sh deploy lines

Remove any `copy_skill_dir` lines that deploy the old standalone skill:

```bash
# Delete lines like:
copy_skill_dir "$REPO_ROOT/hermes/old-skill"  "$base/somewhere"
```

Also check the per-profile loop (lines 60-81) for duplicate deploy lines.

### Step 3: Fix sync-all.sh dst path if skill name = category

When deploying a skill whose name matches its category directory (e.g., `github` skill into `$base/github/`), `copy_skill_dir` creates a nested `github/github/`:

```bash
# BUG: copies shared/github → $base/github/github/
copy_skill_dir "$REPO_ROOT/shared/github"  "$base/github"

# FIX: use parent dir as dst
copy_skill_dir "$REPO_ROOT/shared/github"  "$base"
```

This is because `copy_skill_dir` does `cp -r "$src" "$dst/$(basename "$src")"` — when `dst/github/github/` already exists, it creates a double-nested copy.

### Step 4: Delete nested duplicate from pool

```bash
rm -rf ~/.hermes/skills/category/name/name/
```

### Step 5: Update watchdog baseline

```bash
cd ~/.hermes/profiles/cron-worker
python3 scripts/skill-integrity-watchdog.py --update-baseline

# Verify clean
python3 scripts/skill-integrity-watchdog.py; echo "exit=$?"
# Expected: exit=0 with no output
```

### Step 6: Commit sync script fixes

```
fix(deploy): remove orphan deploy lines + fix dst path / 清理孤儿部署行 + 修正目标路径
```

## Case Study: GitHub Consolidation (2026-06-05)

**Context:** On 2026-05-27, 7 GitHub skills were consolidated into one umbrella (`shared/github/SKILL.md`, commit `51250ff`). The old standalone directories (`github-auth/`, `github-code-review/`, etc.) and `codebase-inspection/` were never deleted from the deployed pool.

**Also found:** `arxiv/` (already integrated into web-research-router but still deployed by sync-all.sh line 43/71) and `humanizer/` (abandoned, no deploy line, file dated 2026-05-14).

**Watchdog alert (2026-06-05):**
```
🔵 INFO: new skills added to pool vs baseline:
arxiv, codebase-inspection, github-auth, github-code-review,
github-issues, github-pr-workflow, github-repo-management, humanizer
```

**Root cause:** 6 orphaned standalone dirs + 1 abandoned skill + 1 stale deploy line. Also the sync-all.sh `$base/github` dst path created a nested `github/github/` duplicate.

**Cleanup:**
- Deleted 9 dirs from `~/.hermes/skills/`
- Removed 2 `arxiv` deploy lines from `sync-all.sh` (main + profile loop)
- Fixed 2 `github` dst paths: `"$base/github"` → `"$base"` and `"$pd/github"` → `"$pd"`
- Deleted `shared/github/github/` nested copy from jz-skills repo
- Updated baseline → 144 skills, exit 0

## Pitfalls

- **sync-all.sh is additive-only** — never removes dirs from the pool. Orphan cleanup is manual.
- **`$base/foo` as dst when source basename is also `foo`** — creates `$base/foo/foo/`. Always use `$base` when deploying a skill whose name IS the category.
- **Per-profile loop duplicates deploy lines** — a fix in `sync_hermes()` must also be applied inside the `for prof` loop.
- **Don't update baseline without cleaning first** — baseline update hides the problem instead of fixing it.
