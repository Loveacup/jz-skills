"""SearXNG 引擎：search only。固化 engines=bing,baidu + language=zh-CN（M1）。

默认引擎(google/ddg/startpage)已失效，仅 bing/baidu 存活，且必须显式 language，
否则跨语言噪音（见 references/searxng-engine-diagnostics.md）。
"""
import httpx
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError, EngineTimeoutError
from ..schemas import SearchOptions, SearchResult, EngineCheckResult


class SearxngEngine(SearchEngine):
    name = "searxng"
    tier = 2  # 本地服务

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

    async def health_check(self, *, deep: bool = False) -> EngineCheckResult:
        """检查 SEARXNG_URL 是否配置并可达。"""
        base_url = config.get_env("SEARXNG_URL")

        if not base_url:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="SEARXNG_URL not configured",
                requirements=["env:SEARXNG_URL"],
                repair=[
                    "Set SEARXNG_URL in your shell or ~/.hermes/.env:",
                    "  export SEARXNG_URL=http://127.0.0.1:32080",
                    "If you run SearXNG via Docker, check: docker ps",
                    "Rerun: wrr-cli.py doctor --engine searxng",
                ],
                evidence={"env.SEARXNG_URL": "missing"},
            )

        # 探测 endpoint 可达性
        endpoint = base_url.rstrip("/") + "/"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(endpoint)
                status_code = resp.status_code
        except httpx.TimeoutException:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="SearXNG endpoint timeout",
                details=f"Endpoint {endpoint} did not respond within 2s",
                requirements=["env:SEARXNG_URL"],
                repair=[
                    "Check if SearXNG is running:",
                    "  curl -I " + endpoint,
                    "If you run SearXNG via Docker:",
                    "  docker ps | grep searxng",
                    "  docker logs <container_id>",
                ],
                evidence={"endpoint_reachable": False, "error": "timeout"},
            )
        except (httpx.ConnectError, httpx.NetworkError) as e:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="SearXNG endpoint unreachable",
                details=f"Cannot connect to {endpoint}",
                requirements=["env:SEARXNG_URL"],
                repair=[
                    "Check if SearXNG is running:",
                    "  curl -I " + endpoint,
                    "If you run SearXNG via Docker:",
                    "  docker ps | grep searxng",
                    "Verify SEARXNG_URL is correct: " + base_url,
                ],
                evidence={"endpoint_reachable": False, "error": type(e).__name__},
            )
        except Exception as e:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary="SearXNG endpoint check failed",
                details=str(e) or type(e).__name__,
                evidence={"endpoint_reachable": False, "error": type(e).__name__},
            )

        # 5xx 视为 fail，4xx 视为 warn（可达但可能配置问题），2xx/3xx 为 ok
        if status_code >= 500:
            return EngineCheckResult(
                engine=self.name,
                status="fail",
                tier=self.tier,
                summary=f"SearXNG returned {status_code}",
                details="Service may be down or misconfigured",
                repair=[
                    "Check SearXNG logs:",
                    "  docker logs <container_id>",
                ],
                evidence={"status_code": status_code},
            )
        elif status_code >= 400:
            return EngineCheckResult(
                engine=self.name,
                status="warn",
                tier=self.tier,
                summary=f"SearXNG reachable but returned {status_code}",
                details="Endpoint may need configuration adjustment",
                evidence={"status_code": status_code},
            )
        else:
            return EngineCheckResult(
                engine=self.name,
                status="ok",
                tier=self.tier,
                summary="SearXNG endpoint reachable",
                active_backend="searxng",
                evidence={"endpoint_checked": True, "status_code": status_code},
            )
