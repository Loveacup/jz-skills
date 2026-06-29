"""local_qmd 引擎单测：CLI 调用 / JSON+文本解析 / 降级 / health_check。"""
import asyncio
import json

import pytest
from unittest.mock import patch

from wrr.engines.local_qmd import LocalQmdEngine
from wrr.errors import EngineError
from wrr.schemas import SearchOptions


def run(coro):
    return asyncio.run(coro)


def _opts(q="wrr 路由", count=5):
    return SearchOptions(query=q, count=count)


def _mock_run(rc=0, stdout="", stderr=""):
    async def _r(args, timeout):
        return rc, stdout, stderr
    return _r


# ── search ───────────────────────────────────────────────────────────
def test_search_binary_missing_raises():
    with patch("shutil.which", return_value=None):
        with pytest.raises(EngineError):
            run(LocalQmdEngine().search(_opts()))


def test_search_parses_json():
    payload = json.dumps([
        {"file": "qmd://vault/a.md", "line": 12, "title": "Doc A",
         "snippet": "命中片段", "score": 0.7},
        {"file": "qmd://vault/b.md", "line": 3, "title": "Doc B",
         "context": "上下文", "score": 0.6},
    ])
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _mock_run(0, payload)):
            res = run(LocalQmdEngine().search(_opts()))
    assert len(res) == 2
    assert res[0].url == "qmd://vault/a.md#L12"
    assert res[0].source_tag == "local:qmd"
    assert res[0].title == "Doc A"
    assert res[1].snippet == "上下文"        # context 兜底 snippet


def test_search_nonzero_exit_raises():
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _mock_run(1, "", "boom")):
            with pytest.raises(EngineError):
                run(LocalQmdEngine().search(_opts()))


def test_search_text_fallback():
    """JSON 解析失败 → 纯文本兜底解析。"""
    text = ("qmd://vault/c.md:42 #abc123\n"
            "Title: Doc C\n"
            "Score: 80%\n")
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _mock_run(0, text)):
            res = run(LocalQmdEngine().search(_opts()))
    assert len(res) == 1
    assert res[0].url == "qmd://vault/c.md#L42"
    assert res[0].title == "Doc C"
    assert res[0].source_tag == "local:qmd"


def test_search_timeout_raises():
    async def _slow(args, timeout):
        raise asyncio.TimeoutError()
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _slow):
            with pytest.raises(EngineError):
                run(LocalQmdEngine().search(_opts()))


# ── health_check ─────────────────────────────────────────────────────
def test_health_binary_missing_fail():
    with patch("shutil.which", return_value=None):
        r = run(LocalQmdEngine().health_check())
    assert r.status == "fail"
    assert r.engine == "local_qmd"
    assert r.tier == 2
    assert r.evidence.get("qmd.path") == "missing"


def test_health_binary_present_shallow_ok():
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        r = run(LocalQmdEngine().health_check())
    assert r.status == "ok"
    assert r.active_backend == "qmd-cli"
    assert r.evidence.get("qmd.path") == "/usr/bin/qmd"


def test_health_deep_stale_index_warn():
    status = ("QMD Status\nDocuments\n  Total: 1000 files indexed\n"
              "  Pending:  5 need embedding (run 'qmd embed')\n")
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _mock_run(0, status)):
            r = run(LocalQmdEngine().health_check(deep=True))
    assert r.status == "warn"
    assert r.evidence.get("pending_embedding") == 5
    assert "stale" in r.summary.lower()


def test_health_deep_clean_index_ok():
    status = "QMD Status\n  Pending:  0 need embedding\n"
    with patch("shutil.which", return_value="/usr/bin/qmd"):
        with patch("wrr.engines.local_qmd.run_command", _mock_run(0, status)):
            r = run(LocalQmdEngine().health_check(deep=True))
    assert r.status == "ok"
    assert r.evidence.get("pending_embedding") == 0
