"""local_supermemory 引擎（v5.2，Tier 1）：云端长期记忆。

数据源：Hermes 内置 supermemory_search(query, limit) tool。
适用查询：「我之前记过 / 记忆里 / 长期偏好 / 历史决策」。
只实现 search() + health_check()；不实现 extract/similar。

降级：Hermes tool 未注入（CLI/CI 环境）→ health_check fail、search 抛 EngineError，
由 router gather 隔离，local mode 仍可用 qmd/obsidian/web 兜底。
"""
from __future__ import annotations

import asyncio
from typing import Callable, List, Optional

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult
from ._local_utils import (resolve_hermes_tool, call_tool, call_tool_with_retry,
                           extract_rows, normalize_local_query,
                           LOCAL_FRESHNESS_DEFAULT)

_TOOL = "supermemory_search"


class LocalSupermemoryEngine(SearchEngine):
    name = "local_supermemory"
    tier = 1

    def __init__(self, tool: Optional[Callable] = None) -> None:
        # 测试注入 callable；运行时留空 → 从 Hermes resolver 解析。
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
        for i, item in enumerate(extract_rows(raw)[:limit]):
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or item.get("memory_title")
                     or f"Memory {i + 1}")
            text = (item.get("content") or item.get("text")
                    or item.get("snippet") or "")
            mem_id = item.get("id") or item.get("memory_id") or str(i + 1)
            results.append(SearchResult(
                title=str(title)[:120],
                url=f"memory://supermemory/{mem_id}",
                snippet=str(text)[:500],
                highlights=item.get("highlights") or [],
                source_tag="local:supermemory",
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
                repair=["Run inside Hermes runtime with Supermemory connected"],
                evidence={f"tool.{_TOOL}": "missing"},
            )
        if not deep:
            return EngineCheckResult(
                engine=self.name, status="ok", tier=self.tier,
                summary=f"{_TOOL} tool registered",
                active_backend="supermemory",
                evidence={f"tool.{_TOOL}": "present"},
            )
        try:
            sample = await asyncio.wait_for(
                call_tool(tool, query="WRR", limit=1), timeout=2.0)
            n = len(extract_rows(sample))
            return EngineCheckResult(
                engine=self.name, status="ok" if n > 0 else "warn", tier=self.tier,
                summary=f"{_TOOL} probe returned {n} result(s)",
                active_backend="supermemory",
                evidence={f"tool.{_TOOL}": "present", "probe_count": n},
            )
        except Exception as exc:  # noqa: BLE001 — 探测异常归一为 fail
            return EngineCheckResult(
                engine=self.name, status="fail", tier=self.tier,
                summary=f"{_TOOL} probe failed: {type(exc).__name__}",
                evidence={"error": str(exc)[:300]},
            )
