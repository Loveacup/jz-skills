"""router fallback 控制流单测（对齐执行包 Step4 验收）。"""
import asyncio

from conftest import FakeEngine, mk_results
from wrr.registry import EngineRegistry
from wrr.router import route, build_chain
from wrr.schemas import SearchOptions, ExtractOptions, SimilarOptions
from wrr.errors import AllEnginesFailedError


def _reg(*engines):
    r = EngineRegistry()
    for e in engines:
        r.register(e)
    return r


def run(coro):
    return asyncio.run(coro)


# ── build_chain ──────────────────────────────────────────────────────
def test_build_chain_default_and_explicit():
    assert build_chain("search", None) == ["exa", "brave", "github", "community", "searxng"]
    assert build_chain("extract", None) == ["exa", "brave"]
    assert build_chain("similar", None) == ["exa"]
    assert build_chain("search", "brave") == ["brave"]   # 显式 → 单元素


# ── search fallback ──────────────────────────────────────────────────
def test_search_normal_no_degrade():
    reg = _reg(FakeEngine("exa", search_results=mk_results(2)),
               FakeEngine("brave", error="should not call"),
               FakeEngine("searxng", error="should not call"))
    rr = run(route("search", SearchOptions("q"), reg))
    assert rr.actual_provider == "exa"
    assert len(rr.payload) == 2


def test_search_exception_falls_to_brave():
    reg = _reg(FakeEngine("exa", error="exa down"),
               FakeEngine("brave", search_results=mk_results(1)),
               FakeEngine("searxng", search_results=mk_results(1)))
    rr = run(route("search", SearchOptions("q"), reg))
    assert rr.actual_provider == "brave"
    assert rr.degraded_from == "exa"


def test_search_empty_falls_through():
    reg = _reg(FakeEngine("exa", search_results=[]),
               FakeEngine("brave", search_results=[]),
               FakeEngine("searxng", search_results=mk_results(1)))
    rr = run(route("search", SearchOptions("q"), reg))
    assert rr.actual_provider == "searxng"


def test_search_all_fail_raises():
    reg = _reg(FakeEngine("exa", error="down"),
               FakeEngine("brave", error="down"),
               FakeEngine("searxng", error="down"))
    try:
        run(route("search", SearchOptions("q"), reg))
        assert False, "should raise"
    except AllEnginesFailedError:
        pass


def test_explicit_provider_disables_fallback():
    reg = _reg(FakeEngine("exa", search_results=mk_results(1)),
               FakeEngine("brave", error="brave down"),
               FakeEngine("searxng", search_results=mk_results(1)))
    try:
        run(route("search", SearchOptions("q", provider="brave"), reg, explicit_provider="brave"))
        assert False, "explicit brave failure must not fall back"
    except AllEnginesFailedError:
        pass


# ── extract fallback ─────────────────────────────────────────────────
def test_extract_empty_text_falls_back():
    reg = _reg(FakeEngine("exa", extract_text=""),
               FakeEngine("brave", extract_text="hello"))
    rr = run(route("extract", ExtractOptions("https://x"), reg))
    assert rr.actual_provider == "brave"
    assert rr.payload.text == "hello"


# ── similar ──────────────────────────────────────────────────────────
def test_similar_single_provider():
    reg = _reg(FakeEngine("exa", similar_results=mk_results(3)))
    rr = run(route("similar", SimilarOptions("https://x"), reg))
    assert rr.actual_provider == "exa"
    assert len(rr.payload) == 3


def test_unknown_provider_in_chain_fails_gracefully():
    reg = _reg(FakeEngine("exa", error="down"))   # brave/searxng 未注册
    try:
        run(route("search", SearchOptions("q"), reg))
        assert False
    except AllEnginesFailedError as e:
        assert "unknown provider" in str(e)
