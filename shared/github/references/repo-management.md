# GitHub Repository Management

Clone, create, fork, configure, and manage repositories. `gh` first, `git`+`curl` fallback.

> **Prerequisite:** Run auth detection block from main SKILL.md. Requires `$AUTH`, `$OWNER`, `$REPO`, `$GITHUB_TOKEN`, optionally `$GH_USER`.

## 1. Clone

```bash
# HTTPS (works with credential helper or token-embedded URL)
git clone https://github.com/owner/repo-name.git
git clone --depth 1 https://github.com/owner/repo-name.git  # shallow
git clone --branch develop https://github.com/owner/repo-name.git

# gh shorthand
gh repo clone owner/repo-name
gh repo clone owner/repo-name -- --depth 1
```

## 2. Create Repositories

**With gh:**
```bash
gh repo create my-project --public --clone
gh repo create my-project --private --description "A tool" --license MIT --clone
gh repo create my-org/my-project --public --clone

# From existing local dir
cd /path/to/project
gh repo create my-project --source . --public --push
```

**With curl:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name":"my-project","description":"A tool","private":false,"auto_init":true}'

# Under org
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/my-org/repos \
  -d '{"name":"my-project","private":false}'
```

**From template:**
```bash
gh repo create my-app --template owner/template-repo --public --clone
```

## 3. Fork

```bash
gh repo fork owner/repo-name --clone
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo-name/forks
sleep 3 && git clone https://github.com/$GH_USER/repo-name.git
cd repo-name && git remote add upstream https://github.com/owner/repo-name.git
```

Keep fork in sync:
```bash
git fetch upstream && git checkout main
git merge upstream/main && git push origin main
# or: gh repo sync $GH_USER/repo-name
```

## 4. Repository Information

**With gh:**
```bash
gh repo view owner/repo-name
gh repo list --limit 20
gh search repos "machine learning" --language python --sort stars
```

**With curl (public repos, no auth needed):**
```bash
python3 - <<'PY'
import base64, json, urllib.request
owner_repo = "OWNER/REPO"
base = f"https://api.github.com/repos/{owner_repo}"
headers = {"Accept": "application/vnd.github+json", "User-Agent": "Hermes"}

def get(path=""):
    req = urllib.request.Request(base + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

repo = get("")
for k in ["full_name","description","html_url","language","stargazers_count",
          "forks_count","open_issues_count","default_branch","created_at","updated_at"]:
    print(f"{k}: {repo.get(k)}")
print("topics:", ", ".join(repo.get("topics", [])))
readme = get("/readme")
content = base64.b64decode(readme["content"]).decode("utf-8","replace")
print("\n--- README head ---")
print("\n".join(content.splitlines()[:120]))
PY
```

For risk-oriented review (binary artifacts, AI agents, browser automation): see `repo-risk-review-cloakbrowser.md` and `repo-review-ai-design-skills.md`.

## 5. Settings

```bash
gh repo edit --description "Updated" --visibility public
gh repo edit --enable-wiki=false --enable-issues=true
gh repo edit --default-branch main
gh repo edit --add-topic "machine-learning,python"
gh repo edit --enable-auto-merge
```

curl:
```bash
curl -s -X PATCH -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO \
  -d '{"description":"Updated","has_wiki":false,"has_issues":true,"allow_auto_merge":true}'
```

## 6. Branch Protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{"required_status_checks":{"strict":true,"contexts":["ci/test","ci/lint"]},
       "enforce_admins":false,
       "required_pull_request_reviews":{"required_approving_review_count":1}}'
```

## 7. Secrets (GitHub Actions)

```bash
gh secret set API_KEY --body "your-secret-value"
gh secret set SSH_KEY < ~/.ssh/id_rsa
gh secret list
gh secret delete API_KEY
```

Note: curl-based secret setting requires encryption with repo public key (involved). Use `gh secret set` if possible.

## 8. Releases

```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release create v2.0.0-rc1 --draft --prerelease --generate-notes
gh release create v1.0.0 ./dist/binary --title "v1.0.0" --notes "Release notes"
gh release list
gh release download v1.0.0 --dir ./downloads
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/releases \
  -d '{"tag_name":"v1.0.0","name":"v1.0.0","body":"## Changelog\n...","draft":false,"generate_release_notes":true}'
```

Upload asset:
```bash
RELEASE_ID=<id>
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/octet-stream" \
  "https://uploads.github.com/repos/$OWNER/$REPO/releases/$RELEASE_ID/assets?name=binary-amd64" \
  --data-binary @./dist/binary-amd64
```

## 9. Workflows

```bash
gh workflow list
gh run list --limit 10
gh run view <RUN_ID>
gh run view <RUN_ID> --log-failed
gh run rerun <RUN_ID>
gh run rerun <RUN_ID> --failed
gh workflow run ci.yml --ref main
```

curl:
```bash
# List runs
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/runs?per_page=10" \
  | python3 -c "
import sys, json
for r in json.load(sys.stdin)['workflow_runs']:
    print(f\"Run {r['id']}  {r['name']:30}  {r['conclusion'] or r['status']}\")"

# Re-run
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/rerun

# Trigger workflow_dispatch
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/dispatches \
  -d '{"ref":"main","inputs":{"environment":"staging"}}'
```

## 10. Gists

```bash
gh gist create script.py --public --desc "Useful script"
gh gist list
```

curl:
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/gists \
  -d '{"description":"Useful script","public":true,"files":{"script.py":{"content":"print(\"hello\")"}}}'
```
