"""ExaEngine 请求 payload 与响应映射单测（fake httpx，无网络）。"""
import asyncio

import conftest
from conftest import FakeAsyncClient
from wrr.engines import exa as exa_mod
from wrr.schemas import SearchOptions, ExtractOptions, SimilarOptions
from wrr import config


def _patch(monkey_response, env):
    FakeAsyncClient.captured = []
    FakeAsyncClient.response_data = monkey_response
    exa_mod.httpx.AsyncClient = FakeAsyncClient   # 替换该模块引用的 httpx 客户端
    import os
    os.environ["EXA_API_KEY"] = env


def run(coro):
    return asyncio.run(coro)


def test_exa_search_payload_and_highlights():
    _patch({"results": [{"title": "T", "url": "U", "text": "body",
                         "highlights": ["HL1", "HL2"]}]}, "k")
    eng = exa_mod.ExaEngine()
    out = run(eng.search(SearchOptions("hello world", count=5)))
    sent = FakeAsyncClient.captured[-1]
    assert sent["url"] == exa_mod.EXA_SEARCH_URL
    assert sent["json"]["query"] == "hello world"
    assert sent["json"]["numResults"] == 5
    assert sent["json"]["contents"]["highlights"] is True
    assert sent["json"]["type"] == config.EXA_SEARCH_TYPE
    assert out[0].highlights == ["HL1", "HL2"]      # citation 源片段映射


def test_exa_extract_uses_contents_endpoint():
    _patch({"results": [{"url": "U", "text": "long text", "highlights": ["h"]}]}, "k")
    eng = exa_mod.ExaEngine()
    out = run(eng.extract(ExtractOptions("https://x", max_characters=4)))
    sent = FakeAsyncClient.captured[-1]
    assert sent["url"] == exa_mod.EXA_CONTENTS_URL
    assert sent["json"]["urls"] == ["https://x"]
    assert out.text == "long"                       # max_characters 截断
    assert out.highlights == ["h"]


def test_exa_similar_uses_findsimilar_endpoint():
    _patch({"results": [{"title": "T", "url": "U", "text": "t", "highlights": []}]}, "k")
    eng = exa_mod.ExaEngine()
    out = run(eng.similar(SimilarOptions("https://x", count=3)))
    sent = FakeAsyncClient.captured[-1]
    assert sent["url"] == exa_mod.EXA_FINDSIMILAR_URL
    assert sent["json"]["url"] == "https://x"
    assert sent["json"]["numResults"] == 3
    assert len(out) == 1
