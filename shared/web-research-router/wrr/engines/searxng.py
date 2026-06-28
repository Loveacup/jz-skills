"""SearXNG 引擎：search only。固化 engines=bing,baidu + language=zh-CN（M1）。

默认引擎(google/ddg/startpage)已失效，仅 bing/baidu 存活，且必须显式 language，
否则跨语言噪音（见 references/searxng-engine-diagnostics.md）。
"""
import httpx
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError, EngineTimeoutError
from ..schemas import SearchOptions, SearchResult


class SearxngEngine(SearchEngine):
    name = "searxng"

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        base = config.get_env("SEARXNG_URL")
        if not base:
            raise EngineError("SEARXNG_URL not set")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{base.rstrip('/')}/search",
                    params={"q": options.query, "format": "json",
                            "engines": config.SEARXNG_ENGINES,
                            "language": config.SEARXNG_LANGUAGE},
                    headers={"Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
            results = data.get("results", [])
            if not results:
                raise EngineError("SearXNG returned empty results")
            return [SearchResult(title=r.get("title", "") or "",
                                 url=r.get("url", "") or "",
                                 snippet=r.get("content", "") or "")
                    for r in results[:options.count]]
        except EngineError:                       # M4: 自身错误不被通用 except 二次包裹
            raise
        except httpx.TimeoutException:
            raise EngineTimeoutError("SearXNG connection timeout")
        except httpx.ConnectError as e:
            raise EngineError(f"SearXNG connection failed: {str(e) or 'unknown error'}")
        except Exception as e:
            raise EngineError(f"SearXNG error: {str(e) or type(e).__name__}")
