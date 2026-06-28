"""CommunityEngine v5 升级单测：跨子源 RRF 聚合 + canonical_url 去重（加法式）。

不动既有 search()/deduplicate（v4 行为由 test_community.py 锁定）。
"""
import asyncio
import json
import time

from wrr.engines import community as cm
from wrr.schemas import SearchOptions
from wrr import config
from wrr.engines import _fusion


def run(coro):
    return asyncio.run(coro)


_REDDIT = [
    {"title": "Reddit A", "url": "https://reddit.com/r/p/1/a",
     "score": 500, "comments": 100, "created_utc": int(time.time()) - 7200,
     "selftext": "body"},
    {"title": "Reddit B", "url": "https://reddit.com/r/p/2/b",
     "score": 3, "comments": 0, "created_utc": int(time.time()) - 100 * 86400,
     "selftext": ""},
]
_TWITTER = [
    {"text": "tweet python", "url": "https://x.com/u/1",
     "likes": 1000, "replies": 50, "created_at": int(time.time()) - 3600},
]


def _fake_run_factory(mapping, fail=()):
    async def fake_run(cli, timeout):
        joined = " ".join(cli).lower()
        for key, payload in mapping.items():
            if key in joined:
                if key in fail:
                    return (None, "")
                return (0, json.dumps(payload))
        return (0, "[]")
    return fake_run


def test_search_rrf_aggregates_multi_source():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory(
        {"reddit": _REDDIT, "twitter": _TWITTER, "xiaohongshu": [], "v2ex": []},
        fail=("v2ex",))
    try:
        out = run(cm.CommunityEngine().search_rrf(SearchOptions("python", count=10)))
    finally:
        cm._run_cmd = orig
    titles = [r.title for r in out]
    assert "Reddit A" in titles and "tweet python" in titles
    # 源内高分（Reddit A）应排在源内低分（Reddit B）之前
    assert titles.index("Reddit A") < titles.index("Reddit B")
    assert all(r.url for r in out)


def test_search_rrf_respects_count():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": _REDDIT, "twitter": _TWITTER,
                                     "xiaohongshu": [], "v2ex": []})
    try:
        out = run(cm.CommunityEngine().search_rrf(SearchOptions("python", count=1)))
    finally:
        cm._run_cmd = orig
    assert len(out) == 1


def test_search_rrf_all_empty_raises():
    orig = cm._run_cmd
    cm._run_cmd = _fake_run_factory({"reddit": [], "twitter": [],
                                     "xiaohongshu": [], "v2ex": []})
    try:
        run(cm.CommunityEngine().search_rrf(SearchOptions("python")))
        assert False, "all empty should raise"
    except Exception as e:
        assert "community" in str(e).lower()
    finally:
        cm._run_cmd = orig


def test_canonical_dedup_cross_platform_same_link():
    # HN 与 Reddit 指向同一外链（utm 不同）→ canonical 去重合并
    from wrr.schemas import SearchResult
    docs = [
        SearchResult("HN: cool post", "https://example.com/x?utm_source=hn", "", source_tag="hackernews"),
        SearchResult("Reddit: cool post", "https://example.com/x/", "", source_tag="reddit"),
    ]
    out = _fusion.dedup_cluster(docs)
    assert len(out) == 1                          # 同一外链跨平台合并
