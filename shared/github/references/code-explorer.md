# GitHub Code Explorer v2.0

Four-layer strategy for exploring GitHub source code. Start light, escalate only when needed.

> **Prerequisite:** Run auth detection from main SKILL.md. Requires `gh` for L2/L4, `mcp_exa_web_fetch_exa` for L1.

## 🚨 Red Flags

| Excuse | Why wrong |
|--------|-----------|
| "I'll just use `web_extract` on the raw URL" | `web_extract` blocks `raw.githubusercontent.com`. Use `mcp_exa_web_fetch_exa`. |
| "I know this repo, I'll just read the main file" | Wrong classification wastes steps. Conceptual → README first, not source. |
| "A quick `gh api` call will answer this" | Only if you know the exact file path. For cross-file questions, start with `gh search code`. |
| "I'll clone it for deep analysis — that's thorough" | L4 costs 30s+ indexing. For a single function, L1 is 2 seconds. |
| "`web_search` will find the implementation" | Web search is for docs/blogs, not source code. Use `gh search code`. |
| "These search results look fine, I'll use the first few" | Always re-sort by stars + recency before picking repos. |

## Decision Tree

### Step 0: Classify the request FIRST

```
User asks about a GitHub project

├─ Conceptual ("这个API怎么用")
│   → L1 README + docs first, NOT source code
│
├─ Implementation ("这个函数怎么实现")
│   → L1→L2→L4 source code path
│
├─ Context/History ("为什么要这么改")
│   → git log/blame/show + gh search issues/PRs
│   → Permalink with full commit SHA
│
└─ Comprehensive ("全面分析这个项目")
    → Classify sub-questions first → L1→L4 progressive deepening
```

### Then choose the layer

```
├─ 单个文件/函数 → L1: mcp_exa_web_fetch_exa OR gh api
├─ 跨项目搜索 → L2: grep.app + gh search code
├─ 探索结构 → L3: github1s browser OR gh browse
└─ 深度分析 → L4: clone + CodeGraph
```

**Rule of thumb:** Don't know the file → L2. Know the file but not structure → L3. Need semantics → L4.

---

## L1 — Single-File Extraction (seconds)

### Read a file

Construct raw URL from GitHub URL:
```
https://github.com/owner/repo/blob/main/path/to/file.py
→ https://raw.githubusercontent.com/owner/repo/main/path/to/file.py
```

Then call `mcp_exa_web_fetch_exa(urls=[raw_url])`. Use `maxCharacters` for large files (default 3000, bump to 10000+).

**Fallback — gh api (when branch unknown):**
```bash
gh api repos/owner/repo --jq '.default_branch'
gh api repos/owner/repo/contents/path/to/file.py --jq '.content' | base64 -d
```

### Directory listing
```bash
gh api repos/owner/repo/contents/path/to/dir --jq '.[].name'
```

---

## L2 — Cross-Repo Code Search (seconds)

### 🔥 Sorting: Heat + Recency First

**Always re-sort before picking repos:**
1. Stars ≥100 preferred, ≥1000 ideal
2. Updated ≤6 months preferred
3. Same stars → pick newer. Same recency → pick more stars.

### grep.app — fastest public code search

Go to `https://grep.app/search?q=<search_term>` in browser, or construct URL + use browser tools.

### GitHub Code Search via gh
```bash
gh search code "function_name" --repo owner/repo
gh search code "import torch.nn.functional" --language python
gh search code "useState" --extension tsx --language typescript
gh search code "class Agent" --filename "*.py"
```

### Exa for semantic discovery
```bash
mcp_exa_web_search_exa(query="open source project for X in Python")
```

| Tool | Best for | Auth |
|------|----------|------|
| `grep.app` | "show me how X API is used" | None |
| `gh search code` | "find this pattern in Y repo" | gh login |
| `Exa` | "find projects that do X" | API key |

---

## L3 — Repository Exploration (minutes)

### github1s (no login, read-only)
Replace `github.com` with `github1s.com`:
```
https://github.com/NousResearch/hermes-agent
→ https://github1s.com/NousResearch/hermes-agent
```
Use `browser_navigate` → `browser_click` for file tree → `browser_console` for editor text.

### gh browse (fastest when you know the path)
```bash
gh browse -R owner/repo                    # open repo
gh browse -R owner/repo -- path/to/file.go # open file
gh browse -R owner/repo -n -- internal/config.go  # print URL only
```

---

## L4 — Deep Analysis (requires clone)

```bash
gh repo clone owner/repo /tmp/explore-repo -- --depth=1
cd /tmp/explore-repo
npx @colbymchenry/codegraph init
npx @colbymchenry/codegraph index
```

Then use CodeGraph MCP tools:
- `mcp_codegraph_codegraph_context` — comprehensive context for a task
- `mcp_codegraph_codegraph_search` — find symbols
- `mcp_codegraph_codegraph_callers` / `_callees` — who calls / what it calls
- `mcp_codegraph_codegraph_trace` — trace path A→B

### Git Archaeology (Context/History)
```bash
git log --oneline -n 20 -- path/to/file.py   # file history
git blame -L 10,30 path/to/file.py            # line-level authorship
git show <sha> -- path/to/file.py             # commit diff
git log --oneline --grep="keyword"            # search commits
gh search issues "keyword" --repo owner/repo --limit 10
gh search prs "keyword" --repo owner/repo --limit 10
```

### Permalinks

**Always use full commit SHA, never branch names:**
```bash
FULL_SHA=$(git rev-parse HEAD)
# https://github.com/owner/repo/blob/$FULL_SHA/path/to/file.py#L10-L20
```

### Cleanup
```bash
rm -rf /tmp/explore-repo
```

---

## Common Patterns

### "Show me how X is implemented"
1. `gh search code "def X" --repo owner/repo`
2. L1 raw URL → `mcp_exa_web_fetch_exa`
3. If complex → L4 clone

### "What projects use X library"
1. `grep.app` for import patterns
2. L1 for specific files in those repos

### "Explain this repo's architecture"
1. L3 github1s → file tree
2. L1 for README, setup.py/go.mod, entry point
3. L4 CodeGraph for data flow tracing

---

## Pitfalls

- **`gh search code`** uses legacy search API — results may lag behind github.com
- **Large files >1MB:** GitHub API truncates. Use `git clone --depth=1`.
- **github1s:** no accessibility tree for code. Use `browser_console` to extract.
- **grep.app:** only public repos. Index may lag hours behind.
- **CodeGraph:** must be in project directory. Indexing takes ~30s.
