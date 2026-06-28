"""GitHubEngine 单测：评分函数（纯）+ search 映射/排序/错误 + 活跃度拉取（fake httpx）。"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

from conftest import FakeAsyncClient
from wrr.engines import github as gh
from wrr.schemas import SearchOptions
from wrr.errors import EngineError
from wrr.router import build_chain
from wrr import config


def run(coro):
    return asyncio.run(coro)


def _reset(data=None):
    FakeAsyncClient.captured = []
    FakeAsyncClient.response_data = data or {}
    FakeAsyncClient.response_text = ""


def _iso(days_ago, now):
    return (now - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── 纯评分函数 ───────────────────────────────────────────────────────
def test_score_formula_weights():
    assert config.GITHUB_SCORE_WEIGHTS == (0.40, 0.35, 0.25)
    assert abs(gh.score(1, 1, 1) - 1.0) < 1e-9
    assert abs(gh.score(1, 0, 0) - 0.40) < 1e-9   # activity 权重
    assert abs(gh.score(0, 1, 0) - 0.35) < 1e-9   # popularity 权重
    assert abs(gh.score(0, 0, 1) - 0.25) < 1e-9   # freshness 权重


def test_freshness_boundaries():
    now = datetime(2026, 6, 28, tzinfo=timezone.utc)
    assert gh.freshness(_iso(10, now), now) == 1.0
    assert gh.freshness(_iso(30, now), now) == 1.0
    assert abs(gh.freshness(_iso(90, now), now) - 0.5) < 1e-9
    assert gh.freshness(_iso(180, now), now) == 0.0
    assert gh.freshness(_iso(400, now), now) == 0.0
    assert gh.freshness(None, now) == 0.0
    assert gh.freshness("not-a-date", now) == 0.0
    # 60 天应在 1.0..0.5 之间线性 → 0.75
    assert abs(gh.freshness(_iso(60, now), now) - 0.75) < 1e-9


def test_popularity_monotonic_and_bounded():
    assert gh.popularity(0, 0) == 0.0
    assert 0.0 < gh.popularity(100, 0) < gh.popularity(100000, 0) <= 1.0
    # fork/star 比例加成
    assert gh.popularity(1000, 500) > gh.popularity(1000, 0)
    assert gh.popularity(10**7, 10**7) <= 1.0      # 封顶


def test_activity_real_vs_proxy():
    assert gh.activity(0) == 0.0
    assert gh.activity(None, 0) == 0.0
    assert 0.0 < gh.activity(100) <= 1.0
    assert gh.activity(10000) == 1.0               # log10(10001)/3 >1 → 钳位
    # 降级代理用 open_issues
    assert gh.activity(None, 100) > gh.activity(None, 0)


def test_parse_commit_count():
    class R:
        def __init__(self, headers, body):
            self.headers = headers
            self._b = body

        def json(self):
            return self._b

    link = '<https://api.github.com/repos/o/r/commits?since=x&per_page=1&page=137>; rel="last"'
    assert gh._parse_commit_count(R({"Link": link}, [{}])) == 137
    assert gh._parse_commit_count(R({}, [{}])) == 1      # 无 Link，1 条
    assert gh._parse_commit_count(R({}, [])) == 0        # 无 Link，0 条


def test_clean_query_strips_trigger():
    assert gh.GitHubEngine._clean_query("asyncio site:github.com") == "asyncio"
    assert gh.GitHubEngine._clean_query("SITE:GitHub.com foo") == "foo"
    assert gh.GitHubEngine._clean_query("plain query") == "plain query"


# ── search 映射 / 排序 / 错误（activity 关闭 → 确定性代理评分）──────────
def _two_repos(now):
    # A：高 star、高新鲜；B：低 star、陈旧 → A 应排前
    a = {"full_name": "org/hot", "html_url": "https://github.com/org/hot",
         "description": "hot repo", "stargazers_count": 100000, "forks_count": 5000,
         "open_issues_count": 10, "pushed_at": _iso(5, now)}
    b = {"full_name": "org/cold", "html_url": "https://github.com/org/cold",
         "description": "cold repo", "stargazers_count": 5, "forks_count": 0,
         "open_issues_count": 0, "pushed_at": _iso(400, now)}
    return a, b


def test_search_maps_ranks_and_cleans_query():
    now = datetime.now(timezone.utc)
    a, b = _two_repos(now)
    _reset({"items": [b, a]})                       # 故意乱序，验证重排
    gh.httpx.AsyncClient = FakeAsyncClient
    os.environ["GITHUB_TOKEN"] = "tkn"
    config.GITHUB_ACTIVITY_LOOKUP = False           # 确定性：用 open_issues 代理
    try:
        out = run(gh.GitHubEngine().search(
            SearchOptions("asyncio site:github.com", count=2)))
    finally:
        config.GITHUB_ACTIVITY_LOOKUP = True
    # 触发词被剥离
    assert FakeAsyncClient.captured[0]["params"]["q"] == "asyncio"
    assert FakeAsyncClient.captured[0]["params"]["per_page"] == 2
    # 综合评分重排：hot 在前
    assert out[0].title == "org/hot"
    assert out[1].title == "org/cold"
    assert out[0].url == "https://github.com/org/hot"
    assert "score=" in out[0].snippet and "★100000" in out[0].snippet


def test_search_missing_token_raises():
    os.environ.pop("GITHUB_TOKEN", None)
    gh.httpx.AsyncClient = FakeAsyncClient
    try:
        run(gh.GitHubEngine().search(SearchOptions("q")))
        assert False, "missing token should raise"
    except EngineError as e:
        assert "GITHUB_TOKEN" in str(e)
    os.environ["GITHUB_TOKEN"] = "tkn"


def test_search_empty_raises():
    _reset({"items": []})
    gh.httpx.AsyncClient = FakeAsyncClient
    os.environ["GITHUB_TOKEN"] = "tkn"
    config.GITHUB_ACTIVITY_LOOKUP = False
    try:
        run(gh.GitHubEngine().search(SearchOptions("q")))
        assert False, "empty should raise"
    except EngineError as e:
        assert "empty" in str(e).lower()
    finally:
        config.GITHUB_ACTIVITY_LOOKUP = True


# ── 活跃度并发拉取 + Link 解析 + 单仓失败降级 ─────────────────────────
def test_fetch_activity_concurrent_parse_and_degrade():
    class _Resp:
        def __init__(self, headers, body):
            self.headers = headers
            self._b = body

        def raise_for_status(self):
            return None

        def json(self):
            return self._b

    class _Client:
        async def get(self, url, params=None, headers=None):
            if "good" in url:
                link = '<...&page=42>; rel="last"'
                return _Resp({"Link": link}, [{}])
            raise RuntimeError("boom")              # bad 仓库 → 触发降级

    items = [{"full_name": "o/good"}, {"full_name": "o/bad"}, {"full_name": None}]
    eng = gh.GitHubEngine()
    counts = run(eng._fetch_activity(_Client(), {}, items))
    assert counts == [42, None, None]              # good=42；bad/无名→None（降级）


def test_fetch_activity_disabled_returns_none():
    config.GITHUB_ACTIVITY_LOOKUP = False
    try:
        counts = run(gh.GitHubEngine()._fetch_activity(None, {}, [{"full_name": "a/b"}]))
    finally:
        config.GITHUB_ACTIVITY_LOOKUP = True
    assert counts == [None]


# ── 自动触发 ─────────────────────────────────────────────────────────
def test_auto_trigger_promotes_github():
    assert config.github_triggered("foo site:github.com")
    assert config.github_triggered("SITE:GITHUB.COM")
    assert not config.github_triggered("plain")
    assert build_chain("search", None, "x site:github.com") == \
        ["github", "exa", "brave", "community", "searxng"]
    assert build_chain("search", None, "plain") == \
        ["exa", "brave", "github", "community", "searxng"]
