# Real-World Tool Path Testing (Session 2026-05-26)

Verification of every code-reading path in the github skill (references/code-explorer.md) four-layer
strategy. Tool names and behaviors are environment-specific — run equivalent
tests after setup changes.

## Environment

- Hermes default profile, macOS 26.2
- `gh` CLI: authenticated (Loveacup, token scopes: repo, read:org, gist, admin:public_key)
- CodeGraph MCP: active
- Exa MCP: active
- Session model: gpt-5.5 (openai-codex)

## L1 — Single-File Extraction

### ✓ `gh api .../contents/... --jq '.content' | base64 -d`

```bash
$ gh api repos/NousResearch/hermes-agent/contents/agent --jq '.[].name' | head -5
__init__.py
account_usage.py
agent_init.py
agent_runtime_helpers.py
anthropic_adapter.py

$ gh api repos/NousResearch/hermes-agent/contents/agent/codex_responses_adapter.py \
    --jq '.content' | base64 -d | head -4
"""Codex Responses API adapter.

Pure format-conversion and normalization logic for the OpenAI Responses API
(used by OpenAI Codex, xAI, GitHub Models, and other Responses-compatible endpoints).
```
✅ Both directory listing and file content extraction work in <1s.

### ✓ `mcp_exa_web_fetch_exa` on raw.githubusercontent.com

```python
mcp_exa_web_fetch_exa(
    urls=["https://raw.githubusercontent.com/NousResearch/hermes-agent/main/agent/codex_responses_adapter.py"],
    maxCharacters=3000
)
→ Returns clean markdown with full source code
```
✅ Reliable; primary L1 path.

### ✗ `web_extract` on raw.githubusercontent.com

```python
web_extract(urls=["https://raw.githubusercontent.com/NousResearch/hermes-agent/main/agent/codex_responses_adapter.py"])
→ Error: "Blocked: URL targets a private or internal network address"
```
❌ Blocked — do not use for GitHub raw URLs. Fall back to Exa fetch.

### ✗ `web_extract` on GitHub HTML pages

```python
web_extract(urls=["https://github.com/NousResearch/hermes-agent/blob/main/..."]])
→ Error: "Blocked: URL targets a private or internal network address"
```
❌ Blocked — as expected.

## L2 — Cross-Repo Code Search

### ✓ `gh search code`

```bash
$ gh search code "to=functions." --repo NousResearch/hermes-agent --language python --limit 3
NousResearch/hermes-agent:agent/codex_responses_adapter.py
NousResearch/hermes-agent:agent/codex_responses_adapter.py
NousResearch/hermes-agent:tests/run_agent/test_run_agent_codex_responses.py
```
✅ Works with authenticated gh. Legacy search API — index may lag behind github.com.

## L3 — Interactive Browse

### ✓ `github1s.com`

```
https://github1s.com/NousResearch/hermes-agent
→ Full VS Code web editor, no login required
→ File tree populated, README.md auto-previewed
→ Code extraction via browser_console: document.querySelectorAll('.view-line')
→ FIRST LOAD: dismiss popup with browser_click on "OK" button
```
✅ Zero-auth, fast, preferred for quick exploration.

### ✗ `github.dev` (without login)

```
https://github.dev/NousResearch/hermes-agent
→ Redirects to "Sign in to GitHub" page
```
❌ Requires GitHub OAuth login before repo access. Use github1s for anonymous browsing.

## L4 — Deep Analysis

### ✓ CodeGraph on cloned repo

```
gh repo clone → npx @colbymchenry/codegraph init → index
→ mcp_codegraph_codegraph_* tools available
```
✅ Pattern verified in prior sessions (hermes-agent self-index).

## Summary

| Path | Status | Speed | Auth |
|------|--------|-------|------|
| `gh api .../contents/` + base64 | ✅ | <1s | gh login |
| `mcp_exa_web_fetch_exa` raw URL | ✅ | <2s | Exa API key |
| `web_extract` raw URL | ❌ blocked | — | — |
| `web_extract` GitHub HTML | ❌ blocked | — | — |
| `gh search code` | ✅ | <2s | gh login |
| `github1s` browser | ✅ | <5s | none |
| `github.dev` browser | ❌ needs login | — | GitHub OAuth |
| clone + CodeGraph | ✅ | <60s | git + npx |
