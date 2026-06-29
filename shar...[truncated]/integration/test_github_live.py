"""GitHub 集成测试 — 需要 GITHUB_TOKEN。无 token 自动跳过。"""
import os
import pytest

from wrr.engines.github import GitHubEngine
from wrr.schemas import SearchOptions


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set")
async def test_github_search_live():
    engine = GitHubEngine()
    results = await engine.search(SearchOptions(query="asyncio", count=5))
    assert len(results) > 0
    assert results[0].url.startswith("https://github.com/")
    # snippet 带评分注解
    assert "score=" in results[0].snippet
    print(f"Got {len(results)} GitHub repos; top={results[0].title}")


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set")
async def test_github_scored_descending():
    """返回结果应按综合评分降序（snippet 内 score= 单调不增）。"""
    engine = GitHubEngine()
    results = await engine.search(SearchOptions(query="machine learning", count=8))
    scores = []
    for r in results:
        # snippet 末尾形如 "... · score=0.873"
        tail = r.snippet.rsplit("score=", 1)
        scores.append(float(tail[1]) if len(tail) == 2 else 0.0)
    assert scores == sorted(scores, reverse=True), scores
