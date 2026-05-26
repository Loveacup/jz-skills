---
name: github-code-explorer
description: "Explores and reads GitHub source code using gh CLI, Exa fetch, github1s, CodeGraph, and grep.app. Use when the user asks to 看源码, 看看项目, 找实现, 搜用法, look at code, find implementation, search code patterns, or understand project architecture — even if they don't explicitly say 'GitHub'. Four-layer escalation: L1 single-file → L2 cross-repo search → L3 interactive browse → L4 clone+CodeGraph. Do NOT use for local files (use read_file), editing code, or non-GitHub tasks."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [github, code-exploration, source-code, browsing, search]
    related_skills: [github-auth, github-repo-management, codebase-inspection]
prerequisites:
  commands: [gh, git]
---

# GitHub Code Explorer v2.0

Four-layer strategy for exploring GitHub source code. Choose the layer based on how deep you need to go — start light, escalate only when needed.

---

## 🚨 Red Flags: DO NOT SKIP THE DECISION TREE

Before calling ANY tool for GitHub access, check this table:

| Excuse your brain will make | Why it's wrong |
|------------------------------|----------------|
| "I'll just use `web_extract` on the raw URL" | `web_extract` blocks `raw.githubusercontent.com` as "internal network." Use `mcp_exa_web_fetch_exa` instead. |
| "I know this repo, I'll just read the main file" | Wrong classification wastes steps. Conceptual questions need README first, not source code. |
| "A quick `gh api` call will answer this" | Only if you know exact file path. For cross-file questions, start with `gh search code`. |
| "I'll clone it for deep analysis — that's thorough" | L4 costs 30s+ indexing. For a single function, L1 is 2 seconds. Escalate only when needed. |
| "`web_search` will find the implementation" | Web search is for documentation and blogs, not source code. Use `gh search code` for specific code patterns. |
| "These search results look fine, I'll just use the first few" | Default search ordering is by relevance match, not quality. Always re-sort by stars or last-updated before picking which repos to examine. |

**If you caught yourself thinking any of these → re-read the decision tree below.**

---

## Decision Tree

**Step 0: Classify the request BEFORE choosing a layer.** Wrong classification wastes steps — e.g., reading source code for a "how do I use this API" question when the README would answer it.

```
User asks about a GitHub project

├─ Conceptual ("这个API怎么用" / "how does X work")
│   → L1 README + docs first, NOT source code
│   → Only go to source if docs are insufficient
│
├─ Implementation ("这个函数怎么实现" / "how is X implemented")
│   → L1→L2→L4 source code path
│   → gh search code to locate → extract to read → clone if complex
│
├─ Context/History ("为什么要这么改" / "why was this changed")
│   → git log/blame/show + gh search issues/PRs
│   → See "Git Archaeology" section below for commands
│   → Permalink with full commit SHA for immutable references
│
└─ Comprehensive ("全面分析这个项目")
    → Classify sub-questions first
    → L1→L4 progressive deepening
    → Produce permalinks + source map
```

**Then choose the layer:**

```
├─ 单个文件/函数 → L1: mcp_exa_web_fetch_exa OR gh api
├─ 跨项目搜索代码用法 → L2: grep.app + gh search code + L1 fallback
├─ 探索项目整体结构 → L3: github1s browser OR gh browse
└─ 深度分析（调用链/影响面）→ L4: gh repo clone + CodeGraph

**Rule of thumb:** If you don't know what file you need → L2. If you know the file but not the repo structure → L3. If you need semantic understanding → L4.

---

## L1 — Single-File Extraction (seconds)

**Fastest path.** Use `mcp_exa_web_fetch_exa` for raw.githubusercontent.com URLs — it reliably returns clean markdown. `web_extract` may block raw URLs.

### Read a single file

```bash
# Construct the raw URL from a GitHub URL:
# https://github.com/owner/repo/blob/main/path/to/file.py
# → https://raw.githubusercontent.com/owner/repo/main/path/to/file.py
```

Then call `mcp_exa_web_fetch_exa(urls=[raw_url])`. Content returns as markdown. Use `maxCharacters` to control output size (default 3000, bump to 10000+ for large files).

Fallback: `web_extract(urls=[raw_url])` works sometimes but may be blocked.

### When raw URL construction fails (unknown branch)

```bash
# Use gh api to discover the default branch
gh api repos/owner/repo --jq '.default_branch'

# Read file content via gh api (returns base64)
gh api repos/owner/repo/contents/path/to/file.py --jq '.content' | base64 -d

# For files >1MB (API limit), use the git data API
gh api repos/owner/repo/git/blobs/$(gh api repos/owner/repo/contents/path/to/file.py --jq '.sha')
```

### Read a directory listing

```bash
gh api repos/owner/repo/contents/path/to/dir --jq '.[].name'
```

### Batch multiple files

When you need several files from the same repo, chain `web_extract` calls:

```python
urls = [f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}" for path in paths]
web_extract(urls=urls)
```

### Tool behaviour reference

See `references/raw-github-extraction.md` for the complete extraction tool behaviour matrix (which tools work for which GitHub URL patterns, tested 2026-05-26).

```python
urls = [f"https://raw.githubusercontent.com/{owner}/{repo}/main/{path}" for path in paths]
web_extract(urls=urls)
```

---

## L2 — Cross-Repo Code Search (seconds)

### 🔥 Sorting Principle: Heat + Recency First

When L2 returns multiple repos/files, **never** blindly use the first results. Default search ordering is by relevance match, not by project quality. Always apply:

```
1. 高热度优先 → sort by stars (≥100 preferred, ≥1000 ideal)
2. 近期更新优先 → sort by last commit/push date (≤6 months preferred)
3. 同热度比时效 → if two repos have similar stars, pick the one updated more recently
4. 时效相近比热度 → if both updated within similar timeframe, pick higher stars
```

**How to apply per tool:**

- **grep.app**: results show repo name + stars inline. Scan and manually pick high-star repos.
- **`gh search code`**: append `--sort stars` or pipe through `gh api` for repo metadata:
  ```bash
  gh search code "pattern" --repo owner/repo --sort indexed --order desc
  ```
- **Exa**: add `"popular"` / `"well-maintained"` descriptors to the query.

**Fallback when star count unavailable:** prefer repos with recent commit activity over dormant ones. A 2-star repo updated last week beats a 100-star repo untouched since 2022.

### grep.app — Fastest public code search

No auth required, covers ~500K+ repos. Good for finding usage examples.

Go to `https://grep.app/search?q=<search_term>` in browser, OR construct search URL programmatically then use browser tools.

### GitHub Code Search via gh

```bash
# Search code in a specific repo
gh search code "function_name" --repo owner/repo

# Search across all of GitHub
gh search code "import torch.nn.functional" --language python

# With extension filter
gh search code "useState" --extension tsx --language typescript

# Search with filename filter
gh search code "class Agent" --filename "*.py"
```

### Exa for semantic discovery

When the user asks "find projects that do X" (not specific code):

```
mcp_exa_web_search_exa(query="open source project for X in Python")
```

Exa is better at finding projects; grep.app is better at finding specific code patterns.

### When to use which

| Tool | Best for | Auth |
|------|----------|------|
| `grep.app` | "show me how X API is used" | None |
| `gh search code` | "find this pattern in Y repo" | gh login |
| `Exa` | "find projects that do X" | API key |
| `GitHub web search` | "what does this repo do" | None |

---

## L3 — Repository Exploration (minutes)

When you need to understand a repo's structure, browse multiple files, or use IDE navigation.

### Option A: github1s (no login, read-only, fast)

Replace `github.com` with `github1s.com` in the URL:

```
https://github.com/NousResearch/hermes-agent
→ https://github1s.com/NousResearch/hermes-agent
```

Use `browser_navigate` to open. Then:
- `browser_click` to navigate file tree
- `browser_console` to extract editor text: `document.querySelectorAll('.view-line')`
- `browser_press` with `Escape` to close modals

### Option B: gh browse (fastest if you know the path)

```bash
# Open repo in browser
gh browse -R owner/repo

# Open specific file
gh browse -R owner/repo -- path/to/file.go

# Print URL without opening browser
gh browse -R owner/repo -n -- internal/config.go
# → https://github.com/owner/repo/blob/main/internal/config.go
```

### Option C: github.dev (full editor, needs login)

Press `.` on any GitHub repo page, or change `github.com` to `github.dev`. Can edit and use extensions. Requires GitHub OAuth.

---

## L4 — Deep Analysis (requires clone)

When you need semantic understanding: call graphs, impact analysis, refactoring safety.

### Clone → CodeGraph → Archaeology

```bash
# Shallow clone for speed
gh repo clone owner/repo /tmp/explore-repo -- --depth=1
cd /tmp/explore-repo

# Index with CodeGraph
npx @colbymchenry/codegraph init
npx @colbymchenry/codegraph index
```

Then use CodeGraph MCP tools:
- `mcp_codegraph_codegraph_context` — comprehensive context for a task
- `mcp_codegraph_codegraph_search` — find symbols by name
- `mcp_codegraph_codegraph_callers` — who calls this function
- `mcp_codegraph_codegraph_callees` — what this function calls
- `mcp_codegraph_codegraph_trace` — trace call path from A to B

### Git Archaeology (for Context/History requests)

When the user asks "why was this changed" or "who wrote this":

```bash
cd /tmp/explore-repo

# File change history
git log --oneline -n 20 -- path/to/file.py

# Line-level authorship
git blame -L 10,30 path/to/file.py

# Specific commit diff
git show <sha> -- path/to/file.py

# Search commit messages
git log --oneline --grep="keyword"

# Search issues/PRs (requires gh login)
gh search issues "keyword" --repo owner/repo --limit 10
gh search prs "keyword" --repo owner/repo --limit 10

# View issue/PR with comments
gh issue view <number> --repo owner/repo --comments
gh pr view <number> --repo owner/repo --comments
```

Without `gh`, fall back to `web_extract` or `browser` for GitHub issue/PR pages.

### Permalink Construction

**Always use full commit SHA, never branch names** (branches mutate, SHAs are immutable):

```bash
cd /tmp/explore-repo
FULL_SHA=$(git rev-parse HEAD)
# Construct: https://github.com/owner/repo/blob/$FULL_SHA/path/to/file.py#L10-L20
```

Use permalinks in L4 output and Source Maps. Format: Markdown link with line range, e.g. `[file.py:10-20](https://github.com/owner/repo/blob/<sha>/path#L10-L20)`.

### Cleanup

```bash
rm -rf /tmp/explore-repo
```

---

## Common Patterns

### Pattern 1: "Show me how X is implemented"

1. Search for the symbol → `gh search code "def X" --repo owner/repo`
2. Read the file → L1 raw URL → `web_extract`
3. If complex, escalate to L4 clone.

### Pattern 2: "What projects use X library"

1. `grep.app` for import patterns
2. Extract repo names from results
3. L1 for specific files in those repos

### Pattern 3: "Explain this repo's architecture"

1. L3 github1s → browser file tree
2. Read top-level files: README, setup.py/pyproject.toml/go.mod, main entry point
3. L1 for key modules
4. L4 CodeGraph if you need to trace data flow

### Pattern 4: "Find similar implementations across projects"

1. `gh search code` for a distinctive pattern
2. `web_extract` a few candidate files
3. Compare and report

---

## Pitfalls

### gh CLI

- **Must be logged in.** Check with `gh auth status`. If not: tell user to run `gh auth login`.
- **Rate limits.** Unauthenticated API = 60 req/hr. Authenticated = 5,000 req/hr. `gh search code` uses the legacy search API — results may lag behind github.com.
- **Large files.** GitHub API truncates files >1MB. Use `git clone --depth=1` for those.

### web_extract / exa_fetch

- **`mcp_exa_web_fetch_exa` is the primary path for raw.github URLs** — reliable, returns markdown. Use `maxCharacters` for large files.
- **`web_extract` may block raw.githubusercontent.com** (private network error). Fall back to Exa fetch when blocked.

### github1s

- **No accessibility tree for code.** VS Code web renders in canvas/WebGL. Use `browser_console` to extract text: `document.querySelectorAll('.view-line')`.
- **Pop-up on first load.** Click "OK" to dismiss.

### grep.app

- **Only public repos.** Won't find private repo code.
- **Index lag.** May be hours behind the latest commits.

### CodeGraph

- **Must be in project directory** for all `mcp_codegraph_codegraph_*` calls.
- **Indexing takes time.** ~30s for a medium repo. Worth it for deep analysis, overkill for quick lookups.
- **Only indexes indexed repos.** `mcp_codegraph_codegraph_status()` to check.

---

## Quick Reference

| Want to... | Tool | Command |
|------------|------|---------|
| Read one file | `mcp_exa_web_fetch_exa` raw URL or `gh api` | L1 |
| List directory | `gh api .../contents/` | L1 |
| Search code globally | `gh search code` or `grep.app` | L2 |
| Find projects | Exa search | L2 |
| Browse with IDE | `github1s` in browser | L3 |
| Quick file open | `gh browse -R --` | L3 |
| Deep code analysis | Clone + CodeGraph | L4 |
| LOC / stats | `codebase-inspection` skill | — |

---

## ✅ Verification Checklist (RUN BEFORE RETURNING RESULTS)

- [ ] Did I classify the request (Conceptual/Implementation/Context/Comprehensive)?
- [ ] For L2: did I re-sort results by stars + recency before picking which repos to examine?
- [ ] Did I pick the right layer for this classification (not defaulting to L4)?
- [ ] Did I skip `web_extract` for GitHub URLs and use `mcp_exa_web_fetch_exa` or `gh api` instead?
- [ ] For Context/History: did I use git log/blame/show and construct permalinks with full commit SHA?
- [ ] For L4: did I clone to `/tmp/` and index with CodeGraph before deep analysis?
- [ ] Did I clean up `/tmp/explore-repo` after L4 analysis?

**If any box is unchecked, go back.**

---

## Deployment & Sync

**After ANY update to this SKILL.md, you MUST:**

1. **Sync to ALL Hermes profiles** — discover and sync to every profile dynamically:
   ```bash
   # Discover all profiles (never hardcode names — profiles grow)
   for prof in $(ls -d ~/.hermes/profiles/*/ 2>/dev/null | xargs -n1 basename); do
     dst=~/.hermes/profiles/$prof/skills/github/github-code-explorer
     [ -d "$dst" ] && cp -r "$dst" ~/.hermes/profiles/$prof/backups/github-code-explorer-$(date +%Y%m%d_%H%M%S)
     rm -rf "$dst"
     cp -r ~/.hermes/skills/github/github-code-explorer "$dst"
   done
   ```
   This auto-scales — new profiles are picked up without code changes.

2. **Sync Obsidian documentation** — update `~/Documents/Obsidian/AlexCai/00-Inbox/工具制作_Hermes检索总控与GitHub源码探索_三省六部体系_20260526.md`:
   - Bump version history table
   - Update one-line summary if scope changed
   - Bump `modified` timestamp

3. **Update qmd index:** `qmd update`

4. **Verify:** Spot-check 2-3 profiles for SKILL.md presence + content markers (`Step 0: Classify`, `Git Archaeology`, `Permalink Construction`).

- `references/raw-github-extraction.md` — tested tool behaviour matrix for GitHub URL extraction patterns.
- `references/real-world-tests.md` — verified tool paths with actual test outputs from session 2026-05-26.
- `references/cross-profile-sync.md` — deployment script for syncing to all 三省六部 profiles.

## Obsidian Documentation Sync

**This skill has an Obsidian knowledge base document.** After ANY update to this SKILL.md, sync the document:

- **Obsidian doc:** `00-Inbox/工具制作_Hermes检索总控与GitHub源码探索_三省六部体系_20260526.md`
- **Sync actions:** update version history table, update one-line summary if scope changed, bump `modified` timestamp
- **Verification:** after sync, confirm the Obsidian doc mentions the latest version/feature added