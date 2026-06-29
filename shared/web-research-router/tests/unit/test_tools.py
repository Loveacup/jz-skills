"""tools handlers 单测：注入 fake 注册表，验证 JSON 契约与 fallback 入口。"""
import asyncio
import json

from conftest import FakeEngine, mk_results
from wrr.registry import EngineRegistry, get_registry, default_registry
from wrr.tools import web_search as ws_mod
from wrr.tools import web_fetch as wf_mod
from wrr.tools import web_similar as wsim_mod


def run(coro):
    return asyncio.run(coro)


def _inject(mod, *engines):
    reg = EngineRegistry()
    for e in engines:
        reg.register(e)
    mod.get_registry = lambda: reg   # 替换该 handler 模块绑定的 get_registry


# ── web_search ───────────────────────────────────────────────────────
def test_handle_web_search_success():
    _inject(ws_mod, FakeEngine("exa", search_results=mk_results(2)))
    out = json.loads(run(ws_mod.handle_web_search({"query": "q", "max_results": 5})))
    assert out["success"] is True
    assert out["details"]["result_count"] == 2


def test_handle_web_search_missing_query():
    out = json.loads(run(ws_mod.handle_web_search({})))
    assert "web_search failed" in out["error"]


def test_handle_web_search_all_fail():
    _inject(ws_mod,
            FakeEngine("exa", error="down"),
            FakeEngine("brave", error="down"),
            FakeEngine("searxng", error="down"))
    out = json.loads(run(ws_mod.handle_web_search({"query": "q"})))
    assert "web_search failed" in out["error"]


# ── web_fetch ────────────────────────────────────────────────────────
def test_handle_web_fetch_success():
    _inject(wf_mod, FakeEngine("exa", extract_text="hello body"))
    out = json.loads(run(wf_mod.handle_web_fetch({"url": "https://x"})))
    assert out["success"] is True
    assert out["details"]["actualProvider"] == "exa"


def test_handle_web_fetch_missing_url():
    out = json.loads(run(wf_mod.handle_web_fetch({})))
    assert "web_fetch failed" in out["error"]


# ── web_similar ──────────────────────────────────────────────────────
def test_handle_web_similar_success():
    _inject(wsim_mod, FakeEngine("exa", similar_results=mk_results(3)))
    out = json.loads(run(wsim_mod.handle_web_similar({"url": "https://x"})))
    assert out["details"]["result_count"] == 3


def test_handle_web_similar_missing_url():
    out = json.loads(run(wsim_mod.handle_web_similar({})))
    assert "web_similar failed" in out["error"]


# ── registry ─────────────────────────────────────────────────────────
def test_registry_singleton_and_names():
    r1 = get_registry()
    r2 = get_registry()
    assert r1 is r2                          # 单例
    assert set(default_registry().names()) == {"exa", "brave", "searxng", "github",
                                                "community", "academic", "skill",
                                                "local_supermemory", "local_session",
                                                "local_qmd", "local_obsidian"}  # v5.2：+4 本地引擎
