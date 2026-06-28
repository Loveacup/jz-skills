"""web_fetch 工具 handler：经 router 做 exa→brave 抽取 fallback。"""
from .. import config
from ..registry import get_registry
from ..router import route
from ..schemas import ExtractOptions
from ..errors import AllEnginesFailedError
from ..formatters import format_extract, format_error


async def handle_web_fetch(args, **kwargs) -> str:
    url = args.get("url", "")
    if not url:
        return format_error("web_fetch", "", ValueError("'url' is required"))
    max_chars = min(
        int(args.get("max_characters", config.DEFAULT_MAX_CHARACTERS) or config.DEFAULT_MAX_CHARACTERS),
        config.MAX_MAX_CHARACTERS,
    )
    provider = args.get("provider")
    options = ExtractOptions(url=url, max_characters=max_chars, provider=provider)
    try:
        result = await route("extract", options, get_registry(), explicit_provider=provider)
        return format_extract(result, url)
    except AllEnginesFailedError as e:
        return format_error("web_fetch", url, e)
