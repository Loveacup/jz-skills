"""CommunityEngine 单测：评分/去重/源选择（纯）+ search 聚合（mock 子进程）。

通过 monkeypatch 模块级 `_run_cmd` 注入各源的 canned 输出，零真实子进程/网络。
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone

from wrr.engines import community as cm
from wrr.schemas import SearchOptions
from wrr.errors import EngineError
from wrr.router import build_chain
from wrr import config


def run(coro):
    return asyncio.run(coro)


# ── 纯评分函数 ───────────────────────────────────────────────────────
def test_score_weights():
    assert config.COMMUNITY_SCORE_WEIGHTS == (0.40, 0.35, 0.25)


def test_engagement_log_compression():
    assert cm._engagement_score(0) == 0.0
    assert 0.0 < cm._engagement_score(100, 1000) < 1.0
    assert cm._engagement_score(1000, 1000) == 1.0          # 命中上限
    assert cm._engagement_score(10**9, 1000) == 1.0         # 钳位


def test_recency_steps():
    now = datetime(2026, 6, 28, tzinfo=timezone.utc)
    mk = lambda h: now - timedelta(hours=h)
    assert cm._recency_score(mk(1), now) == 1.0
    assert cm._recency_score(mk(24), now) == 1.0
    assert cm._recency_score(mk(100), now) == 0.7           # ≤7d
    assert cm._recency_score(mk(500), now) == 0.3           # ≤30d
    assert cm._recency_score(mk(2000), now) == 0.0          # 更旧
    assert cm._recency_score(None, now) == 0.5              # 未知→中等


def test_quality_ratio():
    assert cm._quality_score(0, 100) == 0.0
    assert cm._quality_score(10, 0) == 0.0                  # 无互动→0
    assert cm._quality_score(20, 100) == 1.0               # 20% → 1.0
    assert cm._quality_score(2, 100) == 0.1


def test_parse_time_epoch_and_iso():
    assert cm._parse_time(1778165271).year >= 2026          # epoch 秒
    assert cm._parse_time(1778165271000).year >= 2026       # epoch 毫秒
    assert cm._parse_time("2026-06-01T00:00:00Z") is not None
    assert cm._parse_time("garbage") is None
    assert cm._parse_time(None) is None


def test_calculate_score_formula():
    cfg = cm.COMMUNITY_SOURCES["reddit"]
    now = datetime.now(timezone.utc)
    recent = int(now.timestamp()) - 3600
    item = {"score": 1000, "comments": 200, "created_utc": recent}
    # eng=log10(1001)/log10(10001)=0.75; rec=1.0; qual=min(1,200/1000*5)=1.0
    expected = 0.40 * cm._engagement_score(1000, 10000) + 0.35 * 1.0 + 0.25 * 1.0
    assert abs(cm.calculate_score(item, cfg, now) - expected) < 1e-9


# ── 去重 ─────────────────────────────────────────────────────────────
def test_dedup_url_and_title():
    from wrr.schemas import SearchResult
    rs = [
        SearchResult("Python is great", "https://a.com/x?utm=1", "", source_tag="reddit"),
        SearchResult("totally different", "https://a.com/x", "", source_tag="twitter"),  # URL 规范化后同
        SearchResult("Python is great!!", "https://b.com/y", "", source_tag="hn"),       # 标题高度相似
        SearchResult("unique topic here", "https://c.com/z", "", source_tag="v2ex"),
    ]
    out = cm.deduplicate(rs)
    urls = [r.url for r in out]
    assert "https://a.com/x?utm=1" in urls
    assert "https://a.com/x" not in urls          # URL 规范化去重
    assert "https://b.com/y" not in urls          # 标题相似去重
    assert "https://c.com/z" in urls


# ── 源选择 ───────────────────────────────────────────────────────────
def test_detect_sources_default_and_triggers():
    eng = cm.CommunityEngine()
    assert eng._detect_sources("python") == list(config.COMMUNITY_DEFAULT_SOURCES)
    assert eng._detect_sources("x site:reddit.com") == ["reddit"]
    assert eng._detect_sources("y site:x.com") == ["twitter"]
    assert eng._detect_sources("z site:news.ycombinator.com") == ["last30days_en"]
    assert eng._detect_sources("w site:zhihu.com") == ["last30days_cn"]
    assert "xiaohongshu" in eng._detect_sources("小红书 美食")


def test_detect_sources_last30days_gated():
    eng = cm.CommunityEngine()
    # 研究意图关键词 → 追加 last30days
    s = eng._detect_sources("trending ai")
    assert "last30days_en" in s and "last30days_cn" in s
    # 显式开关
    config.COMMUNITY_INCLUDE_LAST30DAYS = True
    try:
        s2 = eng._detect_sources("python")
        assert "last30days_en" in s2
    finally:
        config.COMMUNITY_INCLUDE_LAST30DAYS = False


def test_community_triggered():
    assert config.community_triggered("foo site:reddit.com")
    assert config.community_triggered("X SITE:X.COM")
    assert not config.community_triggered("plain query")


# ── search 聚合（mock 子进程）────────────────────────────────────────
def _recent_epoch(h=1):
    return int(time.time()) - h * 3600


_REDDIT = [
    {"title": "Reddit A", "url": "https://reddit.com/r/p/comments/1/a",
     "score": 500, "comments": 100, "created_utc": _recent_epoch(2), "selftext": "body a"},
    {"title": "Reddit B", "url": "https://reddit.com/r/p/comments/2/b",
     "score": 3, "comments": 0, "created_utc": int(time.time()) - 100 * 86400, "selftext": ""},
]
_TWITTER = [
    {"text": "tweet about python", "url": "https://x.com/u/1",
     "likes": 1000, "replies": 50, "created_at": _recent_epoch(1)},
]
_L30 = {"clusters": [
    {"title": "cluster py", "score": 42.0, "sources": ["x", "reddit"],
     "representative_ids": ["https://di.gg/ai/m1"]},
]}


def _fake_run_factory(mapping, fail=()):
    async def fake_run(cli, timeout):
        joined = " ".join(cli).lower()
        for key, payload in mapping.items():
            if key in joined:
                if key in fail:
                    return (None, "")           # 模拟该源失败
                return (0, json.dumps(payload))
        return (0, "[]")
    return fake_run


def test_search_aggregates_scores_and_dedups(monkeypatch=None):
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory(
        {"reddit": _REDDIT, "twitter": _TWITTER, "xiaohongshu": [], "v2ex": []},
        fail=("v2ex",))
    try:
        out = run(cm.CommunityEngine().search(SearchOptions("python", count=10)))
    finally:
        cm._run_cmd = orig
    titles = [r.title for r in out]
    assert set(titles) == {"Reddit A", "tweet about python", "Reddit B"}
    assert titles.index("Reddit A") < titles.index("Reddit B")     # 高分在前
    tags = {r.source_tag for r in out}
    assert tags == {"reddit", "twitter"}                            # v2ex 失败被跳过
    assert all(r.url for r in out)


def test_search_respects_count():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": _REDDIT, "twitter": _TWITTER,
                                     "xiaohongshu": [], "v2ex": []})
    try:
        out = run(cm.CommunityEngine().search(SearchOptions("python", count=1)))
    finally:
        cm._run_cmd = orig
    assert len(out) == 1


def test_search_all_empty_raises():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": [], "twitter": [],
                                     "xiaohongshu": [], "v2ex": []})
    try:
        run(cm.CommunityEngine().search(SearchOptions("python")))
        assert False, "all empty should raise"
    except EngineError as e:
        assert "community" in str(e).lower()
    finally:
        cm._run_cmd = orig


def test_search_last30days_clusters_mapped():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"last30days": _L30})
    config.COMMUNITY_INCLUDE_LAST30DAYS = True
    try:
        # site:news.ycombinator.com → 仅 last30days_en
        out = run(cm.CommunityEngine().search(
            SearchOptions("ai site:news.ycombinator.com", count=5)))
    finally:
        cm._run_cmd = orig
        config.COMMUNITY_INCLUDE_LAST30DAYS = False
    assert len(out) == 1
    assert out[0].title == "cluster py"
    assert out[0].url == "https://di.gg/ai/m1"
    assert out[0].source_tag == "last30days_en"


def test_item_to_result_drops_incomplete():
    eng = cm.CommunityEngine()
    cfg = cm.COMMUNITY_SOURCES["reddit"]
    now = datetime.now(timezone.utc)
    assert eng._item_to_result({"title": "", "url": "https://x"}, "reddit", cfg, now) is None
    assert eng._item_to_result({"title": "t", "url": ""}, "reddit", cfg, now) is None
    ok = eng._item_to_result({"title": "t", "url": "https://x", "score": 10,
                              "comments": 1, "created_utc": _recent_epoch()}, "reddit", cfg, now)
    assert ok is not None and ok[1].source_tag == "reddit"


# ── 自动触发链 ───────────────────────────────────────────────────────
def test_build_chain_promotes_community():
    assert build_chain("search", None, "x site:reddit.com") == \
        ["community", "exa", "brave", "github", "searxng"]
    assert build_chain("search", None, "plain") == \
        ["exa", "brave", "github", "community", "searxng"]
