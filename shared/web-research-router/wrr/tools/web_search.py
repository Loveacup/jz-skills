"""web_search 工具 handler：v5 mode 路由（classify_intent → 并行引擎 → RRF 融合）。

显式 provider 仍走单引擎（v4 兼容）；显式 mode 覆盖自动分类。
"""
from .. import config
from ..registry import get_registry
from ..router import route_search_v5
from ..schemas import SearchOptions
from ..errors import AllEnginesFailedError
from ..formatters import format_search, format_error


async def handle_web_search(args, **kwargs) -> str:
    query = args.get("query", "")
    if not query:
        return format_error("web_search", "", ValueError("'query' is required"))
    count = min(
        int(args.get("max_results", config.DEFAULT_SEARCH_COUNT) or config.DEFAULT_SEARCH_COUNT),
        config.MAX_SEARCH_COUNT,
    )
    provider = args.get("provider")
    options = SearchOptions(query=query, count=count, provider=provider,
                            mode=args.get("mode"))
    try:
        result = await route_search_v5(options, get_registry())
        return format_search(result, query)
    except AllEnginesFailedError as e:
        return format_error("web_search", query, e)
