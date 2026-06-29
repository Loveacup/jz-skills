"""local_session 引擎（v5.2，Tier 1）：历史对话检索。

数据源：Hermes 内置 session_search(query, limit) tool。
适用查询：「刚才聊过 / 上次对话 / 历史对话 / 某次 session 里」。
只实现 search() + health_check()；不实现 extract/similar。

隐私：仅返回命中片段 snippet，不返回完整对话链；snippet 截断 500 字符。
降级：同 local_supermemory，Hermes tool 缺失 → fail/EngineError，router 隔离。
"""
from __future__ import annotations

import asyncio
from typing import Callable, List, Optional

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._local_utils import (resolve_hermes_tool, call_tool, call_tool_with_retry, extract_rows,
                           normalize_local_query, LOCAL_FRESHNESS_DEFAULT)

_TOOL = "session_search"


class LocalSessionEngine(SearchEngine):
    name = "local_session"
    tier = 1

    def __init__(self, tool: Optional[Callable] = None) -> None:
        self._tool = tool

    def _resolve(self) -> Optional[Callable]:
        return self._tool or resolve_hermes_tool(_TOOL)

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        tool = self._resolve()
        if tool is None:
            raise EngineError(f"{_TOOL} unavailable (not in Hermes runtime)")

        limit = min(options.count, config.LOCAL_MAX_RESULTS_PER_ENGINE)
        raw = await asyncio.wait_for(
            call_tool_with_retry(tool, query=normalize_local_query(options.query), limit=limit, timeout=5.0),
            timeout=self.timeout,
        )

        results: List[SearchResult] = []
        for i, row in enumerate(extract_rows(raw)[:limit]):
            if not isinstance(row, dict):
                continue
            sid = row.get("session_id") or row.get("conversation_id") or "unknown"
            turn = row.get("turn_id") or row.get("message_id") or (i + 1)
            ts = row.get("timestamp") or row.get("created_at") or ""
            text = (row.get("text") or row.get("content")
                    or row.get("snippet") or "")
            title = row.get("title") or f"Session {sid} turn {turn}"
            results.append(SearchResult(
                title=str(title)[:120],
                url=f"session://{sid}#turn={turn}",
                snippet=f"{ts} {text}".strip()[:500],
                highlights=row.get("highlights") or [],
                source_tag="local:session",
                freshness_score=LOCAL_FRESHNESS_DEFAULT,
            ))
        return results

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        tool = self._resolve()
        if tool is None:
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary=f"{_TOOL} tool unavailable",
                requirements=[f"Hermes tool:{_TOOL}"],
                repair=["Run inside Hermes runtime or configure session history backend"],
                evidence={f"tool.{_TOOL}": "missing"},
            )
        if not deep:
            return EngineCheckResult(
                engine=self.name, status="ok", tier=self.tier,
                summary=f"{_TOOL} tool registered",
                active_backend="hermes-session-search",
                evidence={f"tool.{_TOOL}": "present"},
            )
        try:
            sample = await asyncio.wait_for(
                call_tool(tool, query="WRR", limit=1), timeout=2.0)
            n = len(extract_rows(sample))
            return EngineCheckResult(
                engine=self.name, status="ok" if n > 0 else "warn", tier=self.tier,
                summary=f"{_TOOL} probe returned {n} result(s)",
                active_backend="hermes-session-search",
                evidence={f"tool.{_TOOL}": "present", "probe_count": n},
            )
        except Exception as exc:  # noqa: BLE001
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary=f"{_TOOL} probe failed: {type(exc).__name__}",
                evidence={"error": str(exc)[:300]},
            )
