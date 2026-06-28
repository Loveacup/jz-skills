"""单测公共桩件：fake 引擎 + fake httpx 客户端。无真实网络。"""
import sys
from pathlib import Path

# 让 `import wrr` 生效（plugin 根目录入 sys.path）
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wrr.engines.base import SearchEngine  # noqa: E402
from wrr.errors import EngineError  # noqa: E402
from wrr.schemas import SearchResult, ExtractResult  # noqa: E402


class FakeEngine(SearchEngine):
    """可编排的 fake 引擎：按构造参数决定 search/extract/similar 行为。"""

    def __init__(self, name, *, search_results=None, extract_text=None,
                 similar_results=None, error=None, timeout=5.0):
        self.name = name
        self._search = search_results
        self._extract = extract_text
        self._similar = similar_results
        self._error = error
        self._timeout = timeout

    @property
    def timeout(self):
        return self._timeout

    async def search(self, options):
        if self._error:
            raise EngineError(self._error)
        return self._search if self._search is not None else []

    async def extract(self, options):
        if self._error:
            raise EngineError(self._error)
        return ExtractResult(url=options.url, text=self._extract or "")

    async def similar(self, options):
        if self._error:
            raise EngineError(self._error)
        return self._similar if self._similar is not None else []


def mk_results(n=1):
    return [SearchResult(title=f"t{i}", url=f"https://u{i}", snippet=f"s{i}",
                         highlights=[f"h{i}"]) for i in range(n)]


class FakeResponse:
    def __init__(self, data, text=""):
        self._data = data
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


class FakeAsyncClient:
    """捕获请求并返回固定响应的 httpx.AsyncClient 替身。"""
    captured = []
    response_data = {}
    response_text = ""

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        FakeAsyncClient.captured.append({"method": "POST", "url": url, "json": json})
        return FakeResponse(FakeAsyncClient.response_data, FakeAsyncClient.response_text)

    async def get(self, url, params=None, headers=None):
        FakeAsyncClient.captured.append({"method": "GET", "url": url, "params": params})
        return FakeResponse(FakeAsyncClient.response_data, FakeAsyncClient.response_text)
