"""schemas dataclass 单测。"""
import asyncio  # noqa: F401  (保持 import 风格一致)

from conftest import mk_results
from wrr.schemas import (SearchOptions, SearchResult, ExtractOptions,
                         ExtractResult, SimilarOptions, FallbackStep, RouterResult)
from wrr import config


def test_search_options_defaults():
    o = SearchOptions(query="q")
    assert o.count == config.DEFAULT_SEARCH_COUNT
    assert o.provider is None


def test_search_result_to_dict():
    r = SearchResult(title="t", url="u", snippet="s", highlights=["h"])
    d = r.to_dict()
    assert d == {"title": "t", "url": "u", "snippet": "s", "highlights": ["h"], "source_tag": ""}


def test_extract_defaults():
    o = ExtractOptions(url="u")
    assert o.max_characters == config.DEFAULT_MAX_CHARACTERS
    assert ExtractResult(url="u", text="x").to_dict()["text"] == "x"


def test_similar_defaults():
    assert SimilarOptions(url="u").count == config.DEFAULT_SEARCH_COUNT


def test_fallback_step_to_dict():
    s = FallbackStep("exa", False, 0, "boom")
    assert s.to_dict() == {"provider": "exa", "ok": False, "count": 0, "error": "boom"}


def test_router_result_degraded_from():
    steps = [FallbackStep("exa", False, 0, "down"), FallbackStep("brave", True, 3)]
    rr = RouterResult(actual_provider="brave", payload=mk_results(3), fallback_chain=steps)
    assert rr.degraded_from == "exa"
    rr2 = RouterResult(actual_provider="exa", payload=[], fallback_chain=[FallbackStep("exa", True, 1)])
    assert rr2.degraded_from is None
