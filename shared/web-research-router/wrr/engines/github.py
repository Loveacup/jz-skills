"""GitHub 引擎：仓库搜索 + 轻量三维综合评分排序（P1）。

调用 GitHub Search API ``/search/repositories``，对返回仓库按

    score = w_a*activity + w_p*popularity + w_f*freshness   （默认 0.40/0.35/0.25）

重排（三项均归一到 [0,1]）。仅支持 search；extract/similar 继承基类默认抛 EngineError。

维度（P1 轻量版；完整 5 维 + 反作弊见 P2）：
  - activity   最近 30 天 commit 速度（对数压缩）。默认经 ``/repos/{full}/commits``
               单仓 REST 实测：按 ``Link`` 头 ``rel="last"`` 页号取 30 天提交数，
               **并发**拉取整批结果，任一失败/限流则**降级**到 ``open_issues_count``
               代理（含 PR）。可用 ``config.GITHUB_ACTIVITY_LOOKUP=False`` 关闭，
               退化为单次 search 调用的纯轻量模式。
  - popularity ``log10(stars)`` 归一 + fork/star 比例加成。
  - freshness  ``pushed_at`` 衰减：≤30 天=1.0，90 天=0.5，≥180 天=0（分段线性）。

设计取舍（供审核）：activity 默认实测 30 天 commit 速度以对齐验收"最近 30 天速度"，
代价是每条结果多一次 REST（并发、有界、可关）。不使用 GraphQL（REST 足够，符合非目标）。
"""
from __future__ import annotations

import asyncio
import math
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx

from .base import SearchEngine
from .. import config
from ..errors import EngineError, EngineTimeoutError, RateLimitError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
GITHUB_REPO_URL = "https://api.github.com/repos"
GITHUB_API_VERSION = "2022-11-28"

# Link 头里 rel="last" 的页号 = since 以来的提交总数（per_page=1 时）。
_LINK_LAST_RE = re.compile(r'[?&]page=(\d+)>;\s*rel="last"')


# ── 纯评分函数（无 I/O，单测可直接调用）──────────────────────────────
def freshness(pushed_at: Optional[str], now: Optional[datetime] = None) -> float:
    """pushed_at 新鲜度：≤30 天=1.0，90 天=0.5，≥180 天=0，分段线性。"""
    if not pushed_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    days = (now - dt).total_seconds() / 86400.0
    if days <= 30:
        return 1.0
    if days >= 180:
        return 0.0
    if days <= 90:
        return 1.0 - 0.5 * (days - 30) / 60.0     # 30..90 → 1.0..0.5
    return 0.5 - 0.5 * (days - 90) / 90.0          # 90..180 → 0.5..0.0


def popularity(stars: int, forks: int) -> float:
    """log10(stars) 归一（~1e6 stars→1.0）+ fork/star 比例加成（封顶 0.1）。"""
    base = math.log10((stars or 0) + 1) / 6.0
    ratio = (forks / stars) if stars and stars > 0 else 0.0
    return min(1.0, base + 0.1 * min(ratio, 1.0))


def activity(commits_30d: Optional[int], open_issues: int = 0) -> float:
    """活跃度：实测 30 天 commit 速度（~1000→1.0）；commits_30d=None 时降级到
    open_issues_count（含 PR）代理。"""
    if commits_30d is None:
        return min(1.0, math.log10((open_issues or 0) + 1) / 4.0)
    return min(1.0, math.log10((commits_30d or 0) + 1) / 3.0)


def score(act: float, pop: float, fresh: float) -> float:
    """三维加权综合分（v4 兼容）。权重取自 config.GITHUB_SCORE_WEIGHTS。"""
    w_a, w_p, w_f = config.GITHUB_SCORE_WEIGHTS
    return w_a * act + w_p * pop + w_f * fresh


# ── v5.0：新增 maintenance 维度（加法式，不改 v4 三维 score）──────────
def maintenance(open_issues: int, stars: int) -> float:
    """维护度：open_issues/stars 健康度。>10%（GITHUB_NEGLECT_RATIO）判被忽视→趋近0。

    研究依据 /tmp/wrr-research-report.md §1（awesome 自调节 community_health）。
    """
    if not stars or stars <= 0:
        return 0.0 if (open_issues or 0) > 0 else 0.5
    ratio = (open_issues or 0) / stars
    return 1.0 - min(ratio / config.GITHUB_NEGLECT_RATIO, 1.0)


def score_v5(act: float, pop: float, fresh: float, maint: float) -> float:
    """四维加权综合分（v5）。权重取自 config.GITHUB_SCORE_WEIGHTS_V5。"""
    w_a, w_p, w_f, w_m = config.GITHUB_SCORE_WEIGHTS_V5
    return w_a * act + w_p * pop + w_f * fresh + w_m * maint


def _parse_commit_count(resp) -> int:
    """从 /commits?per_page=1 响应解析 since 以来的提交数。"""
    headers = getattr(resp, "headers", {}) or {}
    link = headers.get("Link") or headers.get("link") or ""
    m = _LINK_LAST_RE.search(link)
    if m:
        return int(m.group(1))
    body = resp.json()
    return len(body) if isinstance(body, list) else 0


class GitHubEngine(SearchEngine):
    name = "github"
    tier = 1

    def _key(self) -> str:
        key = config.get_env("GITHUB_TOKEN")
        if not key:
            raise EngineError("GITHUB_TOKEN not set")
        return key

    def _headers(self, key: str) -> dict:
        return {
            "Authorization": f"Bearer {key}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": config.USER_AGENT,
        }

    @staticmethod
    def _clean_query(q: str) -> str:
        """剥掉 web 风格的 site:github.com 触发词（GitHub 搜索语法不识别）。"""
        cleaned = re.sub(r"(?i)\bsite:github\.com\b", " ", q or "")
        return " ".join(cleaned.split()).strip()

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        key = self._key()
        q = self._clean_query(options.query) or (options.query or "").strip()
        if not q:
            raise EngineError("GitHub query empty after cleaning")
        count = max(1, min(options.count, config.MAX_SEARCH_COUNT))
        headers = self._headers(key)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    GITHUB_SEARCH_URL,
                    params={"q": q, "per_page": count},
                    headers=headers,
                )
                resp.raise_for_status()
                items = (resp.json() or {}).get("items", []) or []
                commit_counts = await self._fetch_activity(client, headers, items)
        except (EngineError, EngineTimeoutError, RateLimitError):
            raise
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            remaining = e.response.headers.get("X-RateLimit-Remaining")
            if code in (403, 429) and remaining == "0":
                raise RateLimitError("GitHub rate limit exceeded")
            if code == 401:
                raise EngineError("GitHub auth failed (check GITHUB_TOKEN)")
            raise EngineError(f"GitHub API HTTP {code}")
        except httpx.TimeoutException:
            raise EngineTimeoutError("GitHub request timeout")
        except httpx.HTTPError as e:
            raise EngineError(f"GitHub error: {str(e) or type(e).__name__}")

        if not items:
            raise EngineError("GitHub returned empty results")

        now = datetime.now(timezone.utc)
        scored = []
        for repo, c30 in zip(items, commit_counts):
            stars = repo.get("stargazers_count", 0) or 0
            forks = repo.get("forks_count", 0) or 0
            open_issues = repo.get("open_issues_count", 0) or 0
            sc = score_v5(
                activity(c30, open_issues),
                popularity(stars, forks),
                freshness(repo.get("pushed_at"), now),
                maintenance(open_issues, stars),    # v5：新增 maintenance 维
            )
            scored.append((sc, repo, stars, forks))

        scored.sort(key=lambda t: t[0], reverse=True)
        out: List[SearchResult] = []
        for sc, repo, stars, forks in scored[:count]:
            desc = repo.get("description") or ""
            out.append(SearchResult(
                title=repo.get("full_name") or repo.get("name") or "",
                url=repo.get("html_url") or "",
                snippet=f"{desc} · ★{stars} ⑂{forks} · score={sc:.3f}".strip(" ·"),
            ))
        return out

    async def _fetch_activity(self, client, headers, items) -> List[Optional[int]]:
        """并发取每个仓库最近 30 天 commit 数；关闭或失败时返回 None（降级代理）。"""
        if not config.GITHUB_ACTIVITY_LOOKUP or not items:
            return [None] * len(items)
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")

        async def one(repo) -> Optional[int]:
            full = repo.get("full_name")
            if not full:
                return None
            try:
                r = await client.get(
                    f"{GITHUB_REPO_URL}/{full}/commits",
                    params={"since": since, "per_page": 1},
                    headers=headers,
                )
                r.raise_for_status()
                return _parse_commit_count(r)
            except Exception:
                return None       # 单仓活跃度失败不应拖垮整次搜索

        return list(await asyncio.gather(*[one(r) for r in items]))

    # ── v5.0：issue 搜索（质量信号 qualifier）─────────────────────────
    async def issue_search(self, options: SearchOptions) -> List[SearchResult]:
        """搜 issue/PR，按 interactions 排序 + 质量信号 qualifier。

        研究依据 §1.4：sort:interactions + reactions:>N + reason:completed + linked:pr。
        """
        key = self._key()
        q = self._clean_query(options.query) or (options.query or "").strip()
        if not q:
            raise EngineError("GitHub issue query empty")
        q = f"{q} sort:interactions"
        count = max(1, min(options.count, config.MAX_SEARCH_COUNT))
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": q, "per_page": count},
                    headers=self._headers(key),
                )
                resp.raise_for_status()
                body = resp.json() or {}
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            if code in (403, 429) and e.response.headers.get("X-RateLimit-Remaining") == "0":
                raise RateLimitError("GitHub rate limit exceeded")
            raise EngineError(f"GitHub issue search HTTP {code}")
        except httpx.TimeoutException:
            raise EngineTimeoutError("GitHub issue search timeout")
        out: List[SearchResult] = []
        for it in body.get("items", []) or []:
            reactions = (it.get("reactions") or {}).get("+1", 0)
            comments = it.get("comments", 0)
            sig = f"👍{reactions} 💬{comments}"
            if it.get("state_reason") == "completed":
                sig += " ✅completed"
            if it.get("pull_request"):
                sig += " ·PR"
            out.append(SearchResult(
                title=it.get("title") or "",
                url=it.get("html_url") or "",
                snippet=f"{(it.get('body') or '')[:160]} · {sig} · state={it.get('state')}",
                source_tag="github-issue",
            ))
        if not out:
            raise EngineError("GitHub issue search empty")
        return out

    # ── v5.0：GraphQL 批量活跃度（一次取 N 仓库 history.totalCount，消 N+1）──
    async def fetch_activity_graphql(self, client_graphql, repos: List[str],
                                     since: str) -> dict:
        """用共享 GitHubClient.graphql 一次取多仓库 30 天 commit 数。

        repos: ["owner/name", ...]；client_graphql: GitHubClient 实例。
        返回 {full_name: commits_30d}。研究依据 §1.3 消除 N+1。
        """
        if not repos:
            return {}
        parts = []
        for i, full in enumerate(repos):
            owner, _, name = full.partition("/")
            parts.append(
                f'r{i}: repository(owner: "{owner}", name: "{name}") {{ '
                f'nameWithOwner defaultBranchRef {{ target {{ ... on Commit {{ '
                f'history(since: "{since}") {{ totalCount }} }} }} }} }}')
        query = "query { " + " ".join(parts) + " }"
        data = await client_graphql.graphql(query, {})
        out = {}
        for i, full in enumerate(repos):
            node = data.get(f"r{i}") or {}
            ref = (node.get("defaultBranchRef") or {}).get("target") or {}
            hist = (ref.get("history") or {})
            out[full] = hist.get("totalCount")
        return out

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """检查 GITHUB_TOKEN 是否配置。"""
        token = config.get_env("GITHUB_TOKEN")
        if not token:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="GITHUB_TOKEN not configured",
                requirements=["env:GITHUB_TOKEN"],
                repair=[
                    "Set GITHUB_TOKEN in your shell or ~/.hermes/.env:",
                    "  export GITHUB_TOKEN=your_token_here",
                    "Rerun: wrr-cli.py doctor --engine github",
                ],
                evidence={"env.GITHUB_TOKEN": "missing"},
            )
        return EngineCheckResult(
            engine=self.name,
            status="ok",
            tier=self.tier,
            summary="GITHUB_TOKEN configured",
            active_backend="github-api",
            evidence={"env.GITHUB_TOKEN": "present"},
        )
