"""共享 GitHub 客户端（v5.0）。github + skill_discovery 共用，避免重复造认证/限流/GraphQL。

提供：
  - code_search(q)              code search（强制认证，10/min，1000 上限）
  - get_contents(repo, path)    取文件/目录内容（contents API）
  - subdir_commit_count(...)    子目录提交数（commits?path=&since=，解 Link 头 last 页号）
  - graphql(query, variables)   GraphQL（批量补全，消 N+1）

认证统一读 GITHUB_TOKEN；读 x-ratelimit-* 暴露剩余配额。单仓/单请求失败不抛到整链由调用方决定。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx

from .. import config
from ..errors import EngineError, EngineTimeoutError, RateLimitError

GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"
GITHUB_API_VERSION = "2022-11-28"

_LINK_LAST_RE = re.compile(r'[?&]page=(\d+)>;\s*rel="last"')


def parse_link_last(resp) -> int:
    """从 per_page=1 响应的 Link 头解析 rel="last" 页号 = since 以来提交总数。"""
    headers = getattr(resp, "headers", {}) or {}
    link = headers.get("Link") or headers.get("link") or ""
    m = _LINK_LAST_RE.search(link)
    if m:
        return int(m.group(1))
    try:
        body = resp.json()
    except Exception:
        return 0
    return len(body) if isinstance(body, list) else 0


class GitHubClient:
    """共享 GitHub REST/GraphQL 客户端。需 GITHUB_TOKEN（code search 强制认证）。"""

    def __init__(self, token: Optional[str] = None, timeout: float = 15.0):
        self._token = token
        self.timeout = timeout
        self._repo_cache: Dict[str, Dict[str, Any]] = {}   # repo 元数据缓存（按 full_name）

    def _key(self) -> str:
        key = self._token or config.get_env("GITHUB_TOKEN")
        if not key:
            raise EngineError("GITHUB_TOKEN not set")
        return key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._key()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": config.USER_AGENT,
        }

    @staticmethod
    def _raise_http(e: httpx.HTTPStatusError) -> None:
        code = e.response.status_code
        remaining = e.response.headers.get("X-RateLimit-Remaining")
        if code in (403, 429) and remaining == "0":
            raise RateLimitError("GitHub rate limit exceeded")
        if code == 401:
            raise EngineError("GitHub auth failed (check GITHUB_TOKEN)")
        raise EngineError(f"GitHub API HTTP {code}")

    async def _get(self, client, url, params=None):
        try:
            r = await client.get(url, params=params, headers=self._headers())
            r.raise_for_status()
            return r
        except httpx.HTTPStatusError as e:
            self._raise_http(e)
        except httpx.TimeoutException:
            raise EngineTimeoutError("GitHub request timeout")

    async def code_search(self, query: str, per_page: int = 30) -> Dict[str, Any]:
        """code search：返回 {items, total_count, incomplete_results}。强制认证。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await self._get(client, f"{GITHUB_API}/search/code",
                                 {"q": query, "per_page": per_page})
            data = r.json() or {}
        return {
            "items": data.get("items", []) or [],
            "total_count": data.get("total_count", 0),
            "incomplete_results": bool(data.get("incomplete_results")),
        }

    async def get_contents(self, repo: str, path: str) -> Any:
        """contents API：文件返回 dict（含 base64 content），目录返回 list。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await self._get(client, f"{GITHUB_API}/repos/{repo}/contents/{path}")
            return r.json()

    async def get_repo(self, repo: str) -> Dict[str, Any]:
        """取仓库元数据（stars/forks/pushed_at/license/...）。按 full_name 缓存。

        供 skill 发现做包级评分（STDD §5.2）；同一 monorepo 多个 skill 仅抓一次。
        """
        if repo in self._repo_cache:
            return self._repo_cache[repo]
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await self._get(client, f"{GITHUB_API}/repos/{repo}")
            data = r.json() or {}
        self._repo_cache[repo] = data
        return data

    async def subdir_commit_count(self, repo: str, path: str, since: str) -> Optional[int]:
        """子目录提交数：commits?path=&since=&per_page=1，读 Link 头 last 页号。

        解大包「整体质量 ≠ 单 skill 质量」难点的核心 API（path 参数官方支持）。
        失败返回 None（由调用方降级）。
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await self._get(client, f"{GITHUB_API}/repos/{repo}/commits",
                                    {"path": path, "since": since, "per_page": 1})
                return parse_link_last(r)
        except Exception:
            return None

    async def graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """GraphQL：一次取多仓库/多字段，消 N+1。返回 data 块。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.post(GITHUB_GRAPHQL,
                                      headers=self._headers(),
                                      json={"query": query, "variables": variables})
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                self._raise_http(e)
            except httpx.TimeoutException:
                raise EngineTimeoutError("GitHub GraphQL timeout")
            data = r.json() or {}
        if data.get("errors"):
            raise EngineError(f"GitHub GraphQL error: {data['errors']}")
        return data.get("data", {}) or {}
