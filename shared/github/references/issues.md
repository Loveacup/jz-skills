# GitHub Issues

Create, search, triage, and manage GitHub issues. `gh` first, `curl` fallback.

> **Prerequisite:** Run the auth detection block from main SKILL.md. Requires `$AUTH`, `$OWNER`, `$REPO`, and optionally `$GITHUB_TOKEN`.

## 1. Viewing Issues

**With gh:**
```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

**With curl:**
```bash
# List open issues
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        labels = ', '.join(l['name'] for l in i['labels'])
        print(f\"#{i['number']:5}  {i['state']:6}  {labels:30}  {i['title']}\")"

# View specific issue
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  | python3 -c "
import sys, json
i = json.load(sys.stdin)
print(f\"#{i['number']}: {i['title']}\")
print(f\"State: {i['state']}  Author: {i['user']['login']}\")
print(f\"\n{i['body']}\")"

# Search issues
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=authentication+error+repo:$OWNER/$REPO" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin)['items']:
    print(f\"#{i['number']}  {i['state']:6}  {i['title']}\")"
```

## 2. Creating Issues

**With gh:**
```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description
After logging in, users always land on /dashboard.

## Steps to Reproduce
1. Navigate to /settings while logged out
2. Get redirected to /login?next=/settings
3. Log in → redirected to /dashboard (should go to /settings)

## Expected Behavior
Respect the ?next= query parameter." \
  --label "bug,backend" \
  --assignee "username"
```

**With curl:**
```bash
curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{"title":"Login redirect ignores ?next=","body":"...","labels":["bug","backend"],"assignees":["username"]}'
```

Templates: see `../templates/bug-report.md` and `../templates/feature-request.md`.

## 3. Managing Issues

### Labels
```bash
gh issue edit 42 --add-label "priority:high,bug"
gh issue edit 42 --remove-label "needs-triage"
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels \
  -d '{"labels":["priority:high","bug"]}'

# Remove label
curl -s -X DELETE -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/labels/needs-triage
```

### Assignment
```bash
gh issue edit 42 --add-assignee username
gh issue edit 42 --add-assignee @me
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/assignees \
  -d '{"assignees":["username"]}'
```

### Commenting
```bash
gh issue comment 42 --body "Investigated — root cause is in auth middleware."
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42/comments \
  -d '{"body":"Investigated — root cause is in auth middleware."}'
```

### Close / Reopen
```bash
gh issue close 42 --reason "not planned"
gh issue reopen 42
```

curl:
```bash
# Close
curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  -d '{"state":"closed","state_reason":"completed"}'
# Reopen
curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  -d '{"state":"open"}'
```

### Link Issues to PRs
Keywords in PR body auto-close: `Closes #42`, `Fixes #42`, `Resolves #42`

Branch from issue:
```bash
gh issue develop 42 --checkout
# Manual equivalent:
git checkout -b fix/issue-42-login-redirect
```

## 4. Triage Workflow

1. List untriaged: `gh issue list --label "needs-triage" --state open`
2. Read and categorize each
3. Apply labels + priority
4. Assign if owner is clear
5. Comment with triage notes

## 5. Bulk Operations

```bash
# Close all with a label
gh issue list --label "wontfix" --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```

curl:
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?labels=wontfix&state=open" \
  | python3 -c "import sys,json; [print(i['number']) for i in json.load(sys.stdin)]" \
  | while read num; do
    curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
      https://api.github.com/repos/$OWNER/$REPO/issues/$num \
      -d '{"state":"closed","state_reason":"not_planned"}'
    echo "Closed #$num"
  done
```
