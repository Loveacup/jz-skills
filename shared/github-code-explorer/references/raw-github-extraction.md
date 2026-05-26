# Raw GitHub Content Extraction — Tool Behaviour Matrix

Findings from 2026-05-26 session testing which tools can reliably fetch raw GitHub source code.

## URL Patterns Tested

| URL Pattern | web_extract | mcp_exa_web_fetch_exa | gh api |
|-------------|-------------|-----------------------|--------|
| `raw.githubusercontent.com/owner/repo/main/file.py` | ❌ Blocked ("private network") | ✅ Returns markdown | N/A |
| `github.com/owner/repo/blob/main/file.py` | ❌ Blocked ("private network") | ❌ Returns HTML page | N/A |
| `api.github.com/repos/owner/repo/contents/path` | N/A (API) | N/A (API) | ✅ Returns base64-encoded content |

## Detailed Findings

### web_extract
- Blocks ALL GitHub domains, including `raw.githubusercontent.com`.
- Error: "Blocked: URL targets a private or internal network address"
- **Do not use for GitHub content at all.**

### mcp_exa_web_fetch_exa
- Works for `raw.githubusercontent.com` → returns clean markdown.
- Does NOT work for `github.com/owner/repo/blob/...` → returns the HTML page, not the code.
- Use `maxCharacters` parameter to control output size (default 3000, bump to 10000+ for large files).

### gh api
- Authenticated: `gh api repos/owner/repo/contents/path --jq '.content' | base64 -d`
- Returns file contents as base64-encoded string.
- Files >1MB: API returns sha only, must use git data API: `gh api repos/owner/repo/git/blobs/<sha>`
- Must be logged in (`gh auth login`). Unauthenticated = 60 req/hr limit.

## Recommended Priority

1. **L1 fast read**: `mcp_exa_web_fetch_exa(urls=["https://raw.githubusercontent.com/..."])`
2. **L1 fallback**: `gh api repos/owner/repo/contents/path --jq '.content' | base64 -d`
3. **L3 interactive**: `github1s.com/owner/repo` via browser (zero auth, VS Code in browser)
4. **L4 deep**: `gh repo clone owner/repo /tmp/explore -- --depth=1` + CodeGraph index

## Tool Names in This Profile

- `mcp_exa_web_fetch_exa` — Exa MCP fetch tool
- `web_extract` — blocked for GitHub, use only for non-GitHub URLs
- `gh` — GitHub CLI (logged in via gh CLI)
