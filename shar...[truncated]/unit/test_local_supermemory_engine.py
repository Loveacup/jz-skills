"""local_supermemory 引擎单测：tool 注入 / 映射 / 降级 / health_check。"""
import asyncio

import pytest

from wrr.engines.local_supermemory import LocalSupermemoryEngine
from wrr.errors import EngineError
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _opts(q="我之前的偏好", count=5):
    return SearchOptions(query=q, count=count)


# ── search：降级 ─────────────────────────────────────────────────────
def test_search_tool_missing_raises():
    """无 Hermes tool（CLI 环境）→ EngineError，由 router 隔离。"""
    eng = LocalSupermemoryEngine(tool=None)
    with pytest.raises(EngineError):
        run(eng.search(_opts()))


# ── search：结果映射 ─────────────────────────────────────────────────
def test_search_maps_sync_tool_results():
    def fake(query, limit):
        return {"results": [
            {"title": "WRR 决策", "content": "选了 RRF 融合", "id": "m1"},
            {"memory_title": "偏好", "text": "第一性原理", "id": "m2"},
        ]}

    eng = LocalSupermemoryEngine(tool=fake)
    res = run(eng.search(_opts()))
    assert len(res) == 2
    assert res[0].url == "memory://supermemory/m1"
    assert res[0].source_tag == "local:supermemory"
    assert res[0].title == "WRR 决策"
    assert res[1].title == "偏好"          # memory_title 兜底
    assert "第一性原理" in res[1].snippet


def test_search_supports_async_tool():
    async def fake(query, limit):
        return [{"title": "T", "content": "C", "id": "x"}]

    eng = LocalSupermemoryEngine(tool=fake)
    res = run(eng.search(_opts()))
    assert len(res) == 1 and res[0].url == "memory://supermemory/x"


def test_search_empty_returns_empty_list():
    eng = LocalSupermemoryEngine(tool=lambda query, limit: {"results": []})
    assert run(eng.search(_opts())) == []


def test_search_respects_count_cap():
    rows = [{"title": f"t{i}", "content": "c", "id": str(i)} for i in range(20)]
    eng = LocalSupermemoryEngine(tool=lambda query, limit: rows)
    res = run(eng.search(_opts(count=3)))
    assert len(res) == 3                    # min(count, LOCAL_MAX_RESULTS_PER_ENGINE)


def test_search_timeout_propagates(monkeypatch):
    monkeypatch.setitem(config.ENGINE_TIMEOUT, "local_supermemory", 0.01)

    async def slow(query, limit):
        await asyncio.sleep(1.0)
        return []

    eng = LocalSupermemoryEngine(tool=slow)
    with pytest.raises(asyncio.TimeoutError):
        run(eng.search(_opts()))


# ── health_check ─────────────────────────────────────────────────────
def test_health_tool_missing_fail():
    r = run(LocalSupermemoryEngine(tool=None).health_check())
    assert r.status == "fail"
    assert r.engine == "local_supermemory"
    assert r.tier == 1
    assert r.evidence.get("tool.supermemory_search") == "missing"


def test_health_tool_present_ok():
    r = run(LocalSupermemoryEngine(tool=lambda **k: []).health_check())
    assert r.status == "ok"
    assert r.active_backend == "supermemory"
    assert r.evidence.get("tool.supermemory_search") == "present"


def test_health_deep_probe_counts(monkeypatch):
    def fake(query, limit):
        return {"results": [{"title": "t", "content": "c", "id": "1"}]}

    r = run(LocalSupermemoryEngine(tool=fake).health_check(deep=True))
    assert r.status == "ok"
    assert r.evidence.get("probe_count") == 1


# ── call_tool_with_retry 测试（v5.2 P1）───────────────────────────────

async def fake_ok(**kwargs):
    return {"results": [{"title": "ok"}]}


async def fake_always_timeout(**kwargs):
    raise asyncio.TimeoutError()


async def fake_value_error(**kwargs):
    raise ValueError("not a timeout")


def _make_timeout_then_ok():
    """工厂：第一次超时，第二次成功"""
    counter = [0]
    async def inner(**kwargs):
        counter[0] += 1
        if counter[0] == 1:
            raise asyncio.TimeoutError()
        return {"results": [{"title": "retry ok"}]}
    return inner


def test_retry_succeeds_first():
    from wrr.engines._local_utils import call_tool_with_retry
    r = asyncio.run(call_tool_with_retry(fake_ok, timeout=1.0, retries=1))
    assert r["results"][0]["title"] == "ok"


def test_retry_succeeds_second():
    from wrr.engines._local_utils import call_tool_with_retry
    r = asyncio.run(call_tool_with_retry(_make_timeout_then_ok(), timeout=1.0, retries=1))
    assert r["results"][0]["title"] == "retry ok"


def test_retry_fails_all():
    from wrr.engines._local_utils import call_tool_with_retry
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(call_tool_with_retry(fake_always_timeout, timeout=0.1, retries=1))


def test_retry_no_retry_on_non_timeout():
    """非超时异常不重试，直接抛出"""
    from wrr.engines._local_utils import call_tool_with_retry
    with pytest.raises(ValueError, match="not a timeout"):
        asyncio.run(call_tool_with_retry(fake_value_error, timeout=1.0, retries=1))
