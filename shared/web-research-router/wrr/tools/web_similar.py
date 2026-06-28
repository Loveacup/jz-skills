"""web_similar 工具 handler：Exa findSimilar，找与给定 URL 相似的页面。"""
from .. import config
from ..registry import get_registry
from ..router import route
from ..schemas import SimilarOptions
from ..errors import AllEnginesFailedError
from ..formatters import format_similar, format_error


async def handle_web_similar(args, **kwargs) -> str:
    url = args.get("url", "")
    if not url:
        return format_error("web_similar", "", ValueError("'url' is required"))
    count = min(
        int(args.get("max_results", config.DEFAULT_SEARCH_COUNT) or config.DEFAULT_SEARCH_COUNT),
        config.MAX_SEARCH_COUNT,
    )
    provider = args.get("provider")
    options = SimilarOptions(url=url, count=count, provider=provider)
    try:
        result = await route("similar", options, get_registry(), explicit_provider=provider)
        return format_similar(result, url)
    except AllEnginesFailedError as e:
        return format_error("web_similar", url, e)
