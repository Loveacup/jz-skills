"""local_obsidian 引擎单测：vault 扫描 / frontmatter / 限流 / 安全 / health_check。"""
import asyncio
import os

import pytest

from wrr.engines.local_obsidian import LocalObsidianEngine
from wrr.errors import EngineError
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _opts(q, count=5):
    return SearchOptions(query=q, count=count)


def _mk_vault(tmp_path, monkeypatch):
    monkeypatch.setenv("WRR_OBSIDIAN_VAULTS", str(tmp_path))
    return tmp_path


def _write(p, name, text):
    f = p / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    return f


# ── search ───────────────────────────────────────────────────────────
def test_search_no_vault_raises(monkeypatch):
    monkeypatch.delenv("WRR_OBSIDIAN_VAULTS", raising=False)
    with pytest.raises(EngineError):
        run(LocalObsidianEngine().search(_opts("anything")))


def test_search_finds_body_match(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "note.md", "# Title\n\n本笔记讨论 RRF 融合算法。\n")
    res = run(LocalObsidianEngine().search(_opts("RRF 融合")))
    assert len(res) == 1
    assert res[0].source_tag == "local:obsidian"
    assert res[0].url.startswith("file://")
    assert "RRF" in res[0].snippet or "融合" in res[0].snippet


def test_search_excludes_dot_dirs(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, ".obsidian/cache.md", "RRF 融合 secret cache")
    _write(tmp_path, ".git/x.md", "RRF 融合 git internal")
    _write(tmp_path, "real.md", "RRF 融合 真实笔记")
    res = run(LocalObsidianEngine().search(_opts("RRF 融合")))
    assert len(res) == 1
    assert "real.md" in res[0].url


def test_search_only_markdown(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "secret.env", "RRF 融合 API_KEY=xxxx")
    _write(tmp_path, "data.txt", "RRF 融合 plain text")
    _write(tmp_path, "ok.md", "RRF 融合 markdown")
    res = run(LocalObsidianEngine().search(_opts("RRF 融合")))
    assert len(res) == 1
    assert res[0].url.endswith("ok.md") or "ok.md" in res[0].url


def test_search_frontmatter_title_used(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "n.md", "---\ntitle: 自定义标题\n---\n\nRRF 融合内容\n")
    res = run(LocalObsidianEngine().search(_opts("RRF 融合")))
    assert res[0].title == "自定义标题"


def test_search_frontmatter_match_scores(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    # 文件名 + frontmatter 命中 → 排在纯正文命中之前
    _write(tmp_path, "RRF.md", "---\ntags:\n  - 融合\n---\n\nRRF 是融合方法\n")
    _write(tmp_path, "other.md", "顺便提了一句 融合\n")
    res = run(LocalObsidianEngine().search(_opts("融合")))
    assert res[0].url.endswith("RRF.md") or "RRF.md" in res[0].url


def test_search_snippet_is_matched_line(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "n.md", "无关行 1\n无关行 2\n这里有 RRF 融合\n后续\n")
    res = run(LocalObsidianEngine().search(_opts("RRF 融合")))
    assert "RRF 融合" in res[0].snippet
    assert "#L" in res[0].url                # 命中行号


def test_search_no_match_returns_empty(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "n.md", "完全无关的内容\n")
    assert run(LocalObsidianEngine().search(_opts("xyzzy 不存在"))) == []


def test_search_respects_max_files(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    for i in range(5):
        _write(tmp_path, f"n{i}.md", "RRF 融合\n")
    monkeypatch.setattr(config, "LOCAL_OBSIDIAN_MAX_FILES", 2)
    res = run(LocalObsidianEngine().search(_opts("RRF 融合", count=10)))
    assert len(res) <= 2                     # 扫描上限生效


# ── health_check ─────────────────────────────────────────────────────
def test_health_no_vault_fail(monkeypatch):
    monkeypatch.delenv("WRR_OBSIDIAN_VAULTS", raising=False)
    r = run(LocalObsidianEngine().health_check())
    assert r.status == "fail"
    assert r.engine == "local_obsidian"
    assert r.tier == 2


def test_health_vault_exists_ok(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    r = run(LocalObsidianEngine().health_check())
    assert r.status == "ok"
    assert r.active_backend == "filesystem"


def test_health_deep_counts_markdown(tmp_path, monkeypatch):
    _mk_vault(tmp_path, monkeypatch)
    _write(tmp_path, "a.md", "x")
    _write(tmp_path, "b.md", "y")
    r = run(LocalObsidianEngine().health_check(deep=True))
    assert r.status == "ok"
    assert r.evidence.get("sample_md_count") == 2
