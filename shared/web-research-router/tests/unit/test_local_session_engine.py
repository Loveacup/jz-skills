"""local_session 引擎单测：tool 注入 / 映射 / 隐私截断 / health_check。"""
import asyncio

import pytest

from wrr.engines.local_session import LocalSessionEngine
from wrr.errors import EngineError
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _opts(q="刚才我们聊的 hermes", count=5):
    return SearchOptions(query=q, count=count)


def test_search_tool_missing_raises():
    with pytest.raises(EngineError):
        run(LocalSessionEngine(tool=None).search(_opts()))


def test_search_maps_session_rows():
    def fake(query, limit):
        return {"results": [
            {"session_id": "s1", "turn_id": 7, "timestamp": "2026-06-29",
             "text": "讨论了本地搜索层", "title": "WRR 设计"},
        ]}

    res = run(LocalSessionEngine(tool=fake).search(_opts()))
    assert len(res) == 1
    assert res[0].url == "session://s1#turn=7"
    assert res[0].source_tag == "local:session"
    assert res[0].title == "WRR 设计"
    assert "本地搜索层" in res[0].snippet


def test_search_fallback_ids_when_missing():
    """无 session_id/turn → unknown + 序号兜底。"""
    res = run(LocalSessionEngine(tool=lambda query, limit: [{"text": "hi"}]).search(_opts()))
    assert res[0].url == "session://unknown#turn=1"


def test_search_empty_returns_empty():
    assert run(LocalSessionEngine(tool=lambda query, limit: []).search(_opts())) == []


def test_search_snippet_truncated_for_privacy():
    """隐私：snippet 截断 500 字符，不返回完整对话。"""
    long_text = "x" * 2000
    fake = lambda query, limit: [{"session_id": "s", "turn_id": 1, "text": long_text}]
    res = run(LocalSessionEngine(tool=fake).search(_opts()))
    assert len(res[0].snippet) <= 500


def test_health_tool_missing_fail():
    r = run(LocalSessionEngine(tool=None).health_check())
    assert r.status == "fail"
    assert r.engine == "local_session"
    assert r.tier == 1
    assert r.evidence.get("tool.session_search") == "missing"


def test_health_tool_present_ok():
    r = run(LocalSessionEngine(tool=lambda **k: []).health_check())
    assert r.status == "ok"
    assert r.active_backend == "hermes-session-search"


def test_health_deep_ok_when_results():
    """deep=True 时执行 tool 调用，有结果 → ok。"""
    def fake(query, limit):
        return [{"session_id": "s", "turn_id": 1, "text": "test"}]
    r = run(LocalSessionEngine(tool=fake).health_check(deep=True))
    assert r.status == "ok"


def test_health_deep_warn_when_empty():
    """deep=True 无结果 → warn。"""
    r = run(LocalSessionEngine(tool=lambda **k: []).health_check(deep=True))
    assert r.status == "warn"


def test_health_deep_fail_when_tool_exception():
    """deep=True tool 抛异常 → fail。"""
    def bad(**k):
        raise RuntimeError("boom")
    r = run(LocalSessionEngine(tool=bad).health_check(deep=True))
    assert r.status == "fail"
    assert "RuntimeError" in r.summary
