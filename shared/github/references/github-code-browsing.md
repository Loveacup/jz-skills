# GitHub Source Code Browsing — Fast Methods

Quick-reference for viewing GitHub repo source code without cloning.

## Methods Compared

### 1. github1s — Zero-Login, Fastest ⭐

- **How:** Change `github.com` → `github1s.com` in any repo URL
- **Example:** `https://github1s.com/NousResearch/hermes-agent`
- **Auth:** None required
- **Capabilities:** Full VS Code Web — file tree, syntax highlighting, global search (⇧⌘F), Go to File (⌘P), outline view
- **Limitations:** Read-only, no extensions, no terminal
- **Best for:** Quick code browsing, exploring unfamiliar repos, searching across files
- **Verified:** Working as of 2026-05. Snappy load, file tree renders immediately.

### 2. github.dev — Full Editor, Needs Login

- **How:** Change `github.com` → `github.dev`, or press `.` on any GitHub repo page
- **Auth:** Requires GitHub OAuth login
- **Capabilities:** Full VS Code Web — editing, extensions, source control, terminal (via Codespaces)
- **Limitations:** Heavier, slower to initialize, 需要登录
- **Best for:** Making quick edits, reviewing PRs with full IDE, when you need extensions

### 3. gh browse — Terminal to Browser

- **How:** `gh browse` (open repo home), `gh browse -- path/to/file` (open file)
- **Auth:** Requires `gh auth login`
- **Capabilities:** Opens repo/files/issues/PRs/settings in default browser
- **Best for:** Jumping from terminal work to browser without copy-pasting URLs

```bash
gh browse                          # repo home
gh browse -- cmd/gh/main.go        # specific file
gh browse -n -- path/to/file.go    # print URL only (no browser)
gh browse -b feature-x             # specific branch
```

### 4. gh api — Raw Content in Terminal

- **How:** `gh api repos/owner/repo/contents/path` → decode base64 content
- **Auth:** Requires `gh auth login`
- **Capabilities:** Fetch file contents, list directories, all via GitHub REST API
- **Best for:** Scripting, piping into other tools, one-off content checks

```bash
# Get raw file content
gh api repos/NousResearch/hermes-agent/contents/agent/codex_responses_adapter.py \
  --jq '.content' | base64 -d

# List directory
gh api repos/NousResearch/hermes-agent/contents/agent/ --jq '.[].name'

# Search code (legacy API, limited)
gh search code "RateLimitError" --repo NousResearch/hermes-agent
```

### 5. grep.app / Sourcegraph — Cross-Repo Code Search

- **grep.app:** `https://grep.app/search?q=function_name` — search across half a million public repos
- **Sourcegraph:** `https://sourcegraph.com/search` — semantic code search with jump-to-definition
- **Best for:** Finding usage examples of an API/function across the open-source ecosystem

## Decision Table

| Need | Tool | Auth? |
|------|------|-------|
| Browse a repo's code fast | `github1s` | ❌ No |
| Edit files in browser | `github.dev` (按 `.`) | ✅ Yes |
| Open from terminal | `gh browse` | ✅ Yes |
| Get raw content to terminal | `gh api` | ✅ Yes |
| Find usage across repos | `grep.app` | ❌ No |
| Semantic search + defs | Sourcegraph | ❌ No |

## Pitfalls

- **`github.dev` 必须登录** — 未登录会重定向到 GitHub 登录页。只读浏览用 `github1s`。
- **`gh api` base64 解码** — GitHub Contents API 返回 base64 编码的内容，必须 pipe 到 `base64 -d`。
- **`gh search code` 限制** — 走旧版 API，不支持正则，结果可能与 github.com 搜索不一致。
- **`gh` 需先认证** — 这些环境 `gh` 未登录，大多数用户需要先跑 `gh auth login`。
