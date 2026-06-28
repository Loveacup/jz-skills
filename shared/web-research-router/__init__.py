"""WRR Hermes Plugin v4.0 — 统一 web 搜索与内容抽取。

入口极薄：只做 Hermes tool 注册，全部逻辑委托 wrr 包。
"""
from wrr.tools.web_search import handle_web_search
from wrr.tools.web_fetch import handle_web_fetch
from wrr.tools.web_similar import handle_web_similar

WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "max_results": {"type": "integer", "default": 10},
        "provider": {"type": "string", "enum": ["exa", "brave", "searxng"]},
        "mode": {"type": "string", "enum": ["fast", "auto", "deep-lite", "deep"]},
    },
    "required": ["query"],
}

WEB_FETCH_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "max_characters": {"type": "integer", "default": 5000},
        "provider": {"type": "string", "enum": ["exa", "brave"]},
    },
    "required": ["url"],
}

WEB_SIMILAR_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "max_results": {"type": "integer", "default": 10},
    },
    "required": ["url"],
}


def register(ctx):
    """注册 WRR 工具，覆盖 Hermes 内置 web_search/web_fetch。"""
    ctx.register_tool(
        "web_search",
        WEB_SEARCH_SCHEMA,
        handle_web_search,
        override=True,
    )
    ctx.register_tool(
        "web_fetch",
        WEB_FETCH_SCHEMA,
        handle_web_fetch,
        override=True,
    )
    ctx.register_tool(
        "web_similar",
        WEB_SIMILAR_SCHEMA,
        handle_web_similar,
        override=True,
    )
