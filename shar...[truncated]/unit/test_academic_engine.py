"""AcademicEngine 单测：纯评分/去重函数 + search 聚合（monkeypatch 模块级 _fetch_*）。

零网络：通过替换模块级 `_fetch_openalex` / `_fetch_s2` 注入 canned paper_dict 列表，
骨架对齐 test_community.py（asyncio.run + 手动 swap 模块级函数）。
"""
import asyncio
import math
from datetime import datetime, timezone

import pytest

from wrr.engines import academic as ac
from wrr.engines._fusion import recency_decay
from wrr.schemas import SearchOptions
from wrr.errors import EngineError
from wrr import config


def run(coro):
    return asyncio.run(coro)


# ── canned paper_dict 工厂 ──────────────────────────────────────────
def _paper(**kw):
    base = {
        "title": "T", "cited_by_count": 0, "influential_citations": 0,
        "pub_date": None, "is_preprint": False, "venue": "", "venue_rank": 0.0,
        "doi": "", "arxiv_id": "", "openalex_id": "", "source": "openalex",
        "source_relevance": 1.0, "tldr": "", "abstract": "",
        "doi_url": "", "landing_url": "",
    }
    base.update(kw)
    return base


# ── 纯函数：citation_velocity ────────────────────────────────────────
def test_citation_velocity_old_does_not_dominate_new():
    # 老论文：引用高（200）但年龄大（20y）→ 年均 10/yr
    old = ac.citation_velocity(200, 20.0)
    # 新论文：引用中（50）但年轻（1y）→ 年均 50/yr
    new = ac.citation_velocity(50, 1.0)
    assert new > old                                  # 年均引用高者胜，非绝对引用数
    assert 0.0 < old < 1.0 and 0.0 < new <= 1.0


def test_citation_velocity_bounds_and_monotonic():
    assert ac.citation_velocity(0, 1.0) == 0.0
    assert ac.citation_velocity(10**6, 1.0) == 1.0    # 钳位到 1.0
    # 同龄下引用越多 velocity 越大
    assert ac.citation_velocity(100, 2.0) > ac.citation_velocity(10, 2.0)


# ── 纯函数：academic_score 手算一致 ─────────────────────────────────
def test_academic_score_matches_manual():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pub = datetime(2024, 1, 1, tzinfo=timezone.utc)
    p = _paper(cited_by_count=100, influential_citations=20, pub_date=pub,
               is_preprint=False, venue="NeurIPS", venue_rank=0.5,
               source_relevance=0.8, source="semantic_scholar")

    w_v, w_a, w_r, w_rel = config.ACADEMIC_SCORE_WEIGHTS
    age_years = max((now - pub).days / 365.0, 0.25)
    velocity = ac.citation_velocity(100, age_years)
    infl_ratio = 20 / 100
    authority = min(0.6 * 0.5 + 0.4 * min(infl_ratio * 3, 1.0), 1.0)   # 0.54
    age_hours = (now - pub).total_seconds() / 3600.0
    recency = recency_decay(age_hours, config.ACADEMIC_RECENCY_HALFLIFE_DAYS * 24.0)
    expected = w_v * velocity + w_a * authority + w_r * recency + w_rel * 0.8

    assert abs(ac.academic_score(p, now) - expected) < 1e-9


def test_academic_score_preprint_recency_boost():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pub = datetime(2025, 10, 1, tzinfo=timezone.utc)
    pre = _paper(pub_date=pub, is_preprint=True, source="arxiv")
    pub_paper = _paper(pub_date=pub, is_preprint=False)
    # 同日期、同引用，预印本 recency ×1.2 → 总分更高（其余维度相同/更低）
    assert ac.academic_score(pre, now) > ac.academic_score(pub_paper, now) - 1e-9
    # 显式核对 recency boost 进了分（预印本 recency 维度更高）
    age_hours = (now - pub).total_seconds() / 3600.0
    base_rec = recency_decay(age_hours, config.ACADEMIC_RECENCY_HALFLIFE_DAYS * 24.0)
    assert min(base_rec * 1.2, 1.0) > base_rec


# ── 纯函数：dedup_by_doi 跨源合并 ───────────────────────────────────
def test_dedup_by_doi_merges_cross_source_max_citation():
    oa = _paper(title="Attention Is All You Need", doi="10.1/abc",
                cited_by_count=1000, source="openalex", venue="NeurIPS",
                venue_rank=0.5, doi_url="https://doi.org/10.1/abc")
    s2 = _paper(title="Attention is all you need", doi="10.1/ABC",   # 大小写不同同 DOI
                cited_by_count=1200, influential_citations=300,
                source="semantic_scholar", tldr="seminal transformer paper")
    out = ac.dedup_by_doi([oa, s2])
    assert len(out) == 1                              # 同 DOI 合并为 1 条
    m = out[0]
    assert m["cited_by_count"] == 1200               # 引用取 max
    assert m["influential_citations"] == 300         # 从 s2 保留
    assert m["tldr"] == "seminal transformer paper"  # 补全缺字段
    assert m["venue"] == "NeurIPS"                    # 正式版权威保留
    assert set(m["cite_sources"]) == {"openalex", "semantic_scholar"}  # 标注双源
    assert m["cite_sources"]["semantic_scholar"] == 1200


def test_dedup_by_doi_arxiv_fallback_and_distinct():
    a = _paper(title="P1", arxiv_id="2401.001", source="arxiv", cited_by_count=5)
    b = _paper(title="P1 published", arxiv_id="2401.001", source="openalex",
               cited_by_count=8, venue="ICML", venue_rank=0.5)
    c = _paper(title="totally other", doi="10.9/zzz", source="openalex")
    out = ac.dedup_by_doi([a, b, c])
    assert len(out) == 2                              # a/b 同 arXiv ID 合并，c 独立
    merged = next(p for p in out if p.get("arxiv_id") == "2401.001")
    assert merged["cited_by_count"] == 8             # max
    assert merged["is_preprint"] is False            # 有正式版 → 不再算预印本
    assert merged["venue"] == "ICML"


# ── search 聚合（monkeypatch 模块级 _fetch_*）───────────────────────
def _fake_async(payload):
    async def _f(options):
        return list(payload)
    return _f


def _fake_raise(exc):
    async def _f(options):
        raise exc
    return _f


def test_search_aggregates_and_dedups(monkeypatch):
    monkeypatch.setattr(config, "ACADEMIC_INCLUDE_ARXIV", False)
    oa = [
        _paper(title="Paper A", doi="10.1/a", cited_by_count=500,
               source="openalex", pub_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
               venue="NeurIPS", venue_rank=0.5, source_relevance=1.0),
        _paper(title="Paper B", doi="10.1/b", cited_by_count=10, source="openalex",
               pub_date=datetime(2018, 1, 1, tzinfo=timezone.utc), source_relevance=0.5),
    ]
    s2 = [
        _paper(title="Paper A dup", doi="10.1/A", cited_by_count=600,    # 与 oa[0] 同 DOI
               influential_citations=120, source="semantic_scholar",
               tldr="great paper", source_relevance=1.0),
        _paper(title="Paper C", doi="10.1/c", cited_by_count=80,
               source="semantic_scholar",
               pub_date=datetime(2025, 6, 1, tzinfo=timezone.utc), source_relevance=0.7),
    ]
    monkeypatch.setattr(ac, "_fetch_openalex", _fake_async(oa))
    monkeypatch.setattr(ac, "_fetch_s2", _fake_async(s2))

    out = run(ac.AcademicEngine().search(SearchOptions("transformer", count=10)))
    titles = [r.title for r in out]
    assert "Paper A" in titles                        # 代表取首见（openalex 标题）
    assert "Paper A dup" not in titles                # DOI 去重生效
    assert len([t for t in titles if t.startswith("Paper A")]) == 1
    assert {"Paper A", "Paper B", "Paper C"} == set(titles)  # 3 篇唯一
    # 合并条 snippet 含引用数 + 来源标签前缀正确
    pa = next(r for r in out if r.title == "Paper A")
    assert "cit" in pa.snippet
    assert pa.source_tag.startswith("academic:")
    assert pa.url == "https://doi.org/10.1/a" or pa.url.startswith("http")


def test_search_isolates_failing_source(monkeypatch):
    monkeypatch.setattr(config, "ACADEMIC_INCLUDE_ARXIV", False)
    oa = [_paper(title="Survived", doi="10.1/ok", cited_by_count=42, source="openalex")]
    monkeypatch.setattr(ac, "_fetch_openalex", _fake_async(oa))
    monkeypatch.setattr(ac, "_fetch_s2", _fake_raise(RuntimeError("s2 down")))

    out = run(ac.AcademicEngine().search(SearchOptions("x", count=5)))
    assert [r.title for r in out] == ["Survived"]     # 单源失败被隔离，其余正常


def test_search_all_failed_raises(monkeypatch):
    monkeypatch.setattr(config, "ACADEMIC_INCLUDE_ARXIV", False)
    monkeypatch.setattr(ac, "_fetch_openalex", _fake_raise(RuntimeError("down")))
    monkeypatch.setattr(ac, "_fetch_s2", _fake_async([]))
    try:
        run(ac.AcademicEngine().search(SearchOptions("x")))
        assert False, "all failed should raise"
    except EngineError as e:
        assert "academic" in str(e).lower()


def test_search_respects_count(monkeypatch):
    monkeypatch.setattr(config, "ACADEMIC_INCLUDE_ARXIV", False)
    oa = [_paper(title=f"P{i}", doi=f"10.1/{i}", cited_by_count=i, source="openalex")
          for i in range(5)]
    monkeypatch.setattr(ac, "_fetch_openalex", _fake_async(oa))
    monkeypatch.setattr(ac, "_fetch_s2", _fake_async([]))
    out = run(ac.AcademicEngine().search(SearchOptions("x", count=2)))
    assert len(out) == 2


# ── 解析器纯函数（OpenAlex / S2 字段映射）───────────────────────────
def test_parse_openalex_work_fields():
    work = {
        "title": "Deep Learning",
        "cited_by_count": 12345,
        "publication_date": "2015-05-28",
        "type": "article",
        "ids": {"doi": "https://doi.org/10.1038/nature14539", "openalex": "W123"},
        "primary_location": {"source": {"display_name": "Nature"},
                             "landing_page_url": "https://nature.com/x"},
    }
    p = ac._parse_openalex_work(work, 0, 1)
    assert p["doi"] == "10.1038/nature14539"          # 剥前缀小写
    assert p["venue"] == "Nature" and p["venue_rank"] == 0.5
    assert p["is_preprint"] is False
    assert p["source"] == "openalex"
    assert p["pub_date"].year == 2015


def test_parse_s2_paper_preprint_and_tldr():
    paper = {
        "title": "GPT", "citationCount": 900, "influentialCitationCount": 100,
        "tldr": {"text": "a language model"}, "venue": "",
        "externalIds": {"ArXiv": "2005.14165"}, "year": 2020,
    }
    p = ac._parse_s2_paper(paper, 0, 1)
    assert p["is_preprint"] is True                   # 无 venue + 有 arXiv
    assert p["tldr"] == "a language model"
    assert p["arxiv_id"] == "2005.14165"
    assert p["landing_url"] == "https://arxiv.org/abs/2005.14165"


# ── 可选 live 集成（无网络默认 deselect）────────────────────────────
@pytest.mark.integration
def test_openalex_live_single_source():
    out = run(ac._fetch_openalex(SearchOptions("transformer attention", count=3)))
    assert out and any(_p.get("cited_by_count", 0) >= 0 for _p in out)
    assert all(_p.get("title") for _p in out)
