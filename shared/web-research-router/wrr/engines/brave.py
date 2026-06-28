"""Brave 引擎：search（GET，params 自动编码）+ extract（裸 HTTP 抓取 + 剥标签）。"""
import re
import httpx
from typing import List

from .base import SearchEngine
from .. import config
from ..errors import EngineError
from ..schemas import SearchOptions, SearchResult, ExtractOptions, ExtractResult

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveEngine(SearchEngine):
    name = "brave"

    def _key(self) -> str:
        # 主用 BRAVE_API_KEY；兼容 Hermes 内置 brave 的 BRAVE_SEARCH_API_KEY 后备。
        key = config.get_env("BRAVE_API_KEY") or config.get_env("BRAVE_SEARCH_API_KEY")
        if not key:
            raise EngineError("BRAVE_API_KEY not set")
        return key

    async def search(self, options: SearchOptions) -> List[SearchResult]:
        key = self._key()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                BRAVE_SEARCH_URL,
                params={"q": options.query, "count": options.count},   # H3: 自动编码
                headers={"Accept": "application/json", "X-Subscription-Token": key},
            )
            resp.raise_for_status()
            data = resp.json()
        return [SearchResult(title=r.get("title", "") or "",
                             url=r.get("url", "") or "",
                             snippet=r.get("description", "") or "")
                for r in data.get("web", {}).get("results", [])]

    async def extract(self, options: ExtractOptions) -> ExtractResult:
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            resp = await client.get(options.url, headers={"User-Agent": config.USER_AGENT})
            resp.raise_for_status()
            html = resp.text
        # 极简正文提取：剥 script/style → 剥标签 → 折叠空白。
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return ExtractResult(url=options.url, text=text[:options.max_characters])
