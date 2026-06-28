"""BraveEngine / SearxngEngine 请求 payload 与映射单测（fake httpx）。"""
import asyncio
import os

from conftest import FakeAsyncClient
from wrr.engines import brave as brave_mod
from wrr.engines import searxng as searxng_mod
from wrr.schemas import SearchOptions, ExtractOptions
from wrr.errors import EngineError
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _reset(data=None, text=""):
    FakeAsyncClient.captured = []
    FakeAsyncClient.response_data = data or {}
    FakeAsyncClient.response_text = text


# ── Brave ────────────────────────────────────────────────────────────
def test_brave_search_params_encoded_and_mapped():
    _reset({"web": {"results": [{"title": "T", "url": "U", "description": "D"}]}})
    brave_mod.httpx.AsyncClient = FakeAsyncClient
    os.environ["BRAVE_API_KEY"] = "k"
    out = run(brave_mod.BraveEngine().search(SearchOptions("a b & c", count=7)))
    sent = FakeAsyncClient.captured[-1]
    assert sent["params"] == {"q": "a b & c", "count": 7}   # H3: 经 params 不裸插值
    assert out[0].snippet == "D"


def test_brave_key_fallback_name():
    _reset({"web": {"results": []}})
    brave_mod.httpx.AsyncClient = FakeAsyncClient
    os.environ.pop("BRAVE_API_KEY", None)
    os.environ["BRAVE_SEARCH_API_KEY"] = "legacy"
    # 不应抛 key 缺失（用后备名）
    run(brave_mod.BraveEngine().search(SearchOptions("q")))
    os.environ.pop("BRAVE_SEARCH_API_KEY", None)
    os.environ["BRAVE_API_KEY"] = "k"


def test_brave_extract_strips_html():
    _reset(text="<html><body><script>x=1</script><p>Hello <b>World</b></p></body></html>")
    brave_mod.httpx.AsyncClient = FakeAsyncClient
    out = run(brave_mod.BraveEngine().extract(ExtractOptions("https://x", max_characters=100)))
    assert "Hello World" in out.text
    assert "x=1" not in out.text         # script 被剥


# ── SearXNG ──────────────────────────────────────────────────────────
def test_searxng_pins_engines_and_language():
    _reset({"results": [{"title": "T", "url": "U", "content": "C"}]})
    searxng_mod.httpx.AsyncClient = FakeAsyncClient
    os.environ["SEARXNG_URL"] = "http://127.0.0.1:32080"
    out = run(searxng_mod.SearxngEngine().search(SearchOptions("中文 query", count=3)))
    sent = FakeAsyncClient.captured[-1]
    assert sent["params"]["engines"] == config.SEARXNG_ENGINES == "bing,baidu"   # M1
    assert sent["params"]["language"] == config.SEARXNG_LANGUAGE == "zh-CN"
    assert sent["params"]["format"] == "json"
    assert out[0].snippet == "C"


def test_searxng_empty_raises_engineerror_not_rewrapped():
    _reset({"results": []})
    searxng_mod.httpx.AsyncClient = FakeAsyncClient
    os.environ["SEARXNG_URL"] = "http://127.0.0.1:32080"
    try:
        run(searxng_mod.SearxngEngine().search(SearchOptions("q")))
        assert False, "empty should raise"
    except EngineError as e:
        assert "empty results" in str(e)          # M4: 未被二次包成 "SearXNG error:"


def test_searxng_missing_url_raises():
    searxng_mod.httpx.AsyncClient = FakeAsyncClient
    os.environ.pop("SEARXNG_URL", None)
    try:
        run(searxng_mod.SearxngEngine().search(SearchOptions("q")))
        assert False
    except EngineError as e:
        assert "SEARXNG_URL" in str(e)
    os.environ["SEARXNG_URL"] = "http://127.0.0.1:32080"
