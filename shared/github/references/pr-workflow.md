# GitHub PR Workflow

Complete PR lifecycle: branch → commit → push → PR → CI → merge. `gh` first, `git`+`curl` fallback.

> **Prerequisite:** Run auth detection block from main SKILL.md. Requires `$AUTH`, `$OWNER`, `$REPO`, `$GITHUB_TOKEN`.

## 1. Branch Creation

```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/add-user-authentication
```

Conventions: `feat/`, `fix/`, `refactor/`, `docs/`, `ci/`

## 2. Commits (Conventional Commits)

```bash
git add src/auth.py src/models/user.py tests/test_auth.py
git commit -m "feat: add JWT-based user authentication

- Add login/register endpoints
- Add User model with password hashing
- Add auth middleware for protected routes"
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`
Full spec: see `../references/conventional-commits.md`

## 3. Push & Create PR

```bash
git push -u origin HEAD
```

**With gh:**
```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
Adds login and register API endpoints.
Closes #42" \
  --label "enhancement"

# Options: --draft, --reviewer user1,user2, --base develop
```

**With curl:**
```bash
BRANCH=$(git branch --show-current)
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{\"title\":\"feat: add JWT auth\",\"body\":\"...\",\"head\":\"$BRANCH\",\"base\":\"main\"}"
# Add \"draft\": true for draft PR
```

Templates: `../templates/pr-body-bugfix.md`, `../templates/pr-body-feature.md`

## 4. Monitor CI

**With gh:**
```bash
gh pr checks          # one-shot
gh pr checks --watch  # poll until complete
```

**With curl:**
```bash
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Overall: {data['state']}\")
for s in data.get('statuses', []):
    print(f\"  {s['context']}: {s['state']} - {s.get('description', '')}\")"

# Also check GitHub Actions check runs
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/check-runs \
  | python3 -c "
import sys, json
for cr in json.load(sys.stdin).get('check_runs', []):
    print(f\"  {cr['name']}: {cr['status']} / {cr['conclusion'] or 'pending'}\")"
```

Poll until complete:
```bash
SHA=$(git rev-parse HEAD)
for i in $(seq 1 20); do
  STATUS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
  echo "Check $i: $STATUS"
  [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ] && break
  sleep 30
done
```

## 5. Auto-Fix CI Failures

**Step 1 — Get failure details:**
```bash
gh run list --branch $(git branch --show-current) --limit 5
gh run view <RUN_ID> --log-failed
```

**Step 2 — Fix and push:**
```bash
git add <fixed_files>
git commit -m "fix: resolve CI failure in <check_name>"
git push
```

**Auto-fix loop:** diagnose → fix → push → wait → re-check. Max 3 attempts, then ask user.

## 6. Merge

**With gh:**
```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch  # auto-merge when CI passes
```

**With curl:**
```bash
PR_NUMBER=<number>
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{\"merge_method\":\"squash\",\"commit_title\":\"feat: add auth (#$PR_NUMBER)\"}"

# Cleanup
git push origin --delete $(git branch --show-current)
git checkout main && git pull origin main
```

Merge methods: `"merge"` (commit), `"squash"`, `"rebase"`

## Complete Workflow

```bash
git checkout main && git pull origin main
git checkout -b fix/login-redirect-bug
# (make code changes)
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login"
git push -u origin HEAD
# (create PR — see section 3)
# (monitor CI — see section 4)
# (merge — see section 6)
```

## Other PR Commands

| Action | gh | curl |
|--------|-----|------|
| List my PRs | `gh pr list --author @me` | `GET /repos/{o}/{r}/pulls?state=open` |
| View diff | `gh pr diff` | `git diff main...HEAD` |
| Add comment | `gh pr comment N -b "..."` | `POST /repos/{o}/{r}/issues/N/comments` |
| Request review | `gh pr edit N --add-reviewer u` | `POST /repos/{o}/{r}/pulls/N/requested_reviewers` |
| Close PR | `gh pr close N` | `PATCH /repos/{o}/{r}/pulls/N` |
| Checkout PR | `gh pr checkout N` | `git fetch origin pull/N/head:pr-N && git checkout pr-N` |
