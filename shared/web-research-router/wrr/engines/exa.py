"""Exa 引擎（强化版）。

  search   → POST /search，contents 带 text + highlights（官方推荐）
  extract  → POST /contents，顶层 text + highlights
  similar  → POST /findSimilar

citation 源片段 = Exa highlights（真实可用能力）。不使用不存在的 output.grounding。
"""
import httpx
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import (SearchOptions, SearchResult, ExtractOptions,
                       ExtractResult, SimilarOptions, EngineCheckResult)

EXA_SEARCH_URL = "https://api.exa.ai/search"
EXA_CONTENTS_URL = "https://api.exa.ai/contents"
EXA_FINDSIMILAR_URL = "https://api.exa.ai/findSimilar"


# ── 查询分类 → 模式选择（质量优先）────────────────────────────────────
MODE_ROUTING = config.EXA_MODE_ROUTING


def classify_query(query: str) -> str:
    """基于查询特征自动分类，返回模式类型。"""
    q = query.lower()
    
    # 学术关键词
    if any(kw in q for kw in config.EXA_ACADEMIC_KEYWORDS):
        return "academic"
    
    # 研究关键词
    if any(kw in q for kw in config.EXA_RESEARCH_KEYWORDS):
        return "research"
    
    # 事实关键词
    if any(kw in q for kw in config.EXA_FACTUAL_KEYWORDS):
        return "factual"
    
    # 默认标准
    return "standard"


def get_search_mode(options: SearchOptions) -> str:
    """确定搜索模式。显式 mode 优先，否则自动路由。"""
    # 用户显式指定 mode
    if options.mode:
        return options.mode
    
    # 自动路由
    query_type = classify_query(options.query)
    return MODE_ROUTING.get(query_type, "auto")


def get_timeout_for_mode(mode: str) -> float:
    """根据模式返回超时时间。"""
    return config.EXA_MODE_TIMEOUT.get(mode, 5.0)


def _contents_block() -> dict:
    return {"text": {"maxCharacters": config.EXA_SEARCH_TEXT_MAX},
            "highlights": config.EXA_WITH_HIGHLIGHTS}


def _to_results(items: List[dict]) -> List[SearchResult]:
    out = []
    for r in items:
        out.append(SearchResult(
            title=r.get("title", "") or "",
            url=r.get("url", "") or "",
            snippet=(r.get("text", "") or "")[:config.EXA_SEARCH_TEXT_MAX],
            highlights=list(r.get("highlights", []) or []),
        ))
    return out


class ExaEngine(SearchEngine):
    name = "exa"
    tier = 1

    def _key(self) -> str:
        key = config.get_env("EXA_API_KEY")
        if not key:
            raise EngineError("EXA_API_KEY not set")
        return key

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        key = self._key()
        
        # 确定模式和超时
        mode = get_search_mode(options)
        timeout = get_timeout_for_mode(mode)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                EXA_SEARCH_URL,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json={"query": options.query, "numResults": options.count,
                      "type": mode, "contents": _contents_block()},
            )
            resp.raise_for_status()
            data = resp.json()
        return _to_results(data.get("results", []))

    async def extract(self, options: ExtractOptions) -> ExtractResult:
        key = self._key()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                EXA_CONTENTS_URL,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json={"urls": [options.url], "text": True,
                      "highlights": config.EXA_WITH_HIGHLIGHTS},
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        first = results[0] if results else {}
        return ExtractResult(
            url=options.url,
            text=(first.get("text", "") or "")[:options.max_characters],
            highlights=list(first.get("highlights", []) or []),
        )

    async def similar(self, options: SimilarOptions) -> List[SearchResult]:
        key = self._key()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                EXA_FINDSIMILAR_URL,
                headers={"x-api-key": key, "Content-Type": "application/json"},
                json={"url": options.url, "numResults": options.count,
                      "contents": _contents_block()},
            )
            resp.raise_for_status()
            data = resp.json()
        return _to_results(data.get("results", []))

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """检查 Exa API key 是否存在。"""
        key = config.get_env("EXA_API_KEY")
        if not key:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="EXA_API_KEY not configured",
                requirements=["env:EXA_API_KEY"],
                repair=[
                    "Set EXA_API_KEY in your shell or ~/.hermes/.env:",
                    "  export EXA_API_KEY=your_key_here",
                    "Rerun: wrr-cli.py doctor --engine exa",
                ],
                evidence={"env.EXA_API_KEY": "missing"},
            )
        return EngineCheckResult(
            engine=self.name,
            status="ok",
            tier=self.tier,
            summary="EXA_API_KEY configured",
            active_backend="exa-api",
            evidence={"env.EXA_API_KEY": "present"},
        )
