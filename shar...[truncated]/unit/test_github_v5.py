"""GitHubEngine v5 升级单测：maintenance 维 / score_v5 / issue_search / GraphQL 批量活跃度。"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

from conftest import FakeAsyncClient
from wrr.engines import github as gh
from wrr.schemas import SearchOptions
from wrr import config


def run(coro):
    return asyncio.run(coro)


# ── maintenance 维 ──────────────────────────────────────────────────
def test_maintenance_dimension():
    assert gh.maintenance(0, 1000) == 1.0                 # 无 open issues → 满分
    assert gh.maintenance(100, 1000) == 0.0               # 10% → 被忽视，趋近 0
    assert 0.0 < gh.maintenance(50, 1000) < 1.0           # 5% → 中间
    assert gh.maintenance(5, 0) == 0.0                    # 无 star 但有 issue


def test_score_v5_weights_and_maintenance_effect():
    assert config.GITHUB_SCORE_WEIGHTS_V5 == (0.30, 0.30, 0.20, 0.20)
    assert abs(gh.score_v5(1, 1, 1, 1) - 1.0) < 1e-9
    assert abs(gh.score_v5(0, 0, 0, 1) - 0.20) < 1e-9     # maintenance 权重 0.20
    # 同活跃/人气/新鲜下，被忽视项分更低
    assert gh.score_v5(0.5, 0.5, 0.5, 1.0) > gh.score_v5(0.5, 0.5, 0.5, 0.0)


# ── issue_search ────────────────────────────────────────────────────
def _reset(data):
    FakeAsyncClient.captured = []
    FakeAsyncClient.response_data = data
    FakeAsyncClient.response_text = ""


def test_issue_search_maps_quality_signals():
    _reset({"items": [
        {"title": "memory leak", "html_url": "https://github.com/o/r/issues/1",
         "body": "leaks on shutdown", "comments": 12,
         "reactions": {"+1": 30}, "state": "closed", "state_reason": "completed",
         "pull_request": {"url": "x"}},
    ]})
    gh.httpx.AsyncClient = FakeAsyncClient
    os.environ["GITHUB_TOKEN"] = "tkn"
    out = run(gh.GitHubEngine().issue_search(SearchOptions("leak", count=5)))
    assert out[0].title == "memory leak"
    assert out[0].source_tag == "github-issue"
    assert "👍30" in out[0].snippet and "💬12" in out[0].snippet
    assert "✅completed" in out[0].snippet and "·PR" in out[0].snippet
    # sort:interactions 注入 query
    assert "sort:interactions" in FakeAsyncClient.captured[0]["params"]["q"]


# ── GraphQL 批量活跃度（消 N+1）─────────────────────────────────────
def test_fetch_activity_graphql_batch():
    class FakeGQL:
        calls = 0
        async def graphql(self, query, variables):
            FakeGQL.calls += 1
            # 一次返回两仓库的 history.totalCount
            return {
                "r0": {"nameWithOwner": "o/a",
                       "defaultBranchRef": {"target": {"history": {"totalCount": 42}}}},
                "r1": {"nameWithOwner": "o/b",
                       "defaultBranchRef": {"target": {"history": {"totalCount": 7}}}},
            }
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    eng = gh.GitHubEngine()
    res = run(eng.fetch_activity_graphql(FakeGQL(), ["o/a", "o/b"], since))
    assert res == {"o/a": 42, "o/b": 7}
    assert FakeGQL.calls == 1                              # 一次调用取两仓库（无 N+1）
