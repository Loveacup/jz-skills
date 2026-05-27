# GitHub Code Review

Review local changes (pre-push) or GitHub PRs. Plain `git` for local, `gh`/`curl` for PR-level interactions.

> **Prerequisite:** Run auth detection block from main SKILL.md. For PR reviews: `$AUTH`, `$OWNER`, `$REPO`, `$GITHUB_TOKEN`.

---

## 1. Reviewing Local Changes (Pre-Push)

### Get the Diff
```bash
git diff --staged                    # staged changes
git diff main...HEAD                 # vs main (what a PR would contain)
git diff main...HEAD --name-only     # file names only
git diff main...HEAD --stat          # insertions/deletions per file
```

### Review Strategy
1. **Big picture:** `git diff main...HEAD --stat` + `git log main..HEAD --oneline`
2. **File by file:** `git diff main...HEAD -- src/auth/login.py`
3. **Quick checks:**
```bash
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|HACK\|XXX\|debugger"
git diff main...HEAD --stat | sort -t'|' -k2 -rn | head -10  # largest files
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="  # merge conflicts
```
4. **Present structured feedback**

### Output Format
```
## Code Review Summary

### 🔴 Critical
- **src/auth.py:45** — SQL injection: user input passed directly to query.
  Suggestion: Use parameterized queries.

### ⚠️ Warnings
- **src/models/user.py:23** — Password stored in plaintext. Use bcrypt.
- **src/api/routes.py:112** — No rate limiting on login endpoint.

### 💡 Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in src/core/utils.py:34.

### ✅ Looks Good
- Clean separation of concerns in middleware layer
- Good test coverage for happy path
```

---

## 2. Reviewing a GitHub PR

### View PR Details
```bash
gh pr view 123
gh pr diff 123
gh pr diff 123 --name-only
```

curl:
```bash
PR_NUMBER=123
# PR metadata
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "
import sys, json
pr = json.load(sys.stdin)
print(f\"Title: {pr['title']}\nAuthor: {pr['user']['login']}\")
print(f\"Branch: {pr['head']['ref']} -> {pr['base']['ref']}\")"

# Changed files
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/files \
  | python3 -c "
import sys, json
for f in json.load(sys.stdin):
    print(f\"{f['status']:10} +{f['additions']:-4} -{f['deletions']:-4}  {f['filename']}\")"
```

### Check Out PR Locally
```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
# Now use read_file, search_files, run tests...
# Shortcut: gh pr checkout 123
```

### Leave Comments
```bash
# General comment
gh pr comment 123 --body "Overall looks good, a few suggestions below."

# Inline comment
HEAD_SHA=$(gh pr view 123 --json headRefOid --jq '.headRefOid')
gh api repos/$OWNER/$REPO/pulls/123/comments \
  --method POST \
  -f body="This could be simplified with a list comprehension." \
  -f path="src/auth/login.py" \
  -f commit_id="$HEAD_SHA" \
  -f line=45 \
  -f side="RIGHT"
```

curl inline comment:
```bash
HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments \
  -d "{\"body\":\"Use list comprehension.\",\"path\":\"src/auth.py\",\"commit_id\":\"$HEAD_SHA\",\"line\":45,\"side\":\"RIGHT\"}"
```

### Submit Formal Review
```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
gh pr review 123 --comment --body "Some suggestions, nothing blocking."
```

curl (atomic multi-comment review):
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews \
  -d "{\"commit_id\":\"$HEAD_SHA\",\"event\":\"REQUEST_CHANGES\",
       \"body\":\"## Hermes Review\nFound 2 issues.\",
       \"comments\":[
         {\"path\":\"src/auth.py\",\"line\":45,\"body\":\"🔴 SQL injection risk.\"},
         {\"path\":\"src/models.py\",\"line\":23,\"body\":\"⚠️ Plaintext password.\"}
       ]}"
```

Events: `"APPROVE"`, `"REQUEST_CHANGES"`, `"COMMENT"`

---

## 3. Review Checklist

### Correctness
- Does code do what it claims? Edge cases (empty, null, large, concurrent)?

### Security
- No hardcoded secrets. Input validation. No SQL injection/XSS. Auth checks.

### Code Quality
- Clear naming. Single responsibility. No duplication. No premature abstraction.

### Testing
- New paths tested? Happy + error cases covered?

### Performance
- No N+1 queries. No blocking ops in async code.

### Documentation
- Public APIs documented. Non-obvious logic explained. README updated.

---

## 4. PR Review End-to-End

1. Gather PR context (metadata + changed files)
2. `git fetch origin pull/N/head:pr-N && git checkout pr-N`
3. Read diff: `git diff main...HEAD`, file-by-file for large PRs
4. Run tests/linter if applicable
5. Apply review checklist
6. Post review (approve/request changes/comment) with inline comments
7. Cleanup: `git checkout main && git branch -D pr-N`

**Decision:** Approve (no blocking issues) / Request Changes (critical/warning) / Comment (observations, non-blocking)
