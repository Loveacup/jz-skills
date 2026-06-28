"""Community 集成测试 — 真实 opencli 调用。

默认跳过（重型/依赖浏览器扩展 + 网络）；设 WRR_LIVE=1 显式启用：
    WRR_LIVE=1 pytest tests/integration/test_community_live.py -v -s
需 opencli 浏览器桥已连接（opencli doctor → Extension: connected）。
"""
import os
import pytest

from wrr.engines.community import CommunityEngine
from wrr.schemas import SearchOptions


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("WRR_LIVE"), reason="set WRR_LIVE=1 to run live community test")
async def test_community_reddit_live():
    engine = CommunityEngine()
    # site:reddit.com → 仅走 reddit（opencli），避免重型 last30days
    results = await engine.search(SearchOptions(query="python site:reddit.com", count=5))
    assert len(results) > 0
    r = results[0]
    assert r.url.startswith("http")
    assert r.source_tag == "reddit"
    assert r.title
    print(f"Got {len(results)} community results; top=[{r.source_tag}] {r.title}")
