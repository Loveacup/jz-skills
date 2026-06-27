# GitHub Lane (Full Reference)

> Load this reference when GitHub mode is triggered and you need detailed strategy.

## Search Ranking Principle

**Results MUST be ranked by heat + recency.** Apply before presenting any GitHub search results.

| Signal | Weight | Why |
|------|:--:|------|
| **Stars** | 🔴 High | Community validation. 82K vs 23 stars is a 3500x signal difference. |
| **pushed_at** | 🔴 High | Active maintenance. >3 months stale → likely broken deps. |
| created_at | 🟡 Medium | Prefer newer repos in same star tier. |
| forks | 🟢 Low | Auxiliary signal only. |

**Process:**
1. Sort by Stars DESC, pick top 5
2. Filter: pushed_at ≤ 3 months
3. Within same tier: prefer newer created_at
4. Cross-validate: ≥2 independent sources confirm quality

**Red cards:**
- High stars but >2 years stale → ⚠️ Flag as potentially outdated
- Active pushes but <10 stars → ⚠️ Flag as unvalidated

---

## Request Classification (Step 0)

| 类型 | 触发词 | 主策略 |
|------|------|------|
| **Conceptual** | "怎么用 X"、"best practice for Y" | web_search + fetch README/docs |
| **Implementation** | "X 怎么实现 Y"、"看源码" | clone → code search → permalink |
| **Context/History** | "为什么改了这个"、"谁写的" | git log/blame + gh search issues/PRs |
| **Comprehensive** | "深度分析"、请求复杂或模糊 | 以上全用 |

## Four-Layer Strategy

| 层 | 工具 | 耗时 | 适用场景 |
|---|------|------|------|
| **L1** | `web_fetch` → `raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}` | 秒 | 看一个文件/函数 |
| **L2** | `web_search(provider="exa")` → GitHub | 秒 | 搜索类似实现 |
| **L3** | `web_fetch` → README + 目录结构 | 分钟 | 了解项目整体 |
| **L4** | L1+L2+L3 + clone + git archaeology + permalink | 分钟 | 深度分析 |

**L1 tips:** Raw URL format. If file too large, fetch directory first. Prioritize entry files.

**L2 tips:** Exa query with `site:github.com`. Brave supplement: `{library_name} example usage`.

**L3 tips:** Fetch README first. Optionally fetch directory structure. Quickly judge if worth deep dive.

## Permalink Construction

```bash
# Get commit SHA
cd /tmp/pi-github-repos/{owner}/{repo} && git rev-parse HEAD

# Construct immutable permalink
https://github.com/{owner}/{repo}/blob/{full-sha}/path/to/file#L10-L20

# Get SHA from tag
gh api repos/{owner}/{repo}/git/refs/tags/v1.0.0 --jq '.object.sha'
```

**Always use full SHA, never branch names.** Branches mutate; SHAs don't.

## Git Archaeology

```bash
git log --oneline -n 20 -- path/to/file.ts       # File history
git blame -L 10,30 path/to/file.ts                # Line attribution
git show <sha> -- path/to/file.ts                  # Commit diff
git log --oneline --grep="keyword" -n 10          # Commit message search
gh search prs "keyword" --repo owner/repo --state merged --limit 10
gh issue view --repo owner/repo --comments <number>
gh pr view --repo owner/repo --comments <number>
```

Requires `gh` CLI with `gh auth login`. Fall back to web_fetch if unavailable.

## Failure Recovery

| 失败 | 恢复 |
|------|------|
| grep finds nothing | Broaden query, try concept names or related imports |
| gh rate limited | Use local git on already-cloned repo |
| Repo too large to clone | web_fetch README + directory, fetch key files step by step |
| File not found in clone | Branch with `/` may misresolve; list repo tree first |
| Uncertain results | State uncertainty explicitly, propose hypothesis, show evidence |
| raw URL 403 | Try GitHub API: `https://api.github.com/repos/{owner}/{repo}/contents/{path}` |

## Common Patterns

| 场景 | 路径 |
|------|------|
| 看实现 | L1: fetch raw → permalink |
| 找用法 | L2: Exa search GitHub → L1 fetch examples → permalink |
| 读架构 | L3: README → directory → L1 core modules |
| 找类似 | L2: Exa semantic + Brave supplement |
| 追历史 | git log → blame → gh search issues/PRs → permalink |
| 全面分析 | classify → L1-L4 progressive → permalink + git archaeology |
