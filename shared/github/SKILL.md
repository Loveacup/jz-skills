---
name: github
description: "GitHub 全操作入口：认证、issues、PR、仓库管理、代码审查、源码探索、代码库统计、README 写作规范。Use when working with any GitHub repository — opening issues, creating PRs, reviewing code, searching source code, cloning repos, managing CI, creating releases, counting LOC, writing or reviewing README files. Do NOT use for: local git-only operations (no GitHub remote), generic code review principles (without GitHub context), or non-GitHub platforms (GitLab/Bitbucket)."
version: 3.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, Git, Issues, PR, Code-Review, CI/CD, Repositories, Code-Exploration]
    replaces: [github-auth, github-issues, github-pr-workflow, github-repo-management, github-code-review, github-code-explorer, codebase-inspection]
---

# GitHub Operations v3.0

Unified skill for all GitHub interactions. Auth is resolved at load time — no separate auth skill needed.

## 🚨 Red Flags: DO NOT SKIP THIS SKILL

| Excuse | Why wrong |
|--------|-----------|
| "I'll just use `web_search` for this repo" | web_search gives docs/blogs, not source code or API access. |
| "I know the gh commands, don't need the skill" | Auth detection + curl fallback are critical when `gh` isn't installed/auth'd. |
| "I'll call the REST API directly without loading the reference" | The references have endpoint formats + Python parsing pipelines tested across 100+ sessions. |
| "It's just a quick issue, I can skip auth check" | Silent auth failures produce confusing 401 errors. Always run the detection block. |
| "`web_extract` works fine for raw GitHub URLs" | It does not — `raw.githubusercontent.com` is blocked. Use `mcp_exa_web_fetch_exa`. |

## 🔀 Decision Tree

```
GitHub task?
├─ Auth setup / troubleshooting  → references/auth.md
├─ Issues (create/search/triage) → references/issues.md
├─ PR (create/review/merge/CI)   → references/pr-workflow.md
├─ Repo (clone/create/fork/etc.) → references/repo-management.md
├─ Code review (local or PR)     → references/code-review.md
├─ Source exploration (search/read/analyze) → references/code-explorer.md
├─ Codebase stats (LOC/languages)→ references/codebase-inspection.md
└─ README writing / review       → references/readme-guide.md

For COMPLEX tasks spanning multiple domains (e.g., "triaging an issue then opening a PR"):
load the individual references you need. The auth block below is shared.
```

## 🔐 Auth Detection

**Run this once at the start of any GitHub task.** Determines `gh` vs `curl` path:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="curl"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      export GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
  [ -z "$GITHUB_TOKEN" ] && echo "⚠️ Not authenticated. Load references/auth.md."
fi

# Extract owner/repo from git remote (if inside a repo)
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [ -n "$REMOTE_URL" ]; then
  OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
  OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
  REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
fi
```

See `references/auth.md` for full setup (HTTPS tokens, SSH keys, `gh auth login`).

## 📋 Quick Reference

| Task | gh (preferred) | curl endpoint |
|------|----------------|---------------|
| Create issue | `gh issue create -t "..." -b "..."` | `POST /repos/{o}/{r}/issues` |
| List issues | `gh issue list -s open` | `GET /repos/{o}/{r}/issues` |
| Create PR | `gh pr create -t "..." -b "..."` | `POST /repos/{o}/{r}/pulls` |
| Check CI | `gh pr checks` | `GET /repos/{o}/{r}/commits/{sha}/status` |
| Merge PR | `gh pr merge --squash` | `PUT /repos/{o}/{r}/pulls/{n}/merge` |
| Review PR | `gh pr review N --approve` | `POST /repos/{o}/{r}/pulls/{n}/reviews` |
| Clone repo | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create repo | `gh repo create name --public` | `POST /user/repos` |
| View repo | `gh repo view o/r` | `GET /repos/{o}/{r}` |
| Read source | `mcp_exa_web_fetch_exa(raw_url)` | `gh api repos/o/r/contents/path` |
| Count LOC | — | `pygount --format=summary .` |
| Set secret | `gh secret set KEY -b "val"` | `PUT /repos/{o}/{r}/actions/secrets/K` |
| Write README | — | see `references/readme-guide.md` |

## 📂 References

| File | Load when |
|------|-----------|
| `references/auth.md` | First-time setup, new machine, token expired, SSH troubleshooting |
| `references/issues.md` | Create, search, triage, label, assign, close issues |
| `references/pr-workflow.md` | Branch → commit → push → PR → CI monitor → merge |
| `references/repo-management.md` | Clone, create, fork, releases, secrets, workflows, branch protection |
| `references/code-review.md` | Review local changes (pre-push) or GitHub PR review with inline comments |
| `references/code-explorer.md` | Search/read/browse source code (L1→L4 escalation), git archaeology |
| `references/codebase-inspection.md` | LOC count, language breakdown, code/comment ratios via pygount |
| `references/readme-guide.md` | Write or review README: section guide, bilingual patterns, anti-patterns, checklist |

## ⚠️ Profile Isolation Pitfall

When running from a non-default Hermes profile (e.g., cron-worker whose `HERMES_HOME` redirects `~`), `gh` commands silently fail or appear unauthenticated because `gh` reads auth from `~/.config/gh/` — which resolves to the profile's redirected home, not the real macOS user home.

Always prefix `gh` and `git` commands with `HOME=/Users/<username>`:

```bash
HOME=/Users/alexcai gh auth status
HOME=/Users/alexcai git push fork branch-name
HOME=/Users/alexcai gh pr create --base main --head user:branch ...
```

The real home path is discoverable via `dscl . -read "/Users/$(id -un)" NFSHomeDirectory` if unsure.

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I run the auth detection block before any GitHub API call?
- [ ] Did I load the correct reference file for the task?
- [ ] For code exploration: did I use `mcp_exa_web_fetch_exa`, not `web_extract`, for raw GitHub URLs?
- [ ] For curl calls: did I set `Authorization: token $GITHUB_TOKEN` header?
- [ ] For PR/issue/repo operations: did I extract `$OWNER/$REPO` from git remote?
- [ ] Did I clean up temp directories (`/tmp/explore-repo`) after L4 analysis?

**If any box is unchecked, go back.**
